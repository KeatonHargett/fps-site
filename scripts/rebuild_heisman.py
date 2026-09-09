#!/usr/bin/env python3
"""Rebuild every Heisman number on the site from heisman_winners.json.

heisman_winners.json is the single source of truth: one entry per award,
1935 to present. Before this script existed the same counts were hand-typed
into four separate places, and they had drifted apart from each other and
from the actual record - 19 of 136 programs were wrong, in both directions
(three programs that have never had a winner were credited with one).

This script derives every copy from the canonical list:

  program_stats.json    heismanWinners + ranks.heismanWinners (136 teams).
                        The live source for compare, team, rank and
                        conference. Ranks are standard competition ranks
                        (1,1,1,1,5,...), which is what the file already used.
  heisman.html          the HEISMAN_BY_TEAM array behind /heisman, rewritten
                        between sentinel comments.
  compare/team/rank     the legacy TEAM_STATS fallback tables, which only
                        render if program_stats.json fails to load. Only the
                        heismans / heismansRank fields are touched.
  rankings.html         cats[8] of each RANKINGS row. avg and rank are NOT
                        recomputed - that composite predates program_stats
                        and is not reproducible from cats, so it is left
                        alone deliberately. See the note above that array.

Two invariants this script exists to enforce:
  - every fbs:true winner's team must be a key in program_stats.json, so a
    naming drift ("Miami (FL)" vs "Miami") is a hard error, not a silent
    mismatch;
  - byte-identical output is never rewritten, so a no-op run does not bump
    mtimes and skew the lastmod dates in generate_sitemap.py.

To add next year's winner: append one entry to heisman_winners.json, bump
_meta.lastYear, then run this. Nothing else needs editing.

Run from the repo root:
    python scripts/rebuild_heisman.py             rewrite every derived copy
    python scripts/rebuild_heisman.py --check     exit 1 if anything drifted
    python scripts/rebuild_heisman.py --dry-run   print the change table only
"""
import io, json, os, re, sys
from collections import Counter

ROOT = os.environ.get("FPS_REPO_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OPEN_MARK = "  /* >>> GENERATED heisman - scripts/rebuild_heisman.py - do not hand-edit."
CLOSE_MARK = "  /* <<< END GENERATED heisman */"

LEGACY_FILES = ["compare.html", "team.html", "rank.html"]
LEGACY_ROW = re.compile(r"^(\s*)'([^']+)':(\s*)\{(.*heismans:)(\d+)(,\s*heismansRank:)(\d+)(.*)$")
RANKINGS_RE = re.compile(r"(const RANKINGS = )(\[.*?\])(;)", re.S)
HEISMAN_CAT = 8


# ------------------------------------------------------------------ file I/O
def read(name):
    """Read preserving line endings. The HTML files in this repo are CRLF;
    universal-newline mode would silently rewrite every one of them to LF."""
    with io.open(os.path.join(ROOT, name), encoding="utf-8", newline="") as f:
        return f.read()


def newline_of(text):
    return "\r\n" if "\r\n" in text else "\n"


def emit(name, text, plan):
    """Queue a write. Byte-identical content is skipped so mtimes stay put."""
    if text != read(name):
        plan[name] = text


def flush(plan):
    for name, text in plan.items():
        with io.open(os.path.join(ROOT, name), "w", encoding="utf-8", newline="") as f:
            f.write(text)


# ------------------------------------------------------------------ the data
def competition_ranks(values):
    """Standard competition rank: 1,1,1,1,5,... Highest value ranks first."""
    rank_of, seen = {}, 0
    for v in sorted(set(values), reverse=True):
        rank_of[v] = seen + 1
        seen += sum(1 for x in values if x == v)
    return rank_of


def load_winners(teams):
    doc = json.loads(read("heisman_winners.json"))
    winners = doc["winners"]
    years = [w["year"] for w in winners]

    if len(set(years)) != len(years):
        sys.exit("heisman_winners.json: duplicate year")
    if years != list(range(years[0], years[-1] + 1)):
        sys.exit("heisman_winners.json: years must be contiguous and ascending")
    meta = doc["_meta"]
    if (meta["firstYear"], meta["lastYear"]) != (years[0], years[-1]):
        sys.exit("heisman_winners.json: _meta year range does not match the winners list")

    counts = Counter(w["team"] for w in winners if w["fbs"])
    unknown = sorted(set(counts) - set(teams))
    if unknown:
        sys.exit("heisman_winners.json: fbs:true team not found in program_stats.json: %s\n"
                 "  (team must be the exact program_stats key, e.g. 'Miami' not 'Miami (FL)')"
                 % ", ".join(unknown))
    non_fbs = Counter(w["team"] for w in winners if not w["fbs"])
    return doc, counts, non_fbs, years


# --------------------------------------------------------------- program_stats
def build_program_stats(counts, rank_of, teams):
    """Set heismanWinners + ranks.heismanWinners, touching nothing else.

    json.dumps with no arguments round-trips this file byte for byte. Do not
    pass separators= or ensure_ascii=False: the file relies on the default
    ASCII escaping and one team key carries a non-ASCII character.
    """
    raw = read("program_stats.json")
    data = json.loads(raw)
    for t in teams:
        n = counts.get(t, 0)
        data[t]["heismanWinners"] = n
        data[t]["ranks"]["heismanWinners"] = rank_of[n]

    def stripped(doc):
        doc = json.loads(json.dumps(doc))
        for k, row in doc.items():
            if k != "_meta":
                row.pop("heismanWinners", None)
                row["ranks"].pop("heismanWinners", None)
        return doc

    if stripped(json.loads(raw)) != stripped(data):
        sys.exit("program_stats.json: a field outside heismanWinners changed - aborting")

    out = json.dumps(data)
    if json.loads(out) != data:
        sys.exit("program_stats.json: re-serialised file does not reparse - aborting")
    return out


# ---------------------------------------------------------------- heisman.html
def build_heisman_page(doc, counts, non_fbs):
    """Rewrite the HEISMAN_BY_TEAM block between the sentinel comments.

    Ranks on /heisman come from array position (the loop just below the
    array), so the order here is load-bearing: count desc, then team asc.
    fbs:false rows are flagged so the renderer can leave them unlinked -
    they have no team page to link to.
    """
    rows = Counter(counts)
    rows.update(non_fbs)
    ordered = sorted(rows.items(), key=lambda kv: (-kv[1], kv[0]))

    pad = max(len(t) for t, _ in ordered) + 3
    body = [OPEN_MARK,
            "     Every Heisman Trophy winner by program, %d-%d. Source of truth is"
            % (doc["_meta"]["firstYear"], doc["_meta"]["lastYear"]),
            "     heisman_winners.json, verified %s against:" % doc["_meta"]["verified"]]
    body += ["       %s" % s for s in doc["_meta"]["sources"]]
    body += ["     Schools marked fbs:false no longer play FBS football and have no",
             "     team page, so the renderer leaves those rows unlinked. */",
             "  const HEISMAN_BY_TEAM = ["]
    for i, (team, n) in enumerate(ordered):
        flag = "" if team in counts else ", fbs: false"
        comma = "," if i < len(ordered) - 1 else ""
        body.append("    { team: %-*s count: %d%s }%s" % (pad, '"%s",' % team, n, flag, comma))
    body += ["  ];", CLOSE_MARK]

    src = read("heisman.html")
    nl = newline_of(src)
    block = nl.join(body)

    if OPEN_MARK in src and CLOSE_MARK in src:
        if src.count(OPEN_MARK) != 1 or src.count(CLOSE_MARK) != 1:
            sys.exit("heisman.html: expected exactly one sentinel pair")
        a, b = src.index(OPEN_MARK), src.index(CLOSE_MARK) + len(CLOSE_MARK)
        if a > b:
            sys.exit("heisman.html: sentinels are inverted")
        return src[:a] + block + src[b:], ordered
    # First run: swallow the hand-written comment + array and plant the sentinels.
    pattern = re.compile(r"  // Heisman Trophy winners by program.*?const HEISMAN_BY_TEAM = \[.*?\r?\n  \];", re.S)
    new, n = pattern.subn(lambda _: block, src, count=1)
    if n != 1:
        sys.exit("heisman.html: could not locate the HEISMAN_BY_TEAM block")
    return new, ordered


# ------------------------------------------------------- legacy TEAM_STATS x3
def build_legacy(name, counts, rank_of):
    """Update only heismans / heismansRank in the fallback tables.

    Splitting on \\n leaves the CRLF's \\r at the end of each line, captured by
    the trailing group and restored by the join - so line endings survive.
    """
    out, hits = [], 0
    for line in read(name).split("\n"):
        m = LEGACY_ROW.match(line)
        if m:
            team = m.group(2)
            n = counts.get(team, 0)
            line = "%s'%s':%s{%s%d%s%d%s" % (m.group(1), team, m.group(3), m.group(4),
                                             n, m.group(6), rank_of[n], m.group(8))
            hits += 1
        out.append(line)
    if not hits:
        sys.exit("%s: no legacy TEAM_STATS rows matched" % name)
    return "\n".join(out), hits


# -------------------------------------------------------------- rankings.html
def build_rankings(counts, rank_of):
    """Update cats[8] only. avg and rank are intentionally left as they are.

    The emitter below reproduces the existing literal byte for byte, so the
    only bytes that move are the ones assigned here.
    """
    src = read("rankings.html")
    m = RANKINGS_RE.search(src)
    if not m:
        sys.exit("rankings.html: could not locate const RANKINGS")
    rows = json.loads(m.group(2))
    changed = 0
    for r in rows:
        new = rank_of[counts.get(r["name"], 0)]
        if r["cats"][HEISMAN_CAT] != new:
            r["cats"][HEISMAN_CAT] = new
            changed += 1
    body = ",".join(
        '{"rank":%d,"name":%s,"display":%s,"avg":%s,"cats":[%s]}' % (
            r["rank"], json.dumps(r["name"]), json.dumps(r["display"]),
            json.dumps(r["avg"]), ", ".join(str(c) for c in r["cats"]))
        for r in rows)
    return src[:m.start(2)] + "[" + body + "]" + src[m.end(2):], len(rows), changed


# ----------------------------------------------------------------------- main
def main():
    args = sys.argv[1:]
    check = "--check" in args
    dry = "--dry-run" in args
    for a in args:
        if a not in ("--check", "--dry-run"):
            sys.exit("unknown option: %s" % a)

    teams = [k for k in json.loads(read("program_stats.json")) if k != "_meta"]
    doc, counts, non_fbs, years = load_winners(teams)
    rank_of = competition_ranks([counts.get(t, 0) for t in teams])

    before = json.loads(read("program_stats.json"))
    plan = {}
    emit("program_stats.json", build_program_stats(counts, rank_of, teams), plan)
    page, ordered = build_heisman_page(doc, counts, non_fbs)
    emit("heisman.html", page, plan)
    legacy = {}
    for name in LEGACY_FILES:
        text, hits = build_legacy(name, counts, rank_of)
        legacy[name] = hits
        emit(name, text, plan)
    rankings, n_rows, n_changed = build_rankings(counts, rank_of)
    emit("rankings.html", rankings, plan)

    moved = [(t, before[t]["heismanWinners"], counts.get(t, 0),
              before[t]["ranks"]["heismanWinners"], rank_of[counts.get(t, 0)])
             for t in teams]
    cnt_moved = [m for m in moved if m[1] != m[2]]
    rank_moved = [m for m in moved if m[3] != m[4]]

    print("==> heisman_winners.json")
    print("    %d awards, %d-%d; %d to FBS programs, %d to schools no longer in FBS (%s)"
          % (len(years), years[0], years[-1], sum(counts.values()), sum(non_fbs.values()),
             ", ".join("%s %d" % kv for kv in sorted(non_fbs.items()))))
    print("==> program_stats.json")
    for t, c0, c1, r0, r1 in sorted(cnt_moved, key=lambda m: (-m[2], m[0])):
        print("    %-16s %d -> %d   rank %d -> %d" % (t, c0, c1, r0, r1))
    print("    %d of %d rows change (%d counts, %d ranks)"
          % (len({m[0] for m in cnt_moved + rank_moved}), len(teams), len(cnt_moved), len(rank_moved)))
    print("    totals: %d winners across %d programs; %d programs at 0 (rank %d)"
          % (sum(counts.values()), len(counts),
             sum(1 for t in teams if counts.get(t, 0) == 0), rank_of[0]))
    print("    count -> rank: %s"
          % ", ".join("%d->%d" % (c, rank_of[c]) for c in sorted(rank_of, reverse=True)))
    print("==> heisman.html")
    print("    %d rows (%d FBS + %d non-FBS), %d winners listed"
          % (len(ordered), len(counts), len(ordered) - len(counts), sum(n for _, n in ordered)))
    print("==> legacy TEAM_STATS (fallback only)")
    print("    " + ", ".join("%s %d rows" % kv for kv in legacy.items()))
    print("==> rankings.html")
    print("    cats[%d] updated on %d of %d rows; avg and rank left as-is"
          % (HEISMAN_CAT, n_changed, n_rows))

    if check:
        if plan:
            print("\nDRIFT: %s differ from heisman_winners.json. Run without --check."
                  % ", ".join(sorted(plan)))
            return 1
        print("\nup to date - every derived copy matches heisman_winners.json")
        return 0
    if dry:
        print("\ndry run - would rewrite: %s" % (", ".join(sorted(plan)) or "nothing"))
        return 0
    flush(plan)
    print("\nwrote: %s" % (", ".join(sorted(plan)) or "nothing (already up to date)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

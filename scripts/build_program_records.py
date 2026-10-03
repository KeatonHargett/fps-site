#!/usr/bin/env python3
"""
build_program_records.py - all-time W/L/T for every program, built from pinned sources.

Replaces the record fields of program_stats.json (which were a frozen, unreproducible
snapshot) with a build anyone can re-run and get byte-identical output:

  official  = NCAA official record through 2024 (Wikipedia "NCAA Division I FBS football
              win-loss records", revision 1271870786, pinned - the NCAA's own table, FCS /
              lower-division years included), or a sourced baselineOverride
            + CollegeFootballData /records for every season after the baseline
              (finished seasons frozen in data/sources/records/cfbd/, the current season
              refreshed every Tuesday)
            - NCAA rulings the baseline does not contain yet (record_adjustments.json)
  onField   = official with every vacated W/L/T added back and every NCAA-ordered forfeit
              reversed for both the penalized team and its opponent

Inputs (data/sources/records/, every entry sourced):
  wiki_fbs_wl_rev1271870786.json  raw wikitext of the pinned revision (re-parsed here)
  ncaa_records_book_2026.json     NCAA 2026 FBS Records Book p.110 / p.111 - cross-check only
  cfbd/records_<season>.json      CFBD season records (our 136 programs)
  record_adjustments.json         vacated wins, forfeits, overrides, decisions, title fixes

Outputs (only these keys change; anything else changing aborts the build):
  program_stats.json  record, winPct, recordOnField, winPctOnField, recordAdjust, recordAsOf,
                      ranks.wins, ranks.winPct, plus the fields named in fieldCorrections
                      and their ranks
  rankings.html       cats[0] (Win %) and cats[5] (Wins) of the RANKINGS literal
  data/sources/records/build_manifest.json  input hashes + per-team totals (drop guard)

Checks (any failure exits non-zero and writes nothing):
  - built official totals through 2025 == NCAA Records Book p.110 (documented exceptions only)
  - built 2019-25 on-field minus vacated == Records Book p.111 table (documented exceptions only)
  - no program's wins or games total may drop unless an adjustment/baseline input changed
  - no field outside the allowed set changes

Usage:
  python scripts/build_program_records.py                  build and write (offline)
  python scripts/build_program_records.py --check          rebuild in memory, exit 1 on any byte difference
  python scripts/build_program_records.py --fetch-current  refresh CFBD current season (CFBD_API_KEY), then build
  python scripts/build_program_records.py --verify-source  re-fetch the pinned Wikipedia revision and compare its hash
front_porch_games.json is never read or written.
"""
import datetime as dt
import hashlib
import io
import json
import os
import re
import sys

ROOT = os.environ.get("FPS_REPO_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join("data", "sources", "records")
ADJ_FILE = os.path.join(SRC, "record_adjustments.json")
BOOK_FILE = os.path.join(SRC, "ncaa_records_book_2026.json")
MANIFEST = os.path.join(SRC, "build_manifest.json")
CFBD_DIR = os.path.join(SRC, "cfbd")
RANKINGS_RE = re.compile(r"(const RANKINGS = )(\[.*?\])(;)", re.S)
WINPCT_CAT, WINS_CAT = 0, 5
BOOK_SEASON = 2025
WIKI_ROW = re.compile(r'!\s*scope="row"\s*\|\s*(.+?)\n\|\s*([\d,]+)\s*\|\|\s*([\d,]+)\s*\|\|\s*([\d,]+)\s*\|\|')


# ------------------------------------------------------------------ file I/O
def path(name):
    return os.path.join(ROOT, name)


def read(name):
    """Read preserving line endings (the HTML files are CRLF)."""
    with io.open(path(name), encoding="utf-8", newline="") as f:
        return f.read()


def load(name):
    return json.loads(read(name))


def sha256(name):
    with open(path(name), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def die(msg):
    sys.exit("build_program_records: " + msg)


# ------------------------------------------------------------------ sources
def wiki_rows(doc):
    wt = doc["wikitext"]
    if hashlib.sha256(wt.encode("utf-8")).hexdigest() != doc["wikitextSha256"]:
        die("pinned Wikipedia snapshot does not match its recorded sha256")
    rows = {}
    for m in WIKI_ROW.finditer(wt):
        link = re.search(r"\[\[([^|\]]+)\|?([^\]]*)\]\]", m.group(1))
        name = (link.group(2) or link.group(1)) if link else m.group(1)
        name = re.sub(r"<ref.*", "", name).strip()
        rows[name] = [int(m.group(i).replace(",", "")) for i in (2, 3, 4)]
    return rows


def wiki_name(team, name_map):
    if team in name_map:
        return name_map[team]
    return team[:-4] + " State" if team.endswith(" St.") else team


def cfbd_seasons():
    out = {}
    for fn in sorted(os.listdir(path(CFBD_DIR))):
        m = re.fullmatch(r"records_(\d{4})\.json", fn)
        if m:
            out[int(m.group(1))] = load(os.path.join(CFBD_DIR, fn))
    return out


def pct(r):
    """(W + T/2) / G to 4 places, rounded half up with exact integer arithmetic so the
    pages (Math.round) and this build never disagree on a .xxxx5 boundary."""
    g = r[0] + r[1] + r[2]
    if not g:
        return 0.0
    num, den = (2 * r[0] + r[2]) * 10000, 2 * g
    return (2 * num + den) // (2 * den) / 10000


def competition_ranks(values):
    """Standard competition rank: 1,2,2,4 - the convention program_stats.json uses."""
    rank_of, seen = {}, 0
    for v in sorted(set(values), reverse=True):
        rank_of[v] = seen + 1
        seen += sum(1 for x in values if x == v)
    return rank_of


# ------------------------------------------------------------------ the build
def compute(teams, adj, wiki, seasons, cap=None):
    """Official and on-field [W, L, T] per team, optionally only through season `cap`."""
    base_through = adj["baseline"]["throughSeason"]
    overrides = {o["team"]: o for o in adj["baselineOverrides"]}
    off, onf, base_info = {}, {}, {}
    for t in teams:
        if t in overrides:
            o = overrides[t]
            rec, through = list(o["record"]), o["throughSeason"]
            base_info[t] = "override"
        else:
            w = wiki.get(wiki_name(t, adj["nameMap"]))
            if w is None:
                die("%s: no row in the pinned Wikipedia revision and no baselineOverride" % t)
            rec, through = list(w), base_through
            base_info[t] = "wikipedia"
        if cap is not None and through > cap:
            die("%s: baseline runs past the check season %d" % (t, cap))
        for y, doc in sorted(seasons.items()):
            if y <= through or (cap is not None and y > cap):
                continue
            r = doc["records"].get(t)
            if r:
                rec = [rec[i] + r[i] for i in range(3)]
        off[t] = (rec, through)
    # official: apply rulings the baseline does not contain (and anything in a season after it)
    def pending(e, t):
        through = off[t][1]
        return (not e["inBaseline"] or e["season"] > through) and (cap is None or e["season"] <= cap)
    official = {t: list(off[t][0]) for t in teams}
    for e in adj["vacated"]:
        t = e["team"]
        if t in official and pending(e, t):
            official[t][0] -= e["wins"]; official[t][1] -= e["losses"]; official[t][2] -= e["ties"]
    for e in adj["forfeits"]:
        if e["team"] not in official:
            continue
        for g in e["games"]:
            if not pending(e, e["team"]):
                continue
            _forfeit(official, e["team"], g, +1)
    # on-field: reverse every vacated / forfeit entry
    for t in teams:
        onf[t] = list(official[t])
    for e in adj["vacated"]:
        if e["team"] in onf and (cap is None or e["season"] <= cap):
            r = onf[e["team"]]; r[0] += e["wins"]; r[1] += e["losses"]; r[2] += e["ties"]
    for e in adj["forfeits"]:
        if cap is not None and e["season"] > cap:
            continue
        for g in e["games"]:
            _forfeit(onf, e["team"], g, -1)
    return official, onf, base_info


def adjust_counts(teams, adj):
    """Wins behind the official / on-field difference, for the pages' footnotes:
    vacated (wins removed), forfeited (on-field wins the NCAA turned into losses),
    awarded (on-field losses/ties the NCAA turned into wins for this team)."""
    out = {t: {"vacated": 0, "forfeited": 0, "awarded": 0} for t in teams}
    for e in adj["vacated"]:
        if e["team"] in out:
            out[e["team"]]["vacated"] += e["wins"]
    for e in adj["forfeits"]:
        for g in e["games"]:
            if e["team"] in out and g["onField"] == "W":
                out[e["team"]]["forfeited"] += 1
            if g["opponent"] in out:
                out[g["opponent"]]["awarded"] += 1
    return out


def _forfeit(recs, team, game, sign):
    """sign=+1 applies an NCAA forfeit to on-field results; sign=-1 reverses it."""
    res = game["onField"]  # penalized team's on-field result: W or T
    if team in recs:
        r = recs[team]
        r[0 if res == "W" else 2] -= sign
        r[1] += sign
    opp = game["opponent"]
    if opp in recs:
        r = recs[opp]
        r[1 if res == "W" else 2] -= sign
        r[0] += sign


def cross_check(teams, adj, wiki, seasons, book):
    errors = []
    exc = adj["bookExceptions"]
    official25, _, _ = compute(teams, adj, wiki, seasons, cap=BOOK_SEASON)
    for t, row in book["allTime"]["rows"].items():
        got, want = official25[t], row["record"]
        if got == want:
            continue
        e = exc.get(t, {}).get("allTime")
        if e and e["book"] == want and e["built"] == got:
            continue
        errors.append("Records Book p.110 %s: built %s, book %s" % (t, got, want))
    for t, want in book["seasons2019to2025"]["rows"].items():
        w = l = 0
        for y in range(2019, 2026):
            r = seasons[y]["records"].get(t)
            if r:
                w += r[0]; l += r[1]
        for e in adj["vacated"]:
            if e["team"] == t and 2019 <= e["season"] <= 2025:
                w -= e["wins"]; l -= e["losses"]
        got = [w, l]
        if got == want:
            continue
        e = exc.get(t, {}).get("seasons2019to2025")
        if e and e["book"] == want and e["built"] == got:
            continue
        errors.append("Records Book p.111 %s 2019-25: built %s, book %s" % (t, got, want))
    # an exception that no longer applies must be removed, so drift cannot hide behind it
    for t, e in exc.items():
        if "allTime" in e and official25.get(t) == e["allTime"]["book"]:
            errors.append("bookExceptions[%s] is stale: build now matches the Records Book" % t)
    return errors


def build(check_only=False):
    raw_stats = read("program_stats.json")
    data = json.loads(raw_stats)
    teams = [k for k in data if k != "_meta"]
    adj = load(ADJ_FILE)
    book = load(BOOK_FILE)
    wiki = wiki_rows(load(os.path.join(SRC, adj["baseline"]["file"])))
    seasons = cfbd_seasons()
    if not seasons:
        die("no CFBD season files in %s" % CFBD_DIR)

    errors = cross_check(teams, adj, wiki, seasons, book)
    official, onfield, base_info = compute(teams, adj, wiki, seasons)
    for t in teams:
        for label, r in (("official", official[t]), ("on-field", onfield[t])):
            if min(r) < 0:
                errors.append("%s %s record went negative: %s" % (t, label, r))

    last = max(seasons)
    # date = last completed game (America/Chicago), recorded by --fetch-current
    as_of = {"season": last, "inProgress": not seasons[last]["final"],
             "date": seasons[last].get("lastGame") or seasons[last]["fetched"]}

    # --- program_stats.json
    counts = adjust_counts(teams, adj)
    for t in teams:
        c = counts[t]
        if onfield[t][0] - official[t][0] != c["vacated"] + c["forfeited"] - c["awarded"]:
            errors.append("%s: on-field minus official wins (%d) does not equal the adjustment counts %s"
                          % (t, onfield[t][0] - official[t][0], c))
    win_rank = competition_ranks([official[t][0] for t in teams])
    pct_rank = competition_ranks([pct(official[t]) for t in teams])
    out = {}
    for k, row in data.items():
        if k == "_meta":
            out[k] = row
            continue
        new = {"record": {"wins": official[k][0], "losses": official[k][1], "ties": official[k][2]},
               "winPct": pct(official[k]),
               "recordOnField": {"wins": onfield[k][0], "losses": onfield[k][1], "ties": onfield[k][2]},
               "winPctOnField": pct(onfield[k]),
               "recordAdjust": dict(counts[k]),
               "recordAsOf": dict(as_of)}
        for f, v in row.items():
            if f not in new:
                new[f] = v
        new["ranks"] = dict(row["ranks"])
        new["ranks"]["wins"] = win_rank[official[k][0]]
        new["ranks"]["winPct"] = pct_rank[pct(official[k])]
        out[k] = new
    corrected = set()
    for c in adj["fieldCorrections"]:
        if c["team"] not in out or c["field"] not in out[c["team"]]:
            errors.append("fieldCorrections: unknown %s.%s" % (c["team"], c["field"]))
            continue
        out[c["team"]][c["field"]] = c["value"]
        corrected.add(c["field"])
    for f in sorted(corrected):
        rk = competition_ranks([out[t][f] for t in teams])
        for t in teams:
            out[t]["ranks"][f] = rk[out[t][f]]

    allowed = {"record", "winPct", "recordOnField", "winPctOnField", "recordAdjust", "recordAsOf"} | corrected
    allowed_ranks = {"wins", "winPct"} | corrected

    def stripped(doc):
        doc = json.loads(json.dumps(doc))
        for k, row in doc.items():
            if k == "_meta":
                continue
            for f in allowed:
                row.pop(f, None)
            for f in allowed_ranks:
                row["ranks"].pop(f, None)
        return doc

    if stripped(data) != stripped(out):
        errors.append("program_stats.json: a field outside the record/allowed set would change")
    stats_text = json.dumps(out)
    if json.loads(stats_text) != out:
        errors.append("program_stats.json: re-serialised output does not reparse")

    # --- rankings.html (cats[0] Win %, cats[5] Wins)
    src = read("rankings.html")
    m = RANKINGS_RE.search(src)
    if not m:
        die("rankings.html: could not locate const RANKINGS")
    rows = json.loads(m.group(2))
    for r in rows:
        if r["name"] not in out:
            errors.append("rankings.html: unknown team %s" % r["name"])
            continue
        r["cats"][WINPCT_CAT] = out[r["name"]]["ranks"]["winPct"]
        r["cats"][WINS_CAT] = out[r["name"]]["ranks"]["wins"]
    body = ",".join(
        '{"rank":%d,"name":%s,"display":%s,"avg":%s,"cats":[%s]}' % (
            r["rank"], json.dumps(r["name"]), json.dumps(r["display"]),
            json.dumps(r["avg"]), ", ".join(str(c) for c in r["cats"]))
        for r in rows)
    rankings_text = src[:m.start(2)] + "[" + body + "]" + src[m.end(2):]

    # --- manifest + drop guard
    inputs = {}
    for name in [ADJ_FILE, BOOK_FILE, os.path.join(SRC, adj["baseline"]["file"])] + \
            [os.path.join(CFBD_DIR, "records_%d.json" % y) for y in sorted(seasons)]:
        inputs[name.replace(os.sep, "/")] = sha256(name)
    manifest = {"_doc": "Written by scripts/build_program_records.py - do not hand-edit.",
                "inputs": inputs,
                "teams": {t: {"official": official[t], "onField": onfield[t], "baseline": base_info[t]} for t in teams}}
    manifest_text = json.dumps(manifest, indent=1, ensure_ascii=False) + "\n"
    if os.path.exists(path(MANIFEST)):
        prev = load(MANIFEST)
        key_inputs = [ADJ_FILE.replace(os.sep, "/"), os.path.join(SRC, adj["baseline"]["file"]).replace(os.sep, "/")]
        sources_changed = any(prev["inputs"].get(k) != inputs[k] for k in key_inputs)
        for t in teams:
            p = prev["teams"].get(t)
            if not p:
                continue
            for label, now in (("official", official[t]), ("onField", onfield[t])):
                before = p[label]
                if (now[0] < before[0] or sum(now) < sum(before)) and not sources_changed:
                    errors.append("%s %s dropped %s -> %s without a change to record_adjustments.json or the baseline"
                                  % (t, label, before, now))

    if errors:
        print("\n".join("  FAIL " + e for e in errors), file=sys.stderr)
        die("%d check(s) failed - nothing written" % len(errors))

    targets = {"program_stats.json": stats_text, "rankings.html": rankings_text, MANIFEST: manifest_text}
    diff = [n for n, txt in targets.items() if not os.path.exists(path(n)) or read(n) != txt]
    if check_only:
        if diff:
            die("build is not reproducible - committed files differ from a fresh build: %s" % ", ".join(diff))
        print("build_program_records: OK - %d programs, Records Book cross-check passed, committed files are byte-identical"
              % len(teams))
        return
    for n in diff:
        with io.open(path(n), "w", encoding="utf-8", newline="") as f:
            f.write(targets[n])
    print("build_program_records: %d programs, through %d%s; wrote %s" % (
        len(teams), last, " (in progress)" if as_of["inProgress"] else "", ", ".join(diff) or "nothing (unchanged)"))


# ------------------------------------------------------------------ network modes
def chicago_date(utc_iso):
    """CFBD kickoff (UTC ISO 8601) -> calendar date in America/Chicago.

    US Central: CDT (UTC-5) from 2:00 local on the second Sunday of March to 2:00 local
    on the first Sunday of November, CST (UTC-6) otherwise. Done by hand so the build needs
    no tz database (Windows Python ships without one). A Saturday-night kickoff at
    01:30Z on Sunday is still Saturday in Chicago - the date the label must show."""
    t = dt.datetime.strptime(utc_iso[:19], "%Y-%m-%dT%H:%M:%S")

    def nth_sunday(year, month, n):
        d = dt.datetime(year, month, 1)
        return d + dt.timedelta(days=(6 - d.weekday()) % 7 + 7 * (n - 1))
    dst_start = nth_sunday(t.year, 3, 2) + dt.timedelta(hours=8)   # 02:00 CST = 08:00Z
    dst_end = nth_sunday(t.year, 11, 1) + dt.timedelta(hours=7)    # 02:00 CDT = 07:00Z
    offset = 5 if dst_start <= t < dst_end else 6
    return (t - dt.timedelta(hours=offset)).strftime("%Y-%m-%d")


def fetch_current():
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    from refresh_games import current_season, normalize
    from build_game_sites import load_key
    from backfill_season_type import api_get
    key = load_key()
    if not key:
        die("CFBD_API_KEY not set - cannot refresh the current season")
    import unicodedata

    def fold(name):
        # normalize() keeps the accent for CFBD's "San José State" but drops it for our
        # "San José St.", so compare accent-folded keys on both sides.
        n = normalize(name)
        return unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode("ascii")
    teams = [k for k in load("program_stats.json") if k != "_meta"]
    key_of = {fold(t): t for t in teams}
    season = current_season()
    todo = [season] + [y for y, d in cfbd_seasons().items() if y < season and not d["final"]]
    for y in sorted(set(todo)):
        rows = api_get("/records", {"year": y}, key)
        if not rows:
            die("CFBD /records %d returned nothing - season file left unchanged" % y)
        recs = {}
        for r in rows:
            t = key_of.get(fold(r.get("team", "")))
            if t:
                tot = r["total"]
                recs[t] = [tot["wins"], tot["losses"], tot["ties"]]
        # Every program must be present: a program silently missing from the file would
        # lose its season (2020 is the one season two programs genuinely did not play).
        prev_path = path(os.path.join(CFBD_DIR, "records_%d.json" % y))
        prev = load(os.path.join(CFBD_DIR, "records_%d.json" % y))["records"] if os.path.exists(prev_path) else {}
        lost = sorted(set(prev) - set(recs))
        if lost or len(recs) < len(teams) - 5:
            die("CFBD /records %d covered %d of %d programs (missing vs committed file: %s) - season file left unchanged"
                % (y, len(recs), len(teams), ", ".join(lost) or "-"))
        # Date of the last completed game involving one of our programs, in America/Chicago:
        # this is what the pages' "Records through games of ..." label shows.
        kickoffs = []
        for st in ("regular", "postseason"):
            games = api_get("/games", {"year": y, "seasonType": st}, key)
            if games is None:
                die("CFBD /games %d %s failed - season file left unchanged" % (y, st))
            for g in games:
                if g.get("completed") and g.get("startDate") and \
                        (fold(g.get("homeTeam", "")) in key_of or fold(g.get("awayTeam", "")) in key_of):
                    kickoffs.append(g["startDate"])
        last_kick = max(kickoffs) if kickoffs else None
        doc = {"season": y, "source": "CollegeFootballData /records (total: all games incl. non-FBS opponents)",
               "fetched": dt.datetime.utcnow().strftime("%Y-%m-%d"), "final": y < season,
               "lastGame": chicago_date(last_kick) if last_kick else None,
               "lastGameKickoffUtc": last_kick,
               "records": dict(sorted(recs.items()))}
        with io.open(path(os.path.join(CFBD_DIR, "records_%d.json" % y)), "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
        print("CFBD /records %d: %d programs%s" % (y, len(recs), "" if y == season else " (now final)"))


def verify_source():
    import requests
    adj = load(ADJ_FILE)
    doc = load(os.path.join(SRC, adj["baseline"]["file"]))
    r = requests.get(doc["api"], timeout=60, headers={
        "User-Agent": "FrontPorchSportsRecords/1.0 (https://frontporchsports.com; scripts/build_program_records.py)"})
    r.raise_for_status()
    wt = r.json()["query"]["pages"][0]["revisions"][0]["slots"]["main"]["content"]
    got = hashlib.sha256(wt.encode("utf-8")).hexdigest()
    if got != doc["wikitextSha256"]:
        die("pinned revision %s no longer matches the committed snapshot" % doc["revid"])
    print("Wikipedia revision %s matches the committed snapshot (%s)" % (doc["revid"], got[:12]))


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--verify-source" in args:
        verify_source()
    else:
        if "--fetch-current" in args:
            fetch_current()
        build(check_only="--check" in args)

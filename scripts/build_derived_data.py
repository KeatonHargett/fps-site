"""
Front Porch Sports - build data/derived/: small, content-hashed files generated from
front_porch_games.json so pages stop downloading the full 17 MB dataset.

front_porch_games.json is READ ONLY here. Every derived file is regenerated from it
(plus game_sites.json / game_venues.json / coaches_data.json for the per-game location
and head-coach fields) on every run; nothing in data/derived/ is ever edited by hand.

Output (all under data/derived/):
  manifest.json                  short-cached entry point: team names, slugs, the current
                                 hashed file name of every file below, gameCount, maxSeason
  teams_index.<hash>.json        shared lookup: [{id, name, slug, abbr, conf, games}]
  league.<hash>.json             league-wide aggregates the pages used to compute in the
                                 browser over every game (rank.html, team.html, compare.html)
  home.<hash>.json               index.html: hero counts + Blue Bloods series records
  teams/<slug>.<hash>.json       every game involving one team, columnar, plus that game's
                                 location, both head coaches and venue
  README.md                      what this is and how to rebuild it

Per-team file format (columnar; all arrays are aligned, one entry per game, in the order
the games appear in front_porch_games.json - "gi" is that global row index, so merging
two teams' files and sorting by gi reproduces the original order exactly):
  v, team, n
  gi            global row index in front_porch_games.json
  s             season
  d             game_date as int YYYYMMDD (0 = "")
  a, b          team_a / team_b as indices into manifest.names
  as, bs        team_a_score / team_b_score
  w             winner: 0 = tie (winner ""), 1 = team_a, 2 = team_b
  e, eras       era as an index into the file's eras list
  p             postseason: 0 = false, 1 = true, 2 = null
  est           rows whose date_estimated is true (row positions)
  c, cities     city as an index into the file's cities list
  st, states    state as an index into the file's states list
  gid           { row position: game_id } only where game_id is not the standard
                "<date8>_<team_a>_vs_<team_b>" (legacy names)
  site          one char per game: a = team_a home, b = team_b home, n = neutral, - = unknown
  ca, cb        head coach of team_a / team_b as indices into the file's coaches list (-1 unknown)
  vn, venues    venue as an index into the file's venues list (-1 unknown)
  margin = |as - bs| and total_points = as + bs are reconstructed (checked at build time).
  is_tie = (w == 0). The decoder (js/derived-data.js) rebuilds records identical to the
  original objects, field for field.

Content hashes: the first 10 hex chars of the SHA-256 of each file's bytes, so a file
name changes exactly when its content does (cached forever; the manifest is short-cached).
Stale hashed files from earlier builds are removed after the new set is written.

Safety: everything is written to a temporary directory first and swapped into place only
when the whole build succeeded, so a failed run leaves the previous data/derived/ intact.

Usage:
  python scripts/build_derived_data.py           # build (then: node scripts/parity_check.js)
  FPS_DRY_RUN=1 python scripts/build_derived_data.py
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import unicodedata
from collections import OrderedDict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_game_sites import decode_existing  # noqa: E402

REPO = Path(os.environ.get("FPS_REPO_ROOT", Path(__file__).resolve().parent.parent))
GAMES_FILE = REPO / "front_porch_games.json"
COACHES_FILE = REPO / "coaches_data.json"
FBS_FILE = REPO / "fbs_teams.json"
OUT_DIR = REPO / "data" / "derived"
HASH_LEN = 10
DERIVED_FORMAT = 1

# index.html's Blue Bloods cards (const BLUE_BLOODS). parity_check.js fails if the two
# lists ever drift apart.
BLUE_BLOODS = [["Texas", "Oklahoma"], ["Notre Dame", "USC"], ["Ohio St.", "Michigan"],
               ["Alabama", "Auburn"], ["Nebraska", "Oklahoma"]]

README = """# data/derived/ - GENERATED FILES, DO NOT EDIT BY HAND

Everything in this folder is produced by `scripts/build_derived_data.py` from
`front_porch_games.json` (read only), `game_sites.json`, `game_venues.json` and
`coaches_data.json`. Hand edits are overwritten on the next build.

Rebuild and verify:

    python scripts/build_derived_data.py
    node scripts/parity_check.js

The weekly GitHub Actions refresh runs both after the data refresh; if either fails,
nothing is committed or deployed and the previous files stay in place.

- `manifest.json` - entry point (short cache): team names/slugs and the current file
  name of every hashed file.
- `teams_index.<hash>.json` - shared team lookup.
- `league.<hash>.json` - league-wide aggregates (rank.html, team.html, compare.html).
- `home.<hash>.json` - index.html hero counts and Blue Bloods records.
- `teams/<slug>.<hash>.json` - every game involving one team, with location, coaches
  and venue. Format documented at the top of `scripts/build_derived_data.py` and decoded
  by `js/derived-data.js`.

Hashed files never change content under the same name, so they are cached for a year
(`immutable`). If any derived file fails to load, pages fall back to
`front_porch_games.json`.
"""


def slugify(name: str) -> str:
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-") or "team"


def fpskey(s: str) -> str:
    """compare.html's fpsKey(): accent-folded, trimmed, lower-case."""
    return "".join(c for c in unicodedata.normalize("NFKD", s or "") if not unicodedata.combining(c)).strip().lower()


def dumps(obj) -> bytes:
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def hashed(name: str, data: bytes) -> str:
    stem, ext = name.rsplit(".", 1)
    return f"{stem}.{hashlib.sha256(data).hexdigest()[:HASH_LEN]}.{ext}"


def coach_picker(doc):
    """Port of FPSMatchupFilter.annotateCoaches' pick() - keep the two identical."""
    teams, pinned, names = doc["teams"], doc.get("games", {}), doc["coaches"]

    def pick(team, g):
        pin = pinned.get(g["game_id"])
        if pin and pin.get(team) is not None:
            return names[pin[team]]
        spans = teams.get(team, {}).get(str(g["season"]))
        if not spans:
            return None
        if len(spans) == 1:
            return names[spans[0][0]]
        if not g["game_date"]:
            return None
        for s in spans:
            if len(s) < 3 or not s[2] or g["game_date"] <= s[2]:
                return names[s[0]]
        return names[spans[-1][0]]
    return pick


def main():
    dry = os.environ.get("FPS_DRY_RUN") == "1"
    raw = GAMES_FILE.read_bytes()
    source_sha = hashlib.sha256(raw).hexdigest()
    games = json.loads(raw.decode("utf-8"))
    n_games = len(games)

    # ---- shared team lookup (first-appearance order) -------------------------------
    names = list(OrderedDict.fromkeys(t for g in games for t in (g["team_a"], g["team_b"])))
    tix = {n: i for i, n in enumerate(names)}
    slugs, seen = [], {}
    for n in names:
        s = slugify(n)
        if s in seen:
            seen[s] += 1
            s = f"{s}-{seen[s]}"
        else:
            seen[s] = 1
        slugs.append(s)
    fbs = {}
    if FBS_FILE.exists():
        for t in json.loads(FBS_FILE.read_text(encoding="utf-8")).get("teams", []):
            fbs[fpskey(t.get("name", ""))] = t
    games_per_team = {n: 0 for n in names}
    for g in games:
        games_per_team[g["team_a"]] += 1
        if g["team_b"] != g["team_a"]:
            games_per_team[g["team_b"]] += 1

    # ---- per-game location / coaches / venue (same semantics as the live loaders) ------
    sites = decode_existing(games)          # game_id -> (code a/b/n, venue, source)
    coach_of = coach_picker(json.loads(COACHES_FILE.read_text(encoding="utf-8")))

    # ---- integrity checks the compact encoding relies on --------------------------------
    for g in games:
        if g["is_tie"] != (g["winner"] == ""):
            sys.exit(f"FATAL: is_tie/winner mismatch in {g['game_id']}")
        if not g["is_tie"] and g["winner"] not in (g["team_a"], g["team_b"]):
            sys.exit(f"FATAL: winner not a participant in {g['game_id']}")
        if g["margin"] != abs(g["team_a_score"] - g["team_b_score"]):
            sys.exit(f"FATAL: margin not |a-b| in {g['game_id']}")
        if g["total_points"] != g["team_a_score"] + g["team_b_score"]:
            sys.exit(f"FATAL: total_points not a+b in {g['game_id']}")
        if set(g) != {"game_id", "season", "game_date", "date_estimated", "era", "postseason", "team_a", "team_b",
                      "team_a_score", "team_b_score", "winner", "is_tie", "margin", "total_points", "city", "state"}:
            sys.exit(f"FATAL: unexpected fields in {g['game_id']}: {sorted(g)}")

    # ---- per-team files ------------------------------------------------------------------
    rows_by_team = {n: [] for n in names}
    for gi, g in enumerate(games):
        rows_by_team[g["team_a"]].append(gi)
        if g["team_b"] != g["team_a"]:   # the one Miami-vs-Miami row appears once
            rows_by_team[g["team_b"]].append(gi)

    def lookup():
        values, index = [], {}

        def ix(v):
            if v not in index:
                index[v] = len(values)
                values.append(v)
            return index[v]
        return values, ix

    files: dict[str, bytes] = {}
    team_files = {}
    for n, slug in zip(names, slugs):
        rows = rows_by_team[n]
        eras, era_ix = lookup()
        cities, city_ix = lookup()
        states, state_ix = lookup()
        coaches, coach_ix = lookup()
        venues, venue_ix = lookup()
        col = {k: [] for k in ("gi", "s", "d", "a", "b", "as", "bs", "w", "e", "p", "c", "st", "ca", "cb", "vn")}
        site_chars, est, gid = [], [], {}
        for pos, gi in enumerate(rows):
            g = games[gi]
            col["gi"].append(gi)
            col["s"].append(g["season"])
            col["d"].append(int(g["game_date"].replace("-", "")) if g["game_date"] else 0)
            col["a"].append(tix[g["team_a"]])
            col["b"].append(tix[g["team_b"]])
            col["as"].append(g["team_a_score"])
            col["bs"].append(g["team_b_score"])
            col["w"].append(0 if g["is_tie"] else (1 if g["winner"] == g["team_a"] else 2))
            col["e"].append(era_ix(g["era"]))
            col["p"].append(2 if g["postseason"] is None else (1 if g["postseason"] else 0))
            col["c"].append(city_ix(g["city"]))
            col["st"].append(state_ix(g["state"]))
            if g["date_estimated"]:
                est.append(pos)
            std = f"{(g['game_date'] or '').replace('-', '') or '00000000'}_{g['team_a']}_vs_{g['team_b']}"
            if g["game_id"] != std:
                gid[str(pos)] = g["game_id"]
            site = sites.get(g["game_id"])
            site_chars.append(site[0] if site else "-")
            ca, cb = coach_of(g["team_a"], g), coach_of(g["team_b"], g)
            col["ca"].append(coach_ix(ca) if ca is not None else -1)
            col["cb"].append(coach_ix(cb) if cb is not None else -1)
            venue = site[1] if site else ""
            col["vn"].append(venue_ix(venue) if venue else -1)
        doc = {"v": DERIVED_FORMAT, "team": n, "n": len(rows), **col,
               "eras": eras, "cities": cities, "states": states, "est": est, "gid": gid,
               "site": "".join(site_chars), "coaches": coaches, "venues": venues}
        data = dumps(doc)
        fname = "teams/" + hashed(f"{slug}.json", data)
        files[fname] = data
        team_files[slug] = fname

    # ---- league-wide aggregates, accumulated exactly like the pages' loops ---------------
    # wins: buildWinsRank()/liveWins() - non-tie games, counts keyed in first-win order.
    wins = OrderedDict()
    for g in games:
        if g["is_tie"]:
            continue
        wins[g["winner"]] = wins.get(g["winner"], 0) + 1
    # records: buildWinPctRank()/liveWinPct() - both teams registered in appearance order;
    # the Miami self-game counts as a win AND a loss for Miami, as the pages' loop does.
    recs = OrderedDict()
    for g in games:
        for t in (g["team_a"], g["team_b"]):
            recs.setdefault(t, [0, 0, 0])
        if g["is_tie"]:
            recs[g["team_a"]][2] += 1
            recs[g["team_b"]][2] += 1
        elif g["winner"] == g["team_a"]:
            recs[g["team_a"]][0] += 1
            recs[g["team_b"]][1] += 1
        elif g["winner"] == g["team_b"]:
            recs[g["team_b"]][0] += 1
            recs[g["team_a"]][1] += 1
    league = {"v": DERIVED_FORMAT,
              "wins": [[t, w] for t, w in wins.items()],
              "records": [[t, r[0], r[1], r[2]] for t, r in recs.items()]}
    league_name = hashed("league.json", dumps(league))
    files[league_name] = dumps(league)

    # ---- index.html ------------------------------------------------------------------
    max_season = max((g["season"] | 0) for g in games) if games else 0
    bb = []
    for a, b in BLUE_BLOODS:
        rg = [g for g in games if (g["team_a"] == a and g["team_b"] == b) or (g["team_a"] == b and g["team_b"] == a)]
        bb.append([a, b, sum(1 for g in rg if g["winner"] == a), sum(1 for g in rg if g["winner"] == b),
                   sum(1 for g in rg if g["is_tie"])])
    home = {"v": DERIVED_FORMAT, "gameCount": n_games, "maxSeason": max_season, "blueBloods": bb}
    home_name = hashed("home.json", dumps(home))
    files[home_name] = dumps(home)

    # ---- shared lookup -------------------------------------------------------------------
    index = {"v": DERIVED_FORMAT, "teams": [
        {"id": i, "name": n, "slug": slugs[i],
         "abbr": (fbs.get(fpskey(n)) or {}).get("abbreviation"),
         "conf": (fbs.get(fpskey(n)) or {}).get("conference"),
         "games": games_per_team[n]} for i, n in enumerate(names)]}
    index_name = hashed("teams_index.json", dumps(index))
    files[index_name] = dumps(index)

    manifest = {
        "v": DERIVED_FORMAT,
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "source": "front_porch_games.json", "sourceSha256": source_sha,
        "gameCount": n_games, "maxSeason": max_season,
        "names": names, "slugs": slugs,
        "index": index_name, "league": league_name, "home": home_name,
        "teams": team_files,
    }
    files["manifest.json"] = dumps(manifest)
    files["README.md"] = README.encode("utf-8")

    total = sum(len(v) for v in files.values())
    team_sizes = sorted(len(files[f]) for f in team_files.values())
    print(f"==> {n_games:,} games, {len(names)} teams, maxSeason {max_season}")
    print(f"==> {len(files)} files, {total / 1024:,.0f} KB raw; team files {team_sizes[0] / 1024:.1f}-"
          f"{team_sizes[-1] / 1024:.1f} KB (median {team_sizes[len(team_sizes) // 2] / 1024:.1f} KB)")
    print(f"==> league {len(files[league_name]) / 1024:.1f} KB, home {len(files[home_name])} B, "
          f"index {len(files[index_name]) / 1024:.1f} KB, manifest {len(files['manifest.json']) / 1024:.1f} KB")
    if dry:
        print("==> dry run: nothing written")
        return

    # Write the full set to a temp dir, then swap it in - a failed run never leaves a half-
    # written data/derived/ behind.
    OUT_DIR.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="derived-", dir=OUT_DIR.parent))
    try:
        for rel, data in files.items():
            p = tmp / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
        old = OUT_DIR.with_name(OUT_DIR.name + ".old")
        if old.exists():
            shutil.rmtree(old)
        if OUT_DIR.exists():
            OUT_DIR.rename(old)
        tmp.rename(OUT_DIR)
        if old.exists():
            shutil.rmtree(old)
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    print(f"==> wrote {OUT_DIR.relative_to(REPO)}/ ({len(files)} files)")


if __name__ == "__main__":
    main()

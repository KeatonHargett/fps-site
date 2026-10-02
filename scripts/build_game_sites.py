"""
Front Porch Sports - build game_sites.json (+ game_venues.json): where every game in
front_porch_games.json was played (team_a home, team_b home, or neutral site).

Why separate files:
  front_porch_games.json has city/state but no home/away/neutral field, and it is
  never modified by this script. Both outputs are purely additive.

Sources, in priority order:
  1. override       game_sites_overrides.json - known corrections (e.g. the Iron
                    Bowl at Legion Field, Birmingham, 1948-1988, which CFBD files as
                    an Alabama home game). Official sources outrank CFBD.
  2. cfbd           CollegeFootballData /games (homeTeam, awayTeam, neutralSite,
                    venue), cached per season in .cfbd_cache/. CFBD's home
                    designation is trusted unless an override says otherwise.
  3. city_inferred  for games CFBD has no record of (mostly pre-1930 and non-FBS
                    opponents), see "City fill" below.

CFBD join (season + both teams, then date, then score):
  same season, same team pair, CFBD date within +/-1 day (CFBD startDate is UTC);
  otherwise same season, same pair, same final score. Team names go through
  refresh_games.normalize(), the map the main dataset was built with.

City fill:
  Each school's home cities are its CFBD home-stadium city (teams cache) plus any
  city where CFBD lists it as the designated home team in at least
  HOME_CITY_MIN_GAMES games - so a regular home venue counts as home (Alabama at
  Legion Field, Arkansas in Little Rock, Ole Miss in Jackson). Using the game's
  city/state from front_porch_games.json:
    in only one team's home cities               -> that team was home
    in neither team's home cities                -> neutral
    a regular city of both, campus city of one   -> the campus team was home
    a regular city of both, campus of neither    -> neutral
    the campus city of both, a team with no CFBD
    profile, or no city in the dataset           -> unresolved (never guessed)

Outputs (both grouped by team pair). A game's key inside its pair is "key4": the
date that starts its game_id as days since 1869-01-01 in 4 base-36 digits ("zzzz"
for the undated 00000000 games). Dates are unique within a pair - the build checks.
  game_sites.json   - loaded by compare.html on every visit, so kept minimal:
    { "_meta": {...}, "pairs": { "<A>|<B>": "<key4><H|A|N><key4><H|A|N>..." } }
    The pair key is the two team names sorted; H = the first-named team was home,
    A = the first-named team was away (the second was home), N = neutral site.
  game_venues.json  - loaded only by games.html:
    { "_meta": {...}, "sources": {...}, "venues": [...],
      "pairs": { "<A>|<B>": "<key4><source>[<venue index>],..." } }
    source: c = cfbd, i = city_inferred, o = override.

Modes:
  full (default)        rebuild every season from the CFBD cache.
  --update-season Y...  CI / weekly refresh: re-fetch only these seasons from CFBD
                        and recompute their games; every other game keeps what the
                        current output files hold. Overrides are applied every run.
  A CFBD error is fatal: the script exits non-zero and leaves both output files
  untouched. Outputs are written to a temp file and swapped in only on success, and
  never if they would cover fewer games than the files they replace.

Env vars:
  CFBD_API_KEY   CollegeFootballData key (env or repo .env). Never printed.
  FPS_DRY_RUN=1  compute and report, write nothing.

Usage:
  python scripts/build_game_sites.py                      # full build from cache
  python scripts/build_game_sites.py --refresh 2026       # full build, re-fetch 2026
  python scripts/build_game_sites.py --update-season 2026 # weekly incremental
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from refresh_games import normalize  # noqa: E402
from backfill_season_type import api_get  # noqa: E402

REPO = Path(os.environ.get("FPS_REPO_ROOT", Path(__file__).resolve().parent.parent))
GAMES_FILE = REPO / "front_porch_games.json"
OVERRIDES_FILE = REPO / "game_sites_overrides.json"
OUT_FILE = REPO / "game_sites.json"
VENUES_FILE = REPO / "game_venues.json"
CACHE_DIR = Path(os.environ.get("FPS_CACHE_DIR", REPO / ".cfbd_cache"))
DATE_TOLERANCE_DAYS = 1
HOME_CITY_MIN_GAMES = 3
SOURCE_NAMES = {"c": "cfbd", "i": "city_inferred", "o": "override"}
SITE_TO_PAIR_CODE = {True: "H", False: "A"}
KEY_EPOCH = dt.date(1869, 1, 1)
B36 = "0123456789abcdefghijklmnopqrstuvwxyz"


def key4(game_id: str) -> str:
    """Compact per-pair game key: days since 1869-01-01 in 4 base-36 digits.
    Mirrored by gameKey() in js/matchup-filter.js - change both together."""
    d8 = game_id[:8]
    if d8 == "00000000":
        return "zzzz"
    n = (dt.date(int(d8[:4]), int(d8[4:6]), int(d8[6:8])) - KEY_EPOCH).days
    out = ""
    for _ in range(4):
        out = B36[n % 36] + out
        n //= 36
    return out


class CFBDError(RuntimeError):
    """A CFBD request failed. Fatal: nothing may be written after this."""


def load_key() -> str | None:
    key = os.environ.get("CFBD_API_KEY")
    if key:
        return key
    env = REPO / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("CFBD_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def cfbd_fetch(path: str, params: dict, key_holder: dict):
    """One CFBD call. Raises CFBDError instead of returning partial data."""
    if "key" not in key_holder:
        key_holder["key"] = load_key()
    if not key_holder["key"]:
        raise CFBDError("CFBD_API_KEY is not set")
    rows = api_get(path, params, key_holder["key"])  # never echoes the key
    if rows is None:
        raise CFBDError(f"CFBD {path} {params} failed")
    return rows


def season_rows(year: int, refresh: bool, key_holder: dict):
    cf = CACHE_DIR / f"cfbd_{year}.json"
    if cf.exists() and not refresh:
        return json.loads(cf.read_text(encoding="utf-8"))
    rows = cfbd_fetch("/games", {"year": year, "seasonType": "both"}, key_holder)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cf.write_text(json.dumps(rows), encoding="utf-8")
    print(f"  fetched {year}: {len(rows):,} CFBD games", flush=True)
    return rows


def index_season(rows):
    """pair -> list of CFBD games (normalized), for one season."""
    idx = defaultdict(list)
    for g in rows:
        home, away = normalize(g.get("homeTeam") or ""), normalize(g.get("awayTeam") or "")
        if not home or not away:
            continue
        raw = (g.get("startDate") or "")[:10]
        try:
            date = dt.date.fromisoformat(raw) if raw else None
        except ValueError:
            date = None
        idx[frozenset((home, away))].append({
            "id": g.get("id"), "home": home, "away": away, "date": date,
            "neutral": bool(g.get("neutralSite")),
            "venue": (g.get("venue") or "").strip(),
            "pts": {home: g.get("homePoints"), away: g.get("awayPoints")},
        })
    return idx


def match(game, cands):
    """Return (cfbd_game, method) or (None, reason)."""
    if not cands:
        return None, "no CFBD game for pair+season"
    a, b = game["team_a"], game["team_b"]
    sa, sb = game["team_a_score"], game["team_b_score"]
    score_ok = lambda c: c["pts"].get(a) == sa and c["pts"].get(b) == sb
    if game["game_date"]:
        d = dt.date.fromisoformat(game["game_date"])
        near = [c for c in cands if c["date"] and abs((c["date"] - d).days) <= DATE_TOLERANCE_DAYS]
        if len(near) == 1:
            return near[0], "date"
        if len(near) > 1:
            s = [c for c in near if score_ok(c)]
            if len(s) == 1:
                return s[0], "date+score"
    s = [c for c in cands if score_ok(c)]
    if len(s) == 1:
        return s[0], "score"
    return None, "ambiguous" if len(s) > 1 else "date and score disagree"


def code_for(game, c):
    if c["neutral"]:
        return "n"
    if c["home"] == game["team_a"]:
        return "a"
    if c["home"] == game["team_b"]:
        return "b"
    return None


def city_key(g):
    city = (g.get("city") or "").strip().lower()
    return (city, (g.get("state") or "").strip().upper()) if city else None


def campus_cities(team_rows=None):
    """school -> {(city, state)} from CFBD teams (the cache, plus any rows passed in)."""
    out = defaultdict(set)
    batches = [json.loads(f.read_text(encoding="utf-8")) for f in sorted(CACHE_DIR.glob("cfbd_teams_*.json"))]
    if team_rows:
        batches.append(team_rows)
    for rows in batches:
        for t in rows:
            loc = t.get("location") or {}
            if loc.get("city"):
                out[normalize(t.get("school") or "")].add(
                    (loc["city"].strip().lower(), (loc.get("state") or "").strip().upper()))
    return out


def infer_from_city(g, campus, regular):
    """City fill for a game CFBD could not place. Returns (code, None) or (None, reason)."""
    ck = city_key(g)
    if not ck:
        return None, "no city in dataset"
    a, b = g["team_a"], g["team_b"]
    known_a = bool(campus.get(a) or regular.get(a))
    known_b = bool(campus.get(b) or regular.get(b))
    ca, cb = ck in campus.get(a, ()), ck in campus.get(b, ())
    ra, rb = ca or ck in regular.get(a, ()), cb or ck in regular.get(b, ())
    if ra and rb:
        if ca and cb:
            return None, "shared campus city"
        if ca:
            return "a", None
        if cb:
            return "b", None
        return "n", None
    if ra:
        return "a", None
    if rb:
        return "b", None
    if known_a and known_b:
        return "n", None
    return None, "no home-city profile for one team"


def apply_overrides(game, overrides):
    pair = {game["team_a"], game["team_b"]}
    for o in overrides:
        if set(o["teams"]) != pair:
            continue
        lo, hi = o["seasons"]
        if not (lo <= game["season"] <= hi):
            continue
        if o.get("city") and (game.get("city") or "") not in ("", o["city"]):
            continue  # dataset says it was played somewhere else: don't force it
        if o["site"] == "neutral":
            return "n", o.get("venue", "")
        home = o["site"]  # a team name
        return ("a" if home == game["team_a"] else "b"), o.get("venue", "")
    return None


def cfbd_join(games, seasons, refresh, key_holder):
    """game_id -> (cfbd_game, method) for the given seasons. Shared with
    build_coaches_data.py, which needs the CFBD game to date coaching changes."""
    by_season = defaultdict(list)
    for g in games:
        if g["season"] in seasons:
            by_season[g["season"]].append(g)
    joined, misses = {}, {}
    for season in sorted(by_season):
        idx = index_season(season_rows(season, season in refresh, key_holder))
        for g in by_season[season]:
            c, how = match(g, idx.get(frozenset((g["team_a"], g["team_b"])), []))
            if c:
                joined[g["game_id"]] = (c, how)
            else:
                misses[g["game_id"]] = how
    return joined, misses


# ---- output encoding ---------------------------------------------------------

def pair_key(g):
    return "|".join(sorted((g["team_a"], g["team_b"])))


def pair_code(g, code):
    """team_a/team_b code -> H/A/N from the point of view of the pair key's first team."""
    if code == "n":
        return "N"
    home = g["team_a"] if code == "a" else g["team_b"]
    return SITE_TO_PAIR_CODE[home == pair_key(g).split("|")[0]]


def decode_existing(games):
    """Read the current output files back into game_id -> (code, venue, src)."""
    if not OUT_FILE.exists():
        return {}
    sites = json.loads(OUT_FILE.read_text(encoding="utf-8")).get("pairs", {})
    vdoc = json.loads(VENUES_FILE.read_text(encoding="utf-8")) if VENUES_FILE.exists() else {}
    venues, vpairs = vdoc.get("venues", []), vdoc.get("pairs", {})
    site_map, venue_map = {}, {}
    for pk, s in sites.items():
        for i in range(0, len(s), 5):
            site_map[(pk, s[i:i + 4])] = s[i + 4]
    for pk, s in vpairs.items():
        for e in s.split(","):
            if len(e) >= 5:
                venue_map[(pk, e[:4])] = (e[4], venues[int(e[5:])] if len(e) > 5 else "")
    out = {}
    for g in games:
        k = (pair_key(g), key4(g["game_id"]))
        pc = site_map.get(k)
        if not pc:
            continue
        first = k[0].split("|")[0]
        if pc == "N":
            code = "n"
        else:
            home = first if pc == "H" else [t for t in (g["team_a"], g["team_b"]) if t != first][0]
            code = "a" if home == g["team_a"] else "b"
        src, venue = venue_map.get(k, ("c", ""))
        out[g["game_id"]] = (code, venue, src)
    return out


def write_atomic(path: Path, doc):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(doc, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", nargs="*", type=int, default=[], help="seasons to re-fetch from CFBD (full build)")
    ap.add_argument("--update-season", nargs="*", type=int, default=None,
                    help="only recompute these seasons (fresh from CFBD); keep the rest from the current files")
    ap.add_argument("--report", nargs="*", default=["Alabama|Auburn", "Oklahoma St.|Oklahoma"],
                    help='matchups to report on, as "Team A|Team B"')
    args = ap.parse_args()
    dry = os.environ.get("FPS_DRY_RUN") == "1"

    games = json.loads(GAMES_FILE.read_text(encoding="utf-8"))
    by_id = {g["game_id"]: g for g in games}
    overrides = json.loads(OVERRIDES_FILE.read_text(encoding="utf-8"))["overrides"] if OVERRIDES_FILE.exists() else []
    seen = set()
    for g in games:
        k = (pair_key(g), key4(g["game_id"]))
        if k in seen:
            sys.exit(f"FATAL: two games share pair+date key {k}; the compact format cannot hold them")
        seen.add(k)

    key_holder: dict = {}
    incremental = args.update_season is not None
    try:
        if incremental:
            target = set(args.update_season)
            if not target:
                sys.exit("FATAL: --update-season needs at least one season")
            baseline = decode_existing(games)
            if not baseline:
                sys.exit(f"FATAL: --update-season needs an existing {OUT_FILE.name} to build on")
            # Fresh CFBD data for the target seasons only - a failed call raises.
            joined, _ = cfbd_join(games, target, target, key_holder)
            team_rows = []
            for y in sorted(target):
                team_rows += cfbd_fetch("/teams", {"year": y}, key_holder)
            campus = campus_cities(team_rows)
        else:
            target = {g["season"] for g in games}
            baseline = {}
            joined, _ = cfbd_join(games, target, set(args.refresh), key_holder)
            campus = campus_cities()
    except CFBDError as e:
        print(f"::error::{e}. Leaving {OUT_FILE.name} and {VENUES_FILE.name} untouched.", flush=True)
        sys.exit(1)

    # CFBD placements for the games being (re)computed.
    cfbd = {}
    for gid, (c, how) in joined.items():
        code = code_for(by_id[gid], c)
        if code:
            cfbd[gid] = (code, c["venue"])

    # Regular home cities, learned from CFBD's own home designations (in an
    # incremental run the existing CFBD-sourced entries supply the history).
    city_counts = defaultdict(lambda: defaultdict(int))
    history = {gid: (v[0], v[1]) for gid, v in baseline.items() if v[2] == "c"}
    history.update(cfbd)
    for gid, (code, _) in history.items():
        g = by_id.get(gid)
        ck = city_key(g) if g else None
        if g and code in "ab" and ck:
            city_counts[g["team_a"] if code == "a" else g["team_b"]][ck] += 1
    regular = {t: {ck for ck, n in cs.items() if n >= HOME_CITY_MIN_GAMES} for t, cs in city_counts.items()}

    # Resolve: override > cfbd > city fill (target seasons); everything else from baseline.
    result: dict[str, tuple] = {}
    stats = defaultdict(int)
    unresolved = []
    for g in games:
        gid = g["game_id"]
        ov = apply_overrides(g, overrides)
        if ov:
            result[gid] = (ov[0], ov[1], "o")
        elif g["season"] not in target:
            if gid in baseline:
                result[gid] = baseline[gid]
            else:
                unresolved.append((g, "not in previous build"))
            continue
        elif gid in cfbd:
            result[gid] = (cfbd[gid][0], cfbd[gid][1], "c")
        else:
            code, why = infer_from_city(g, campus, regular)
            if code is None:
                unresolved.append((g, why))
                continue
            result[gid] = (code, "", "i")
    for code, _, src in result.values():
        stats[src] += 1

    total = len(games)
    resolved = len(result)
    if incremental and resolved < len([g for g in games if g["game_id"] in baseline]):
        print(f"::error::incremental build resolves {resolved:,} games, fewer than the "
              f"{len(baseline):,} already on file. Not writing.", flush=True)
        sys.exit(1)

    # Encode.
    venues, venue_ix = [], {}
    site_pairs, venue_pairs = defaultdict(list), defaultdict(list)
    for g in sorted(games, key=lambda x: x["game_id"][:8]):
        r = result.get(g["game_id"])
        if not r:
            continue
        code, venue, src = r
        pk, k4 = pair_key(g), key4(g["game_id"])
        site_pairs[pk].append(k4 + pair_code(g, code))
        if venue and venue not in venue_ix:
            venue_ix[venue] = len(venues)
            venues.append(venue)
        venue_pairs[pk].append(k4 + src + (str(venue_ix[venue]) if venue else ""))
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    meta = {
        "source": "CollegeFootballData /games (homeTeam, awayTeam, neutralSite, venue); city fill from "
                  "front_porch_games.json city/state; game_sites_overrides.json (official sources outrank CFBD)",
        "generated": stamp,
        "games_total": total, "games_resolved": resolved,
        "by_source": {name: stats[k] for k, name in SOURCE_NAMES.items()},
    }
    sites_doc = {
        "_meta": dict(meta, format="pairs[sorted 'A|B'] = concatenated <key4><H|A|N> (key4 = base-36 days since 1869-01-01, zzzz = undated); "
                                   "H/A = first-named team home/away, N = neutral"),
        "pairs": {pk: "".join(v) for pk, v in sorted(site_pairs.items())},
    }
    venues_doc = {
        "_meta": dict(meta, format="pairs[sorted 'A|B'] = comma-separated <key4><source>[venue index]"),
        "sources": SOURCE_NAMES,
        "venues": venues,
        "pairs": {pk: ",".join(v) for pk, v in sorted(venue_pairs.items())},
    }

    print(f"\n==> mode: {'incremental ' + str(sorted(target)) if incremental else 'full'}{' (dry run)' if dry else ''}")
    print(f"==> resolved {resolved:,} / {total:,} ({resolved / total:.1%}), {len(unresolved):,} unresolved")
    for k, name in SOURCE_NAMES.items():
        print(f"      {name}: {stats[k]:,}")
    reasons = defaultdict(int)
    for _, why in unresolved:
        reasons[why] += 1
    if reasons:
        print("==> unresolved by reason: " + ", ".join(f"{k}: {v:,}" for k, v in reasons.items()))
    for spec in args.report:
        a, b = spec.split("|")
        pg = [g for g in games if {g["team_a"], g["team_b"]} == {a, b}]
        ok = sum(1 for g in pg if g["game_id"] in result)
        print(f"==> {a} vs {b}: {ok} / {len(pg)} ({ok / max(1, len(pg)):.1%})")

    if dry:
        print("==> dry run: nothing written")
        return
    write_atomic(OUT_FILE, sites_doc)
    write_atomic(VENUES_FILE, venues_doc)
    print(f"==> wrote {OUT_FILE.name} ({OUT_FILE.stat().st_size:,} bytes) and "
          f"{VENUES_FILE.name} ({VENUES_FILE.stat().st_size:,} bytes, {len(venues):,} venues)")


if __name__ == "__main__":
    main()

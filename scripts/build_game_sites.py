"""
Front Porch Sports - build game_sites.json: where every game in
front_porch_games.json was played (team_a home, team_b home, or neutral site).

Why a separate file:
  front_porch_games.json has city/state but no home/away/neutral field, and it is
  never modified by this script. game_sites.json is purely additive and keyed by
  game_id, so the weekly games refresh can keep rewriting the main dataset without
  touching it; new game_ids simply show up as unresolved until this is re-run.

Sources, in priority order:
  1. override       game_sites_overrides.json - known corrections (e.g. the Iron
                    Bowl at Legion Field, Birmingham, 1948-1988, which CFBD files as
                    an Alabama home game).
  2. cfbd           CollegeFootballData /games (homeTeam, awayTeam, neutralSite,
                    venue), cached per season in .cfbd_cache/ (shared with
                    backfill_season_type.py). CFBD's home designation is trusted.
  3. city_inferred  for games CFBD has no record of (mostly pre-1930 and non-FBS
                    opponents), see "City fill" below.

CFBD join (season + both teams, then date, then score):
  same season, same team pair, CFBD date within +/-1 day (CFBD startDate is UTC);
  otherwise same season, same pair, same final score - catches early games whose
  dates disagree between sources and the rows with no game_date. Team names go
  through refresh_games.normalize(), the map the main dataset was built with.

City fill:
  Each school's home cities are its CFBD home-stadium city (teams cache, every
  season) plus any city where CFBD lists it as the designated home team in at least
  HOME_CITY_MIN_GAMES games. That second set is what makes a regular home venue
  count as home (Alabama at Legion Field, Arkansas in Little Rock, Ole Miss in
  Jackson). Using the game's city/state from front_porch_games.json:
    in only one team's home cities               -> that team was home
    in neither team's home cities                -> neutral
    a regular city of both, campus city of one   -> the campus team was home
    a regular city of both, campus of neither    -> neutral
    the campus city of both, a team with no CFBD
    profile, or no city in the dataset           -> unresolved (never guessed)

Output shape (compact on purpose - compare.html loads it on every visit):
  {
    "_meta":  {...},
    "venues": ["Bryant-Denny Stadium", ...],
    "games":  { "<game_id>": "<site><source>[<venue index>]", ... }
  }
  site:   "a" = team_a was the home team, "b" = team_b was home, "n" = neutral site
  source: "c" = cfbd, "i" = city_inferred, "o" = override
  e.g. "ac12" = team_a home per CFBD at venues[12]; "ni" = neutral, inferred.
  home_team/away_team are recoverable from the game record plus the site code.

Env vars:
  CFBD_API_KEY   CollegeFootballData key (env or repo .env). Only needed when a
                 season is not cached or is passed to --refresh. Never printed.

Usage:
  python scripts/build_game_sites.py                     # build from cache
  python scripts/build_game_sites.py --refresh 2026      # re-fetch a season first
  python scripts/build_game_sites.py --report "Alabama|Auburn" "Oklahoma St.|Oklahoma"
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
CACHE_DIR = Path(os.environ.get("FPS_CACHE_DIR", REPO / ".cfbd_cache"))
DATE_TOLERANCE_DAYS = 1
HOME_CITY_MIN_GAMES = 3
SOURCE_NAMES = {"c": "cfbd", "i": "city_inferred", "o": "override"}


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


def season_rows(year: int, refresh: bool, key_holder: dict):
    cf = CACHE_DIR / f"cfbd_{year}.json"
    if cf.exists() and not refresh:
        return json.loads(cf.read_text(encoding="utf-8"))
    if "key" not in key_holder:
        key_holder["key"] = load_key()
    if not key_holder["key"]:
        print(f"  WARN: season {year} not cached and CFBD_API_KEY is not set", flush=True)
        return []
    rows = api_get("/games", {"year": year, "seasonType": "both"}, key_holder["key"])
    if rows is None:
        return []
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cf.write_text(json.dumps(rows), encoding="utf-8")
    print(f"  fetched {year}: {len(rows):,} CFBD rows", flush=True)
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


def campus_cities():
    """school -> {(city, state)} from the CFBD teams cache, every season."""
    out = defaultdict(set)
    for f in sorted(CACHE_DIR.glob("cfbd_teams_*.json")):
        for t in json.loads(f.read_text(encoding="utf-8")):
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


def cfbd_join(games, refresh):
    """game_id -> (cfbd_game, method) for every game CFBD can place. Shared with
    build_coaches_data.py, which needs the CFBD game to date coaching changes."""
    by_season = defaultdict(list)
    for g in games:
        by_season[g["season"]].append(g)
    key_holder: dict = {}
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", nargs="*", type=int, default=[], help="seasons to re-fetch from CFBD")
    ap.add_argument("--report", nargs="*", default=["Alabama|Auburn", "Oklahoma St.|Oklahoma"],
                    help='matchups to report on, as "Team A|Team B"')
    args = ap.parse_args()

    games = json.loads(GAMES_FILE.read_text(encoding="utf-8"))
    overrides = json.loads(OVERRIDES_FILE.read_text(encoding="utf-8"))["overrides"] if OVERRIDES_FILE.exists() else []

    # Pass 1: CFBD join.
    joined, _ = cfbd_join(games, set(args.refresh))
    cfbd = {}
    by_id = {g["game_id"]: g for g in games}
    for gid, (c, how) in joined.items():
        code = code_for(by_id[gid], c)
        if code:
            cfbd[gid] = (code, c["venue"], how)

    # Regular home cities, learned from CFBD's own home designations.
    city_counts = defaultdict(lambda: defaultdict(int))
    for g in games:
        r = cfbd.get(g["game_id"])
        ck = city_key(g)
        if r and r[0] in "ab" and ck:
            city_counts[g["team_a"] if r[0] == "a" else g["team_b"]][ck] += 1
    regular = {t: {ck for ck, n in cs.items() if n >= HOME_CITY_MIN_GAMES} for t, cs in city_counts.items()}
    campus = campus_cities()

    # Pass 2: override > cfbd > city fill.
    venues: list[str] = []
    venue_ix: dict[str, int] = {}
    out: dict[str, str] = {}
    stats = defaultdict(int)
    unresolved = []

    def vix(name):
        if not name:
            return -1
        if name not in venue_ix:
            venue_ix[name] = len(venues)
            venues.append(name)
        return venue_ix[name]

    for g in games:
        gid = g["game_id"]
        ov = apply_overrides(g, overrides)
        if ov:
            code, venue, src = ov[0], ov[1], "o"
        elif gid in cfbd:
            code, venue, src = cfbd[gid][0], cfbd[gid][1], "c"
        else:
            code, why = infer_from_city(g, campus, regular)
            venue, src = "", "i"
            if code is None:
                stats["unresolved"] += 1
                unresolved.append((g, why))
                continue
        stats["matched"] += 1
        stats[src] += 1
        v = vix(venue)
        out[gid] = code + src + (str(v) if v >= 0 else "")

    total = len(games)
    doc = {
        "_meta": {
            "source": "CollegeFootballData /games (homeTeam, awayTeam, neutralSite, venue), "
                      "city fill from front_porch_games.json city/state, game_sites_overrides.json",
            "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
            "codes": {"a": "team_a home", "b": "team_b home", "n": "neutral site"},
            "sources": SOURCE_NAMES,
            "games_total": total, "games_resolved": stats["matched"],
            "by_source": {name: stats[k] for k, name in SOURCE_NAMES.items()},
        },
        "venues": venues,
        "games": out,
    }
    OUT_FILE.write_text(json.dumps(doc, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")

    print(f"\n==> wrote {OUT_FILE.name}: {OUT_FILE.stat().st_size:,} bytes, {len(venues):,} venues")
    print(f"==> before (CFBD join only): {len(cfbd):,} / {total:,} ({len(cfbd) / total:.1%})")
    print(f"==> after: {stats['matched']:,} / {total:,} ({stats['matched'] / total:.1%}), "
          f"{stats['unresolved']:,} unresolved")
    for k, name in SOURCE_NAMES.items():
        print(f"      {name}: {stats[k]:,}")
    reasons = defaultdict(int)
    for _, why in unresolved:
        reasons[why] += 1
    print("==> unresolved by reason: " + ", ".join(f"{k}: {v:,}" for k, v in reasons.items()))
    decade = defaultdict(lambda: [0, 0])
    for g in games:
        d = decade[g["season"] // 10 * 10]
        d[0] += 1
        d[1] += g["game_id"] in out
    print("==> by decade: " + "  ".join(f"{k}s {v[1] / v[0]:.0%}" for k, v in sorted(decade.items())))

    for spec in args.report:
        a, b = spec.split("|")
        pg = [g for g in games if {g["team_a"], g["team_b"]} == {a, b}]
        before = sum(1 for g in pg if g["game_id"] in cfbd)
        after = [g for g in pg if g["game_id"] in out]
        cnt, srcs = defaultdict(int), defaultdict(int)
        for g in after:
            code, src = out[g["game_id"]][0], out[g["game_id"]][1]
            cnt["neutral" if code == "n" else f"{g['team_a'] if code == 'a' else g['team_b']} home"] += 1
            srcs[SOURCE_NAMES[src]] += 1
        print(f"\n==> {a} vs {b}: before {before} / {len(pg)} ({before / max(1, len(pg)):.1%}), "
              f"after {len(after)} / {len(pg)} ({len(after) / max(1, len(pg)):.1%})")
        print("      " + ", ".join(f"{k}: {v}" for k, v in sorted(cnt.items()))
              + "  |  " + ", ".join(f"{k}: {v}" for k, v in sorted(srcs.items())))
        for g in sorted(pg, key=lambda g: g["season"]):
            r = out.get(g["game_id"])
            if r and r[1] == "i":
                home = "neutral" if r[0] == "n" else (g["team_a"] if r[0] == "a" else g["team_b"]) + " home"
                print(f"      city_inferred: {g['season']} {g['city']}, {g['state']} -> {home}")
            elif not r:
                why = next((w for u, w in unresolved if u is g), "?")
                print(f"      unresolved: {g['season']} {g['game_date'] or '(no date)'}  [{why}]")


if __name__ == "__main__":
    main()

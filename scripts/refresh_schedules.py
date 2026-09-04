"""
Front Porch Sports - per-team season schedules, 2022-present, from CollegeFootballData.

Writes schedules_data.json at the repo root. This is a supplemental, additive file:
it is the only place on the site that carries FCS and other non-FBS opponents, which
front_porch_games.json deliberately does not (that dataset is FBS-vs-FBS only and is
never touched by this script).

Team names are normalized with the SAME map used by refresh_games.py - imported, not
copied, so the two cannot drift.

Env vars:
  CFBD_API_KEY           required   CollegeFootballData API key (Bearer token)
  FPS_SCHEDULE_START     optional   first season to pull (default 2022)
  FPS_SCHEDULE_END       optional   last season to pull (default: current season)
  FPS_REPO_ROOT          optional   override repo root path
  FPS_DRY_RUN            optional   "1" to skip the write

Usage:
  python scripts/refresh_schedules.py
"""

from __future__ import annotations
import json
import os
import sys
import time
import datetime as dt
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: requests not installed. pip install -r scripts/requirements.txt", flush=True)
    sys.exit(2)

# Reuse the canonical name map rather than pasting a third copy of it.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from refresh_games import normalize, current_season  # noqa: E402

CFBD_BASE = "https://api.collegefootballdata.com"
JSON_FILENAME = "schedules_data.json"
HTTP_TIMEOUT = 30
HTTP_RETRIES = 3
HTTP_SLEEP = 0.20
DEFAULT_START = 2022

# CFBD spells three conferences differently from the rest of the site. Normalise here
# so the shipped JSON only ever contains the site's own vocabulary (the same strings
# CONF_ORDER and CONF_LOGOS use in teams.html).
CONF_REMAP = {
    "American Athletic": "American",
    "Mid-American": "MAC",
    "FBS Independents": "Independent",
}


def api_get(path: str, params: dict, key: str):
    """GET one CFBD endpoint with the same retry shape refresh_games.py uses."""
    url = f"{CFBD_BASE}{path}"
    headers = {"Authorization": f"Bearer {key}", "Accept": "application/json"}
    for attempt in range(HTTP_RETRIES):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=HTTP_TIMEOUT)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (429, 502, 503, 504):
                time.sleep(1.5 ** attempt)
                continue
            # Never echo the key, and never echo a body that might contain it.
            print(f"    ERROR: {path} returned HTTP {r.status_code}", flush=True)
            return None
        except Exception as e:
            print(f"    WARN: {path} attempt {attempt + 1} failed ({type(e).__name__})", flush=True)
            time.sleep(1.5 ** attempt)
    return None


def fbs_teams(year: int, key: str) -> dict:
    """canonical name -> {mascot, conference, cfbdSchool} for one season's FBS members."""
    rows = api_get("/teams/fbs", {"year": year}, key) or []
    out = {}
    for t in rows:
        school = t.get("school") or ""
        if not school:
            continue
        out[normalize(school)] = {
            "mascot": t.get("mascot") or "",
            "conference": CONF_REMAP.get(t.get("conference") or "", t.get("conference") or ""),
            "cfbdSchool": school,
        }
    return out


def season_games(year: int, key: str) -> list:
    """Every game that season involving at least one FBS program."""
    rows = api_get("/games", {"year": year, "seasonType": "both"}, key) or []
    return [g for g in rows
            if g.get("homeClassification") == "fbs" or g.get("awayClassification") == "fbs"]


def result_for(pts_for, pts_against):
    if pts_for is None or pts_against is None:
        return None
    if pts_for > pts_against:
        return "W"
    if pts_for < pts_against:
        return "L"
    return "T"


def build(seasons: list, key: str):
    """Return (schedules, teams_meta, warnings)."""
    schedules: dict = {}   # team -> season(str) -> [game, ...]
    teams_meta: dict = {}  # team -> {mascot, conference, seasons:[...]}
    warnings: list = []

    for year in seasons:
        print(f"==> {year}", flush=True)
        members = fbs_teams(year, key)
        time.sleep(HTTP_SLEEP)
        if not members:
            warnings.append(f"{year}: FBS team list came back empty")
        games = season_games(year, key)
        time.sleep(HTTP_SLEEP)
        if not games:
            warnings.append(f"{year}: no games returned")
            print(f"    0 games", flush=True)
            continue

        for name, meta in members.items():
            m = teams_meta.setdefault(name, {"mascot": meta["mascot"],
                                             "conference": meta["conference"],
                                             "seasons": []})
            # keep the newest season's mascot/conference
            m["mascot"] = meta["mascot"] or m["mascot"]
            m["conference"] = meta["conference"] or m["conference"]
            if year not in m["seasons"]:
                m["seasons"].append(year)

        rows = 0
        for g in games:
            home = normalize(g.get("homeTeam") or "")
            away = normalize(g.get("awayTeam") or "")
            if not home or not away:
                continue
            hp, ap = g.get("homePoints"), g.get("awayPoints")
            neutral = bool(g.get("neutralSite"))
            date = (g.get("startDate") or "")[:10]
            for side, opp, pts, opp_pts, is_home in (
                (home, away, hp, ap, True),
                (away, home, ap, hp, False),
            ):
                # Only build a schedule for FBS programs; the other side still appears
                # as an opponent, which is the whole point of this file.
                if side not in members:
                    continue
                opp_class = g.get("awayClassification") if is_home else g.get("homeClassification")
                schedules.setdefault(side, {}).setdefault(str(year), []).append({
                    "opp": opp,
                    "site": "neutral" if neutral else ("home" if is_home else "away"),
                    "date": date,
                    "tbd": bool(g.get("startTimeTBD")),
                    "pts": pts,
                    "oppPts": opp_pts,
                    "result": result_for(pts, opp_pts) if g.get("completed") else None,
                    "completed": bool(g.get("completed")),
                    "oppFbs": opp_class == "fbs",
                    "week": g.get("week"),
                    "postseason": g.get("seasonType") == "postseason",
                })
                rows += 1
        print(f"    {len(members)} FBS teams, {len(games)} games, {rows} schedule rows", flush=True)

    # chronological order within each season
    for team, by_year in schedules.items():
        for y in by_year:
            by_year[y].sort(key=lambda r: (r["date"] or "9999-99-99", r["week"] or 99))

    # flag anything a reader should know about
    for team, meta in sorted(teams_meta.items()):
        for y in meta["seasons"]:
            got = len(schedules.get(team, {}).get(str(y), []))
            if got == 0:
                warnings.append(f"{team} {y}: FBS member with no games")
            elif got < 8:
                warnings.append(f"{team} {y}: only {got} games")
    return schedules, teams_meta, warnings


def main() -> int:
    key = os.environ.get("CFBD_API_KEY")
    if not key:
        print("ERROR: CFBD_API_KEY is not set. Add it to .env locally or as a GitHub "
              "Actions secret; this script will not run without it.", flush=True)
        return 2

    repo_root = Path(os.environ.get("FPS_REPO_ROOT", Path(__file__).resolve().parent.parent))
    out_path = repo_root / JSON_FILENAME
    start = int(os.environ.get("FPS_SCHEDULE_START", DEFAULT_START))
    end = int(os.environ.get("FPS_SCHEDULE_END", current_season()))
    seasons = list(range(start, end + 1))
    print(f"==> Seasons {seasons[0]}-{seasons[-1]}  ->  {out_path}", flush=True)

    schedules, teams_meta, warnings = build(seasons, key)
    if not schedules:
        print("ERROR: no schedules built; refusing to write an empty file.", flush=True)
        return 1

    payload = {
        "_meta": {
            "source": "CFBD /games and /teams/fbs",
            "fetchedAt": dt.datetime.utcnow().isoformat() + "Z",
            "seasons": seasons,
            "teams": len(schedules),
            "games": sum(len(v) for by in schedules.values() for v in by.values()),
        },
        "teams": teams_meta,
        "schedules": schedules,
    }
    new_bytes = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    if warnings:
        print(f"\n==> {len(warnings)} note(s):", flush=True)
        for w in warnings:
            print(f"    - {w}", flush=True)

    if os.environ.get("FPS_DRY_RUN") == "1":
        print(f"\n==> Dry run: would write {len(new_bytes):,} bytes", flush=True)
        return 0
    if out_path.exists() and out_path.read_bytes() == new_bytes:
        print("\n==> No change.", flush=True)
        return 0
    out_path.write_bytes(new_bytes)
    print(f"\n==> Wrote {out_path} ({len(new_bytes):,} bytes)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

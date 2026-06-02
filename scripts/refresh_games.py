"""
Front Porch Sports - in-season refresh, KEYLESS via ESPN.

Pulls current-season completed FBS games from ESPN's public scoreboard
endpoint (no API key), maps them to the site's locked JSON schema, and
REPLACES only the current season's rows in front_porch_games.json.
All prior seasons remain untouched.

Env vars:
  FPS_CURRENT_SEASON   optional  override the season year (int)
  FPS_REPO_ROOT        optional  override repo root path
  FPS_DRY_RUN          optional  "1" to compute but not write
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


ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard"
JSON_FILENAME = "front_porch_games.json"
HTTP_TIMEOUT = 30
HTTP_RETRIES = 3
HTTP_SLEEP = 0.20


def era_for(season: int) -> str:
    if season < 1936:  return "pre_modern"
    if season <= 1968: return "ap_era"
    if season <= 1997: return "modern"
    if season <= 2013: return "bcs"
    if season <= 2023: return "cfp_4team"
    return "cfp_12team"


def current_season() -> int:
    override = os.environ.get("FPS_CURRENT_SEASON")
    if override:
        return int(override)
    now = dt.datetime.utcnow()
    # CFB season starts late August. From Aug onwards we're "this year".
    return now.year if now.month >= 8 else now.year - 1


TEAM_REMAP = {
    "Ohio State": "Ohio St.", "Michigan State": "Michigan St.", "Penn State": "Penn St.",
    "Florida State": "Florida St.", "Mississippi State": "Mississippi St.", "Iowa State": "Iowa St.",
    "Oklahoma State": "Oklahoma St.", "Oregon State": "Oregon St.", "Kansas State": "Kansas St.",
    "Kent State": "Kent St.", "San Diego State": "San Diego St.", "San Jose State": "San Jose St.",
    "Colorado State": "Colorado St.", "Utah State": "Utah St.", "Boise State": "Boise St.",
    "Fresno State": "Fresno St.", "Washington State": "Washington St.", "Arizona State": "Arizona St.",
    "New Mexico State": "New Mexico St.", "Arkansas State": "Arkansas St.", "Texas State": "Texas St.",
    "Appalachian State": "Appalachian St.", "App State": "Appalachian St.", "Ball State": "Ball St.",
    "Georgia State": "Georgia St.", "Missouri State": "Missouri St.", "Sam Houston": "Sam Houston St.",
    "Sam Houston State": "Sam Houston St.", "NC State": "North Carolina St.",
    "North Carolina State": "North Carolina St.", "Ole Miss": "Mississippi", "Pitt": "Pittsburgh",
    "Louisiana": "Louisiana Lafayette", "Louisiana-Lafayette": "Louisiana Lafayette",
    "Massachusetts": "UMass", "Brigham Young": "BYU", "Southern California": "USC",
    "Southern Methodist": "SMU", "Texas Christian": "TCU", "Central Florida": "UCF",
    "Nevada Las Vegas": "UNLV", "Hawai'i": "Hawaii", "Miami (FL)": "Miami", "Miami (Florida)": "Miami",
    "UConn": "Connecticut", "USF": "South Florida", "Florida Atlantic": "FAU",
    "Florida International": "FIU", "UL Monroe": "Louisiana Monroe",
    "Louisiana-Monroe": "Louisiana Monroe", "ULM": "Louisiana Monroe",
}


def normalize(name: str) -> str:
    if not name: return ""
    n = str(name).strip()
    if n in TEAM_REMAP: return TEAM_REMAP[n]
    if n.endswith(" State"): return n[:-6] + " St."
    return n


def fetch(year, stype, week):
    params = {"dates": str(year), "seasontype": stype, "week": week, "groups": "80", "limit": 400}
    for attempt in range(HTTP_RETRIES):
        try:
            r = requests.get(ESPN_BASE, params=params, timeout=HTTP_TIMEOUT)
            if r.status_code == 200: return r.json()
            if r.status_code in (429, 502, 503, 504):
                time.sleep(1.5 ** attempt); continue
            return None
        except Exception:
            time.sleep(1.5 ** attempt)
    return None


def parse_event(event):
    try:
        season = int(event["season"]["year"])
        date_str = (event.get("date") or "")[:10]
        comp = event["competitions"][0]
        if not comp.get("status", {}).get("type", {}).get("completed", False): return None
        cs = comp["competitors"]
        home = next(c for c in cs if c.get("homeAway") == "home")
        away = next(c for c in cs if c.get("homeAway") == "away")
        home_team = normalize((home["team"] or {}).get("location") or (home["team"] or {}).get("displayName") or "")
        away_team = normalize((away["team"] or {}).get("location") or (away["team"] or {}).get("displayName") or "")
        if not home_team or not away_team: return None
        home_pts = int(home.get("score") or 0)
        away_pts = int(away.get("score") or 0)
        venue = comp.get("venue", {}) or {}
        addr = venue.get("address", {}) or {}
        is_tie = home_pts == away_pts
        winner = "" if is_tie else (home_team if home_pts > away_pts else away_team)
        safe_date = date_str.replace("-", "") if date_str else f"{season}00000"
        return {
            "game_id": f"{safe_date}_{home_team}_vs_{away_team}",
            "season": season,
            "game_date": date_str,
            "date_estimated": False,
            "era": era_for(season),
            "team_a": home_team, "team_b": away_team,
            "team_a_score": home_pts, "team_b_score": away_pts,
            "winner": winner, "is_tie": is_tie,
            "margin": abs(home_pts - away_pts),
            "total_points": home_pts + away_pts,
            "city": addr.get("city", "") or "",
            "state": addr.get("state", "") or "",
        }
    except Exception:
        return None


def fetch_season(year):
    games = []
    for stype, weeks in ((2, range(0, 17)), (3, range(1, 7))):
        for week in weeks:
            data = fetch(year, stype, week)
            if not data:
                time.sleep(HTTP_SLEEP); continue
            for ev in data.get("events", []):
                g = parse_event(ev)
                if g and g["season"] == year: games.append(g)
            time.sleep(HTTP_SLEEP)
    seen, unique = set(), []
    for g in games:
        k = (tuple(sorted([g["team_a"].lower(), g["team_b"].lower()])), g["game_date"])
        if k in seen: continue
        seen.add(k); unique.append(g)
    return unique


def main() -> int:
    season = current_season()
    repo_root = Path(os.environ.get("FPS_REPO_ROOT", Path(__file__).resolve().parent.parent))
    json_path = repo_root / JSON_FILENAME
    dry_run = os.environ.get("FPS_DRY_RUN") == "1"

    print(f"==> Season: {season}", flush=True)
    print(f"==> JSON path: {json_path}", flush=True)
    print(f"==> Dry run: {dry_run}", flush=True)

    if not json_path.exists():
        print(f"ERROR: {json_path} does not exist.", flush=True)
        return 2

    print(f"==> Pulling {season} from ESPN...", flush=True)
    new_games = fetch_season(season)
    print(f"    {len(new_games)} completed games for {season}", flush=True)

    with open(json_path, "r", encoding="utf-8") as f:
        existing = json.load(f)
    print(f"    {len(existing)} existing rows", flush=True)

    kept = [r for r in existing if int(r.get("season", 0)) != season]
    print(f"    Removed {len(existing) - len(kept)} for season {season}", flush=True)

    merged = kept + new_games
    merged.sort(key=lambda r: (r.get("game_date", ""), r.get("game_id", "")))
    print(f"    {len(merged)} rows after merge", flush=True)

    new_bytes = json.dumps(merged, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    with open(json_path, "rb") as f:
        old_bytes = f.read()

    if new_bytes == old_bytes:
        print("==> No change.", flush=True); return 0
    if dry_run:
        print("==> Dry run, skipping write.", flush=True); return 0

    json_path.with_suffix(".json.bak").write_bytes(old_bytes)
    json_path.write_bytes(new_bytes)
    print(f"==> Wrote {json_path} ({len(new_bytes):,} bytes)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
Front Porch Sports - in-season refresh.

Pulls current season games from CFBD (free tier), maps them to the site's
JSON schema, and replaces ONLY the current season's rows in
front_porch_games.json. All prior seasons remain untouched.

Env vars:
  CFBD_API_KEY         required  CFBD free tier API key
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
    print("ERROR: requests not installed. Run: pip install -r scripts/requirements.txt", flush=True)
    sys.exit(2)


CFBD_BASE = "https://api.collegefootballdata.com"
JSON_FILENAME = "front_porch_games.json"


def era_for(season: int) -> str:
    if season < 1936:
        return "pre_modern"
    if season <= 1968:
        return "ap_era"
    if season <= 1997:
        return "modern"
    if season <= 2013:
        return "bcs"
    if season <= 2023:
        return "cfp_4team"
    return "cfp_12team"


def current_season() -> int:
    override = os.environ.get("FPS_CURRENT_SEASON")
    if override:
        return int(override)
    now = dt.datetime.utcnow()
    return now.year if now.month >= 8 else now.year - 1


def cfbd_get(path: str, params: dict, api_key: str) -> list:
    url = f"{CFBD_BASE}{path}"
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    for attempt in range(3):
        r = requests.get(url, headers=headers, params=params, timeout=30)
        if r.status_code == 200:
            return r.json()
        if r.status_code in (429, 502, 503, 504):
            wait = 2 ** attempt
            print(f"  retry in {wait}s (status {r.status_code})", flush=True)
            time.sleep(wait)
            continue
        raise RuntimeError(f"CFBD {path} failed: HTTP {r.status_code} {r.text[:200]}")
    raise RuntimeError(f"CFBD {path} retries exhausted")


def fetch_season_games(season: int, api_key: str) -> list:
    all_games: list = []
    for season_type in ("regular", "postseason"):
        params = {"year": season, "seasonType": season_type, "division": "fbs"}
        games = cfbd_get("/games", params, api_key)
        all_games.extend(games)
    return all_games


def build_venue_map(api_key: str) -> dict:
    try:
        venues = cfbd_get("/venues", {}, api_key)
        return {v.get("id"): v for v in venues if v.get("id") is not None}
    except Exception as e:
        print(f"  WARN: venue lookup failed ({e}); city/state will be blank")
        return {}


def map_to_site_schema(g: dict, venues: dict):
    home = g.get("home_team")
    away = g.get("away_team")
    if not home or not away:
        return None
    if not g.get("completed"):
        return None

    home_pts = g.get("home_points")
    away_pts = g.get("away_points")
    if home_pts is None or away_pts is None:
        return None

    season = int(g["season"])
    start_date = g.get("start_date") or ""
    game_date = start_date[:10] if start_date else ""
    date_estimated = not bool(game_date)

    venue_id = g.get("venue_id")
    venue = venues.get(venue_id, {}) if venue_id else {}
    city = venue.get("city") or ""
    state = venue.get("state") or ""

    home_pts = int(home_pts)
    away_pts = int(away_pts)
    is_tie = home_pts == away_pts
    winner = home if home_pts > away_pts else (away if away_pts > home_pts else "")
    margin = abs(home_pts - away_pts)
    total_points = home_pts + away_pts

    safe_date = game_date.replace("-", "") if game_date else f"{season}00000"
    game_id = f"{safe_date}_{home}_vs_{away}"

    return {
        "game_id": game_id,
        "season": season,
        "game_date": game_date,
        "date_estimated": date_estimated,
        "era": era_for(season),
        "team_a": home,
        "team_b": away,
        "team_a_score": home_pts,
        "team_b_score": away_pts,
        "winner": winner,
        "is_tie": is_tie,
        "margin": margin,
        "total_points": total_points,
        "city": city,
        "state": state,
    }


def main() -> int:
    api_key = os.environ.get("CFBD_API_KEY", "").strip()
    if not api_key:
        print("ERROR: CFBD_API_KEY env var is required.", flush=True)
        return 2

    season = current_season()
    repo_root = Path(os.environ.get("FPS_REPO_ROOT", Path(__file__).resolve().parent.parent))
    json_path = repo_root / JSON_FILENAME
    dry_run = os.environ.get("FPS_DRY_RUN") == "1"

    print(f"==> Season: {season}", flush=True)
    print(f"==> Repo root: {repo_root}", flush=True)
    print(f"==> JSON path: {json_path}", flush=True)
    print(f"==> Dry run: {dry_run}", flush=True)

    if not json_path.exists():
        print(f"ERROR: {json_path} does not exist. Refusing to create from scratch.", flush=True)
        return 2

    print("==> Fetching CFBD games...", flush=True)
    cfbd_games = fetch_season_games(season, api_key)
    print(f"    {len(cfbd_games)} raw games returned", flush=True)

    venues = build_venue_map(api_key)
    print(f"    {len(venues)} venues loaded", flush=True)

    mapped: list = []
    for g in cfbd_games:
        row = map_to_site_schema(g, venues)
        if row:
            mapped.append(row)
    print(f"    {len(mapped)} completed games mapped to site schema", flush=True)

    print("==> Loading existing JSON...", flush=True)
    with open(json_path, "r", encoding="utf-8") as f:
        existing = json.load(f)
    print(f"    {len(existing)} existing game rows", flush=True)

    kept = [row for row in existing if int(row.get("season", 0)) != season]
    print(f"    {len(existing) - len(kept)} rows removed for season {season}", flush=True)

    merged = kept + mapped
    merged.sort(key=lambda r: (r.get("game_date", ""), r.get("game_id", "")))
    print(f"    {len(merged)} rows after merge", flush=True)

    new_bytes = json.dumps(merged, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    with open(json_path, "rb") as f:
        old_bytes = f.read()

    if new_bytes == old_bytes:
        print("==> No changes. Skipping write.", flush=True)
        return 0

    if dry_run:
        print("==> Dry run, skipping write.", flush=True)
        return 0

    backup_path = json_path.with_suffix(".json.bak")
    backup_path.write_bytes(old_bytes)
    json_path.write_bytes(new_bytes)
    print(f"==> Wrote {json_path} ({len(new_bytes):,} bytes)", flush=True)
    print(f"    Backup of previous: {backup_path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
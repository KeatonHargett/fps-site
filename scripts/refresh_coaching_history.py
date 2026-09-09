"""
Front Porch Sports - head-coaching tenures per team, from CollegeFootballData.

WHAT THIS FILE DELIBERATELY DOES NOT CONTAIN
  Whether a coach was fired, resigned or retired. The CFBD coach object has
  exactly five keys - firstName, lastName, id, hireDate, seasons - and no other
  CFBD endpoint carries a departure reason. Rather than invent the distinction,
  this ships hire year and departure year only. If a reliable structured source
  for the reason ever turns up, it belongs in a separate curated overlay file,
  not inferred here.

Two facts about the source that shape the output:

  1. hireDate is null for nearly everything before ~2000 (of Oklahoma St.'s 22
     coach records, only the last four carry one). So tenure years are derived
     from min/max of the seasons array, NOT from hireDate.

  2. Tenures overlap. A mid-season firing produces two coaches sharing a year -
     Oklahoma St. 2025 returns both Mike Gundy (2005-2025) and interim Doug
     Meacham (2025), with Eric Morris hired for 2026. This is increasingly
     common (6 schools in 2020, 4 in 2010, none before 1970), so a span that
     shares a year with another span for the same team is flagged "overlap":
     true and the UI splits that cell rather than picking a winner.

COVERAGE, which is a real gap and is reported in _meta:
  CFBD coaching data is FBS-only - 136 schools in 2025, with North Dakota State,
  Montana and Villanova all absent. Only about 138 of the 239 teams in
  front_porch_games.json get any coaching history at all, and coverage is
  near-zero before 1900 (2 schools in 1890, 23 in 1900). Teams with no data are
  simply absent from "teams" and the UI drops the coach band for them.

This script NEVER writes front_porch_games.json.

Env vars:
  CFBD_API_KEY      required   CollegeFootballData API key (Bearer token)
  FPS_REPO_ROOT     optional   override repo root path
  FPS_CACHE_DIR     optional   where to cache raw CFBD responses
  FPS_DRY_RUN       optional   "1" to compute but not write

Usage:
  python scripts/refresh_coaching_history.py
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
from refresh_games import normalize  # noqa: E402

CFBD_BASE = "https://api.collegefootballdata.com"
GAMES_FILENAME = "front_porch_games.json"
FBS_FILENAME = "fbs_teams.json"
OUT_FILENAME = "coaching_history.json"
HTTP_TIMEOUT = 45
HTTP_RETRIES = 5
SEASON_SLEEP = 2.0          # CFBD rate-limits a fast 140-season sweep; pace it.


def api_get(path: str, params: dict, key: str):
    """GET one CFBD endpoint with the retry shape refresh_schedules.py uses."""
    url = f"{CFBD_BASE}{path}"
    headers = {"Authorization": f"Bearer {key}", "Accept": "application/json"}
    for attempt in range(HTTP_RETRIES):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=HTTP_TIMEOUT)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (429, 502, 503, 504):
                time.sleep(2.0 + 3.0 * attempt)
                continue
            # Never echo the key, and never echo a body that might contain it.
            print(f"    ERROR: {path} returned HTTP {r.status_code}", flush=True)
            return None
        except Exception as e:
            print(f"    WARN: attempt {attempt + 1} failed ({type(e).__name__})", flush=True)
            time.sleep(2.0 + 3.0 * attempt)
    return None


def coaches_for_year(year: int, key: str, cache_dir: Path):
    """Every CFBD coach row touching one season, cached so a re-run does not re-hit."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    cf = cache_dir / f"cfbd_coaches_{year}.json"
    if cf.exists():
        try:
            return json.loads(cf.read_text(encoding="utf-8"))
        except Exception:
            pass
    rows = api_get("/coaches", {"year": year}, key)
    if rows is None:
        return None
    cf.write_text(json.dumps(rows), encoding="utf-8")
    return rows


def contiguous_runs(years):
    """[1984,1985,1987] -> [(1984,1985),(1987,1987)]. A coach can have two stints."""
    out = []
    for y in sorted(years):
        if out and out[-1][1] == y - 1:
            out[-1][1] = y
        else:
            out.append([y, y])
    return [(a, b) for a, b in out]


def encode(payload) -> bytes:
    return (json.dumps(payload, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def main() -> int:
    repo_root = Path(os.environ.get("FPS_REPO_ROOT", Path(__file__).resolve().parent.parent))

    key = os.environ.get("CFBD_API_KEY")
    if not key:
        env = repo_root / ".env"
        if env.exists():
            for line in env.read_text(encoding="utf-8").splitlines():
                if line.startswith("CFBD_API_KEY="):
                    key = line.split("=", 1)[1].strip()
                    break
    if not key:
        print("ERROR: CFBD_API_KEY is not set (env or .env).", flush=True)
        return 2

    games_path = repo_root / GAMES_FILENAME
    if not games_path.exists():
        print(f"ERROR: {games_path} does not exist.", flush=True)
        return 2
    cache_dir = Path(os.environ.get("FPS_CACHE_DIR", repo_root / ".cfbd_cache"))

    # Read-only. This script never writes the core dataset.
    games = json.loads(games_path.read_text(encoding="utf-8"))
    dataset_names = set()
    seasons = set()
    for g in games:
        dataset_names.add(g["team_a"])
        dataset_names.add(g["team_b"])
        seasons.add(int(g["season"]))
    years = sorted(seasons)
    print(f"==> {len(dataset_names)} dataset teams, seasons {years[0]}-{years[-1]}", flush=True)

    by_espn_id = {}
    fbs_path = repo_root / FBS_FILENAME
    if fbs_path.exists():
        for t in json.loads(fbs_path.read_text(encoding="utf-8")).get("teams", []):
            if t.get("espn_id"):
                by_espn_id[str(t["espn_id"])] = t["name"]
    print(f"==> {len(by_espn_id)} espn_id -> team-name entries from {FBS_FILENAME}", flush=True)

    # coach id -> {"name": str, "schools": {site name: set(years)}}
    coaches = {}
    unresolved = {}
    failed_fetch = []
    for yr in years:
        cached = (cache_dir / f"cfbd_coaches_{yr}.json").exists()
        rows = coaches_for_year(yr, key, cache_dir)
        if rows is None:
            failed_fetch.append(yr)
            print(f"    {yr}: FETCH FAILED", flush=True)
            continue
        for c in rows:
            cid = c.get("id")
            name = " ".join(x for x in [c.get("firstName"), c.get("lastName")] if x).strip()
            if cid is None or not name:
                continue
            rec = coaches.setdefault(cid, {"name": name, "schools": {}})
            for s in c.get("seasons") or []:
                # teamId is the ESPN id, same join as conference history.
                site = by_espn_id.get(str(s.get("teamId"))) or normalize(s.get("school") or "")
                if site not in dataset_names:
                    if s.get("school"):
                        unresolved.setdefault(s["school"], yr)
                    continue
                rec["schools"].setdefault(site, set()).add(int(s["year"]))
        n_schools = len({sc for c in rows for sc in
                         [s.get("school") for s in (c.get("seasons") or []) if s.get("year") == yr]})
        print(f"    {yr}: {len(rows):>4} coach rows, {n_schools:>3} schools", flush=True)
        time.sleep(0.01 if cached else SEASON_SLEEP)

    if failed_fetch:
        print(f"\nERROR: {len(failed_fetch)} season(s) failed to fetch: {failed_fetch}", flush=True)
        print("Refusing to write a partial file. Re-run to retry.", flush=True)
        return 1

    # Flatten to per-team spans.
    by_team = {}
    for rec in coaches.values():
        for site, yrs in rec["schools"].items():
            for start, end in contiguous_runs(yrs):
                by_team.setdefault(site, []).append({"name": rec["name"], "start": start, "end": end})

    # Flag spans that share a year with another span for the same team - a
    # mid-season change. The UI splits that cell instead of picking a winner.
    overlaps = 0
    for site, spans in by_team.items():
        spans.sort(key=lambda s: (s["start"], s["end"], s["name"]))
        for i, a in enumerate(spans):
            for j, b in enumerate(spans):
                if i != j and a["start"] <= b["end"] and b["start"] <= a["end"]:
                    a["overlap"] = True
                    break
        overlaps += sum(1 for s in spans if s.get("overlap"))

    covered = sorted(by_team)
    missing = sorted(dataset_names - set(by_team))
    total_spans = sum(len(v) for v in by_team.values())
    print(f"\n==> {len(covered)}/{len(dataset_names)} dataset teams have coaching data", flush=True)
    print(f"    {total_spans:,} tenures, {overlaps} of them overlapping (mid-season changes)",
          flush=True)
    print(f"    NO COACHING DATA for {len(missing)} teams (CFBD coaching is FBS-only)", flush=True)

    payload = {
        "_meta": {
            "source": "CFBD /coaches",
            "note": "Hire and departure YEARS only. CFBD carries no fired/resigned/retired "
                    "field, so that distinction is deliberately absent rather than invented.",
            "yearsFrom": "min/max of each coach's seasons array; hireDate is null pre-2000",
            "overlap": "true when a tenure shares a year with another - a mid-season change",
            "coverage": "FBS-only. Teams absent from 'teams' have no CFBD coaching data.",
            "fetchedAt": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "years": [years[0], years[-1]],
            "teams": len(covered),
            "teamsWithoutData": len(missing),
        },
        "teams": {k: by_team[k] for k in covered},
    }

    out_path = repo_root / OUT_FILENAME
    new_bytes = encode(payload)
    old_bytes = out_path.read_bytes() if out_path.exists() else b""
    print(f"==> {len(new_bytes):,} bytes", flush=True)

    if new_bytes == old_bytes:
        print("==> No change.", flush=True)
        return 0
    if os.environ.get("FPS_DRY_RUN") == "1":
        print(f"==> Dry run: would write {len(new_bytes):,} bytes", flush=True)
        return 0

    out_path.write_bytes(new_bytes)
    print(f"==> Wrote {out_path} ({len(new_bytes):,} bytes)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

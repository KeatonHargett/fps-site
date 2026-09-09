"""
Front Porch Sports - season-by-season conference affiliation for every team in
front_porch_games.json, from CollegeFootballData.

Why /teams?year= and not something else:
  Three CFBD endpoints expose a conference. Only /teams?year= gives one
  authoritative row per team per season with complete coverage. The conference
  fields on /games are the same values but are missing on a lot of early rows
  (only ~76% of game sides carry a conference in 1901, ~81% in 1925), and
  /records carries the same string with fewer rows. So /teams is the source and
  the already-cached /games responses are used as a free cross-check instead.

Verified against real realignment before the full pull was trusted:
  Oklahoma St. - Southwest 1915-1924, Missouri Valley 1925-1957, independent
  1958-1959, Big 8 1960-1995, Big 12 1996-. Michigan independent 1907-1917.
  Nebraska Big 8 -> Big 12 -> Big Ten 2011. Texas Southwest -> Big 12 -> SEC 2024.

Name joining, in two tiers, because the dataset says "Oklahoma St." while CFBD
says "Oklahoma State" and sometimes something else entirely ("App State"):
  1. fbs_teams.json espn_id -> CFBD team id. CFBD's team id IS the ESPN id, so
     this is exact for all 138 current FBS teams and survives renames.
  2. normalize() from refresh_games.py over school + alternateNames, for the
     other 101 historical/defunct programs.
  Together these resolve 239 of 239 distinct team names. A miss is reported,
  never silently dropped.

Independents:
  CFBD buckets these as "FBS Independents" / "FCS Independents" /
  "Pre-classification Independents". Those are classification buckets, not
  conferences, and shipping "FBS Independents" against a 1901 season would be an
  anachronism - the FBS did not exist. They are stored as null and rendered as
  "Independent".

This script NEVER writes front_porch_games.json. It only reads it to learn which
teams and which seasons matter.

Env vars:
  CFBD_API_KEY      required   CollegeFootballData API key (Bearer token)
  FPS_REPO_ROOT     optional   override repo root path
  FPS_CACHE_DIR     optional   where to cache raw CFBD responses
  FPS_DRY_RUN       optional   "1" to compute but not write

Usage:
  python scripts/refresh_conference_history.py
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
OUT_FILENAME = "conference_history.json"
HTTP_TIMEOUT = 45
HTTP_RETRIES = 5
SEASON_SLEEP = 2.0          # CFBD rate-limits a fast 140-season sweep; pace it.

# CFBD classification buckets that are not conferences. Stored as null.
INDEPENDENT = {
    "FBS Independents",
    "FCS Independents",
    "Pre-classification Independents",
    "Independent DII",
    "Independent DIII",
    "College Division Independents",
}


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


def teams_for_year(year: int, key: str, cache_dir: Path):
    """Every CFBD team row for one season, cached so a re-run does not re-hit the API."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    cf = cache_dir / f"cfbd_teams_{year}.json"
    if cf.exists():
        try:
            return json.loads(cf.read_text(encoding="utf-8"))
        except Exception:
            pass
    rows = api_get("/teams", {"year": year}, key)
    if rows is None:
        return None
    cf.write_text(json.dumps(rows), encoding="utf-8")
    return rows


def conferences_meta(key: str, cache_dir: Path):
    """The /conferences lookup, for display names and abbreviations."""
    cf = cache_dir / "cfbd_conferences.json"
    if cf.exists():
        try:
            return json.loads(cf.read_text(encoding="utf-8"))
        except Exception:
            pass
    rows = api_get("/conferences", {}, key)
    if rows is None:
        return []
    cf.write_text(json.dumps(rows), encoding="utf-8")
    return rows


def site_name_for(row, by_espn_id, dataset_names):
    """Map one CFBD team row onto the dataset's own team-name string, or None."""
    hit = by_espn_id.get(str(row.get("id")))
    if hit:
        return hit
    for cand in [row.get("school")] + list(row.get("alternateNames") or []):
        n = normalize(cand or "")
        if n in dataset_names:
            return n
    return None


def spans_from_years(year_conf: dict):
    """{year: conf} -> contiguous [{conf, start, end}] spans, gap years excluded."""
    out = []
    for yr in sorted(year_conf):
        conf = year_conf[yr]
        if out and out[-1]["conf"] == conf and out[-1]["end"] == yr - 1:
            out[-1]["end"] = yr
        else:
            out.append({"conf": conf, "start": yr, "end": yr})
    return out


def cross_check(cache_dir: Path, by_team, dataset_names):
    """Replay the already-cached /games responses and report disagreements.

    Costs nothing (the cache is on disk from backfill_season_type.py) and is the
    only independent source available on this data.
    """
    checked = agreed = 0
    conflicts = []
    for cf in sorted(cache_dir.glob("cfbd_[0-9][0-9][0-9][0-9].json")):
        try:
            year = int(cf.stem.split("_")[1])
            rows = json.loads(cf.read_text(encoding="utf-8"))
        except Exception:
            continue
        for g in rows:
            for side in ("home", "away"):
                conf = g.get(side + "Conference")
                team = normalize(g.get(side + "Team") or "")
                if not conf or team not in dataset_names:
                    continue
                ours = by_team.get(team, {}).get(year, "__missing__")
                if ours == "__missing__":
                    continue
                theirs = None if conf in INDEPENDENT else conf
                checked += 1
                if ours == theirs:
                    agreed += 1
                else:
                    conflicts.append((team, year, ours, theirs))
    return checked, agreed, conflicts


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
    print(f"==> {len(games):,} games, {len(dataset_names)} teams, "
          f"seasons {years[0]}-{years[-1]} ({len(years)} of them)", flush=True)

    by_espn_id = {}
    fbs_path = repo_root / FBS_FILENAME
    if fbs_path.exists():
        for t in json.loads(fbs_path.read_text(encoding="utf-8")).get("teams", []):
            if t.get("espn_id"):
                by_espn_id[str(t["espn_id"])] = t["name"]
    print(f"==> {len(by_espn_id)} espn_id -> team-name entries from {FBS_FILENAME}", flush=True)

    by_team = {}                 # site name -> {year: conf or None}
    unresolved = {}              # cfbd school -> first year seen
    failed_fetch = []
    for yr in years:
        cached = (cache_dir / f"cfbd_teams_{yr}.json").exists()
        rows = teams_for_year(yr, key, cache_dir)
        if rows is None:
            failed_fetch.append(yr)
            print(f"    {yr}: FETCH FAILED", flush=True)
            continue
        matched = 0
        for row in rows:
            name = site_name_for(row, by_espn_id, dataset_names)
            if name is None:
                unresolved.setdefault(row.get("school") or "?", yr)
                continue
            conf = row.get("conference")
            by_team.setdefault(name, {})[yr] = None if conf in INDEPENDENT else conf
            matched += 1
        print(f"    {yr}: {len(rows):>4} cfbd rows, {matched:>3} are dataset teams", flush=True)
        time.sleep(0.01 if cached else SEASON_SLEEP)

    if failed_fetch:
        print(f"\nERROR: {len(failed_fetch)} season(s) failed to fetch: {failed_fetch}", flush=True)
        print("Refusing to write a partial file. Re-run to retry.", flush=True)
        return 1

    missing = sorted(dataset_names - set(by_team))
    print(f"\n==> resolved {len(by_team)}/{len(dataset_names)} dataset teams", flush=True)
    if missing:
        print(f"    NO CONFERENCE DATA for {len(missing)}: {missing}", flush=True)

    # Cross-check against the cached /games conference fields. Free, and the only
    # independent source available.
    checked, agreed, conflicts = cross_check(cache_dir, by_team, dataset_names)
    if checked:
        print(f"\n==> cross-check vs cached /games: {agreed:,}/{checked:,} agree "
              f"({100.0 * agreed / checked:.2f}%), {len(conflicts):,} disagree", flush=True)
        seen = {}
        for team, year, ours, theirs in conflicts:
            seen.setdefault((ours, theirs), []).append(f"{team} {year}")
        for (ours, theirs), examples in sorted(seen.items(), key=lambda kv: -len(kv[1]))[:15]:
            print(f"    /teams={ours!r:34} /games={theirs!r:34} x{len(examples):<5} "
                  f"e.g. {examples[0]}", flush=True)
    else:
        print("\n==> cross-check skipped: no cached /games responses on disk", flush=True)

    meta_rows = conferences_meta(key, cache_dir)
    used = {c for years_map in by_team.values() for c in years_map.values() if c}
    conf_meta = {}
    for row in meta_rows:
        name = row.get("name")
        if name in used and name not in conf_meta:
            conf_meta[name] = {
                "abbr": row.get("abbreviation") or name,
                "full": row.get("shortName") or name,
            }
    # A conference CFBD used on a team row but has no /conferences entry for.
    for name in sorted(used - set(conf_meta)):
        conf_meta[name] = {"abbr": name, "full": name}

    teams_out = {name: spans_from_years(yrs) for name, yrs in sorted(by_team.items())}
    payload = {
        "_meta": {
            "source": "CFBD /teams?year= (conference per team per season)",
            "crossCheck": "CFBD /games homeConference/awayConference, from .cfbd_cache",
            "note": "conf null means independent - CFBD's *Independents buckets are "
                    "classifications, not conferences.",
            "fetchedAt": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "years": [years[0], years[-1]],
            "teams": len(teams_out),
            "conferences": len(conf_meta),
            "unresolvedTeams": missing,
        },
        "conferences": dict(sorted(conf_meta.items())),
        "teams": teams_out,
    }

    out_path = repo_root / OUT_FILENAME
    new_bytes = encode(payload)
    old_bytes = out_path.read_bytes() if out_path.exists() else b""
    total_spans = sum(len(v) for v in teams_out.values())
    print(f"\n==> {len(teams_out)} teams, {total_spans:,} spans, "
          f"{len(conf_meta)} conferences, {len(new_bytes):,} bytes", flush=True)

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

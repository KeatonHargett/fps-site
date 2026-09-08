"""
Front Porch Sports - one-time backfill of the `postseason` flag onto every row
of front_porch_games.json, from CollegeFootballData.

Why this exists rather than refresh_games.py:
  refresh_games.py only ever replaces the CURRENT season's rows, and ESPN's
  scoreboard endpoint has no data before 2001 (verified: 1973, 1992, 1996, 1999
  and 2000 all return zero events). Two thirds of this dataset predates ESPN's
  coverage, so the historical flag has to come from CFBD, which the repo already
  uses in refresh_schedules.py and already has a key for.

What it does and does NOT do:
  It loads the existing records and adds exactly ONE key to each. It never
  re-derives team names, scores, dates, cities or any other field, so the 15
  existing fields survive byte-for-byte. Verify that with --verify.

A note on what `postseason` means:
  It is CFBD's season type, NOT a bowl flag. CFBD tags conference championship
  games as postseason from roughly 1992-2000 (the 1992 SEC Championship is
  tagged postseason) but as regular from 2001 on. So a team's postseason count
  runs slightly ahead of its bowl-appearance count in that window. The field is
  deliberately not called is_bowl for that reason.

Rows that cannot be matched to a CFBD game get null, not False. Guessing
"regular" would fabricate a classification for a row we could not verify.

Env vars:
  CFBD_API_KEY      required   CollegeFootballData API key (Bearer token)
  FPS_REPO_ROOT     optional   override repo root path
  FPS_CACHE_DIR     optional   where to cache raw CFBD responses
  FPS_DRY_RUN       optional   "1" to compute but not write

Usage:
  python scripts/backfill_season_type.py            # fetch, join, write
  python scripts/backfill_season_type.py --verify   # byte-level check vs git HEAD
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
JSON_FILENAME = "front_porch_games.json"
FIELD = "postseason"
AFTER_KEY = "era"           # insert position, must match parse_event() in refresh_games.py
HTTP_TIMEOUT = 45
HTTP_RETRIES = 5
SEASON_SLEEP = 2.0          # CFBD rate-limits a fast 140-season sweep; pace it.
DATE_TOLERANCE_DAYS = 1     # CFBD startDate is UTC; game_date is local.


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


def season_rows(year: int, key: str, cache_dir: Path):
    """Every CFBD game for one season, cached so a re-run does not re-hit the API."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    cf = cache_dir / f"cfbd_{year}.json"
    if cf.exists():
        try:
            return json.loads(cf.read_text(encoding="utf-8"))
        except Exception:
            pass
    # seasonType=postseason as a server-side filter is broken (it returns almost
    # nothing), so pull both and split client-side, same as refresh_schedules.py.
    rows = api_get("/games", {"year": year, "seasonType": "both"}, key)
    if rows is None:
        return None
    cf.write_text(json.dumps(rows), encoding="utf-8")
    return rows


def build_index(rows):
    """(team-pair, date) -> is_postseason, for every date the game might carry."""
    idx = {}
    for g in rows:
        home = normalize(g.get("homeTeam") or "")
        away = normalize(g.get("awayTeam") or "")
        if not home or not away:
            continue
        raw = (g.get("startDate") or "")[:10]
        if not raw:
            continue
        try:
            d0 = dt.date.fromisoformat(raw)
        except ValueError:
            continue
        is_post = g.get("seasonType") == "postseason"
        pair = frozenset((home, away))
        for off in range(-DATE_TOLERANCE_DAYS, DATE_TOLERANCE_DAYS + 1):
            k = (pair, (d0 + dt.timedelta(days=off)).isoformat())
            # An exact-date hit must never be overwritten by a neighbour's tolerance.
            if off == 0:
                idx[k] = is_post
            else:
                idx.setdefault(k, is_post)
    return idx


def with_field(rec: dict, value):
    """Copy rec, inserting FIELD immediately after AFTER_KEY. Order is preserved."""
    out = {}
    for k, v in rec.items():
        out[k] = v
        if k == AFTER_KEY:
            out[FIELD] = value
    if FIELD not in out:          # defensive: a record without an `era` key
        out[FIELD] = value
    return out


def encode(records) -> bytes:
    """The exact encoding front_porch_games.json already uses."""
    return json.dumps(records, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def verify(repo_root: Path) -> int:
    """Prove the 15 original fields are untouched, byte for byte, vs git HEAD."""
    import subprocess
    json_path = repo_root / JSON_FILENAME
    cur = json.loads(json_path.read_text(encoding="utf-8"))
    base_raw = subprocess.run(
        ["git", "show", f"HEAD:{JSON_FILENAME}"],
        cwd=str(repo_root), capture_output=True, check=True,
    ).stdout
    base = json.loads(base_raw.decode("utf-8"))

    print(f"==> baseline (git HEAD): {len(base):,} records, {len(base_raw):,} bytes", flush=True)
    print(f"==> current on disk    : {len(cur):,} records", flush=True)
    ok = True
    if len(base) != len(cur):
        print(f"FAIL: record count changed {len(base):,} -> {len(cur):,}", flush=True)
        return 1
    print(f"PASS: record count unchanged at {len(cur):,}", flush=True)

    missing = [i for i, r in enumerate(cur) if FIELD not in r]
    if missing:
        print(f"FAIL: {len(missing):,} records missing '{FIELD}'", flush=True)
        ok = False
    else:
        print(f"PASS: '{FIELD}' present on all {len(cur):,} records", flush=True)

    bad = [i for i, r in enumerate(cur) if len(r) != 16]
    if bad:
        print(f"FAIL: {len(bad):,} records do not have exactly 16 keys", flush=True)
        ok = False
    else:
        print("PASS: every record has exactly 16 keys", flush=True)

    # The real test: strip the new key and the file must be byte-identical.
    stripped = []
    for r in cur:
        c = dict(r)
        c.pop(FIELD, None)
        stripped.append(c)
    if encode(stripped) == base_raw:
        print("PASS: stripping the new key reproduces git HEAD byte-for-byte", flush=True)
    else:
        print("FAIL: stripped output does NOT match git HEAD", flush=True)
        ok = False

    t = sum(1 for r in cur if r.get(FIELD) is True)
    f = sum(1 for r in cur if r.get(FIELD) is False)
    n = sum(1 for r in cur if r.get(FIELD) is None)
    print(f"==> {FIELD}: true={t:,}  false={f:,}  null={n:,}", flush=True)
    return 0 if ok else 1


def main() -> int:
    repo_root = Path(os.environ.get("FPS_REPO_ROOT", Path(__file__).resolve().parent.parent))

    if "--verify" in sys.argv:
        return verify(repo_root)

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

    json_path = repo_root / JSON_FILENAME
    if not json_path.exists():
        print(f"ERROR: {json_path} does not exist.", flush=True)
        return 2
    cache_dir = Path(os.environ.get("FPS_CACHE_DIR", repo_root / ".cfbd_cache"))

    old_bytes = json_path.read_bytes()
    records = json.loads(old_bytes.decode("utf-8"))
    print(f"==> {len(records):,} existing rows, {len(old_bytes):,} bytes", flush=True)
    if any(FIELD in r for r in records):
        print(f"NOTE: some rows already carry '{FIELD}'; they will be recomputed.", flush=True)

    seasons = sorted({int(r["season"]) for r in records})
    print(f"==> seasons {seasons[0]}-{seasons[-1]} ({len(seasons)} of them)", flush=True)

    by_season = {}
    for r in records:
        by_season.setdefault(int(r["season"]), []).append(r)

    flags = {}          # id(record) -> bool
    stats = {}          # season -> (rows, matched)
    failed_fetch = []
    for yr in seasons:
        cached = (cache_dir / f"cfbd_{yr}.json").exists()
        rows = season_rows(yr, key, cache_dir)
        if rows is None:
            failed_fetch.append(yr)
            stats[yr] = (len(by_season[yr]), 0)
            print(f"    {yr}: FETCH FAILED", flush=True)
            continue
        idx = build_index(rows)
        matched = 0
        for r in by_season[yr]:
            k = (frozenset((r["team_a"], r["team_b"])), r["game_date"])
            if k in idx:
                flags[id(r)] = idx[k]
                matched += 1
        n_rows = len(by_season[yr])
        stats[yr] = (n_rows, matched)
        print(f"    {yr}: {n_rows:>4} rows, {matched:>4} matched, {n_rows - matched:>3} unmatched",
              flush=True)
        time.sleep(0.01 if cached else SEASON_SLEEP)

    if failed_fetch:
        print(f"\nERROR: {len(failed_fetch)} season(s) failed to fetch: {failed_fetch}", flush=True)
        print("Refusing to write a partially-backfilled file. Re-run to retry.", flush=True)
        return 1

    merged = [with_field(r, flags.get(id(r))) for r in records]

    total = len(merged)
    t = sum(1 for r in merged if r[FIELD] is True)
    f = sum(1 for r in merged if r[FIELD] is False)
    n = sum(1 for r in merged if r[FIELD] is None)
    print(f"\n==> {total:,} rows: true={t:,}  false={f:,}  null={n:,}", flush=True)

    print("\n==> unmatched by decade:", flush=True)
    buckets = {}
    for yr in seasons:
        rows_n, matched = stats[yr]
        d = yr // 10 * 10
        a, b = buckets.get(d, (0, 0))
        buckets[d] = (a + rows_n, b + (rows_n - matched))
    for d in sorted(buckets):
        rows_n, un = buckets[d]
        if un:
            print(f"    {d}s  {rows_n:>6,} rows  {un:>5,} unmatched  ({100.0 * un / rows_n:.1f}%)",
                  flush=True)

    new_bytes = encode(merged)
    if new_bytes == old_bytes:
        print("\n==> No change.", flush=True)
        return 0
    if os.environ.get("FPS_DRY_RUN") == "1":
        print(f"\n==> Dry run: would write {len(new_bytes):,} bytes", flush=True)
        return 0

    json_path.write_bytes(new_bytes)
    print(f"\n==> Wrote {json_path} ({len(new_bytes):,} bytes, "
          f"+{len(new_bytes) - len(old_bytes):,})", flush=True)
    print("==> Now run:  python scripts/backfill_season_type.py --verify", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
Pick the week's six featured matchups and write featured_matchups.json at the
repo root.

Runs inside the existing Tuesday refresh job, after the games/teams/schedules
refreshers, so it scores against freshly-pulled data.

Week selection is self-advancing: it walks ESPN's weekly scoreboard and takes the
EARLIEST week that still has unplayed games. On a Tuesday that is the coming
weekend, and it needs no calendar table and no hardcoded week. The season comes
from refresh_games.current_season() - never a literal year.

Everything is keyless (the same ESPN host refresh_games.py already uses), so this
step has no secret to skip on, unlike the CFBD schedules refresh.

Scoring, per matchup:
    40  both teams in the AP Top 25   (20 if exactly one)
  + 25  an AP top-10 team is involved
  + 35  a named rivalry (rivalries.json)
  +0-20 all-time meetings, scaled
  +0-10 recency of the series

The whole card payload is precomputed here - records, percentages, bar widths,
current streak - so the home page paints the section from a ~6 KB file instead of
waiting on the 16 MB games dataset.

front_porch_games.json is READ ONLY. This script never writes it.

Env vars:
  FPS_REPO_ROOT        optional  override repo root path
  FPS_DRY_RUN          optional  "1" to compute but not write
  FPS_CURRENT_SEASON   optional  override season year (honoured by current_season)
  FPS_FEATURED_WEEK    optional  force a specific week (testing)

Usage:
  python scripts/compute_featured.py
"""

from __future__ import annotations
import json
import os
import sys
import time
import unicodedata
import datetime as dt
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: requests not installed. pip install -r scripts/requirements.txt", flush=True)
    sys.exit(2)

# Reuse the canonical ESPN->site name map rather than pasting a third copy of it.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from refresh_games import normalize, current_season  # noqa: E402

ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard"
ESPN_RANKINGS = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/rankings"
JSON_FILENAME = "featured_matchups.json"

HTTP_TIMEOUT = 30
HTTP_RETRIES = 3
HTTP_SLEEP = 0.20

FEATURED_COUNT = 6
MAX_WEEK = 16

# Scoring weights. Kept as named constants so the blend is tunable in one place.
W_BOTH_RANKED = 40
W_ONE_RANKED = 20
W_TOP10_BONUS = 25
W_RIVALRY = 35
W_MEETINGS_MAX = 20
W_RECENCY_MAX = 10
MEETINGS_FULL_CREDIT = 100  # a 100-meeting series earns the full meetings weight


def http_json(url: str, params: dict | None = None):
    last = None
    for attempt in range(HTTP_RETRIES):
        try:
            # No custom User-Agent: ESPN 403s some agent strings, and requests' own
            # default is what refresh_games.py has always used against this host.
            r = requests.get(url, params=params, timeout=HTTP_TIMEOUT)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (429, 502, 503, 504):
                time.sleep(1.5 ** attempt)
                continue
            print(f"    WARN: {url} returned HTTP {r.status_code}", flush=True)
            return None
        except Exception as e:
            last = e
            time.sleep(1.5 ** attempt)
    print(f"    WARN: {url} failed ({type(last).__name__})", flush=True)
    return None


def fold(name: str) -> str:
    """Accent-folded, lowercased key - mirrors fpsKey() in the pages."""
    if not name:
        return ""
    n = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode("ascii")
    return n.strip().lower()


# ---------------------------------------------------------------- AP Top 25

def ap_rankings() -> dict:
    """espn team id (str) -> AP rank (int). Empty dict if the poll is unavailable."""
    data = http_json(ESPN_RANKINGS)
    if not data:
        return {}
    for poll in (data.get("rankings") or []):
        if (poll.get("type") or "").lower() != "ap":
            continue
        out = {}
        for entry in (poll.get("ranks") or []):
            tid = str(((entry.get("team") or {}).get("id") or ""))
            cur = entry.get("current")
            if tid and isinstance(cur, int):
                out[tid] = cur
        print(f"    AP Top 25: {len(out)} teams (season "
              f"{(poll.get('season') or {}).get('year')}, week "
              f"{(poll.get('occurrence') or {}).get('value')})", flush=True)
        return out
    print("    WARN: no AP poll in the rankings payload", flush=True)
    return {}


# ------------------------------------------------------------ week + slate

def week_events(season: int, week: int) -> list:
    data = http_json(ESPN_SCOREBOARD, {
        "dates": str(season), "seasontype": "2", "week": str(week),
        "groups": "80", "limit": "400",
    })
    return (data or {}).get("events") or []


def pick_week(season: int) -> tuple:
    """Return (week, events) for the earliest week that still has unplayed games."""
    forced = os.environ.get("FPS_FEATURED_WEEK")
    if forced:
        w = int(forced)
        print(f"==> Week {w} (forced via FPS_FEATURED_WEEK)", flush=True)
        return w, week_events(season, w)

    for w in range(1, MAX_WEEK + 1):
        events = week_events(season, w)
        time.sleep(HTTP_SLEEP)
        if not events:
            continue
        unplayed = [e for e in events if not _completed(e)]
        print(f"    week {w}: {len(events)} games, {len(unplayed)} unplayed", flush=True)
        if unplayed:
            return w, events
    return 0, []


def _completed(event: dict) -> bool:
    comps = event.get("competitions") or []
    if not comps:
        return False
    status = (comps[0].get("status") or {}).get("type") or {}
    return bool(status.get("completed"))


def parse_matchups(events: list, fbs_keys: set) -> list:
    """[{a, b, espnA, espnB, date}] for unplayed FBS-vs-FBS games, deduped."""
    out, seen = [], set()
    for ev in events:
        if _completed(ev):
            continue
        comps = ev.get("competitions") or []
        if not comps:
            continue
        competitors = comps[0].get("competitors") or []
        if len(competitors) != 2:
            continue
        sides = []
        for c in competitors:
            team = c.get("team") or {}
            name = normalize(team.get("location") or team.get("displayName") or "")
            sides.append({
                "name": name,
                "espnId": str(team.get("id") or ""),
                "rank": ((c.get("curatedRank") or {}).get("current")),
            })
        # groups=80 still returns FCS opponents; both sides must be FBS programs.
        if not all(fold(s["name"]) in fbs_keys for s in sides):
            continue
        a, b = sorted(sides, key=lambda s: s["name"])
        key = (fold(a["name"]), fold(b["name"]))
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "a": a["name"], "b": b["name"],
            "espnA": a["espnId"], "espnB": b["espnId"],
            "curatedA": a["rank"], "curatedB": b["rank"],
            "date": (ev.get("date") or "")[:10],
        })
    return out


# ------------------------------------------------------- series from games

def build_series(games: list) -> dict:
    """folded pair key -> list of that pair's games, oldest first."""
    series: dict = {}
    for g in games:
        a, b = g.get("team_a"), g.get("team_b")
        if not a or not b:
            continue
        key = tuple(sorted((fold(a), fold(b))))
        series.setdefault(key, []).append(g)
    for rows in series.values():
        rows.sort(key=lambda g: (g.get("season") or 0, g.get("game_date") or ""))
    return series


def current_streak(rows: list) -> dict:
    """Port of currentH2HStreak() in compare.html: walk back from the most recent game."""
    if not rows:
        return {"count": 0, "team": None, "startYear": None, "endYear": None, "tied": False}
    latest = rows[-1]
    if latest.get("is_tie"):
        return {"count": 0, "team": None, "startYear": latest.get("season"),
                "endYear": latest.get("season"), "tied": True}
    team = latest.get("winner")
    count, start, end = 0, None, None
    for g in reversed(rows):
        if g.get("winner") == team and not g.get("is_tie"):
            count += 1
            if end is None:
                end = g.get("season")
            start = g.get("season")
        else:
            break
    return {"count": count, "team": team, "startYear": start, "endYear": end, "tied": False}


def pct3(v: float) -> str:
    """.658 - three decimals, leading zero stripped, matching the site's convention."""
    return ("%.3f" % v).lstrip("0") if v < 1 else "1.000"


# ------------------------------------------------------------------ scoring

def score_matchup(m: dict, ranks: dict, rivalry, meetings: int, last_season: int,
                  season: int) -> int:
    ra = ranks.get(m["espnA"]) or m.get("curatedA")
    rb = ranks.get(m["espnB"]) or m.get("curatedB")
    ra = ra if isinstance(ra, int) and 1 <= ra <= 25 else None
    rb = rb if isinstance(rb, int) and 1 <= rb <= 25 else None

    score = 0
    if ra and rb:
        score += W_BOTH_RANKED
    elif ra or rb:
        score += W_ONE_RANKED
    if (ra and ra <= 10) or (rb and rb <= 10):
        score += W_TOP10_BONUS
    if rivalry:
        score += W_RIVALRY
    score += int(round(W_MEETINGS_MAX * min(meetings, MEETINGS_FULL_CREDIT) / MEETINGS_FULL_CREDIT))
    if last_season:
        gap = max(0, season - last_season)
        score += max(0, W_RECENCY_MAX - 2 * gap)
    return score


def main() -> int:
    repo_root = Path(os.environ.get("FPS_REPO_ROOT", Path(__file__).resolve().parent.parent))
    dry_run = os.environ.get("FPS_DRY_RUN") == "1"
    out_path = repo_root / JSON_FILENAME
    season = current_season()

    print(f"==> Featured matchups for season {season}", flush=True)

    # --- inputs -----------------------------------------------------------
    fbs = json.loads((repo_root / "fbs_teams.json").read_text(encoding="utf-8"))
    meta_by_key = {}
    for t in fbs.get("teams", []):
        meta_by_key.setdefault(fold(t["name"]), t)
    fbs_keys = set(meta_by_key)

    try:
        riv_doc = json.loads((repo_root / "rivalries.json").read_text(encoding="utf-8"))
        rivalries = riv_doc.get("rivalries", riv_doc)
    except Exception as e:
        print(f"    WARN: rivalries.json unreadable ({e}); scoring without rivalry weight", flush=True)
        rivalries = {}
    riv_by_key = {}
    for k, v in rivalries.items():
        parts = k.split("|")
        if len(parts) == 2:
            riv_by_key[tuple(sorted((fold(parts[0]), fold(parts[1]))))] = v

    # READ ONLY - Kyle's dataset is never written by this script.
    games = json.loads((repo_root / "front_porch_games.json").read_text(encoding="utf-8"))
    series = build_series(games)
    print(f"    loaded {len(games):,} games, {len(series):,} distinct pairings", flush=True)

    ranks = ap_rankings()

    week, events = pick_week(season)
    if not events:
        print("==> No week with unplayed games found; leaving the existing file alone.", flush=True)
        return 0
    matchups = parse_matchups(events, fbs_keys)
    print(f"==> Week {week}: {len(matchups)} unplayed FBS-vs-FBS matchups", flush=True)
    if not matchups:
        print("==> Nothing to feature; leaving the existing file alone.", flush=True)
        return 0

    # --- score ------------------------------------------------------------
    scored = []
    for m in matchups:
        key = tuple(sorted((fold(m["a"]), fold(m["b"]))))
        rows = series.get(key, [])
        rivalry = riv_by_key.get(key)
        last_season = rows[-1].get("season") if rows else 0
        m["_score"] = score_matchup(m, ranks, rivalry, len(rows), last_season, season)
        m["_rows"] = rows
        m["_rivalry"] = rivalry
        scored.append(m)
    scored.sort(key=lambda m: (-m["_score"], m["a"], m["b"]))
    top = scored[:FEATURED_COUNT]

    # --- build the card payload -------------------------------------------
    cards = []
    for m in top:
        a, b = m["a"], m["b"]
        rows = m["_rows"]
        aw = sum(1 for g in rows if g.get("winner") == a)
        bw = sum(1 for g in rows if g.get("winner") == b)
        ties = sum(1 for g in rows if g.get("is_tie"))
        total = aw + bw + ties
        # Winsipedia convention: divide by every meeting played, so the three printed
        # percentages equal their own bar-segment widths and sum to 1.000.
        denom = total or 1
        a_meta = meta_by_key.get(fold(a), {})
        b_meta = meta_by_key.get(fold(b), {})
        streak = current_streak(rows)
        cards.append({
            "a": a, "b": b,
            "kickoff": m["date"],
            "aId": a_meta.get("espn_id", ""), "bId": b_meta.get("espn_id", ""),
            "aColor": "#" + (a_meta.get("color") or "003594"),
            "bColor": "#" + (b_meta.get("color") or "fe5c00"),
            "aAbbr": a_meta.get("abbreviation", ""), "bAbbr": b_meta.get("abbreviation", ""),
            "aRank": ranks.get(m["espnA"]), "bRank": ranks.get(m["espnB"]),
            "w": aw, "l": bw, "t": ties, "total": total,
            "aPct": pct3(aw / denom) if total else "",
            "bPct": pct3(bw / denom) if total else "",
            "aWidth": round(aw / denom * 100, 2),
            "tieWidth": round(ties / denom * 100, 2),
            "bWidth": round(bw / denom * 100, 2),
            "streak": streak,
            "rivalry": m["_rivalry"] or None,
            "url": "compare.html?team1=%s&team2=%s" % (
                requests.utils.quote(a, safe=""), requests.utils.quote(b, safe="")),
            "score": m["_score"],
        })
        print(f"    {m['_score']:>3}  {a} vs {b}  ({total} meetings, {ties} ties)"
              f"{'  [' + m['_rivalry']['name'] + ']' if m['_rivalry'] else ''}", flush=True)

    payload = {
        "_meta": {
            "source": "ESPN scoreboard + ESPN AP Top 25, scored against front_porch_games.json",
            "generatedAt": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "season": season,
            "week": week,
            "count": len(cards),
        },
        "matchups": cards,
    }
    new_bytes = (json.dumps(payload, ensure_ascii=False, indent=1) + "\n").encode("utf-8")

    if dry_run:
        print(f"==> DRY RUN: would write {len(new_bytes):,} bytes to {out_path}", flush=True)
        return 0
    if out_path.exists() and out_path.read_bytes() == new_bytes:
        print("==> No changes (file already current)", flush=True)
        return 0
    out_path.write_bytes(new_bytes)
    print(f"==> Wrote {out_path} ({len(new_bytes):,} bytes)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

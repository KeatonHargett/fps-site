"""
Front Porch Sports - build coaches_data.json: each school's head coach(es) by
season, with game counts, so every game in front_porch_games.json can be tied to
both teams' head coaches. front_porch_games.json is never modified.

Source:
  CollegeFootballData /coaches (one file per season, cached in .cfbd_cache/ as
  cfbd_coaches_<year>.json; shared with the other CFBD scripts). Each coach
  record lists the seasons they coached at each school with a game count.
  School names go through refresh_games.normalize().

Seasons with more than one head coach:
  Coaches are ordered within the season - a coach who also led the school the
  season before goes first, one who continues the season after goes last, then
  hire date - and the school's CFBD schedule for that season (date order) is cut
  by each coach's game count. The date of each coach's last game becomes the
  boundary. A game is assigned by comparing its date to those boundaries.
  Flagged as ambiguous (and listed in the report):
    - the coaches' game counts do not add up to the CFBD schedule length
    - the coaches cannot be ordered (no carry-over and no distinct hire dates)
    - a game in a split season has no date in front_porch_games.json

Overrides (coaches_overrides.json):
  Early seasons CFBD has no record of, co-coach labels and single-game fixes,
  each with a cited source and the name exactly as the source spells it. A
  season-level entry replaces CFBD for that school-season; an entry with game_id
  pins that one game. "No coach" is a valid value (a season the source says had
  no head coach). Overrides win over CFBD.

  STANDING RULE: official school or conference sources (school media guides,
  official athletics sites, conference media guides) outrank CFBD whenever the
  two conflict. A conflict is fixed with an override citing the official
  source, never by trusting CFBD's version.

Output (compact - compare.html loads it on every visit):
  {
    "_meta":   {...},
    "coaches": ["Nick Saban", ...],
    "teams":   { "<school>": { "<season>": [[coach_idx, games, "<last game date>"], ...] } },
    "games":   { "<game_id>": { "<school>": coach_idx } }      # single-game overrides
  }
  The date is only present on all but the last coach of a split season; a game on
  or before it belongs to that coach.

Env vars:
  CFBD_API_KEY   CollegeFootballData key (env or repo .env). Only needed for
                 seasons not cached or passed to --refresh. Never printed.

Usage:
  python scripts/build_coaches_data.py
  python scripts/build_coaches_data.py --refresh 2026
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from refresh_games import normalize  # noqa: E402
from backfill_season_type import api_get  # noqa: E402
from build_game_sites import REPO, CACHE_DIR, GAMES_FILE, load_key, season_rows  # noqa: E402

OUT_FILE = REPO / "coaches_data.json"
OVERRIDES_FILE = REPO / "coaches_overrides.json"


def coaches_for(year: int, refresh: bool, key_holder: dict):
    cf = CACHE_DIR / f"cfbd_coaches_{year}.json"
    if cf.exists() and not refresh:
        return json.loads(cf.read_text(encoding="utf-8"))
    if "key" not in key_holder:
        key_holder["key"] = load_key()
    if not key_holder["key"]:
        print(f"  WARN: coaches {year} not cached and CFBD_API_KEY is not set", flush=True)
        return []
    rows = api_get("/coaches", {"year": year}, key_holder["key"]) or []
    cf.write_text(json.dumps(rows), encoding="utf-8")
    print(f"  fetched coaches {year}: {len(rows):,}", flush=True)
    return rows


def schedules(season: int, refresh: bool, key_holder: dict):
    """school -> sorted list of CFBD game dates for one season."""
    out = defaultdict(list)
    for g in season_rows(season, refresh, key_holder):
        raw = (g.get("startDate") or "")[:10]
        if not raw:
            continue
        for side in ("homeTeam", "awayTeam"):
            t = normalize(g.get(side) or "")
            if t:
                out[t].append(raw)
    for t in out:
        out[t].sort()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", nargs="*", type=int, default=[])
    ap.add_argument("--report", nargs="*", default=["Alabama|Auburn", "Oklahoma St.|Oklahoma"])
    args = ap.parse_args()
    refresh = set(args.refresh)

    games = json.loads(GAMES_FILE.read_text(encoding="utf-8"))
    seasons_needed = sorted({g["season"] for g in games})
    key_holder: dict = {}

    # (school, season) -> {coach name: (games, hireDate)}
    by_ts: dict = defaultdict(dict)
    for y in seasons_needed:
        for c in coaches_for(y, y in refresh, key_holder):
            name = f"{c.get('firstName') or ''} {c.get('lastName') or ''}".strip()
            for s in c.get("seasons") or []:
                if s.get("year") != y or not s.get("games"):
                    continue
                by_ts[(normalize(s["school"]), y)][name] = (s["games"], c.get("hireDate") or "")

    coach_names: list[str] = []
    coach_ix: dict[str, int] = {}

    def cix(name):
        if name not in coach_ix:
            coach_ix[name] = len(coach_names)
            coach_names.append(name)
        return coach_ix[name]

    teams: dict = defaultdict(dict)
    ambiguous_ts = {}
    sched_cache = {}
    overrides = json.loads(OVERRIDES_FILE.read_text(encoding="utf-8"))["overrides"] if OVERRIDES_FILE.exists() else []
    season_ov = {(o["school"], o["season"]): o for o in overrides if "game_id" not in o}
    game_ov = defaultdict(dict)
    for o in overrides:
        if "game_id" in o:
            game_ov[o["game_id"]][o["school"]] = o

    for (school, season), cs in sorted(by_ts.items()):
        if (school, season) in season_ov:
            continue  # replaced by an override below
        if len(cs) == 1:
            (name, (n, _)), = cs.items()
            teams[school][str(season)] = [[cix(name), n]]
            continue
        prev = by_ts.get((school, season - 1), {})
        nxt = by_ts.get((school, season + 1), {})
        order = sorted(cs.items(), key=lambda kv: (kv[0] not in prev, kv[0] in nxt, kv[1][1][:10], kv[0]))
        keys = [(k not in prev, k in nxt, v[1][:10]) for k, v in order]
        issues = []
        if len(set(keys)) != len(keys):
            issues.append("coach order undetermined")
        if season not in sched_cache:
            sched_cache[season] = schedules(season, season in refresh, key_holder)
        dates = sched_cache[season].get(school, [])
        total = sum(v[0] for _, v in order)
        if total != len(dates):
            issues.append(f"coach games {total} vs CFBD schedule {len(dates)}")
        spans, cum = [], 0
        for i, (name, (n, _)) in enumerate(order):
            cum += n
            if i < len(order) - 1:
                last = dates[min(cum, len(dates)) - 1] if dates else None
                spans.append([cix(name), n, last])
            else:
                spans.append([cix(name), n])
        teams[school][str(season)] = spans
        if issues:
            ambiguous_ts[(school, season)] = (issues, [(coach_names[s[0]], s[1]) for s in spans])

    # Standing rule: official school / conference sources outrank CFBD, so an
    # override always replaces whatever CFBD says for that school-season or game.
    # Season-level overrides replace CFBD outright (one coach - or one co-coach label -
    # for the whole season). The game count comes from the CFBD schedule when it has one.
    for (school, season), o in sorted(season_ov.items()):
        if season not in sched_cache:
            sched_cache[season] = schedules(season, season in refresh, key_holder)
        n = len(sched_cache[season].get(school, [])) or None
        teams[school][str(season)] = [[cix(o["coach"]), n]]
        ambiguous_ts.pop((school, season), None)
    games_out = {gid: {school: cix(o["coach"]) for school, o in m.items()} for gid, m in game_ov.items()}

    def coach_of(team, g):
        """(coach index or None, reason)."""
        pinned = games_out.get(g["game_id"], {}).get(team)
        if pinned is not None:
            return pinned, None
        spans = teams.get(team, {}).get(str(g["season"]))
        if not spans:
            return None, "no CFBD coach for school+season"
        if len(spans) == 1:
            return spans[0][0], None
        if not g["game_date"]:
            return None, "split season, game has no date"
        for s in spans:
            if len(s) < 3 or (s[2] and g["game_date"] <= s[2]):
                return s[0], None
        return spans[-1][0], None

    covered = 0
    reasons = defaultdict(int)
    amb_games = []
    for g in games:
        ca, ra = coach_of(g["team_a"], g)
        cb, rb = coach_of(g["team_b"], g)
        if ca is not None and cb is not None:
            covered += 1
        for r in (ra, rb):
            if r:
                reasons[r] += 1
        for t in (g["team_a"], g["team_b"]):
            if (t, g["season"]) in ambiguous_ts and t not in games_out.get(g["game_id"], {}):
                amb_games.append((g, t))

    total = len(games)
    doc = {
        "_meta": {
            "source": "CollegeFootballData /coaches; split seasons cut by CFBD schedule order",
            "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
            "games_total": total, "games_with_both_coaches": covered,
            "ambiguous_team_seasons": len(ambiguous_ts),
            "overrides": {"season": len(season_ov), "game": sum(len(m) for m in game_ov.values())},
        },
        "coaches": coach_names,
        "teams": teams,
        "games": games_out,
    }
    OUT_FILE.write_text(json.dumps(doc, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")

    print(f"\n==> wrote {OUT_FILE.name}: {OUT_FILE.stat().st_size:,} bytes, "
          f"{len(coach_names):,} coaches, {sum(len(v) for v in teams.values()):,} team-seasons")
    print(f"==> games with both head coaches: {covered:,} / {total:,} ({covered / total:.1%})")
    print("==> missing coach (per team-side): " + ", ".join(f"{k}: {v:,}" for k, v in reasons.items()))
    print(f"==> split seasons: {sum(1 for t in teams.values() for s in t.values() if len(s) > 1):,}, "
          f"ambiguous: {len(ambiguous_ts):,} team-seasons touching {len(amb_games):,} game-sides")

    for spec in args.report:
        a, b = spec.split("|")
        pg = sorted([g for g in games if {g["team_a"], g["team_b"]} == {a, b}], key=lambda g: g["game_date"] or str(g["season"]))
        ok = [g for g in pg if coach_of(g["team_a"], g)[0] is not None and coach_of(g["team_b"], g)[0] is not None]
        print(f"\n==> {a} vs {b}: {len(ok)} / {len(pg)} games with both coaches ({len(ok) / max(1, len(pg)):.1%})")
        for g in pg:
            if g not in ok:
                miss = [t for t in (g["team_a"], g["team_b"]) if coach_of(t, g)[0] is None]
                print(f"      missing: {g['season']} {g['game_date']}  no coach for {', '.join(miss)}")
        for g, t in amb_games:
            if g in pg:
                iss, spans = ambiguous_ts[(t, g["season"])]
                print(f"      ambiguous: {g['season']} {t}: {'; '.join(iss)}  {spans}")
        splits = {(t, g["season"]) for g in pg for t in (a, b) if len(teams.get(t, {}).get(str(g["season"]), [])) > 1}
        for t, s in sorted(splits, key=lambda x: x[1]):
            print(f"      split season: {s} {t}: " + ", ".join(
                f"{coach_names[x[0]]} ({x[1]} g{', thru ' + x[2] if len(x) > 2 and x[2] else ''})" for x in teams[t][str(s)]))

    print(f"\n==> all ambiguous team-seasons ({len(ambiguous_ts)}):")
    for (t, s), (iss, spans) in sorted(ambiguous_ts.items(), key=lambda kv: kv[0][1]):
        print(f"      {s} {t}: {'; '.join(iss)}  {spans}")


if __name__ == "__main__":
    main()

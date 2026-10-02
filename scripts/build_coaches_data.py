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
  no head coach). Overrides win over CFBD, and are applied on every run.

  STANDING RULE: official school or conference sources (school media guides,
  official athletics sites, conference media guides) outrank CFBD whenever the
  two conflict. A conflict is fixed with an override citing the official
  source, never by trusting CFBD's version.

Output (compact - compare.html loads it after first paint):
  {
    "_meta":   {...},
    "coaches": ["Nick Saban", ...],
    "teams":   { "<school>": { "<season>": [[coach_idx, games, "<last game date>"], ...] } },
    "games":   { "<game_id>": { "<school>": coach_idx } }      # single-game overrides
  }
  The date is only present on all but the last coach of a split season; a game on
  or before it belongs to that coach.

Modes:
  full (default)        rebuild every season from the CFBD cache.
  --update-season Y...  CI / weekly refresh: re-fetch only these seasons from CFBD
                        (coaches + schedule) and recompute them; every other season
                        keeps what coaches_data.json already holds.
  A CFBD error is fatal: the script exits non-zero and leaves coaches_data.json
  untouched. The output is written to a temp file and swapped in only on success,
  and never if it would cover fewer games than the file it replaces.

Env vars:
  CFBD_API_KEY   CollegeFootballData key (env or repo .env). Never printed.
  FPS_DRY_RUN=1  compute and report, write nothing.

Usage:
  python scripts/build_coaches_data.py
  python scripts/build_coaches_data.py --refresh 2026
  python scripts/build_coaches_data.py --update-season 2026
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
from build_game_sites import (  # noqa: E402
    REPO, CACHE_DIR, GAMES_FILE, CFBDError, cfbd_fetch, season_rows, write_atomic,
)

OUT_FILE = REPO / "coaches_data.json"
OVERRIDES_FILE = REPO / "coaches_overrides.json"


def coaches_for(year: int, refresh: bool, key_holder: dict):
    cf = CACHE_DIR / f"cfbd_coaches_{year}.json"
    if cf.exists() and not refresh:
        return json.loads(cf.read_text(encoding="utf-8"))
    rows = cfbd_fetch("/coaches", {"year": year}, key_holder)  # raises CFBDError on failure
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
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


def coaches_by_team_season(years, refresh, key_holder):
    """(school, season) -> {coach name: (games, hireDate)} for the given seasons."""
    by_ts: dict = defaultdict(dict)
    for y in years:
        for c in coaches_for(y, y in refresh, key_holder):
            name = f"{c.get('firstName') or ''} {c.get('lastName') or ''}".strip()
            for s in c.get("seasons") or []:
                if s.get("year") != y or not s.get("games"):
                    continue
                by_ts[(normalize(s["school"]), y)][name] = (s["games"], c.get("hireDate") or "")
    return by_ts


def season_spans(school, season, cs, prev, nxt, dates):
    """Named spans for one school-season: [[name, games(, last date)], ...] + issues."""
    if len(cs) == 1:
        (name, (n, _)), = cs.items()
        return [[name, n]], []
    order = sorted(cs.items(), key=lambda kv: (kv[0] not in prev, kv[0] in nxt, kv[1][1][:10], kv[0]))
    keys = [(k not in prev, k in nxt, v[1][:10]) for k, v in order]
    issues = []
    if len(set(keys)) != len(keys):
        issues.append("coach order undetermined")
    total = sum(v[0] for _, v in order)
    if total != len(dates):
        issues.append(f"coach games {total} vs CFBD schedule {len(dates)}")
    spans, cum = [], 0
    for i, (name, (n, _)) in enumerate(order):
        cum += n
        if i < len(order) - 1:
            spans.append([name, n, dates[min(cum, len(dates)) - 1] if dates else None])
        else:
            spans.append([name, n])
    return spans, issues


def decode_named(doc):
    """coaches_data.json -> (school -> season -> named spans, game pins by name)."""
    names = doc.get("coaches", [])
    teams = {school: {season: [[names[s[0]]] + s[1:] for s in spans] for season, spans in seasons.items()}
             for school, seasons in doc.get("teams", {}).items()}
    pins = {gid: {school: names[ix] for school, ix in m.items()} for gid, m in doc.get("games", {}).items()}
    return teams, pins


def coach_resolver(teams_ix, games_out):
    def coach_of(team, g):
        """(coach index or None, reason)."""
        pinned = games_out.get(g["game_id"], {}).get(team)
        if pinned is not None:
            return pinned, None
        spans = teams_ix.get(team, {}).get(str(g["season"]))
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
    return coach_of


def covered_count(games, coach_of):
    return sum(1 for g in games if coach_of(g["team_a"], g)[0] is not None and coach_of(g["team_b"], g)[0] is not None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", nargs="*", type=int, default=[], help="seasons to re-fetch from CFBD (full build)")
    ap.add_argument("--update-season", nargs="*", type=int, default=None,
                    help="only recompute these seasons (fresh from CFBD); keep the rest from coaches_data.json")
    ap.add_argument("--report", nargs="*", default=["Alabama|Auburn", "Oklahoma St.|Oklahoma"])
    args = ap.parse_args()
    dry = os.environ.get("FPS_DRY_RUN") == "1"

    games = json.loads(GAMES_FILE.read_text(encoding="utf-8"))
    overrides = json.loads(OVERRIDES_FILE.read_text(encoding="utf-8"))["overrides"] if OVERRIDES_FILE.exists() else []
    season_ov = {(o["school"], o["season"]): o for o in overrides if "game_id" not in o}
    game_ov = defaultdict(dict)
    for o in overrides:
        if "game_id" in o:
            game_ov[o["game_id"]][o["school"]] = o

    key_holder: dict = {}
    incremental = args.update_season is not None
    baseline_doc = json.loads(OUT_FILE.read_text(encoding="utf-8")) if OUT_FILE.exists() else None
    named: dict = defaultdict(dict)     # school -> season(str) -> named spans
    ambiguous_ts = {}
    sched_cache = {}
    try:
        if incremental:
            target = sorted(set(args.update_season))
            if not target or not baseline_doc:
                sys.exit(f"FATAL: --update-season needs at least one season and an existing {OUT_FILE.name}")
            base_named, _ = decode_named(baseline_doc)
            for school, seasons in base_named.items():
                for season, spans in seasons.items():
                    if int(season) not in target:
                        named[school][season] = spans
            # Fresh CFBD for the target seasons only - a failed call raises.
            by_ts = coaches_by_team_season(target, set(target), key_holder)
            prev_names = lambda school, y: {s[0] for s in base_named.get(school, {}).get(str(y), [])}
        else:
            target = sorted({g["season"] for g in games})
            by_ts = coaches_by_team_season(target, set(args.refresh), key_holder)
            prev_names = lambda school, y: set(by_ts.get((school, y), {}))

        for (school, season), cs in sorted(by_ts.items()):
            if (school, season) in season_ov:
                continue  # replaced by an override below
            if season not in sched_cache and len(cs) > 1:
                sched_cache[season] = schedules(season, incremental or season in args.refresh, key_holder)
            spans, issues = season_spans(
                school, season, cs,
                prev=prev_names(school, season - 1),
                nxt=set(by_ts.get((school, season + 1), {})),
                dates=sched_cache.get(season, {}).get(school, []))
            named[school][str(season)] = spans
            if issues:
                ambiguous_ts[(school, season)] = (issues, [(s[0], s[1]) for s in spans])

        # Standing rule: official school / conference sources outrank CFBD, so an
        # override always replaces whatever CFBD says for that school-season or game.
        # Season-level overrides replace CFBD outright (one coach - or one co-coach
        # label - for the whole season); the game count comes from the CFBD schedule
        # when it is at hand.
        for (school, season), o in sorted(season_ov.items()):
            n = len(sched_cache.get(season, {}).get(school, [])) or None
            if n is None and baseline_doc:
                old = baseline_doc.get("teams", {}).get(school, {}).get(str(season))
                n = old[0][1] if old else None
            named[school][str(season)] = [[o["coach"], n]]
            ambiguous_ts.pop((school, season), None)
    except CFBDError as e:
        print(f"::error::{e}. Leaving {OUT_FILE.name} untouched.", flush=True)
        sys.exit(1)

    # Index names (first use order) and encode.
    coach_names: list[str] = []
    coach_ix: dict[str, int] = {}

    def cix(name):
        if name not in coach_ix:
            coach_ix[name] = len(coach_names)
            coach_names.append(name)
        return coach_ix[name]

    teams_ix = {school: {season: [[cix(s[0])] + s[1:] for s in spans]
                         for season, spans in sorted(seasons.items(), key=lambda kv: int(kv[0]))}
                for school, seasons in sorted(named.items())}
    games_out = {gid: {school: cix(o["coach"]) for school, o in m.items()} for gid, m in game_ov.items()}
    coach_of = coach_resolver(teams_ix, games_out)

    covered = covered_count(games, coach_of)
    total = len(games)
    if baseline_doc:
        old_teams = baseline_doc.get("teams", {})
        old_of = coach_resolver(old_teams, baseline_doc.get("games", {}))
        before = covered_count(games, old_of)
        if covered < before:
            print(f"::error::new build covers {covered:,} games, fewer than the {before:,} in the "
                  f"current {OUT_FILE.name}. Not writing.", flush=True)
            sys.exit(1)

    reasons = defaultdict(int)
    amb_games = []
    for g in games:
        for t in (g["team_a"], g["team_b"]):
            r = coach_of(t, g)[1]
            if r:
                reasons[r] += 1
            if (t, g["season"]) in ambiguous_ts and t not in games_out.get(g["game_id"], {}):
                amb_games.append((g, t))

    doc = {
        "_meta": {
            "source": "CollegeFootballData /coaches; split seasons cut by CFBD schedule order; "
                      "coaches_overrides.json (official sources outrank CFBD)",
            "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
            "games_total": total, "games_with_both_coaches": covered,
            "ambiguous_team_seasons_this_run": len(ambiguous_ts),
            "overrides": {"season": len(season_ov), "game": sum(len(m) for m in game_ov.values())},
        },
        "coaches": coach_names,
        "teams": teams_ix,
        "games": games_out,
    }

    print(f"\n==> mode: {'incremental ' + str(target) if incremental else 'full'}{' (dry run)' if dry else ''}")
    print(f"==> {len(coach_names):,} coaches, {sum(len(v) for v in teams_ix.values()):,} team-seasons")
    print(f"==> games with both head coaches: {covered:,} / {total:,} ({covered / total:.1%})")
    print("==> missing coach (per team-side): " + ", ".join(f"{k}: {v:,}" for k, v in reasons.items()))
    print(f"==> split seasons: {sum(1 for t in teams_ix.values() for s in t.values() if len(s) > 1):,}, "
          f"ambiguous (this run): {len(ambiguous_ts):,} team-seasons touching {len(amb_games):,} game-sides")

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
        splits = {(t, g["season"]) for g in pg for t in (a, b) if len(teams_ix.get(t, {}).get(str(g["season"]), [])) > 1}
        for t, s in sorted(splits, key=lambda x: x[1]):
            print(f"      split season: {s} {t}: " + ", ".join(
                f"{coach_names[x[0]]} ({x[1]} g{', thru ' + x[2] if len(x) > 2 and x[2] else ''})" for x in teams_ix[t][str(s)]))

    if ambiguous_ts:
        print(f"\n==> ambiguous team-seasons this run ({len(ambiguous_ts)}):")
        for (t, s), (iss, spans) in sorted(ambiguous_ts.items(), key=lambda kv: kv[0][1]):
            print(f"      {s} {t}: {'; '.join(iss)}  {spans}")

    if dry:
        print("\n==> dry run: nothing written")
        return
    write_atomic(OUT_FILE, doc)
    print(f"\n==> wrote {OUT_FILE.name}: {OUT_FILE.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()

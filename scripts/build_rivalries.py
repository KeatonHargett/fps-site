#!/usr/bin/env python3
"""
build_rivalries.py - the derived fields of rivalries.json, computed instead of hand typed.

  last_meeting  latest season the two teams met in front_porch_games.json (null if never)
  status        "active"  if they met in either of the last two completed seasons (or in
                          the season being played), or have an unplayed game between them
                          in schedules_data.json
                "dormant" otherwise
                A sourced status_override {"status", "reason", "source"} wins over the rule,
                for known cases the data can't see (e.g. a series formally paused with its
                next game scheduled years out).

"Completed" comes from the data, not the clock, so --check gives the same answer on any day:
S = the latest season in front_porch_games.json; S is still in progress while
schedules_data.json lists any unplayed S game. Last completed season C = S - 1 while S is in
progress, else S. Active if last_meeting >= C - 1.

Everything else in rivalries.json (names, trophies, logos, sources, tiers) is curated and
left exactly as it is. Team names must be dataset names; an unknown name is an error, never
a guess.

front_porch_games.json and schedules_data.json are READ ONLY.

Usage:
  python scripts/build_rivalries.py           rebuild the derived fields and write rivalries.json
  python scripts/build_rivalries.py --check   rebuild in memory, exit 1 on any byte difference
"""
import io
import json
import os
import sys

ROOT = os.environ.get("FPS_REPO_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RIVALRIES = os.path.join(ROOT, "rivalries.json")
GAMES = os.path.join(ROOT, "front_porch_games.json")
SCHEDULES = os.path.join(ROOT, "schedules_data.json")
STATUSES = ("active", "dormant")


def load(path):
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def serialise(doc, nl):
    # The file's existing format (indent 1, real UTF-8, its own line endings), so a rebuild
    # with no data change is byte-identical on Windows and on the Linux CI runner.
    return json.dumps(doc, indent=1, ensure_ascii=False).replace("\n", nl) + nl


def build(doc, games, schedules):
    meetings = {}
    names = set()
    for g in games:
        a, b = g["team_a"], g["team_b"]
        names.update((a, b))
        key = tuple(sorted((a, b)))
        if g["season"] > meetings.get(key, -1):
            meetings[key] = g["season"]
    latest = max(g["season"] for g in games)

    unplayed = set()
    in_progress = False
    for team, seasons in schedules["schedules"].items():
        for season, rows in seasons.items():
            for row in rows:
                if row.get("completed"):
                    continue
                unplayed.add(tuple(sorted((team, row["opp"]))))
                if int(season) == latest:
                    in_progress = True
    last_completed = latest - 1 if in_progress else latest

    errors, changes = [], []
    for key, r in doc["rivalries"].items():
        for t in (r["team1"], r["team2"]):
            if t not in names:
                errors.append(f"{key}: team {t!r} is not a front_porch_games.json name")
        pair = tuple(sorted((r["team1"], r["team2"])))
        last = meetings.get(pair)
        status = "active" if ((last is not None and last >= last_completed - 1) or pair in unplayed) else "dormant"
        ov = r.get("status_override")
        if ov is not None:
            if ov.get("status") not in STATUSES or not ov.get("reason") or not ov.get("source"):
                errors.append(f"{key}: status_override needs status ({'/'.join(STATUSES)}), reason and source")
            else:
                status = ov["status"]
        if r.get("last_meeting") != last or r.get("status") != status:
            changes.append((key, r["name"], r.get("last_meeting"), last, r.get("status"), status))
        r["last_meeting"] = last
        r["status"] = status
    return errors, changes, latest, in_progress, last_completed


def main(argv):
    check = "--check" in argv
    with io.open(RIVALRIES, encoding="utf-8", newline="") as f:
        raw = f.read()
    nl = "\r\n" if "\r\n" in raw else "\n"
    doc = json.loads(raw)
    games = load(GAMES)
    games = games if isinstance(games, list) else games["games"]
    errors, changes, latest, in_progress, last_completed = build(doc, games, load(SCHEDULES))
    if errors:
        print("build_rivalries: FAILED")
        for e in errors:
            print("  " + e)
        return 1
    out = serialise(doc, nl)
    print(f"build_rivalries: {len(doc['rivalries'])} rivalries; latest season {latest} "
          f"({'in progress' if in_progress else 'complete'}), last completed {last_completed}; "
          f"active = met {last_completed - 1} or later, or an unplayed game on the schedule")
    for key, name, old_last, last, old_status, status in changes:
        print(f"  {name} ({key}): last_meeting {old_last} -> {last}, status {old_status} -> {status}")
    if check:
        if out != raw:
            print("build_rivalries: --check FAILED - rivalries.json is not what the build produces "
                  "(run python scripts/build_rivalries.py and commit)")
            return 1
        print("build_rivalries: OK - committed rivalries.json is byte-identical to a fresh build")
        return 0
    if out != raw:
        with io.open(RIVALRIES, "w", encoding="utf-8", newline="") as f:
            f.write(out)
        print(f"build_rivalries: wrote {RIVALRIES}")
    else:
        print("build_rivalries: no change")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

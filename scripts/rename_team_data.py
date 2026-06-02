"""
Server-side one-off: rename legacy team names in front_porch_games.json to the
canonical names used by TEAM_META across the HTML pages. Idempotent — running
this on already-canonical data is a no-op.

Renames:
  'Mississippi'         -> 'Ole Miss'
  'Southern Mississippi'-> 'Southern Miss'
  'San Jose St.'        -> 'San José St.'
"""
import json, os, sys

PATH = 'front_porch_games.json'
RENAMES = {
    'Mississippi':          'Ole Miss',
    'Southern Mississippi': 'Southern Miss',
    'San Jose St.':         'San José St.',
}

with open(PATH, 'r', encoding='utf-8') as f:
    games = json.load(f)

count = 0
per_team = {k: 0 for k in RENAMES}
for g in games:
    for field in ('team_a', 'team_b', 'winner'):
        v = g.get(field)
        if v in RENAMES:
            g[field] = RENAMES[v]
            count += 1
            per_team[v] += 1

if count == 0:
    print("Nothing to rename (already canonical).")
    sys.exit(0)

with open(PATH, 'w', encoding='utf-8') as f:
    json.dump(games, f, separators=(',', ':'))

for old, n in per_team.items():
    print(f"  '{old}' -> '{RENAMES[old]}': {n} field updates")
print(f"Total fields updated: {count}")
print(f"New file size: {os.path.getsize(PATH)} bytes")

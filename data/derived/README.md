# data/derived/ - GENERATED FILES, DO NOT EDIT BY HAND

Everything in this folder is produced by `scripts/build_derived_data.py` from
`front_porch_games.json` (read only), `game_sites.json`, `game_venues.json` and
`coaches_data.json`. Hand edits are overwritten on the next build.

Rebuild and verify:

    python scripts/build_derived_data.py
    node scripts/parity_check.js

The weekly GitHub Actions refresh runs both after the data refresh; if either fails,
nothing is committed or deployed and the previous files stay in place.

- `manifest.json` - entry point (short cache): team names/slugs and the current file
  name of every hashed file.
- `teams_index.<hash>.json` - shared team lookup.
- `league.<hash>.json` - league-wide aggregates (rank.html, team.html, compare.html).
- `home.<hash>.json` - index.html hero counts and Blue Bloods records.
- `teams/<slug>.<hash>.json` - every game involving one team, with location, coaches
  and venue. Format documented at the top of `scripts/build_derived_data.py` and decoded
  by `js/derived-data.js`.

Hashed files never change content under the same name, so they are cached for a year
(`immutable`). If any derived file fails to load, pages fall back to
`front_porch_games.json`.

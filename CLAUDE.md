# Front Porch Sports

Before any data, records, rivalry, filter, caching, or deploy work, read docs/data-standards.md and follow it.

Front Porch Sports (frontporchsports.com) is a static college football rivalry site: head-to-head series records, team pages, all-time program records and rankings, schedules and a scoreboard, built from vanilla HTML/JS with no framework or build step and hosted on Netlify. The game history lives in front_porch_games.json, which is read only; every other dataset (derived files in data/derived/, program_stats.json, rivalries.json, schedules, sites and coaches) is produced by the scripts in scripts/ and kept honest in CI by scripts/build_program_records.py --check, scripts/build_rivalries.py --check and scripts/parity_check.js. Production deploys run only from main through .github/workflows/weekly_refresh.yml, which also refreshes the data every Tuesday during the season.

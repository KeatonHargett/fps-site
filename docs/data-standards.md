# Front Porch Sports: Data and Build Standards

## Sources
- front_porch_games.json (Kyle Umlang) is never modified. Verify its checksum on every build.
- All new data is additive, in separate files built by scripts. Nothing is hand edited.
- Official sources outrank CFBD when they conflict: NCAA Records Book, then the school's own media guide or athletics site, then Wikipedia (via the MediaWiki API with a descriptive User-Agent), then CFBD.
- Never scrape sites that block bots or prohibit scraping (stats.ncaa.org, Sports Reference). Downloading a published PDF (Records Book, media guide) is fine.
- Every override entry carries a source URL. Never guess a name or number. If no source exists, leave it missing and show a "missing data" note.

## All time records
- Built by scripts/build_program_records.py from a pinned Wikipedia revision, the NCAA Records Book, CFBD for later seasons, and a sourced adjustments file. Reproducible byte for byte in CI.
- Official NCAA count is the main number everywhere. On field count shows as a second line with an asterisk where wins were vacated or forfeited. Footnote wording comes from js/record-notes.js.
- Rank pages sort by official by default, with an On field toggle saved in the URL (basis=onfield).
- FCS and lower division era games are included, as the NCAA does.
- Michigan uses its media guide (1,021 through 2025), the only documented exception to the Records Book.
- Oklahoma St. claimed and recognized national titles = 1 (1945).
- Weeks at AP #1 come from the NCAA Records Book list ("as of 2025").

## Hidden categories (until rebuilt from sources)
Consensus All Americans, NFL draft picks, first round picks, conference titles, bowl appearances and record, records vs ranked teams, recognized national titles, weeks in AP poll, and the /rankings composite score. Old links redirect with "This category is being rebuilt with verified data."
Rebuild order: weeks in AP poll, conference titles, bowls, recognized titles, All Americans and draft picks, then the composite.

## Location and coach filters
- Site data: CFBD neutral site flag, filled from the game file's city field, plus a sourced overrides file. Alabama vs Auburn in Birmingham 1948 to 1988 = Neutral. Designated home games at a regular secondary home stadium (Alabama at Legion Field 1990 to 1998, Arkansas in Little Rock, Ole Miss in Jackson) = Home.
- Coach data: CFBD plus a sourced coaches_overrides.json. Midseason changes resolve by game date. "No coach" is a valid value.

## Rivalry logos
- Logos sourced from Wikipedia, mostly fair use files. Display on frontporchsports.com only, never on FrontPorchSports.shop merch.
- Single game logos and unverified fan made logos are excluded. Current sponsor branded logos are kept; recheck each preseason.
- Florida vs Georgia displays as "Florida–Georgia" (never the cocktail party nickname).
- Featured matchups: tier 1 rivalries (original 64) get the full +35 bonus, tier 2 get +10.

## Rivalry trophies
- Trophy names come from official school athletics sites or media guides first; Wikipedia infoboxes only as a fallback. Every tier 1 entry has trophy_source; tier 2 entries are trophy_verified: false until checked.
- Show only a football trophy on a football matchup. All sports series trophies are not shown as the football trophy. Retired trophies get no trophy line.
- Three way trophies are not shown on head to head rows unless official and widely recognized. Commander-in-Chief's Trophy shows as "(three-way)" on all three service academy pairs. The Florida Cup is not shown.
- Bedlam: "Bell Clapper / Crystal Bell". Source: go.okstate.edu/about-osu/traditions/bedlam.
- Purdue vs Illinois: "Purdue Cannon" (Purdue calls it the Cannon Trophy; both noted).
- Official long names are kept; captions wrap to two centered lines on phones rather than being shortened.
- last_meeting and status are computed by scripts/build_rivalries.py from game and schedule data, never typed by hand. Active = met in the last 2 completed seasons or has a scheduled future game. Sourced status_override handles formally paused series.

## Build and deploy rules
- Work on a branch, draft PR, preview only. Production deploys only from main, after CI, the records build check, the rivalry derived fields check, and the parity check pass.
- Record the rollback deploy ID before every production deploy.
- Caching: HTML, non hashed JS/CSS, data files, and rivalry logos use "public, max-age=0, must-revalidate". Content hashed derived files use "max-age=31536000, immutable".
- Team name aliases (osu, Oklahoma State, ohst, etc.) resolve through one shared resolver on every page.
- Mobile layout: the compare header must end above the 667px fold at 375px wide.
- Internal files (docs, scripts, audits, build inputs, CLAUDE.md, README.md) must return 404 on production; new internal folders get added to the netlify.toml block list.
- Deploys upload only the staged public folder; internal files never ship.

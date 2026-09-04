# Front Porch Sports

Static site for college football head to head rivalry records, deployed on Netlify.

Live: https://frontporchsports.com
Netlify project: front-porch-sports
Netlify site ID: ba621860-d998-4c7e-a858-94c100312b49

## Layout

```
.
|-- index.html                          live page, do not redesign
|-- teams.html  team.html               team directory and per-team profile
|-- compare.html  games.html            matchup comparison and full game list
|-- rankings.html  rank.html            all-time rankings and per-category page
|-- heisman.html                        Heisman winners by program
|-- 404.html                            branded not-found page (Netlify serves it automatically)
|-- front_porch_games.json              dataset the pages fetch
|-- fbs_teams.json  program_stats.json  supporting datasets
|-- historical_opponents.json  upcoming_lines.json
|-- robots.txt  sitemap.xml  llms.txt   crawler files
|-- favicon.ico  favicon-16/32.png      brand icons (generated from the poker chip mark)
|-- apple-touch-icon.png  icon-192/512.png
|-- site.webmanifest
|-- og-image.png  logo.png              social share image and wordmark
|-- netlify.toml                        Netlify publish config, security and cache headers
|-- scripts/
|   |-- refresh_games.py                ESPN pull (keyless), current season only
|   |-- refresh_fbs_teams.py            ESPN standings -> fbs_teams.json
|   |-- refresh_schedules.py            CFBD pull -> schedules_data.json (needs CFBD_API_KEY)
|   |-- generate_sitemap.py             regenerates sitemap.xml
|   |-- requirements.txt
|-- .github/
    |-- workflows/
        |-- weekly_refresh.yml          weekly auto refresh during season
```

## SEO files

`sitemap.xml` is generated, not hand-edited. It lists the 6 static routes plus one
URL per FBS program and one per ranking category (154 URLs). Regenerate it after
any change to `fbs_teams.json` or to the `CATEGORIES` map in `rank.html`:

```
python scripts/generate_sitemap.py
```

`team.html`, `compare.html`, `games.html` and `rank.html` each render many
different pages from one HTML file. Their inline JS rewrites `title`,
`meta description`, `canonical` and the `og:` tags from the query string via the
`fpsMeta()` helper, so each variant is a distinct page to a crawler. If you add a
query parameter that changes what a page shows, update its `fpsMeta()` call too.

`robots.txt` deliberately allows the JSON datasets. Every page renders its
content client-side from those files, so blocking them would leave crawlers with
empty page shells.

## Deploy

This repo is wired to Netlify. Every push to main triggers a Netlify build and deploy. No more dragging files.

To wire Netlify to this repo the first time:

1. Push this repo to GitHub.
2. In Netlify, open the front-porch-sports site, go to Site configuration -> Build and deploy -> Continuous deployment -> Link repository, and select this repo on the main branch.
3. Confirm the publish directory is the repo root (.) and the build command is empty.

## Automation

The weekly refresh runs every Tuesday at 12:00 UTC from August through January. It can also be triggered manually from the Actions tab.

The workflow uses these GitHub repo secrets:

| Secret | Used by | Notes |
| --- | --- | --- |
| NETLIFY_AUTH_TOKEN | deploy step | Netlify personal access token. |
| NETLIFY_SITE_ID | deploy step | Netlify site id. |
| CFBD_API_KEY | refresh_schedules.py | CollegeFootballData.com key. Never commit. If unset, the schedules step is skipped and the rest of the refresh still runs. |

FPS_CURRENT_SEASON is a workflow_dispatch input, not a secret: if unset, the script
derives the season from the system date.

Add secrets at GitHub -> repo -> Settings -> Secrets and variables -> Actions -> New repository secret.
 <!-- v25 deploy nudge -->
## Refresh behavior

- refresh_games.py pulls current season games from ESPN (keyless) where completed = true.
- Games already in front_porch_games.json for the current season are replaced, not merged, because in-season data is volatile.
- All prior seasons are left untouched.
- refresh_schedules.py rebuilds schedules_data.json (2022-present) from CFBD. This is a
  separate, additive file and the only place FCS and other non-FBS opponents appear;
  front_porch_games.json stays FBS-vs-FBS and is never written by it.
- If the resulting JSON is identical to the existing one, no commit is made.

## Local dev

No build step. Open index.html in a browser, or run a local server:

```
py -m http.server 5500
```

Then visit http://localhost:5500.

## Do not change the design

The HTML, CSS, and JavaScript in index.html are locked. Only front_porch_games.json is updated by automation.

## Credits

All rights reserved. Site built by Keaton Hargett (https://keatonhargett.com).
<!-- pipe-check 2026-06-02T06:32:21Z -->


<!-- v25 deploy trigger: re-publish after server side dataset rename -->

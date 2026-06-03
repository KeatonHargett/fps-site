# Front Porch Sports

Static site for college football head to head rivalry records, deployed on Netlify.

Live: https://front-porch-sports.netlify.app
Netlify site ID: 3970b88d-f352-4ca3-85ad-80b8bcca3ebb

## Layout

```
.
|-- index.html                          live page, do not redesign
|-- front_porch_games.json              dataset the page fetches
|-- netlify.toml                        Netlify build and headers config
|-- scripts/
|   |-- refresh_games.py                CFBD pull, current season only
|   |-- requirements.txt
|-- .github/
    |-- workflows/
        |-- weekly_refresh.yml          weekly auto refresh during season
```

## Deploy

This repo is wired to Netlify. Every push to main triggers a Netlify build and deploy. No more dragging files.

To wire Netlify to this repo the first time:

1. Push this repo to GitHub.
2. In Netlify, open the front-porch-sports site, go to Site configuration -> Build and deploy -> Continuous deployment -> Link repository, and select this repo on the main branch.
3. Confirm the publish directory is the repo root (.) and the build command is empty.

## Automation

The weekly refresh runs every Tuesday at 12:00 UTC from August through January. It can also be triggered manually from the Actions tab.

The workflow uses two GitHub repo secrets:

| Secret | Used by | Notes |
| --- | --- | --- |
| CFBD_API_KEY | refresh_games.py | CollegeFootballData.com free tier key. Never commit. |
| FPS_CURRENT_SEASON | optional override | If unset, the script derives the season from the system date. |

Add secrets at GitHub -> repo -> Settings -> Secrets and variables -> Actions -> New repository secret.
 <!-- v25 deploy nudge -->
## Refresh behavior

- The script pulls current season games from CFBD where completed = true.
- Games already in front_porch_games.json for the current season are replaced, not merged, because in-season data is volatile.
- All prior seasons are left untouched.
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

All rights reserved. Dataset compiled by Kyle Umlang. Site built by Keaton Hargett (https://keatonhargett.com).
<!-- pipe-check 2026-06-02T06:32:21Z -->


<!-- v25 deploy trigger: re-publish after server side dataset rename -->

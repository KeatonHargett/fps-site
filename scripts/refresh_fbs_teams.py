"""
Build the canonical FBS team list from ESPN (keyless) and write fbs_teams.json
at the repo root.

Approach: enumerate the 11 known FBS conferences by ESPN group id and pull
each conference's roster via /teams?groups=<id>. This avoids ESPN's
group=80 endpoint, which returns FCS and lower divisions, and avoids the
scoreboard endpoint, which includes any opponent of an FBS team.

Names are normalized with the same map used in refresh_games.py.

Env vars:
  FPS_REPO_ROOT          optional   override repo root path

Usage:
  python scripts/refresh_fbs_teams.py
"""

from __future__ import annotations
import json
import os
import sys
import time
import unicodedata
import datetime as dt
import urllib.request
import urllib.error
from pathlib import Path


ESPN_STANDINGS = "https://site.web.api.espn.com/apis/v2/sports/football/college-football/standings"
ESPN_TEAM_BY_ID = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/teams/{id}"
HTTP_TIMEOUT = 30
HTTP_SLEEP   = 0.20
HTTP_RETRIES = 3

# ESPN group IDs for each FBS conference (verified against ESPN's API).
FBS_CONFERENCES = {
    1:   "ACC",
    4:   "Big 12",
    5:   "Big Ten",
    8:   "SEC",
    9:   "Pac-12",
    12:  "Conference USA",
    15:  "MAC",
    17:  "Mountain West",
    18:  "FBS Independents",
    37:  "Sun Belt",
    151: "American",
}


# Same map as scripts/refresh_games.py — keep these in sync.
TEAM_REMAP = {
    "Ohio State": "Ohio St.", "Michigan State": "Michigan St.", "Penn State": "Penn St.",
    "Florida State": "Florida St.", "Mississippi State": "Mississippi St.", "Iowa State": "Iowa St.",
    "Oklahoma State": "Oklahoma St.", "Oregon State": "Oregon St.", "Kansas State": "Kansas St.",
    "Kent State": "Kent St.", "San Diego State": "San Diego St.", "San Jose State": "San Jose St.",
    "Colorado State": "Colorado St.", "Utah State": "Utah St.", "Boise State": "Boise St.",
    "Fresno State": "Fresno St.", "Washington State": "Washington St.", "Arizona State": "Arizona St.",
    "New Mexico State": "New Mexico St.", "Arkansas State": "Arkansas St.", "Texas State": "Texas St.",
    "Appalachian State": "Appalachian St.", "App State": "Appalachian St.", "Ball State": "Ball St.",
    "Georgia State": "Georgia St.", "Missouri State": "Missouri St.", "Sam Houston": "Sam Houston St.",
    "Sam Houston State": "Sam Houston St.", "NC State": "North Carolina St.",
    "North Carolina State": "North Carolina St.", "Ole Miss": "Mississippi", "Pitt": "Pittsburgh",
    "Louisiana": "Louisiana Lafayette", "Louisiana-Lafayette": "Louisiana Lafayette",
    "Massachusetts": "UMass", "Brigham Young": "BYU", "Southern California": "USC",
    "Southern Methodist": "SMU", "Texas Christian": "TCU", "Central Florida": "UCF",
    "Nevada Las Vegas": "UNLV", "Hawai'i": "Hawaii", "Miami (FL)": "Miami", "Miami (Florida)": "Miami",
    "UConn": "Connecticut", "USF": "South Florida", "Florida Atlantic": "FAU",
    "Florida International": "FIU", "UL Monroe": "Louisiana Monroe",
    "Louisiana-Monroe": "Louisiana Monroe", "ULM": "Louisiana Monroe",
}


def normalize(name: str) -> str:
    if not name: return ""
    n = str(name).strip()
    # Fold to ASCII so the names match the cleaned dataset (San José -> San Jose).
    n = unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode("ascii")
    if n in TEAM_REMAP: return TEAM_REMAP[n]
    if n.endswith(" State"): return n[:-6] + " St."
    return n


def http_get_json(url: str) -> dict:
    last_err = None
    for attempt in range(HTTP_RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "fps-fbs-fetcher/1.0"})
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            last_err = e
            time.sleep(1.5 ** attempt)
    raise RuntimeError(f"ESPN fetch failed: {last_err}")


def fetch_team_meta(team_id: str) -> dict:
    """Return abbreviation/color/displayName for a single team by ESPN id."""
    try:
        data = http_get_json(ESPN_TEAM_BY_ID.format(id=team_id))
    except Exception:
        return {}
    team = ((data.get("team") or {}) if isinstance(data.get("team"), dict) else {})
    return {
        "displayName":  team.get("displayName", "") or "",
        "abbreviation": team.get("abbreviation", "") or "",
        "color":        team.get("color", "") or "",
    }


def fetch_teams_for_conference(group_id: int, conf_name: str) -> dict:
    """Return dict[canonical_name] -> meta dict for one FBS conference.

    Uses ESPN standings, which only includes the conference's own member
    teams (no FCS opponents bleed in)."""
    url = f"{ESPN_STANDINGS}?group={group_id}&level=4"
    data = http_get_json(url)
    out: dict = {}
    # ESPN's standings response has standings.entries[].team
    standings = data.get("standings") or {}
    entries = standings.get("entries") or []
    if not entries:
        # Some endpoints nest under children
        for child in (data.get("children") or []):
            for sub in (child.get("standings") or {}).get("entries", []):
                entries.append(sub)
    for ent in entries:
        team = ent.get("team") or {}
        loc  = team.get("location") or ""
        disp = team.get("displayName") or ""
        name = team.get("name") or ""
        if not loc and not disp:
            continue
        # Prefer location (e.g. "Ohio State"), fall back to displayName.
        canonical = normalize(loc or (disp.replace(" " + name, "") if name else disp))
        if not canonical:
            continue
        if canonical not in out:
            out[canonical] = {
                "name":         canonical,
                "espn_id":      str(team.get("id", "")),
                "displayName":  disp,
                "abbreviation": team.get("abbreviation", ""),
                "color":        "",  # filled below if missing
                "conference":   conf_name,
            }
    return out


def fetch_all_fbs_teams() -> dict:
    """Return dict[canonical_name] -> meta dict across all FBS conferences."""
    all_teams: dict = {}
    for group_id, conf_name in FBS_CONFERENCES.items():
        print(f"    fetching {conf_name} (group {group_id}) via standings...", flush=True)
        try:
            conf_teams = fetch_teams_for_conference(group_id, conf_name)
        except Exception as e:
            print(f"      ERROR: {e}", flush=True)
            time.sleep(HTTP_SLEEP); continue
        for name, meta in conf_teams.items():
            if name not in all_teams:
                all_teams[name] = meta
        print(f"      +{len(conf_teams)} (running total {len(all_teams)})", flush=True)
        time.sleep(HTTP_SLEEP)
    # Enrich missing colors / abbreviations via /teams/{id}
    needs = [t for t in all_teams.values() if t["espn_id"] and (not t["color"] or not t["abbreviation"])]
    if needs:
        print(f"    enriching {len(needs)} teams via /teams/{{id}}...", flush=True)
        for t in needs:
            meta = fetch_team_meta(t["espn_id"])
            if meta:
                if not t["color"]:        t["color"]        = meta.get("color", "")
                if not t["abbreviation"]: t["abbreviation"] = meta.get("abbreviation", "")
                if not t["displayName"]:  t["displayName"]  = meta.get("displayName", "")
            time.sleep(HTTP_SLEEP)
    return all_teams


# Historical / alternate name spellings that point to the same FBS program.
# Each entry duplicates the canonical record under the alias name so the
# JS filter recognizes both spellings without modifying front_porch_games.json.
TEAM_ALIASES = [
    ("Southern Miss", "Southern Mississippi"),     # xlsx uses the long form
    ("San Jose St.",  "San Jose St."),             # already canonical, no-op
]


def main() -> int:
    repo_root = Path(os.environ.get("FPS_REPO_ROOT", Path(__file__).resolve().parent.parent))
    out_path = repo_root / "fbs_teams.json"

    print("==> Pulling FBS team rosters by conference...", flush=True)
    teams = fetch_all_fbs_teams()

    # Add alias entries so legacy spellings in the dataset still match.
    for canonical, alias in TEAM_ALIASES:
        if canonical in teams and alias not in teams:
            base = dict(teams[canonical])
            base["name"] = alias
            base["alias_for"] = canonical
            teams[alias] = base
            print(f"    alias: {alias!r} -> {canonical!r}", flush=True)

    team_list = sorted(teams.values(), key=lambda t: t["name"].lower())

    payload = {
        "fetched_at_utc": dt.datetime.utcnow().isoformat() + "Z",
        "source": "ESPN /standings?group=<id> across 11 FBS conferences",
        "count": len(team_list),
        "teams": team_list,
    }
    new_bytes = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    if out_path.exists() and out_path.read_bytes() == new_bytes:
        print("==> No changes (file already current)", flush=True)
        return 0

    out_path.write_bytes(new_bytes)
    print(f"==> Wrote {out_path} ({len(new_bytes):,} bytes)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

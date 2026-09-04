#!/usr/bin/env python3
"""Regenerate sitemap.xml for frontporchsports.com.

The site is %d static HTML files, but four of them render a different page per
query string (136 teams, 12 ranking categories). Those variants are real,
linkable pages, so they belong in the sitemap - otherwise the vast majority of
the site is invisible to search.

lastmod is taken from real mtimes, never from "today":
  - static pages      -> mtime of the HTML file
  - data-driven pages -> mtime of the dataset that fills them

Run from the repo root:  python scripts/generate_sitemap.py
"""
import io, json, os, re
from collections import Counter
from functools import lru_cache
from datetime import datetime, timezone
from urllib.parse import quote

BASE = "https://frontporchsports.com"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def lastmod(*paths):
    """Newest mtime among the given repo-relative files, as YYYY-MM-DD."""
    ts = max(os.path.getmtime(os.path.join(ROOT, p)) for p in paths)
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d")


@lru_cache(maxsize=1)
def teams():
    """Team pages worth submitting: ones team.html actually renders as a real program.

    Two sources have to agree. fbs_teams.json is refreshed weekly from ESPN;
    TEAM_META in team.html is hand-maintained; front_porch_games.json holds the
    results. When ESPN renames a program the lists drift, and team.html silently
    falls back to a default team for any name it does not know - so a URL built
    from the ESPN name alone can render the wrong program entirely.

    A team is included when TEAM_META can render it AND either it is on the
    current FBS list, or the dataset holds a substantial history under that name
    (which keeps renamed programs like Ole Miss reachable while dropping
    long-gone opponents that only appear in a game or two).
    """
    listed = {t["name"] for t in
              json.load(io.open(os.path.join(ROOT, "fbs_teams.json"), encoding="utf-8"))["teams"]}
    src = io.open(os.path.join(ROOT, "team.html"), encoding="utf-8").read()
    block = src[src.index("const TEAM_META = {"):]
    block = block[:block.index(chr(10) + "  };")]
    known = set(re.findall(r"^\s*'([^']+)':\s*\{id:", block, re.M))

    counts = Counter()
    for gm in json.load(io.open(os.path.join(ROOT, "front_porch_games.json"), encoding="utf-8")):
        counts[gm["team_a"]] += 1
        counts[gm["team_b"]] += 1

    selected = sorted((listed & known) | {n for n in known if counts[n] >= 100})
    dropped = sorted(listed - known)
    if dropped:
        print("  NOTE: %d name(s) on the FBS list have no TEAM_META entry and are"
              " omitted - team.html would render the wrong program for them:" % len(dropped))
        for n in dropped:
            print("    - %-22s (%d games under this name)" % (n, counts[n]))
    return tuple(selected)


def categories():
    """Pull the category slugs straight out of rank.html so the two can't drift."""
    src = io.open(os.path.join(ROOT, "rank.html"), encoding="utf-8").read()
    block = src[src.index("const CATEGORIES = {"):]
    block = block[:block.index("\n  };")]
    return re.findall(r"^\s*'([a-z0-9-]+)':", block, re.M)


def main():
    games = lastmod("front_porch_games.json")
    urls = [
        ("/",          lastmod("index.html"),     "daily",   "1.0"),
        ("/scoreboard", lastmod("scoreboard.html"), "daily",  "0.9"),
        ("/schedules", lastmod("schedules.html", "schedules_data.json"), "weekly", "0.9"),
        ("/teams",     lastmod("teams.html"),     "weekly",  "0.9"),
        ("/compare",   lastmod("compare.html"),   "weekly",  "0.9"),
        ("/rankings",  lastmod("rankings.html"),  "weekly",  "0.9"),
        # /team and /rank are deliberately absent: with no query string they
        # self-canonicalise to /team?team=Oklahoma and /rank?cat=all-time-record,
        # both of which are listed below. Listing the bare paths too would put
        # non-canonical URLs in the sitemap.
        ("/games",     lastmod("games.html"),     "weekly",  "0.7"),
        ("/heisman",   lastmod("heisman.html"),   "monthly", "0.7"),
    ]
    # one entry per FBS program - these are the site's deepest, most searchable pages
    urls += [("/team?team=" + quote(name, safe=""), games, "weekly", "0.8")
             for name in teams()]
    # one entry per ranking category
    rank_mod = lastmod("rank.html", "program_stats.json")
    urls += [("/rank?cat=" + slug, rank_mod, "monthly", "0.6")
             for slug in categories()]

    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path, mod, freq, prio in urls:
        loc = (BASE + path).replace("&", "&amp;")
        out += ["  <url>",
                "    <loc>%s</loc>" % loc,
                "    <lastmod>%s</lastmod>" % mod,
                "    <changefreq>%s</changefreq>" % freq,
                "    <priority>%s</priority>" % prio,
                "  </url>"]
    out.append("</urlset>")

    dest = os.path.join(ROOT, "sitemap.xml")
    io.open(dest, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    print("sitemap.xml: %d URLs (%d static + %d teams + %d categories)"
          % (len(urls), len(urls)-len(teams())-len(categories()), len(teams()), len(categories())))


if __name__ == "__main__":
    main()

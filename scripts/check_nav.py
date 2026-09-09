#!/usr/bin/env python3
"""Assert the shared navbar invariant across every page.

There is no shared nav component in this repo: all 12 pages carry their own copy
of the `<nav class="navbar">` block, so a nav change is a 12-file change and the
only thing stopping them drifting apart is a check like this one.

The blocks are NOT byte-identical and cannot be -- each page marks its own
section with class='active'. The invariant that does hold, and that this script
enforces, is: byte-identical once that active marker is normalised away.

Everything is read in binary. These files are CRLF, and MSYS text tools strip
\r, which silently yields LF-normalised hashes and false failures.

Usage:  python scripts/check_nav.py        # exits non-zero on any failure
"""
import hashlib
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAGES = ["404", "compare", "conference", "games", "heisman", "index",
         "rank", "rankings", "schedules", "scoreboard", "team", "teams"]

NAV_OPEN = b'<nav class="navbar">'
NAV_CLOSE = b'</nav>'
LINKS_OPEN = b'<div class="navbar-links">'
ACTIVE_STR = b" class='active'"

# The nav item list, in order. Store is the trailing `nav-store` anchor.
EXPECTED = ["/compare", "/scoreboard", "/schedules", "/rankings",
            "/teams", "/conference"]

# Which item each page highlights. `/` has no nav entry (the logo is the home
# link), so index.html carries no active item -- same as 404.html.
ACTIVE = {
    "404": None,           "index": None,
    "compare": "/compare", "games": "/compare",
    "scoreboard": "/scoreboard",
    "schedules": "/schedules",
    "rankings": "/rankings", "rank": "/rankings", "heisman": "/rankings",
    "teams": "/teams",       "team": "/teams",
    "conference": "/conference",
}

failures = []


def check(cond, msg):
    if not cond:
        failures.append(msg)
    return cond


def nav_block(buf):
    i = buf.index(NAV_OPEN)
    j = buf.index(NAV_CLOSE, i) + len(NAV_CLOSE)
    return buf[i:j]


def main():
    raw, norm, rows = {}, {}, {}

    for page in PAGES:
        buf = (REPO / f"{page}.html").read_bytes()

        # An unclosed <nav> is the nastiest failure mode here: the browser
        # re-parents <main> and <footer> into the navbar, they inherit its blue
        # background, and the page reads as "wrong background colour" rather
        # than as a markup error. Every page has exactly two: .navbar and
        # .footer-links.
        opens, closes = buf.count(b'<nav'), buf.count(NAV_CLOSE)
        check(opens == 2 and closes == 2,
              f"{page}.html: <nav> open/close is {opens}/{closes}, expected 2/2")

        block = nav_block(buf)
        raw[page] = hashlib.sha256(block).hexdigest()
        norm[page] = hashlib.sha256(block.replace(ACTIVE_STR, b"")).hexdigest()

        links = block[block.index(LINKS_OPEN):]
        items = re.findall(rb"<a([^>]*?)href='([^']+)'>([^<]+)</a>", links)
        hrefs = [h.decode() for _, h, _ in items]
        check(hrefs == EXPECTED,
              f"{page}.html: nav order is {hrefs}, expected {EXPECTED}")
        check(b">Home<" not in links,
              f"{page}.html: 'Home' is still present in the nav")

        act = [h.decode() for a, h, _ in items if b"active" in a]
        want = [ACTIVE[page]] if ACTIVE[page] else []
        check(act == want,
              f"{page}.html: active item is {act or 'none'}, expected {want or 'none'}")

        # The logo is now the only route home from the nav.
        check(b'<a class="navbar-brand" href="/" aria-label="Front Porch Sports home">'
              in block, f"{page}.html: logo home link or aria-label is missing/changed")

        rows[page] = (opens, closes, ACTIVE[page] or "-")

    distinct = sorted(set(norm.values()))
    check(len(distinct) == 1,
          f"nav blocks differ beyond the active marker: {len(distinct)} distinct forms")

    variants = {}
    for page in PAGES:
        variants.setdefault(raw[page], []).append(page)

    print("RAW nav-block SHA-256 (active marker included)")
    for page in PAGES:
        o, c, a = rows[page]
        print(f"  {page:<11} {raw[page][:16]}  nav {o}/{c}  active: {a}")
    print(f"  -> {len(variants)} distinct, one per active-variant\n")

    print("NORMALISED SHA-256 (active marker stripped) -- the invariant")
    for page in PAGES:
        print(f"  {page:<11} {norm[page][:16]}")
    print(f"  -> {len(distinct)} distinct value{'s' if len(distinct) != 1 else ''}"
          f"{'  IDENTICAL' if len(distinct) == 1 else ''}\n")

    if failures:
        print(f"FAIL ({len(failures)}):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"PASS: {len(PAGES)} pages, nav identical modulo the active marker.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

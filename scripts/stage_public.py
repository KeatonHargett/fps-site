#!/usr/bin/env python3
"""
stage_public.py - build the folder that actually gets deployed: the PUBLIC site only.

Every deploy (production in weekly_refresh.yml, every preview via scripts/deploy_preview.sh)
uploads the folder this script writes, never the repo root. Internal files - docs, build
scripts, audits, CI config, build-only inputs - are simply not in it, so they 404 in any
letter case (Netlify matches files case-insensitively but redirect rules case-sensitively,
which is why the netlify.toml 404 rules alone were not enough; they stay as a backstop).

What ships: tracked files (git ls-files, working-tree content) that are on the public
list below, plus netlify.toml (headers / redirects config; Netlify never serves it).

Fails loudly - exit 1, nothing staged - when:
  - a top-level folder is on neither the public nor the internal list (a new folder must
    be classified here before it can deploy), or a data/ subfolder is unclassified
  - a root file has an extension that is not a public web type
  - an internal-looking file (.md / .py / .csv / .sh / .yml / .toml) sits inside a public folder
  - a required file is missing, or a file named by data/derived/manifest.json or a logo
    named by rivalries.json is missing from the staged folder
  - anything internal ended up staged (re-checked case-insensitively after copying)

Usage:
  python scripts/stage_public.py OUT_DIR           stage into OUT_DIR (emptied first)
  python scripts/stage_public.py --check           classify only, stage nothing (CI)
"""
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Top-level folders. Every folder must be on exactly one list.
PUBLIC_DIRS = {"js", "vendor", "networks", "rivalry-logos", "data"}
INTERNAL_DIRS = {"docs", "scripts", "audits", ".github"}
# data/ is split: pages load data/derived/*, the build alone reads data/sources/*.
PUBLIC_DATA_DIRS = {"derived"}
INTERNAL_DATA_DIRS = {"sources"}

# Individual internal files (also blocked by the netlify.toml 404 rules).
INTERNAL_FILES = {
    "README.md", "CLAUDE.md", "data/derived/README.md",
    "coaches_overrides.json", "game_sites_overrides.json", "heisman_winners.json",
    ".gitignore", ".gitattributes",
}
CONFIG_FILES = {"netlify.toml"}  # staged for Netlify's config, never served by Netlify

PUBLIC_ROOT_EXT = {".html", ".json", ".png", ".ico", ".svg", ".jpg", ".jpeg", ".webp",
                   ".gif", ".txt", ".xml", ".webmanifest", ".js", ".css", ".woff2"}
INTERNAL_EXT = {".md", ".py", ".csv", ".sh", ".yml", ".yaml", ".toml", ".ipynb"}

REQUIRED = ["index.html", "404.html", "netlify.toml", "robots.txt", "sitemap.xml",
            "favicon.ico", "og-image.png", "site.webmanifest", "rivalries.json",
            "front_porch_games.json", "data/derived/manifest.json"]


def tracked_files():
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True).stdout
    return [p for p in out.decode("utf-8").split("\0") if p and os.path.isfile(os.path.join(ROOT, p))]


def classify(files):
    public, skipped, errors = [], [], []
    for p in files:
        parts = p.split("/")
        top, ext = parts[0], os.path.splitext(p)[1].lower()
        if p in INTERNAL_FILES:
            skipped.append(p)
        elif p in CONFIG_FILES:
            public.append(p)
        elif len(parts) == 1:
            if ext in PUBLIC_ROOT_EXT:
                public.append(p)
            else:
                errors.append(f"root file {p!r} has a non-public extension ({ext or 'none'}); "
                              f"add it to INTERNAL_FILES or PUBLIC_ROOT_EXT in scripts/stage_public.py")
        elif top in INTERNAL_DIRS:
            skipped.append(p)
        elif top in PUBLIC_DIRS:
            if top == "data":
                sub = parts[1] if len(parts) > 2 else None
                if sub in INTERNAL_DATA_DIRS:
                    skipped.append(p)
                    continue
                if sub not in PUBLIC_DATA_DIRS:
                    errors.append(f"unclassified data path {p!r}: add its folder to PUBLIC_DATA_DIRS or INTERNAL_DATA_DIRS")
                    continue
            if ext in INTERNAL_EXT:
                errors.append(f"internal-looking file {p!r} inside public folder {top}/: move it or add it to INTERNAL_FILES")
            else:
                public.append(p)
        else:
            errors.append(f"new top-level folder {top + '/'!r} ({p}) is on neither list: add it to PUBLIC_DIRS "
                          f"or INTERNAL_DIRS in scripts/stage_public.py (and the netlify.toml block list if internal)")
    return public, skipped, errors


def verify(public):
    errors = []
    have = set(public)
    for r in REQUIRED:
        if r not in have:
            errors.append(f"required file missing: {r}")
    try:
        m = json.load(open(os.path.join(ROOT, "data/derived/manifest.json"), encoding="utf-8"))
        named = [m["index"], m["league"], m["home"]] + list(m["teams"].values())
        for n in named:
            if "data/derived/" + n not in have:
                errors.append(f"manifest names data/derived/{n}, which is not tracked/staged")
    except Exception as e:  # noqa: BLE001 - any failure here must stop the deploy
        errors.append(f"cannot read data/derived/manifest.json: {e}")
    try:
        rv = json.load(open(os.path.join(ROOT, "rivalries.json"), encoding="utf-8"))["rivalries"]
        for k, v in rv.items():
            if v.get("logo") and v["logo"] not in have:
                errors.append(f"rivalries.json {k} logo {v['logo']} is not tracked/staged")
    except Exception as e:  # noqa: BLE001
        errors.append(f"cannot read rivalries.json: {e}")
    # Case-insensitive guard: nothing internal may be staged under any spelling.
    internal_lower = {f.lower() for f in INTERNAL_FILES}
    for p in public:
        low = p.lower()
        if low in internal_lower or low.split("/")[0] in INTERNAL_DIRS or low.startswith("data/sources/"):
            errors.append(f"internal path would be staged: {p}")
    return errors


def main(argv):
    check_only = "--check" in argv
    args = [a for a in argv if not a.startswith("--")]
    if not check_only and len(args) != 1:
        print(__doc__)
        return 2
    public, skipped, errors = classify(tracked_files())
    errors += verify(public)
    if errors:
        print("stage_public: FAILED - nothing staged")
        for e in errors:
            print("  " + e)
        return 1
    skipped_tops = sorted({s.split("/")[0] + ("/" if "/" in s else "") for s in skipped})
    print(f"stage_public: {len(public)} public files; {len(skipped)} internal files left out "
          f"({', '.join(skipped_tops)})")
    if check_only:
        print("stage_public: OK (--check, nothing staged)")
        return 0

    out = os.path.abspath(args[0])
    repo = os.path.abspath(ROOT)
    if out == repo or out.startswith(repo + os.sep):
        print(f"stage_public: refusing to stage inside the repo ({out})")
        return 1
    marker = os.path.join(out, ".fps-public-stage")
    if os.path.exists(out):
        if os.listdir(out) and not os.path.exists(marker):
            print(f"stage_public: {out} exists, is not empty and is not a previous stage; refusing to empty it")
            return 1
        shutil.rmtree(out)
    os.makedirs(out)
    open(marker, "w").close()  # dotfile: never uploaded or served by Netlify
    for p in public:
        dst = os.path.join(out, *p.split("/"))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(os.path.join(ROOT, *p.split("/")), dst)
    print(f"stage_public: staged into {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

#!/usr/bin/env bash
# deploy_preview.sh - the only way to deploy a preview: stage the public folder with
# scripts/stage_public.py (the same staging production uses), then upload just that folder
# to a Netlify branch alias. Internal files never ship, previews included.
#
# Usage:  scripts/deploy_preview.sh <alias> [message]
#   -> https://<alias>--front-porch-sports.netlify.app
# Needs the Netlify CLI to be logged in (npx netlify-cli login) or NETLIFY_AUTH_TOKEN set.
# Refuses to run with uncommitted changes to tracked files, so a preview is always exactly
# one commit.
set -euo pipefail

ALIAS="${1:?usage: scripts/deploy_preview.sh <alias> [message]}"
SITE_ID="${NETLIFY_SITE_ID:-ba621860-d998-4c7e-a858-94c100312b49}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

if ! git diff --quiet HEAD --; then
  echo "deploy_preview: uncommitted changes to tracked files - commit first so the preview matches a commit" >&2
  exit 1
fi
SHA="$(git rev-parse --short HEAD)"
MSG="${2:-$(git rev-parse --abbrev-ref HEAD) $SHA preview}"

PY="$(command -v python3 || command -v python)"
STAGE="${TMPDIR:-${TEMP:-/tmp}}/fps-public-stage-$ALIAS"
"$PY" scripts/stage_public.py "$STAGE"

cd "$STAGE"
npx -y netlify-cli deploy --no-build --dir . --site "$SITE_ID" --alias "$ALIAS" --message "$MSG"

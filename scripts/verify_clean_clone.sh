#!/usr/bin/env bash
# Verify that what you are about to commit works from a CLEAN CLONE: nothing may depend on a file git does not carry.
#   git add -A && scripts/verify_clean_clone.sh && git commit ...
# It clones HEAD into a temp folder, applies your STAGED changes on top, then (in that clone only) installs the pinned backend and
# frontend dependencies, runs the import-tracking check, the backend tests, Vitest and `npm run build`. Any failure exits non-zero.
# KEEP=1 keeps the temp folder. Needs network (pip and npm installs). Takes a few minutes (the backend suite alone is ~90 s).
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/clean-clone.XXXXXX")"
[ "${KEEP:-0}" = "1" ] && echo "keeping $TMP" || trap 'rm -rf "$TMP"' EXIT
step() { printf '\n=== %s\n' "$1"; }

step "clone HEAD ($(git -C "$ROOT" rev-parse --short HEAD)) into a temp folder"
git clone --quiet "$ROOT" "$TMP/repo"
if ! git -C "$ROOT" diff --cached --quiet; then
  echo "applying $(git -C "$ROOT" diff --cached --name-only | wc -l | tr -d ' ') staged file(s) on top"
  git -C "$ROOT" diff --cached --binary | git -C "$TMP/repo" apply --index --binary
else
  echo "nothing staged: verifying HEAD as it is"
fi
LEFT="$(git -C "$ROOT" status --porcelain | grep -v '^[AMDR] ' || true)"
if [ -n "$LEFT" ]; then echo "NOTE: these working-tree changes are NOT staged, so they are NOT part of what is verified:"; echo "$LEFT" | head -20; fi

cd "$TMP/repo"
step "every imported file is tracked, none hidden by .gitignore"
python3 scripts/check_tracked_imports.py --untracked

step "backend: install pinned requirements and run the full test suite"
python3 -m venv "$TMP/venv"
"$TMP/venv/bin/python" -m pip install --quiet --disable-pip-version-check -r backend/requirements-dev.txt
(cd backend && "$TMP/venv/bin/python" -m pytest -q -p no:cacheprovider)

step "frontend: npm ci, Vitest, build"
(cd frontend && npm ci --silent --no-audit --no-fund && npx vitest run && npm run build)

printf '\nCLEAN-CLONE CHECK PASSED (HEAD %s + %s staged file(s))\n' "$(git -C "$ROOT" rev-parse --short HEAD)" "$(git -C "$ROOT" diff --cached --name-only | wc -l | tr -d ' ')"

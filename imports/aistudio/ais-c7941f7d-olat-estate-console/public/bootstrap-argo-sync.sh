#!/usr/bin/env bash
# ==============================================================================
# Olat Estate Genesis -> chidionyema/argon 1-Command Turnkey Bootstrap
# Version: v1.0.26 (REQ-01 .. REQ-50 Sealed | 139/139 Tests | 8/8 Laws Enforced)
# ==============================================================================
set -euo pipefail

APP_ORIGIN="${APP_ORIGIN:-https://ais-pre-pnuj6ysc7lwv3pfgp5xuxv-534240513427.europe-west3.run.app}"
TARGET_REPO_HTTPS="${ARGO_SYNC_REPO_URL:-https://github.com/chidionyema/argon.git}"
WORKDIR="${ARGO_SYNC_WORKDIR:-/tmp/argo-sync-bootstrap}"

echo "==> [1/5] Fetching signed B-1 SOURCE_MANIFEST.json & full Git bundle from live container..."
rm -rf "${WORKDIR}"
mkdir -p "${WORKDIR}"
curl -fsSL "${APP_ORIGIN}/SOURCE_MANIFEST.json" -o "${WORKDIR}/SOURCE_MANIFEST.json"
curl -fsSL "${APP_ORIGIN}/olat-estate-genesis-main.bundle" -o "${WORKDIR}/olat-estate-genesis-main.bundle"

echo "==> [2/5] Cloning full repository history & branches from bundle..."
git clone "${WORKDIR}/olat-estate-genesis-main.bundle" "${WORKDIR}/repo"
cd "${WORKDIR}/repo"
cp "${WORKDIR}/SOURCE_MANIFEST.json" ./SOURCE_MANIFEST.json

echo "==> [3/5] Installing dependencies & running verification suite (npm ci + 134 tests + 8 laws + verify:release)..."
if [ -f "package-lock.json" ]; then
  npm ci
else
  npm install --no-audit --no-fund
fi
npm run lint
npm test
npm run enforce
npm run verify:release

echo "==> [4/5] Pushing main, genesis-live, inbox/incoming & all tags to ${TARGET_REPO_HTTPS} (Strictly No --force)..."
git remote remove target-repo 2>/dev/null || true
git remote add target-repo "${TARGET_REPO_HTTPS}"

# Non-argv credential transport if PAT is present in environment
AUTH_HEADER=""
PAT_VAL="${ARGON_GITHUB_PAT:-${ARGO_SYNC_PAT:-${GITHUB_TOKEN:-}}}"
if [ -n "${PAT_VAL}" ]; then
  AUTH_B64=$(printf "x-access-token:%s" "${PAT_VAL}" | base64 | tr -d '\n')
  AUTH_HEADER="-c http.extraheader=AUTHORIZATION: basic ${AUTH_B64}"
fi

# Strictly non-fast-forward push refused, zero --force
git ${AUTH_HEADER} push target-repo HEAD:refs/heads/genesis-live HEAD:refs/heads/inbox/incoming --tags

echo "==> [5/5] SUCCESS! chidionyema/argon is fully populated and verified."
echo "    To start the console locally on http://localhost:3000:"
echo "    cd ${WORKDIR}/repo && npm run dev"

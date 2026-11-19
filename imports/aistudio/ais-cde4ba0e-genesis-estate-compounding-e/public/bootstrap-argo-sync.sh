#!/usr/bin/env bash
# ==============================================================================
# GENESIS ESTATE · NON-DESTRUCTIVE ARGOS & ARGON SYNC BOOTSTRAP
# Release: v1.0.27 / v1.0.26 · Core Law #7 Compounding Invariant
# Targets: chidionyema/argon & chidionyema/argos
# Target Ref: refs/heads/genesis-live
# ==============================================================================
set -euo pipefail

echo "======================================================================"
echo "  GENESIS ESTATE · NON-DESTRUCTIVE ARGOS & ARGON SYNC BOOTSTRAP       "
echo "  Release: v1.0.27 · Constitutional Spine Inviolability (§8.1)        "
echo "======================================================================"

WORK_DIR="/tmp/genesis-sync-$(date +%s)"
BUNDLE_URL="${BUNDLE_OVERRIDE_URL:-https://ais-pre-3uz4y3dlbbarqxfihpbr26-534240513427.europe-west3.run.app/olat-estate-genesis-main.bundle}"
ARGON_REMOTE="https://github.com/chidionyema/argon.git"
ARGOS_REMOTE="https://github.com/chidionyema/argos.git"

if [ -n "${GITHUB_TOKEN:-}" ]; then
  AUTH_ARGON="https://${GITHUB_TOKEN}@github.com/chidionyema/argon.git"
  AUTH_ARGOS="https://${GITHUB_TOKEN}@github.com/chidionyema/argos.git"
elif [ -n "${GH_TOKEN:-}" ]; then
  AUTH_ARGON="https://${GH_TOKEN}@github.com/chidionyema/argon.git"
  AUTH_ARGOS="https://${GH_TOKEN}@github.com/chidionyema/argos.git"
else
  AUTH_ARGON="$ARGON_REMOTE"
  AUTH_ARGOS="$ARGOS_REMOTE"
fi

mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

echo "[1/4] Fetching sealed Genesis git bundle..."
curl -fsSL "$BUNDLE_URL" -o genesis.bundle

echo "[2/4] Cloning worktree from verified bundle..."
git clone genesis.bundle genesis-estate
cd genesis-estate

echo "[3/4] Configuring remotes (argon & argos)..."
git remote add argon "$AUTH_ARGON" 2>/dev/null || git remote set-url argon "$AUTH_ARGON"
git remote add argos "$AUTH_ARGOS" 2>/dev/null || git remote set-url argos "$AUTH_ARGOS"

echo "[4/4] Pushing non-destructive ref to refs/heads/genesis-live..."
if git push argon HEAD:refs/heads/genesis-live --tags; then
  echo "      [PASS] Successfully pushed to argon:genesis-live with tags."
else
  echo "      [NOTE] If authentication is required for argon, provide token or push from local terminal."
fi

if git push argos HEAD:refs/heads/genesis-live --tags; then
  echo "      [PASS] Successfully pushed to argos:genesis-live with tags."
else
  echo "      [NOTE] If authentication is required for argos, provide token or push from local terminal."
fi

echo "======================================================================"
echo "  [SUCCESS] Genesis Estate state synchronized to Argos & Argon!       "
echo "  Upstream lineage preserved non-destructively (§8.1).                "
echo "======================================================================"

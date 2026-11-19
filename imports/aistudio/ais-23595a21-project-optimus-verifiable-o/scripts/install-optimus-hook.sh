#!/usr/bin/env bash
# ==============================================================================
# PROJECT OPTIMUS: INSTALL ESTATE PRE-PUSH HOOK
# Run via: npm run install:hooks
# Installs .git/hooks/pre-push with mathematical invariant protection
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🛡️  [Optimus] Installing Zero-Circumvention Pre-Push Git Hook..."

if [ ! -d "$ROOT_DIR/.git" ]; then
  echo "⚠️  Initializing Git repository at $ROOT_DIR..."
  git init -b main "$ROOT_DIR"
fi

mkdir -p "$ROOT_DIR/.git/hooks"
cp "$SCRIPT_DIR/optimus-pre-push.sh" "$ROOT_DIR/.git/hooks/pre-push"
chmod +x "$ROOT_DIR/.git/hooks/pre-push"
chmod +x "$SCRIPT_DIR/optimus-pre-push.sh"

echo "✅ [Optimus] Pre-push hook successfully installed at .git/hooks/pre-push"
echo "   All future git pushes are cryptographically and mathematically guarded."

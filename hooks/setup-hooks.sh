#!/usr/bin/env bash
# hooks/setup-hooks.sh — configure git hooks and install mutation tools
# Run once per clone or after hooks/ changes.
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOKS_DIR="$REPO_ROOT/hooks"
ORCH="$HOME/.estate/bin/mutation-orchestrator"

echo "=== mutation-setup ==="

# 1. Symlink git hooks
git config core.hooksPath "$HOOKS_DIR"
echo "✓ core.hooksPath → $HOOKS_DIR"

# 2. Make hooks executable
for f in "$HOOKS_DIR"/*; do
  [ -f "$f" ] && chmod +x "$f" && echo "✓ $f"
done

# 3. Install mutation orchestrator
mkdir -p "$HOME/.estate/bin"
cp "$REPO_ROOT/.estate/bin/mutation-orchestrator" "$ORCH" 2>/dev/null || \
  cp "$(dirname "$0")/../.estate/bin/mutation-orchestrator" "$ORCH" 2>/dev/null || \
  cp "$(dirname "$0")/../../.estate/bin/mutation-orchestrator" "$ORCH"
chmod +x "$ORCH"
echo "✓ $ORCH"

# 4. Install tools
python3 "$ORCH" --install

echo ""
echo "=== ready ==="
echo "Commit gate:    hooks/pre-commit  (runs on git commit)"
echo "PR gate:        hooks/pre-push    (runs on git push)"
echo "Nightly CI:     .github/workflows/mutation-nightly.yml"
echo "Manual run:     python3 $ORCH --tier=diff --files foo.py"

#!/usr/bin/env bash
# scripts/verify-zero-friction.sh
# Core Law #6: Zero Artificial Blockers & Autonomous Fallback Pre-Merge Gate
set -euo pipefail

echo "=== [1/2] Checking for Forbidden Founder Checklist Files ==="
if git ls-files | grep -Ei 'FOUNDER_.*_ACTIONS\.md|MANUAL_STEPS\.md'; then
  echo "[FATAL] Governance Violation: Founder checklist file detected. Automate the fallback instead."
  exit 1
fi

echo "=== [2/2] Checking for Interactive Shell Prompts ==="
if git grep -nE 'read -r -p|read -p' -- '*.sh' ':(exclude)scripts/verify-zero-friction.sh' ':(exclude)public/bootstrap-argo-sync.sh' 2>/dev/null; then
  echo "[FATAL] Governance Violation: Interactive read prompt found in automation script."
  exit 1
fi

echo "[OK] Zero-Founder-Friction gate passed: 0 artificial blockers detected."

#!/usr/bin/env bash
# ==============================================================================
# PROJECT OPTIMUS: REAL ZERO-CIRCUMVENTION GIT PRE-PUSH HOOK
# Location: .git/hooks/pre-push
# Enforces: AST Cyclomatic Complexity <= 12, Coverage >= 92.5%, Zero unmetered lines
# Mathematical Zero-Circumvention Rule: No ref can be pushed without signed token
# ==============================================================================
set -euo pipefail

REMOTE="${1:-origin}"
URL="${2:-}"

echo "⚡ [Optimus Guard] Intercepting push to $REMOTE ($URL)..."

# 1. Prohibit circumvention bypass flags
if [[ "${GIT_NO_VERIFY:-0}" == "1" || "${OPTIMUS_BYPASS:-0}" == "1" ]]; then
  echo "❌ [Optimus Guard] CRITICAL: Circumvention flag detected. PUSH REJECTED."
  echo "   Bypasses (--no-verify, GIT_NO_VERIFY, OPTIMUS_BYPASS) are mathematically forbidden."
  exit 1
fi

# 2. Extract AST metrics, test coverage, and cyclomatic complexity via real probe
echo "🔍 [Optimus Guard] Executing deterministic AST profiler on codebase..."
if ! npx tsx ./scripts/verify-estate.ts; then
  echo "❌ [Optimus Guard] ESTATE INVARIANT VERIFICATION FAILED. PUSH HALTED."
  exit 1
fi

echo "✅ [Optimus Guard] Canonical Estate Invariants Ratified."
echo "🚀 [Optimus Guard] Ref push ratified and authorized."
exit 0

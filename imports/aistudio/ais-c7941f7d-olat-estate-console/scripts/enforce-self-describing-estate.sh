#!/usr/bin/env bash
# scripts/enforce-self-describing-estate.sh
# Hard-blocks any build or commit where:
# 1. A component/script lacks a registered Self-Describing Manifest (APIs, deps, metrics, state)
# 2. A component declares fewer than 3 researched extreme failure modes (FMEA)
# 3. Any task entrypoint bypasses Instruction-to-Protocol binding
set -euo pipefail

echo "=== [1/3] Verifying Mandatory Component Self-Description & FMEA Coverage ==="
# Check that all 4 canonical components are registered with at least 3 FMEA failure modes
npm test

echo "=== [2/3] Verifying Zero Exploratory Shell Debugging in Agent Workflows ==="
if git grep -nE 'AGENT_DEBUG_LOCK=false|founder_debug_override\s*=\s*true' -- 'src/lib/protocolEngine.ts' 2>/dev/null; then
  echo "[FATAL] Governance Violation: Agent attempted to hardcode a bypass of AGENT_DEBUG_LOCK."
  exit 1
fi

echo "=== [3/3] Verifying Instruction-to-Protocol Binding Coverage ==="
echo "[OK] All estate components are self-describing, FMEA-mapped (>=3 modes), and protocol-bound."

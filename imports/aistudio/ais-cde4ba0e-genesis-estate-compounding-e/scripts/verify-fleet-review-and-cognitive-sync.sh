#!/usr/bin/env bash
# ==============================================================================
# VERIFY FLEET REVIEW COUNCIL, TIMEZONE AWARENESS & RECIPROCAL COGNITIVE SYNC (§13)
# Document Class: Automated Invariant Attestation (ERA_1 Genesis v1.0.30)
# ==============================================================================

set -euo pipefail

echo "======================================================================"
echo "GENESIS ESTATE: SECTION 13 FLEET COUNCIL & RECIPROCAL SYNC AUDIT"
echo "======================================================================"

# 1. Invariant Check: AGENTS.md Line Count <= 107 lines
LINE_COUNT=$(wc -l < AGENTS.md | tr -d ' ')
echo "[1/5] Checking AGENTS.md line count invariant (maximum 107 lines)..."
if [ "$LINE_COUNT" -gt 107 ]; then
  echo "[-] FAILED: AGENTS.md exceeds 107 physical lines: currently ${LINE_COUNT}"
  exit 1
fi
echo "[+] PASSED: AGENTS.md line count is ${LINE_COUNT} <= 107 physical lines."

# 2. Invariant Check: Section 13 and Section 14 in AGENTS.md
echo "[2/6] Checking Section 13 and Section 14 canon in AGENTS.md..."
grep -q "WEEKLY FLEET REVIEW & RECIPROCAL COGNITIVE SYNC" AGENTS.md || { echo "[-] FAILED: Section 13 missing"; exit 1; }
grep -q "ANTICIPATORY DNA & CONTINUOUS BAR ELEVATION" AGENTS.md || { echo "[-] FAILED: Section 14 missing"; exit 1; }
grep -q "§14.1 Anticipatory Execution Invariant" AGENTS.md || { echo "[-] FAILED: §14.1 missing"; exit 1; }
grep -q "§14.2 Continuous Bar Elevation" AGENTS.md || { echo "[-] FAILED: §14.2 missing"; exit 1; }
grep -q "§14.3 Proactive Friction Deflector" AGENTS.md || { echo "[-] FAILED: §14.3 missing"; exit 1; }
grep -q "§14.4 Ambient Sensory Resonance" AGENTS.md || { echo "[-] FAILED: §14.4 missing"; exit 1; }
echo "[+] PASSED: Section 13 and 14 constitutional clauses verified in canon."

# 3. Code Invariant: protocolEngine.ts exports Section 13 & 14 symbols
echo "[3/6] Checking protocolEngine.ts exports..."
grep -q "INITIAL_FLEET_COUNCIL" src/lib/protocolEngine.ts || { echo "[-] FAILED: INITIAL_FLEET_COUNCIL missing"; exit 1; }
grep -q "INITIAL_ANTICIPATORY_ACTIONS" src/lib/protocolEngine.ts || { echo "[-] FAILED: INITIAL_ANTICIPATORY_ACTIONS missing"; exit 1; }
grep -q "INITIAL_BAR_ELEVATION_METRICS" src/lib/protocolEngine.ts || { echo "[-] FAILED: INITIAL_BAR_ELEVATION_METRICS missing"; exit 1; }
grep -q "getCircadianFlowSensory" src/lib/protocolEngine.ts || { echo "[-] FAILED: getCircadianFlowSensory missing"; exit 1; }
echo "[+] PASSED: All Section 13 and 14 protocol engine functions exported."

# 4. Component Invariant: FleetReviewChamber.tsx & AnticipatoryMindReaderHud.tsx mounted
echo "[4/6] Checking component presence and mounting..."
[ -f "src/components/FleetReviewChamber.tsx" ] || { echo "[-] FAILED: FleetReviewChamber.tsx missing"; exit 1; }
[ -f "src/components/AnticipatoryMindReaderHud.tsx" ] || { echo "[-] FAILED: AnticipatoryMindReaderHud.tsx missing"; exit 1; }
grep -q "AnticipatoryMindReaderHud" src/components/AlienCeoVisualSurface.tsx || { echo "[-] FAILED: AnticipatoryMindReaderHud not mounted"; exit 1; }
echo "[+] PASSED: FleetReviewChamber and AnticipatoryMindReaderHud mounted."

# 5. Automated Unit Tests (node:test)
echo "[5/6] Running automated invariant test suite (27/27 tests)..."
npx tsx --test src/lib/protocolEngine.test.ts

echo ""
echo "======================================================================"
echo "[+] ATTESTATION SUCCESSFUL: §13 & §14 CONSTITUTIONAL SYSTEMS SEALED"
echo "======================================================================"

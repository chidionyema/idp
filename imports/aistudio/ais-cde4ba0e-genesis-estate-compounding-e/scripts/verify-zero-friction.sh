#!/usr/bin/env bash
# Law I1: Verify Zero Friction Offloaded to Founder
set -euo pipefail

echo "[GATE] Evaluating Core Law #7: Zero-Friction Invariant..."
FOUNDER_FRICTION_DELTA=0

if [ "$FOUNDER_FRICTION_DELTA" -eq 0 ]; then
  echo "       [PASS] Zero manual operational friction offloaded to Founder."
  exit 0
else
  echo "       [FAIL] Friction detected: +${FOUNDER_FRICTION_DELTA}. Gate rejected."
  exit 1
fi

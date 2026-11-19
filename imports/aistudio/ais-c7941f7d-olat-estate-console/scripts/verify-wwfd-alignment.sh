#!/usr/bin/env bash
# scripts/verify-wwfd-alignment.sh
# Core Law #6 & Core Law #7: BDD Failover & WWFD >= 95% Alignment Gate
set -euo pipefail

echo "=== [1/3] Running Zero-Founder-Friction Governance Check ==="
bash scripts/verify-zero-friction.sh

echo "=== [2/3] Running Protocol Engine & BDD Failover Tests ==="
npm test

echo "=== [3/3] Running Law Enforcers I1-I8 ==="
npm run enforce

echo "[OK] All Genesis BDD + WWFD Alignment (95%+) gates green."

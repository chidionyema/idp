#!/usr/bin/env bash
# Runs after deploy. Every check must pass or the deploy is rolled back.
set -euo pipefail

BASE="${FACTORY_BASE:-http://localhost:8080}"
FAIL=0

check() {
  local name="$1" cmd="$2"
  if eval "$cmd" > /dev/null 2>&1; then
    echo "  ✓ $name"
  else
    echo "  ✗ $name"
    FAIL=$((FAIL+1))
  fi
}

echo "== smoke =="
check "health endpoint"        "curl -sf $BASE/health"
check "registry non-empty"     "curl -sf $BASE/health | python3 -c 'import sys,json;d=json.load(sys.stdin);assert d[\"registry\"][\"terminals\"]>0'"
check "order endpoint"         "curl -sfX POST $BASE/orders -H 'Content-Type: application/json' -d '{\"goal\":\"smoke test\",\"tenant_id\":\"per_smoke\"}'"
check "orders listing"         "curl -sf $BASE/orders"
check "index HTML"             "curl -sf $BASE/ | grep -q Factory"

if [ $FAIL -gt 0 ]; then
  echo "smoke FAILED: $FAIL checks"; exit 1
fi
echo "smoke PASSED"

#!/usr/bin/env bash
set -uo pipefail
export PATH="/opt/local/bin:/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"
K="${K:-$HOME/.kube/oke-direct}"
KC=(kubectl --kubeconfig "$K" --request-timeout=10s)

echo "=== Node conditions (pressure, deadlock, disk) ==="
# Quoted: unquoted, the [?(@.type=="Ready")] filter is a bash syntax error (measured 2026-09-27).
"${KC[@]}" get nodes -o custom-columns='NAME:.metadata.name,READY:.status.conditions[?(@.type=="Ready")].status,MEM:.status.conditions[?(@.type=="MemoryPressure")].status,DISK:.status.conditions[?(@.type=="DiskPressure")].status,PID:.status.conditions[?(@.type=="PIDPressure")].status' 2>&1

echo ""
echo "=== Node Problem Detector pods ==="
"${KC[@]}" get pods -A -l 'app=node-problem-detector' -o wide 2>&1 || echo "  (NPD not installed)"

echo ""
echo "=== NPD-reported conditions ==="
for n in $("${KC[@]}" get nodes -o name 2>/dev/null); do
  name=${n#node/}
  conds=$("${KC[@]}" get "$n" -o jsonpath='{.status.conditions[?(@.status=="True")].type}' 2>/dev/null | tr ' ' ',')
  echo "  $name: $conds"
done

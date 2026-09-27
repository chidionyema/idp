#!/usr/bin/env bash
set -uo pipefail
export PATH="/opt/local/bin:/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"
K="${K:-$HOME/.kube/oke-direct}"
KC=(kubectl --kubeconfig "$K" --request-timeout=10s)

echo "=== Top CPU-throttled containers ==="
"${KC[@]}" get --raw /metrics 2>/dev/null \
  | grep 'container_cpu_cfs_throttled_periods_total' \
  | awk -F'[{}]' '{gsub(/.*container="/,"",$2); gsub(/".*/,"",$2); print $2, $NF}' \
  | sort -k2 -rn | head -20 || echo "  (cAdvisor metrics unavailable)"

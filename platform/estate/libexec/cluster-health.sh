#!/usr/bin/env bash
set -uo pipefail
export PATH="/opt/local/bin:/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"
K="${K:-$HOME/.kube/oke-direct}"
KC=(kubectl --kubeconfig "$K" --request-timeout=10s)

echo "=== NODE STATUS ==="
"${KC[@]}" get nodes -o 'custom-columns=NAME:.metadata.name,READY:.status.conditions[-1:].status,REASON:.status.conditions[-1:].reason' 2>&1

echo ""
echo "=== UNHEALTHY PODS ==="
"${KC[@]}" get pods -A --field-selector=status.phase!=Running,status.phase!=Succeeded 2>&1 | head -40

echo ""
echo "=== WARNING EVENTS (last 20) ==="
"${KC[@]}" get events -A --field-selector type=Warning --sort-by='.metadata.creationTimestamp' 2>&1 | tail -20

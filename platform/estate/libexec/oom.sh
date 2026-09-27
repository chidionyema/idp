#!/usr/bin/env bash
set -uo pipefail
export PATH="/opt/local/bin:/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"
K="${K:-$HOME/.kube/oke-direct}"
KC=(kubectl --kubeconfig "$K" --request-timeout=10s)

echo "=== OOMKilled pods (last hour) ==="
"${KC[@]}" get pods -A -o json 2>/dev/null \
  | jq -r '.items[] | select(.status.containerStatuses != null) | .status.containerStatuses[] | select(.lastState.terminated.reason=="OOMKilled") | "\(.name)  exit=\(.lastState.terminated.exitCode)  at=\(.lastState.terminated.finishedAt)"' \
  | head -20 || echo "  (no OOMKilled containers)"

echo ""
echo "=== Exit code 137 (SIGKILL/OOM) events ==="
"${KC[@]}" get events -A --field-selector reason=OOMKilling 2>&1 | tail -10 || echo "  (none)"

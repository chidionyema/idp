#!/usr/bin/env bash
set -uo pipefail
export PATH="/opt/local/bin:/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"
if ! command -v kubectl-gadget >/dev/null 2>&1; then
  echo "kubectl-gadget not installed. Install: brew install kubectl-gadget"
  exit 0
fi
K="${K:-$HOME/.kube/oke-direct}"
CMD="${1:-trace-exec}"
echo "=== gadget $CMD (10s sample) ==="
case "$CMD" in
  trace-exec) timeout 10 kubectl-gadget trace exec --kubeconfig "$K" 2>&1 | head -30 ;;
  trace-open) timeout 10 kubectl-gadget trace open --kubeconfig "$K" 2>&1 | head -30 ;;
  trace-tcp)  timeout 10 kubectl-gadget trace tcp --kubeconfig "$K" 2>&1 | head -30 ;;
  top)        timeout 10 kubectl-gadget top --kubeconfig "$K" 2>&1 | head -30 ;;
  *)          echo "unknown gadget: $CMD (try trace-exec, trace-open, trace-tcp, top)"; exit 1 ;;
esac

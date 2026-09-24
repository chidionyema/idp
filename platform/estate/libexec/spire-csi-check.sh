#!/usr/bin/env bash
KC="kubectl --kubeconfig ${OKE_KUBECONFIG:-}"
NODE="${1:-}"
echo "=== CSI nodes ==="
$KC get csinodes -o wide
echo ""
if [ -n "$NODE" ]; then
  echo "=== Node $NODE detail ==="
  $KC get node "$NODE" -o wide
  echo ""
  echo "=== Pods on $NODE ==="
  $KC get pods -A -o wide --field-selector spec.nodeName="$NODE"
  echo ""
  echo "=== SPIRE pods on $NODE ==="
  $KC get pods -n spire-mgmt -o wide --field-selector spec.nodeName="$NODE"
fi

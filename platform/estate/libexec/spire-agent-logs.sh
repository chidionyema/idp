#!/usr/bin/env bash
KC="kubectl --kubeconfig ${OKE_KUBECONFIG:-}"
NODE="${1:-}"; LINES="${2:-100}"; SINCE="${3:-1h}"
if [ -z "$NODE" ]; then echo "ERROR: node required"; exit 1; fi
$KC logs -n spire-mgmt daemonset/spire-agent \
  --field-selector spec.nodeName="$NODE" \
  --tail="$LINES" --since="$SINCE" 2>&1 || echo "no logs or node not found"

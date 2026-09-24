#!/usr/bin/env bash
set -e
KC="kubectl --kubeconfig ${OKE_KUBECONFIG:-}"
NS="${1:-backstage}"; TIMEOUT="${2:-300s}"
$KC -n "$NS" delete pod spire-proof-manual --ignore-not-found 2>/dev/null || true
$KC -n "$NS" wait --for=delete pod/spire-proof-manual --timeout=30s 2>/dev/null || true
$KC -n "$NS" run spire-proof-manual \
  --image=ghcr.io/spiffe/spire-agent:1.15.3 \
  --restart=Never \
  --command -- /opt/spire/bin/spire-agent api fetch x509 \
    -socketPath /spiffe-workload-api/spire-agent.sock -timeout "$TIMEOUT" 2>&1
$KC -n "$NS" wait --for=condition=Ready pod/spire-proof-manual --timeout=60s
$KC -n "$NS" logs spire-proof-manual
$KC -n "$NS" delete pod spire-proof-manual --ignore-not-found

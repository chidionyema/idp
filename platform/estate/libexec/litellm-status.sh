#!/usr/bin/env bash
KC="kubectl --kubeconfig ${OKE_KUBECONFIG:-}"
COMP="${1:-all}"

case "$COMP" in all|deploy)
  echo "=== litellm Deployment ==="
  $KC get deploy -n llm
  echo ""
  $KC get pods -n llm -o wide
esac

case "$COMP" in all|externalsecret)
  echo "=== ExternalSecrets in llm ==="
  $KC get externalsecret -n llm 2>&1
  echo ""
  $KC describe externalsecret -n llm 2>&1 | tail -30
esac

case "$COMP" in all|pods)
  echo "=== litellm pod events ==="
  $KC get events -n llm --sort-by=.lastTimestamp | tail -20
esac

case "$COMP" in all|keys)
  echo "=== Broker key files ==="
  $KC exec -n llm deploy/litellm -c broker -- ls -la /vault-keys/ 2>&1 || echo "broker container not ready"
esac

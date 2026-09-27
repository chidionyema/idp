#!/usr/bin/env bash
set -uo pipefail
export PATH="/opt/local/bin:/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"
K="${K:-$HOME/.kube/oke-direct}"
KC=(kubectl --kubeconfig "$K" --request-timeout=10s)

echo "=== etcd / apiserver / scheduler pods ==="
"${KC[@]}" get pods -n kube-system 2>&1 | grep -E 'etcd|apiserver|scheduler|controller-manager' || echo "  (not visible - OKE managed control plane)"

echo ""
echo "=== API server latency (P99) ==="
"${KC[@]}" get --raw /metrics 2>/dev/null | grep 'apiserver_request_duration_seconds' | grep 'quantile="0.99"' | head -10 || echo "  (metrics unavailable)"

echo ""
echo "=== Admission webhook rejections ==="
"${KC[@]}" get --raw /metrics 2>/dev/null | grep 'apiserver_admission_webhook_rejection_count' | head -10 || echo "  (metrics unavailable)"

echo ""
echo "=== Scheduling latency (P99) ==="
"${KC[@]}" get --raw /metrics 2>/dev/null | grep 'scheduler_e2e_scheduling_duration_seconds' | grep 'quantile="0.99"' | head -5 || echo "  (metrics unavailable)"

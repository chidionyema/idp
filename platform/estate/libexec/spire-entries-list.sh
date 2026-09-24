#!/usr/bin/env bash
KC="kubectl --kubeconfig ${OKE_KUBECONFIG:-}"
echo "=== ClusterSPIFFEID entries ==="
$KC get clusterspiffeid -A 2>&1
echo ""
echo "=== SPIRE server pods ==="
$KC get pods -n spire-mgmt -o wide 2>&1
echo ""
echo "=== SPIRE agent status (all nodes) ==="
$KC get nodes -o wide 2>&1

#!/usr/bin/env bash
set -uo pipefail
export PATH="/opt/local/bin:/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"
K="${K:-$HOME/.kube/oke-direct}"
KC=(kubectl --kubeconfig "$K" --request-timeout=10s)

echo "=== VolumeAttachments (stuck CSI) ==="
"${KC[@]}" get volumeattachments -o custom-columns=\
NAME:.metadata.name,\
NODE:.spec.nodeName,\
ATTACHED:.status.attached 2>&1 | head -30

echo ""
echo "=== PVCs not Bound ==="
"${KC[@]}" get pvc -A --no-headers 2>/dev/null | awk '$3 != "Bound" {print}' | head -20
echo "  (empty = all bound)"

echo ""
echo "=== PVs Released/Failed ==="
"${KC[@]}" get pv --no-headers 2>/dev/null | awk '$5 != "Bound" && $5 != "Available" {print}' | head -20
echo "  (empty = all healthy)"

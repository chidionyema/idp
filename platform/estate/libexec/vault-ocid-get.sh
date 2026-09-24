#!/usr/bin/env bash
KC="kubectl --kubeconfig ${OKE_KUBECONFIG:-}"
echo "=== vault OCID from flux-system namespace ==="
$KC -n flux-system get configmap estate-vars -o jsonpath='{.data.vault_ocid}' 2>&1 || echo "estate-vars not found"
echo ""
echo "=== vault-ocid from llm namespace ==="
$KC -n llm get configmap vault-ocid -o jsonpath='{.data.vault_ocid}' 2>&1 || echo "vault-ocid not found in llm"

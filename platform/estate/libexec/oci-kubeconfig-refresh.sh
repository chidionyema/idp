#!/usr/bin/env bash
OKE_KUBECONFIG="${OKE_KUBECONFIG:-$HOME/.kube/oke-direct}"
CLUSTER_ID="ocid1.cluster.oc1.uk-london-1.aaaaaaaak3vxjechxim2cnrxowiec4jjvagtcbpenob2oj5ftcrq7jwxsjxq"
TOKEN=$(oci ce cluster generate-token \
  --cluster-id "$CLUSTER_ID" \
  --config-file "$HOME/.oci/config" \
  --profile agent \
  --auth security_token 2>/dev/null \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['status']['token'])")
if [[ -z "$TOKEN" ]]; then
  echo "ERROR: failed to generate token. Check OCI agent profile."
  exit 1
fi
if [[ -f "$OKE_KUBECONFIG" ]]; then
  sed -i '' "s|token: .*|token: $TOKEN|" "$OKE_KUBECONFIG"
fi
echo "token refreshed in $OKE_KUBECONFIG"

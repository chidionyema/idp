#!/usr/bin/env bash
# net-flannel-unmasq -- MUTATING. Remove flannel's orphaned masquerade chain from node nat tables.
# See platform/estate/intents/net-flannel-unmasq.yaml for why. Idempotent: a node without the
# chain reports "already clean".
set -uo pipefail
export PATH="/opt/local/bin:/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$HOME/.rd/bin:$PATH"
NODE="${1:-all}"
K=(kubectl --request-timeout=30s)

args=$("${K[@]}" -n kube-system get ds kube-flannel-ds -o jsonpath='{.spec.template.spec.containers[0].args}' 2>/dev/null)
case "$args" in *--ip-masq*) echo "REFUSED kube-flannel-ds still runs --ip-masq ($args): it re-adds the chain on restart. Remove the flag first."; exit 1;; esac

nodes=$("${K[@]}" get nodes -o jsonpath='{.items[*].metadata.name}')
[ "$NODE" = all ] || nodes="$NODE"
rc=0
for n in $nodes; do
  C=$("${K[@]}" -n kube-system get pod -l k8s-app=calico-node --field-selector "spec.nodeName=$n" -o name 2>/dev/null)
  [ -n "$C" ] || { echo "FAIL $n: no calico-node pod"; rc=1; continue; }
  echo "=== $n ($C)"
  "${K[@]}" -n kube-system exec "$C" -c calico-node -- sh -c '
    iptables-nft-save -t nat 2>/dev/null | grep -q FLANNEL-POSTRTG || { echo "already clean"; exit 0; }
    iptables-nft-save -c -t nat 2>/dev/null | grep FLANNEL-POSTRTG | sed "s/^/before: /"
    while iptables-nft -t nat -D POSTROUTING -m comment --comment "flanneld masq" -j FLANNEL-POSTRTG 2>/dev/null; do echo "removed POSTROUTING -> FLANNEL-POSTRTG"; done
    iptables-nft -t nat -F FLANNEL-POSTRTG 2>/dev/null && iptables-nft -t nat -X FLANNEL-POSTRTG 2>/dev/null && echo "deleted chain FLANNEL-POSTRTG"
    left=$(iptables-nft-save -t nat 2>/dev/null | grep -c FLANNEL)
    echo "flannel nat rules left: $left"; [ "$left" = 0 ]' 2>&1 | grep -v "iptables-legacy tables present" || rc=1
done
exit $rc

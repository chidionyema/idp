#!/usr/bin/env bash
# net-gnp-orphan-remove -- MUTATING (cluster network policy). Delete a Calico GlobalNetworkPolicy that
# is a Flux orphan and whose Deny rules deny nothing, after snapshotting it for net-gnp-restore.
# See platform/estate/intents/net-gnp-orphan-remove.yaml for why. Refuses unless every precondition
# holds; idempotent: an absent policy reports "already absent".
set -uo pipefail
export PATH="/opt/local/bin:/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$HOME/.rd/bin:$PATH"
NAME="$1"; SETLABEL="$2"
K=(kubectl --request-timeout=30s)
SNAP="$HOME/.estate/state/snapshots"; mkdir -p "$SNAP"

obj=$("${K[@]}" get globalnetworkpolicies.crd.projectcalico.org "$NAME" -o json 2>&1) || {
  case "$obj" in *NotFound*) echo "already absent: $NAME"; exit 0;; esac
  echo "REFUSED cannot read $NAME: $obj"; exit 1; }

# precondition 1: an orphan. A live Flux owner means git decides: fix it there, never under Flux's feet.
owner=$(printf '%s' "$obj" | python3 -c 'import json,sys; l=json.load(sys.stdin)["metadata"].get("labels",{}); print(l.get("kustomize.toolkit.fluxcd.io/namespace","")+"/"+l.get("kustomize.toolkit.fluxcd.io/name",""))')
if [ "$owner" != / ]; then
  ns=${owner%%/*}; ks=${owner#*/}
  if "${K[@]}" -n "$ns" get kustomizations.kustomize.toolkit.fluxcd.io "$ks" >/dev/null 2>&1; then
    echo "REFUSED $NAME is owned by live Flux Kustomization $owner: change it in git"; exit 1; fi
  echo "precondition ok: owner $owner no longer exists (orphan)"
else
  echo "precondition ok: no Flux owner label"
fi

# precondition 2: removing it loses no enforcement -- its one rule denies network sets with no nets
nets=$("${K[@]}" get globalnetworksets.crd.projectcalico.org -l "$SETLABEL" -o jsonpath='{.items[*].spec.nets[*]}' 2>&1) || {
  echo "REFUSED cannot read GlobalNetworkSets -l $SETLABEL: $nets"; exit 1; }
[ -z "$nets" ] || { echo "REFUSED sets -l $SETLABEL hold nets ($nets): the policy denies real traffic"; exit 1; }
rules=$(printf '%s' "$obj" | python3 -c 'import json,sys; s=json.load(sys.stdin)["spec"]; print(" ".join(r["action"] for r in s.get("egress",[])+s.get("ingress",[])))')
[ "$rules" = Deny ] || { echo "REFUSED expected exactly one Deny rule, found: ${rules:-none}"; exit 1; }
echo "precondition ok: its only rule denies sets -l $SETLABEL, which hold no nets"

snap="$SNAP/gnp-$NAME-$(date -u +%Y%m%dT%H%M%SZ).json"
printf '%s' "$obj" | python3 -c 'import json,sys; o=json.load(sys.stdin); m=o["metadata"]
for k in ("resourceVersion","uid","creationTimestamp","generation","managedFields"): m.pop(k,None)
json.dump(o,sys.stdout,indent=1)' > "$snap" && echo "snapshot: $snap"
"${K[@]}" delete globalnetworkpolicies.crd.projectcalico.org "$NAME" || exit 1
echo "rollback: estate-execute net-gnp-restore snapshot=$snap"

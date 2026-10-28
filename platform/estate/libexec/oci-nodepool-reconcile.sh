#!/usr/bin/env bash
# oci-nodepool-reconcile.sh -- remove phantom nodes from OKE node pools (idp#7343).
# Rules live in oci-nodepool-reconcile.py; this script only talks to OCI and only ever
# deletes a node the rules called a phantom. Dry run by default.
# Usage: oci-nodepool-reconcile.sh <apply|plan> [compartment_id]
# Exit: 0 ok, 2 BLIND (no identity/compartment/read), 3 a node delete did not happen.
set -uo pipefail

MODE="${1:-plan}"
case "$MODE" in apply | true) MODE=apply ;; plan | false) MODE=plan ;; esac
COMPARTMENT="${2:-${OCI_COMPARTMENT_OCID:-}}"
HERE="$(cd "$(dirname "$0")" && pwd)"
IDP="$(cd "$HERE/../../.." && pwd)"
OCI_CONFIG="${OCI_CONFIG:-$HOME/.oci/config}"
OCI_PROFILE="${OCI_PROFILE:-agent}"

[ "$MODE" = apply ] || [ "$MODE" = plan ] || { echo "FAIL  oci-nodepool-reconcile  mode must be plan or apply"; exit 2; }
command -v oci >/dev/null || { echo "BLIND oci-nodepool-reconcile  the oci CLI is not installed"; exit 2; }
command -v python3 >/dev/null || { echo "BLIND oci-nodepool-reconcile  python3 is missing"; exit 2; }

# Compartment discovery, exactly as oci-reclaim.sh does it.
if [ -z "$COMPARTMENT" ]; then
  MAIN="$(dirname "$(git -C "$IDP" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)")"
  for TV in "$IDP/platform/oci/terraform.tfvars" "$MAIN/platform/oci/terraform.tfvars"; do
    [ -f "$TV" ] || continue
    COMPARTMENT="$(sed -n 's/^compartment_ocid[[:space:]]*=[[:space:]]*"\(.*\)"/\1/p' "$TV" | head -1)"
    [ -n "$COMPARTMENT" ] && break
  done
fi
if [ -z "$COMPARTMENT" ]; then
  VAULT="${ESTATE_SECRETS:-$(dirname "$(git -C "$IDP" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)")/../estate-secrets}"
  VFILE="$VAULT/secrets/${OCI_ENV:-dev}/OCI_COMPARTMENT_OCID.yaml"
  if [ -f "$VFILE" ] && command -v sops >/dev/null; then
    COMPARTMENT="$(SOPS_AGE_KEY_FILE="${SOPS_AGE_KEY_FILE:-$HOME/.config/prospector/age-key.txt}" \
      sops -d --extract '["OCI_COMPARTMENT_OCID"]' "$VFILE" 2>/dev/null)"
  fi
fi
if [ -z "$COMPARTMENT" ] && command -v gh >/dev/null; then
  COMPARTMENT="$(gh api "repos/${GITHUB_REPOSITORY:-chidionyema/idp}/actions/variables/OCI_COMPARTMENT_OCID" --jq .value 2>/dev/null)"
fi
[ -n "$COMPARTMENT" ] || { echo "BLIND oci-nodepool-reconcile  no compartment: set OCI_COMPARTMENT_OCID or pass one"; exit 2; }

if [ "${OCI_CI:-0}" = "1" ] || [ "${OCI_CLI_AUTH:-}" = "security_token" ]; then
  OCI_PROFILE="${OCI_CLI_PROFILE:-DEFAULT}"
  AUTH=(--config-file "$OCI_CONFIG" --profile "$OCI_PROFILE" --auth security_token)
else
  AUTH=(--config-file "$OCI_CONFIG" --profile "$OCI_PROFILE")
fi

T="$(mktemp -d -t oci-nodepool.XXXXXX)"
trap 'rm -rf "$T"' EXIT

blind() { echo "BLIND oci-nodepool-reconcile  $1: $(tail -2 "$T/err" | tr '\n' ' ' | cut -c1-200)"; exit 2; }

# Every oci call costs ~15s of CLI start-up, so the reads run in parallel rounds (the door has
# a 90s budget): round 1 pools + instances, round 2 one get per pool, round 3 one get per node
# the instance list did not show.
oci ce node-pool list --compartment-id "$COMPARTMENT" --all "${AUTH[@]}" --output json >"$T/pools.json" 2>"$T/err" &
P1=$!
oci compute instance list --compartment-id "$COMPARTMENT" --all "${AUTH[@]}" --output json >"$T/inst.json" 2>"$T/err2" &
P2=$!
wait $P1 || blind "oci ce node-pool list failed"
wait $P2 || { cp "$T/err2" "$T/err"; blind "oci compute instance list failed"; }

python3 - "$T/pools.json" >"$T/poolids" <<'PY'
import json, sys
for p in json.load(open(sys.argv[1])).get("data", []):
    print(p["id"])
PY
N=0
while read -r PID; do
  [ -n "$PID" ] || continue
  N=$((N + 1))
  oci ce node-pool get --node-pool-id "$PID" "${AUTH[@]}" --output json >"$T/pool.$N.json" 2>"$T/perr.$N" &
done <"$T/poolids"
for J in $(jobs -p); do wait "$J" || blind "oci ce node-pool get failed"; done
python3 - "$T" "$N" >"$T/pools-full.json" <<'PY'
import json, sys
t, n = sys.argv[1], int(sys.argv[2])
acc = []
for i in range(1, n + 1):
    d = json.load(open(f"{t}/pool.{i}.json"))["data"]
    acc.append({"id": d["id"], "name": d.get("name"), "nodes": d.get("nodes") or []})
print(json.dumps(acc))
PY

python3 - "$T/inst.json" "$T/pools-full.json" "$T/instances.json" "$T/missing" <<'PY'
import json, sys
inst = {i["id"]: i.get("lifecycle-state") for i in json.load(open(sys.argv[1])).get("data", [])}
json.dump(inst, open(sys.argv[3], "w"))
with open(sys.argv[4], "w") as f:
    for p in json.load(open(sys.argv[2])):
        for n in p["nodes"]:
            if n.get("id") and n["id"] not in inst:
                f.write(n["id"] + "\n")
PY
# A 404 is "absent"; any other failure is BLIND, never a guess.
K=0
while read -r NID; do
  [ -n "$NID" ] || continue
  K=$((K + 1))
  oci compute instance get --instance-id "$NID" "${AUTH[@]}" --output json >"$T/one.$K.json" 2>"$T/oerr.$K" &
done <"$T/missing"
for J in $(jobs -p); do wait "$J"; done
for I in $(seq 1 "$K"); do
  [ "$K" -gt 0 ] || break
  if [ -s "$T/one.$I.json" ]; then
    python3 - "$T/instances.json" "$T/one.$I.json" <<'PY'
import json, sys
m = json.load(open(sys.argv[1])); d = json.load(open(sys.argv[2]))["data"]
m[d["id"]] = d.get("lifecycle-state"); json.dump(m, open(sys.argv[1], "w"))
PY
  elif ! grep -q '"status": 404' "$T/oerr.$I"; then
    cp "$T/oerr.$I" "$T/err"; blind "oci compute instance get failed"
  fi
done

python3 "$HERE/oci-nodepool-reconcile.py" --pools "$T/pools-full.json" --instances "$T/instances.json" \
  --ids-out "$T/ids" || exit 2

COUNT=$(wc -l <"$T/ids" | tr -d ' ')
if [ "$COUNT" -eq 0 ]; then
  echo "ok    oci-nodepool-reconcile  no phantom nodes: every pool node has a live instance"
  exit 0
fi
if [ "$MODE" = plan ]; then
  echo "plan  oci-nodepool-reconcile  $COUNT phantom node(s) would be removed; run with apply=true"
  exit 0
fi

DELETED=0; FAILED=0
while read -r PID NID; do
  [ -n "$NID" ] || continue
  if oci ce node-pool delete-node --node-pool-id "$PID" --node-id "$NID" --is-decrement-size true --force \
    "${AUTH[@]}" >/dev/null 2>"$T/err"; then
    DELETED=$((DELETED + 1))
    echo "ok    oci-nodepool-reconcile  delete-node requested $NID from pool $PID"
  else
    FAILED=$((FAILED + 1))
    echo "FAIL  oci-nodepool-reconcile  could not remove $NID: $(grep -o '"message": "[^"]*"' "$T/err" | head -1)"
  fi
done <"$T/ids"

# Measured result: re-read each pool.
while read -r PID; do
  oci ce node-pool get --node-pool-id "$PID" "${AUTH[@]}" --output json 2>/dev/null | python3 -c "
import json,sys
try: d=json.load(sys.stdin)['data']
except Exception: print('?'); sys.exit()
ns=d.get('nodes') or []
print('pool', d.get('name'), 'size', d.get('node-config-details',{}).get('size'), 'nodes', [(n.get('id','')[-8:], n.get('lifecycle-state')) for n in ns])
" | sed 's/^/measured oci-nodepool-reconcile  /'
done <"$T/poolids"
echo "ok    oci-nodepool-reconcile  requested $DELETED removal(s), $FAILED failed (delete-node is asynchronous: re-run to see the pool settle)"
[ "$FAILED" -eq 0 ] || exit 3
exit 0

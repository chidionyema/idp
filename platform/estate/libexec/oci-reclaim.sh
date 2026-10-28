#!/usr/bin/env bash
# oci-reclaim.sh -- free OCI capacity that orphaned block volumes are holding.
#
# The door behind the intent oci-reclaim (idp#7318). Read the rules in
# platform/estate/libexec/oci-reclaim.py: this script only talks to OCI, and it only ever
# deletes a volume the rules chose.
#
# A dry run is the default. The apply deletes one volume at a time, prints a receipt line per
# volume, and re-lists afterwards so the answer is measured, not asserted.
#
# Usage: oci-reclaim.sh <apply|plan> [keep_oldest] [older_than_hours] [compartment_id] [what] [node_id]
#   apply|plan            apply deletes, plan only reports
#   keep_oldest           how many of the oldest volumes to keep (default 3)
#   older_than_hours      minimum age of a reclaimable volume (default 24)
#   compartment_id        the compartment to look at (default: $OCI_COMPARTMENT_OCID, else the
#                         one in platform/oci/terraform.tfvars)
#   what                 "volumes" (default) or "node"
#   node_id              for what=node: the instance OCID whose capacity is being reclaimed
#
# Exit: 0 ok, 2 BLIND (no identity or no compartment), 3 a delete did not happen.
set -uo pipefail

MODE="${1:-plan}"
case "$MODE" in
  apply | true) MODE="apply" ;;
  plan | false) MODE="plan" ;;
esac
KEEP_OLDEST="${2:-3}"
OLDER_THAN_HOURS="${3:-24}"
COMPARTMENT="${4:-${OCI_COMPARTMENT_OCID:-}}"
WHAT="${5:-volumes}"
NODE_ID="${6:-}"

HERE="$(cd "$(dirname "$0")" && pwd)"
IDP="$(cd "$HERE/../../.." && pwd)"
OCI_CONFIG="${OCI_CONFIG:-$HOME/.oci/config}"
OCI_PROFILE="${OCI_PROFILE:-agent}"

if [ "$MODE" != "apply" ] && [ "$MODE" != "plan" ]; then
  echo "FAIL  oci-reclaim  mode must be plan or apply, not '$MODE'"
  exit 2
fi
if [ "$WHAT" != "volumes" ] && [ "$WHAT" != "node" ]; then
  echo "FAIL  oci-reclaim  what must be volumes or node, not '$WHAT'"
  exit 2
fi
command -v oci >/dev/null || { echo "BLIND oci-reclaim  the oci CLI is not installed"; exit 2; }
command -v python3 >/dev/null || { echo "BLIND oci-reclaim  python3 is missing"; exit 2; }

if [ -z "$COMPARTMENT" ]; then
  # The rendered tfvars of this tree, then of the main checkout: a worktree has no
  # terraform.tfvars of its own (it is git-ignored and written by bin/idp-oci-login).
  MAIN="$(dirname "$(git -C "$IDP" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)")"
  for TV in "$IDP/platform/oci/terraform.tfvars" "$MAIN/platform/oci/terraform.tfvars"; do
    [ -f "$TV" ] || continue
    COMPARTMENT="$(sed -n 's/^compartment_ocid[[:space:]]*=[[:space:]]*"\(.*\)"/\1/p' "$TV" | head -1)"
    [ -n "$COMPARTMENT" ] && break
  done
fi
if [ -z "$COMPARTMENT" ]; then
  # The vault's identifier (a compartment OCID is an identifier, not a credential, so it is
  # read here; the KEY is never read outside the founder's own terminal).
  VAULT="${ESTATE_SECRETS:-$(dirname "$(git -C "$IDP" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)")/../estate-secrets}"
  VFILE="$VAULT/secrets/${OCI_ENV:-dev}/OCI_COMPARTMENT_OCID.yaml"
  if [ -f "$VFILE" ] && command -v sops >/dev/null; then
    COMPARTMENT="$(SOPS_AGE_KEY_FILE="${SOPS_AGE_KEY_FILE:-$HOME/.config/prospector/age-key.txt}" \
      sops -d --extract '["OCI_COMPARTMENT_OCID"]' "$VFILE" 2>/dev/null)"
  fi
fi
if [ -z "$COMPARTMENT" ] && command -v gh >/dev/null; then
  # The repository variable the CI door itself uses (vars.OCI_COMPARTMENT_OCID). An identifier,
  # not a credential.
  REPO_SLUG="${GITHUB_REPOSITORY:-chidionyema/idp}"
  COMPARTMENT="$(gh api "repos/$REPO_SLUG/actions/variables/OCI_COMPARTMENT_OCID" --jq .value 2>/dev/null)"
fi
[ -n "$COMPARTMENT" ] || { echo "BLIND oci-reclaim  no compartment: set OCI_COMPARTMENT_OCID or pass one"; exit 2; }

# The identity: the CI path uses the exchanged session token, the laptop path uses the agent
# profile's own key. Nothing here prints a credential.
if [ "${OCI_CI:-0}" = "1" ] || [ "${OCI_CLI_AUTH:-}" = "security_token" ]; then
  # CI: the exchanged session token, written into the DEFAULT profile by the token exchange step.
  OCI_PROFILE="${OCI_CLI_PROFILE:-DEFAULT}"
  OCI_ARGS=(--compartment-id "$COMPARTMENT" --all --config-file "$OCI_CONFIG" --profile "$OCI_PROFILE" --auth security_token)
else
  OCI_ARGS=(--compartment-id "$COMPARTMENT" --all --config-file "$OCI_CONFIG" --profile "$OCI_PROFILE")
fi

LIST=$(mktemp -t oci-reclaim-volumes.XXXXXX)
IDS=$(mktemp -t oci-reclaim-ids.XXXXXX)
INST=$(mktemp -t oci-reclaim-instance.XXXXXX)
trap 'rm -f "$LIST" "$IDS" "$INST"' EXIT

if [ "$WHAT" = "node" ]; then
  # The node mode: reclaim the capacity a node that never came up is holding. OKE refuses to
  # remove that node from its pool ("LimitExceeded: nodes-per-node-pool limit has been
  # exceeded", oke-check run 40650458830) because the pool is already over the free tier's
  # limit, so the compute API is the door that can close the catch: it does not count pool
  # nodes. The rules are in oci-reclaim.py: only a STOPPED instance is ever a candidate.
  [ -n "$NODE_ID" ] || { echo "FAIL  oci-reclaim  the node mode needs an instance id"; exit 2; }
  if ! oci compute instance get --instance-id "$NODE_ID" --config-file "$OCI_CONFIG" \
    --profile "$OCI_PROFILE" --output json >"$INST" 2>/tmp/oci-reclaim-inst.err; then
    echo "BLIND oci-reclaim  oci compute instance get failed: $(tail -2 /tmp/oci-reclaim-inst.err | tr '\n' ' ' | cut -c1-200)"
    exit 2
  fi
  VERDICT=$(python3 "$HERE/oci-reclaim.py" --node-instance "$INST")
  case "$VERDICT" in
    TERMINE*)
      if [ "$MODE" = "plan" ]; then
        echo "plan  oci-reclaim  $VERDICT"
      else
        if oci compute instance terminate --instance-id "$NODE_ID" --force \
          --config-file "$OCI_CONFIG" --profile "$OCI_PROFILE" >/dev/null 2>/tmp/oci-reclaim-term.err; then
          echo "ok    oci-reclaim  terminating $NODE_ID -- it was STOPPED: it served nothing"
        else
          echo "FAIL  oci-reclaim  could not terminate $NODE_ID: $(grep -o '"message": "[^"]*"' /tmp/oci-reclaim-term.err | head -1)"
          exit 3
        fi
      fi
      ;;
    *)
      echo "keep  oci-reclaim  $VERDICT"
      ;;
  esac
  # The boot volume the node was holding: it is released when the termination settles, and it
  # is deleted only when OCI says it is free (AVAILABLE, no attachment).
  BOOT=$(python3 -c "
import json
d = json.load(open('$INST'))
d = d.get('data', d)
print(d.get('boot-volume-id') or '')
" 2>/dev/null || echo "")
  if [ -n "$BOOT" ]; then
    VOLSTATE=$(oci bv volume get --volume-id "$BOOT" --config-file "$OCI_CONFIG" \
      --profile "$OCI_PROFILE" --output json 2>/dev/null | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
except ValueError:
    print('unknown'); raise SystemExit(0)
d = d.get('data', d)
print(d.get('lifecycle-state') or 'unknown')
" 2>/dev/null || echo unknown)
    ATTACHMENTS=$(oci compute volume-attachment list --compartment-id "$COMPARTMENT" --all \
      --config-file "$OCI_CONFIG" --profile "$OCI_PROFILE" --output json 2>/dev/null | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
except ValueError:
    print(0); raise SystemExit(0)
items = d.get('data', d) if isinstance(d, dict) else d
print(sum(1 for a in (items or []) if a.get('volume-id') == '$BOOT'))
" 2>/dev/null || echo "?")
    if [ "$VOLSTATE" = "AVAILABLE" ] && [ "$ATTACHMENTS" = "0" ]; then
      if [ "$MODE" = "plan" ]; then
        echo "plan  oci-reclaim  the boot volume $BOOT is free and would be deleted"
      elif oci bv volume delete --volume-id "$BOOT" --force --config-file "$OCI_CONFIG" \
        --profile "$OCI_PROFILE" >/dev/null 2>/tmp/oci-reclaim-boot.err; then
        echo "ok    oci-reclaim  deleted the boot volume $BOOT (the node's)"
      else
        echo "keep  oci-reclaim  the boot volume $BOOT is free but OCI refused the delete: $(grep -o '"message": "[^"]*"' /tmp/oci-reclaim-boot.err | head -1)"
      fi
    else
      echo "keep  oci-reclaim  the boot volume $BOOT is $VOLSTATE with $ATTACHMENTS attachment(s): it is released when the termination settles, then run the door again"
    fi
  fi
  exit 0
fi

if ! oci bv volume list "${OCI_ARGS[@]}" --output json >"$LIST" 2>/tmp/oci-reclaim.err; then
  echo "BLIND oci-reclaim  oci bv volume list failed: $(tail -2 /tmp/oci-reclaim.err | tr '\n' ' ' | cut -c1-200)"
  exit 2
fi

python3 "$HERE/oci-reclaim.py" --volumes "$LIST" --keep-oldest "$KEEP_OLDEST" \
  --older-than-hours "$OLDER_THAN_HOURS" --ids-out "$IDS" || exit 2

COUNT=$(wc -l <"$IDS" | tr -d ' ')
if [ "$COUNT" -eq 0 ]; then
  echo "ok    oci-reclaim  nothing is reclaimable: the capacity is not held by orphaned volumes"
  exit 0
fi
if [ "$MODE" = "plan" ]; then
  echo "plan  oci-reclaim  $COUNT volume(s) would be deleted; run with apply to delete them"
  exit 0
fi

DELETED=0
FAILED=0
KEPT_ATTACHED=0
while read -r OCID; do
  [ -n "$OCID" ] || continue
  NAME=$(python3 - "$LIST" "$OCID" <<'PY'
import json, sys
doc = json.load(open(sys.argv[1]))
for v in doc.get("data", doc):
    if v.get("id") == sys.argv[2]:
        print(v.get("display-name") or sys.argv[2])
        break
PY
)
  # --force: the OCI CLI asks for a confirmation on an interactive terminal, and a door that
  # runs without one would abort on the answer it never got.
  if oci bv volume delete --volume-id "$OCID" --force --config-file "$OCI_CONFIG" --profile "$OCI_PROFILE" >/dev/null 2>/tmp/oci-reclaim-del.err; then
    DELETED=$((DELETED + 1))
    printf 'ok    oci-reclaim  deleted %s (%s)\n' "$NAME" "$OCID"
  elif grep -q "may not be deleted while attached" /tmp/oci-reclaim-del.err; then
    # The API is the truth about an attachment, not the list: a volume the list calls
    # unattached can still be attached to a node. The refusal is a KEEP, not a failure: this
    # volume carries a PersistentVolume that is in use.
    KEPT_ATTACHED=$((KEPT_ATTACHED + 1))
    printf 'keep  oci-reclaim  %s (%s) is attached to an instance; it is in use\n' "$NAME" "$OCID"
  else
    FAILED=$((FAILED + 1))
    printf 'FAIL  oci-reclaim  could not delete %s (%s): %s\n' "$NAME" "$OCID" \
      "$(grep -o '"code": "[^"]*"' /tmp/oci-reclaim-del.err | head -1)$(grep -o '"message": "[^"]*"' /tmp/oci-reclaim-del.err | head -1)"
  fi
done <"$IDS"

# The receipt is measured, not asserted: the compartment is listed again and counted. A delete
# is asynchronous, so a volume OCI is still tearing down is not counted as held.
AFTER=$(mktemp -t oci-reclaim-after.XXXXXX)
oci bv volume list "${OCI_ARGS[@]}" --output json >"$AFTER" 2>/dev/null
LEFT=$(python3 -c "
import json,sys
doc=json.load(open('$AFTER'))
items=doc.get('data',doc)
held=[v for v in items if v.get('lifecycle-state') not in ('TERMINATING','TERMINATED')]
print(len(held), sum(int(v.get('size-in-gbs') or 0) for v in held))
" 2>/dev/null || echo "? ?")
rm -f "$AFTER"
echo "ok    oci-reclaim  deleted $DELETED volume(s), $KEPT_ATTACHED kept because they are attached, $FAILED failed; the compartment now holds $LEFT (count GB)"
[ "$FAILED" -eq 0 ] || exit 3
exit 0

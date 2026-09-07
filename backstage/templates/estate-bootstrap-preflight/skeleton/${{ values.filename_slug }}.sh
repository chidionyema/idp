#!/usr/bin/env bash
# Estate bootstrap preflight runbook.
#
# Rendered by the Backstage Scaffolder tile `estate-bootstrap-preflight`.
# The scaffolder renders only the FILENAME (the operator + reason slug
# becomes the script's file name in the PR). The body below takes its
# values from argv, so the file is a plain bash script the moment it
# lands in the repo -- no template markers in the body, no pre-commit
# bash-parse false positives.
#
# Usage:
#   bin/estate-preflight.d/<operator>-<reason>.sh \
#       '<reason>' <operator> <scope>
#
# Where scope is one of: full | tailscale | cloudflare | vendors | estate-seed
# (full walks every provider in dependency order; the others skip to one.)
#
# Standing ruling (crew#66, R45-root-trust): every credential the estate
# holds is born through a bootstrapper, never pasted. This script is the
# operator's half: it prints the preflight command, the SSO consent it
# will open, and the root-trust post-condition. It stops at the green
# gate; the live run is `bin/idp-bootstrap-estate` (no flag) and is a
# separate, deliberate act. The PR that added this file is the audit
# trail -- reviewers see the scope, the reason, and the operator's
# handle without having to read a chat thread.

set -euo pipefail
IDP=$(cd "$(dirname "$0")/../.." && pwd)

# 0. trap: standard shape (bin/idp-bootstrap-macrun). The script is
#    read-only -- it does not write the vault, does not mint a key --
#    so the trap just reports the exit code; no temp dirs to clean.
on_exit() {
	local ec=$?
	[ "$ec" -eq 0 ] || echo "  (preflight-runbook exit $ec)" >&2
}
trap on_exit EXIT

REASON="${1:?usage: $0 '<reason>' <operator> <scope>}"
OPERATOR="${2:?usage: $0 '<reason>' <operator> <scope>}"
SCOPE="${3:?usage: $0 '<reason>' <operator> <scope>}"
case "$SCOPE" in
full) CMD="bin/idp-bootstrap-estate --preflight" ;;
tailscale) CMD="bin/idp-bootstrap-tailscale --preflight" ;;
cloudflare) CMD="bin/idp-bootstrap-cloudflare --preflight" ;;
vendors) CMD="bin/idp-bootstrap-vendors --preflight" ;;
estate-seed) CMD="bin/idp-estate-seed --preflight" ;;
*)
	echo "FAIL    preflight-runbook: unknown scope '$SCOPE'" >&2
	exit 2
	;;
esac

cat <<EOF
## Preflight: $REASON (scope=$SCOPE, operator=@$OPERATOR)

Run, on this operator's laptop, from the estate repo root:
    \$IDP/$CMD

What happens, in order: (1) the bootstrapper opens one SSO consent in your
browser -- your OCI tenancy, your vendor console, whichever is missing for
this scope; that consent is the only manual act. (2) The bootstrapper mints
every derived credential through the provider's API; you never paste one.
(3) The bootstrapper writes the vault through bin/idp-vault-put; values
stay in process; the audit row is a key NAME, not a value. (4) The
bootstrapper proves the credential works (token exchange, read with it)
before storing it. (5) The orchestrator ends with bin/idp-root-trust
--check, the gate every run is graded against: exit 0 means every row in
docs/reference/policy/root-trust.md is MEETS and the estate is ready.

What you do NOT do during a preflight: edit ~/.estate/.env unless a
rotation is the explicit purpose; run the live 'bin/idp-bootstrap-estate'
(no flag) until the preflight is green; bypass the root-trust gate.
EOF

if [ -t 0 ]; then read -r -p "Press Enter to run the preflight now, or Ctrl-C to abort: "; fi
command -v jq >/dev/null 2>&1 || {
	echo "FAIL    preflight-runbook: jq not installed" >&2
	exit 2
}
[ -f "$IDP/$CMD" ] || {
	echo "FAIL    preflight-runbook: $IDP/$CMD not found" >&2
	exit 2
}

cd "$IDP"
"$CMD"
RC=$?
LIVE="${CMD% --preflight}"
case $RC in
0) echo "PASS    preflight: $SCOPE is ready. Run '$IDP/$LIVE' for the live seed when ready." ;;
1) echo "FAIL    preflight: a row in docs/reference/policy/root-trust.md is MISS or PARTIAL. Do not bypass." ;;
2) echo "BLIND   preflight: a tool, a session, or the vault is missing. The line above names which." ;;
*) echo "UNKNOWN preflight: exit $RC (treat as FAIL; rerun with bash -x for the failing step)" ;;
esac
exit $RC

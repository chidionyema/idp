#!/bin/bash
# crew#751 CP1: WORK dispatch runs Cursor CLI on the Mac through mac-run.
# Auth is the vault CURSOR_API_KEY (SEED_CURSOR_API_KEY). A person Cursor login
# is not a machine identity; Cursor SSO (SAML) is for people and does not mint
# a machine credential, and there is no GitHub OIDC exchange (unlike Tailscale).
# The key never appears in argv (--api-key and env CURSOR_API_KEY= are both
# visible in ps): it is read from the vault file and passed on ssh stdin.
# `$$` escapes a dollar Flux must leave alone (same as mac-run.tpl). The `.tpl`
# extension keeps this file a template until Flux renders it.
# Non-interactive ssh often misses ~/.local/bin; the remote login shell puts it back.
# shellcheck disable=SC1083,SC2034,SC2016
set -euo pipefail
on_exit() {
	rc=$?
	[ "$rc" -eq 0 ] || echo "cursor-agent: gave up before agent started (exit $rc)" >&2
}
trap on_exit EXIT
command -v mac-run >/dev/null || {
	echo "cursor-agent: mac-run is not on PATH" >&2
	exit 2
}
dir=$${HERMES_ENV_DIR:-/run/secrets/hermes-agent-env}
file="$dir/CURSOR_API_KEY"
if [ ! -s "$file" ]; then
	echo "cursor-agent: no CURSOR_API_KEY in the vault; refusing the Mac login" >&2
	exit 2
fi
IFS= read -r key <"$file" || exit 2
printf '%s\n' "$key" | exec mac-run bash -lc 'IFS= read -r CURSOR_API_KEY; export CURSOR_API_KEY; export PATH="$$HOME/.local/bin:/usr/local/bin:$$PATH"; exec agent "$$@"' agent "$$@"

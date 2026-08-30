#!/bin/bash
# crew#516 CP5 (founder's locked spec, crew#66 5451926212 Phase 3): "inside the Hermes agent pod,
# execution is cleanly abstracted into a deterministic script injected via a Kubernetes ConfigMap".
# Mounted read-only, mode 0755, at /usr/local/bin/mac-run in the gateway container (gateway.yaml) --
# never baked into the image, so a change here needs no rebuild. FOUNDER_MAC_USER and
# FOUNDER_MAC_TS_IP are Flux postBuild substitutions from clusters/oke/estate-config.yaml (LAW 46:
# this script is the only place the Mac's tailnet IP or login user may be named, and it names them
# through a variable, never a literal). `$$` escapes a dollar Flux must leave alone; a single dollar
# in front of a braced name is a substitution. This comment may not spell an empty braced name: the
# envsubst rung of bin/idp-ci parses comments too and answers `unable to parse variable name`.
# The `.tpl` extension says the same thing, and keeps the shell linters off a file
# that is not valid shell until Flux has rendered it.
#
# crew#561: the identity to sshd is a key, because Tailscale SSH cannot run on the founder's GUI
# Tailscale build (platform/tailscale/policy.hujson header, kb/1193). The key is minted on a CI
# runner into vault `hermes-mac-run` (bin/idp-bootstrap-macrun), lands here through the
# ExternalSecret in mac-run-key.yaml, and is never in git, never typed, never printed.
#
# The SOCKS5 ProxyCommand into the sidecar (localhost:1055, tailscale.yaml) is Tailscale's own
# pattern for a pod that must not hold NET_ADMIN
# (tailscale.com/docs/solutions/connect-kubernetes-pods-to-tailnet-using-sidecar; LAW 21, LAW 43).
# ConnectTimeout=5 is the fail-fast half of the "sleeping Mac" UX: a dead tunnel or a sleeping host
# answers in 5s, not a hung request.
# shellcheck disable=SC1083  # `$$` is Flux's escape for a dollar it must leave alone (see the
# header): ShellCheck reads the second `{` as literal because this file is a template, not shell.
set -euo pipefail
# crew#561: every failure before `exec` used to reach the caller as a bare non-zero exit, and the
# founder read three days of them as "no tailscale on pod". This says which side gave up. It never
# fires on the ssh path: `exec` replaces this process, so a remote failure is ssh's own exit code.
on_exit() {
	rc=$?
	[ "$rc" -eq 0 ] || echo "mac-run: gave up before ssh started (exit $rc)" >&2
}
trap on_exit EXIT
src=$${MAC_RUN_KEY_DIR:-/run/secrets/hermes-agent-mac-run}/id_ed25519
[ -s "$src" ] || {
	echo "mac-run: no key at $src (vault hermes-mac-run not synced yet; oke-check apply mints it)" >&2
	exit 2
}
# crew#561 (otto-parity run 33291368505, 2026-08-30 03:58Z): the tunnel was up and the key was
# mounted, and `cp` to the fixed name /tmp/mac-run.id_ed25519 died with "Permission denied", so
# Otto could not reach the Mac and the founder read it as "no tailscale on pod". A fixed name is
# also a race between two calls. otto-parity run 33294804159 (2026-08-30): ssh reaches the Mac with
# the mounted key directly (row key-direct), and the stale 0400 copy in /tmp was the whole outage;
# so no copy, ever.
exec ssh -i "$src" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new \
	-o UserKnownHostsFile="$${HERMES_HOME:-/data}/known_hosts" -o ConnectTimeout=5 \
	-o ProxyCommand='nc -x localhost:1055 %h %p' "${FOUNDER_MAC_USER}@${FOUNDER_MAC_TS_IP}" "$@"

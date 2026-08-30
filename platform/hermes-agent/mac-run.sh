#!/bin/bash
# shellcheck disable=SC1083  # `$${VAR}` is Flux's escape: postBuild substitutes ${FOUNDER_*} and leaves $$ as one $ for the shell
# crew#516 CP5 (founder's locked spec, crew#66 5451926212 Phase 3): "inside the Hermes agent pod,
# execution is cleanly abstracted into a deterministic script injected via a Kubernetes ConfigMap".
# Mounted read-only, mode 0755, at /usr/local/bin/mac-run in the gateway container (gateway.yaml) —
# never baked into the image, so a change here needs no rebuild.
# crew#561, 2026-08-30: that mount is a subPath, and Kubernetes never refreshes a subPath-mounted
# ConfigMap in a running pod (kubernetes.io/docs/concepts/storage/volumes, configMap: "a container
# using a ConfigMap as a subPath volume mount will not receive ConfigMap updates"). idp#935 and
# idp#949 both landed on the cluster and the pod kept running the 02:45Z script (otto-parity
# 33295694219 still printed the old cp). So the ConfigMap is generated from this file by kustomize
# (kustomization.yaml, configMapGenerator) with a content hash in its name: every change to this
# file renames the ConfigMap, rewrites the Deployment's reference, and rolls the pod. FOUNDER_MAC_USER and
# FOUNDER_MAC_TS_IP are Flux postBuild substitutions from clusters/oke/estate-config.yaml (LAW 46:
# this script is the only place the Mac's tailnet IP or login user may be named, and it names them
# through a variable, never a literal).
#
# crew#561: the identity to sshd is a key, because Tailscale SSH cannot run on the founder's GUI
# Tailscale build (platform/tailscale/policy.hujson header, kb/1193). The key is minted on a CI
# runner into vault `hermes-mac-run` (bin/idp-bootstrap-macrun), lands here through the
# ExternalSecret in mac-run-key.yaml, and is never in git, never typed, never printed. ssh refuses a
# group-readable key file, and the mounted file is 0440 under fsGroup 10001, so the script copies
# it to /tmp (emptyDir) with mode 600 first. Host keys are pinned on the volume (/data, the PVC):
# accept-new on first contact, refused on change.
#
# The SOCKS5 ProxyCommand into the sidecar (localhost:1055, tailscale.yaml) is Tailscale's own
# pattern for a pod that must not hold NET_ADMIN
# (tailscale.com/docs/solutions/connect-kubernetes-pods-to-tailnet-using-sidecar; LAW 21, LAW 43).
# ConnectTimeout=5 is the fail-fast half of the "sleeping Mac" UX: a dead tunnel or a sleeping host
# answers in 5s, not a hung request.
set -euo pipefail
src=$${MAC_RUN_KEY_DIR:-/run/secrets/hermes-agent-mac-run}/id_ed25519
[ -s "$src" ] || { echo "mac-run: no key at $src (vault hermes-mac-run not synced yet; oke-check apply mints it)" >&2; exit 2; }
# crew#561 (otto-parity run 33291368505, 2026-08-30 03:58Z): the tunnel was up and the key was
# mounted, and `cp` to the fixed name /tmp/mac-run.id_ed25519 died with "Permission denied", so
# Otto could not reach the Mac and the founder read it as "no tailscale on pod". A fixed name is
# also a race between two calls. Each call now gets its own 0700 directory: under TMPDIR, or
# under HERMES_HOME (the PVC, where known_hosts already lives) when /tmp refuses; removed on exit.
# otto-parity run 33294804159 (2026-08-30): ssh reaches the Mac with the mounted key directly
# (row key-direct), and the stale 0400 copy in /tmp was the whole outage; so no copy, ever.
exec ssh -i "$src" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new \
  -o UserKnownHostsFile="$${HERMES_HOME:-/data}/known_hosts" -o ConnectTimeout=5 \
  -o ProxyCommand='nc -x localhost:1055 %h %p' "${FOUNDER_MAC_USER}@${FOUNDER_MAC_TS_IP}" "$@"

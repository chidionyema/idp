#!/usr/bin/env bash
# spire-proof-run -- prove a workload on OKE is issued an X.509 SVID: one ephemeral pod, the spec
# of platform/spire/proof-cronjob.yaml (CSI socket mounted, PSA-restricted, OnFailure so the
# agent's entry sync is not raced by a new pod uid), its log read, the pod deleted on every path.
#
# Measured 2026-09-27: the CronJob is not on the cluster (spire has no Flux row), so nothing on OKE
# proves possession. The previous version of this script could not either: its `kubectl run` pod
# mounted no workload-API socket, was refused by backstage's PSA `restricted`, waited for Ready on
# a pod that exits, and returned 0 whatever it logged.
#
# Exit: 0 an SVID was issued (the SPIFFE ID is printed), 1 not proven -- never 0 on a guess.
set -uo pipefail
NS="${1:-backstage}"; TIMEOUT="${2:-300s}"
secs="${TIMEOUT%s}"
case "$secs" in ''|*[!0-9]*) echo "REFUSED timeout=$TIMEOUT is not <seconds>s"; exit 1;; esac
KC=(kubectl --request-timeout=30s)
[ -n "${OKE_KUBECONFIG:-}" ] && KC+=(--kubeconfig "$OKE_KUBECONFIG")
POD=spire-proof-manual
IMAGE=ghcr.io/spiffe/spire-agent:1.15.3   # as proof-cronjob.yaml: the image the spire chart runs

cleanup() { "${KC[@]}" -n "$NS" delete pod "$POD" --ignore-not-found --wait=false >/dev/null 2>&1; }
trap cleanup EXIT
cleanup
"${KC[@]}" -n "$NS" wait --for=delete "pod/$POD" --timeout=30s >/dev/null 2>&1

overrides=$(cat <<EOF
{"spec": {"restartPolicy": "OnFailure",
  "securityContext": {"runAsNonRoot": true, "runAsUser": 1000, "seccompProfile": {"type": "RuntimeDefault"}},
  "containers": [{"name": "$POD", "image": "$IMAGE",
    "command": ["/opt/spire/bin/spire-agent", "api", "fetch", "x509",
                "-socketPath", "/spiffe-workload-api/spire-agent.sock", "-timeout", "${secs}s"],
    "securityContext": {"allowPrivilegeEscalation": false, "readOnlyRootFilesystem": true,
                        "capabilities": {"drop": ["ALL"]}},
    "resources": {"requests": {"cpu": "10m", "memory": "32Mi"}, "limits": {"cpu": "100m", "memory": "64Mi"}},
    "volumeMounts": [{"name": "spiffe-workload-api", "mountPath": "/spiffe-workload-api", "readOnly": true},
                     {"name": "tmp", "mountPath": "/tmp"}]}],
  "volumes": [{"name": "tmp", "emptyDir": {"sizeLimit": "16Mi"}},
              {"name": "spiffe-workload-api", "csi": {"driver": "csi.spiffe.io", "readOnly": true}}]}}
EOF
)
if ! err=$("${KC[@]}" -n "$NS" run "$POD" --image="$IMAGE" --restart=OnFailure --overrides="$overrides" 2>&1); then
  echo "NOT PROVEN could not create $NS/$POD: $err"; exit 1
fi

phase=""; deadline=$((SECONDS + secs + 60))
while [ "$SECONDS" -lt "$deadline" ]; do
  phase=$("${KC[@]}" -n "$NS" get pod "$POD" -o jsonpath='{.status.phase}' 2>/dev/null)
  case "$phase" in Succeeded|Failed) break;; esac
  sleep "${SPIRE_PROOF_POLL_S:-5}"
done
logs=$("${KC[@]}" -n "$NS" logs "$POD" 2>&1)
printf '%s\n' "$logs"
id=$(printf '%s\n' "$logs" | sed -n 's/^SPIFFE ID:[[:space:]]*//p' | head -1)
if [ "$phase" = Succeeded ] && [ -n "$id" ]; then
  echo "ok SVID issued to $NS/$POD: $id"; exit 0
fi
echo "NOT PROVEN no SVID: phase=${phase:-unknown} after ${secs}s (+60s)"
exit 1

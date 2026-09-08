# RESUME HERE — 2026-09-08

## The fire
Estate at 26/80 Flux Kustomizations Ready and climbing slowly. Only 5-6 are actually broken;
the rest are queued behind `edge`. Every root failure is an admission webhook timing out.

## Root cause, four converging angles
The API server cannot reach pods on node `10.0.159.197`.
- cert-manager: 3 of 3 pods on .197 -> its webhook fails 100%
- external-secrets: 4 of 4 pods on .197 -> its webhook fails 100%
- kyverno: 1 of 2 pods on .197 -> fails ~50%, which is the 13<->26 oscillation
- kustomize-controller was on .197 and fetched no artifact at all; PR #2546 moved it to
  .221 by podAffinity and artifact fetching recovered completely.

Mechanism (not proved, kernel state is not readable from `agent-reader`): flannel's DaemonSet
was deleted but `flannel.1` and its 10.244.0.0/16 routes survive in the node kernel and
collide with Calico's. Both nodes still carry `flannel.alpha.coreos.com/backend-data`, VNI 1.

## Staged with the founder (telegram 43621)
Scale the OKE node pool 2 -> 3 (no room to drain .197 at 91/95 percent CPU requested), then
recycle 10.0.159.197. Step one is the `oci-scale-node-pool` JIT grant, which is also the
end-to-end break-glass proof crew#920 wants. `jit-broker` is 1/1 Running on .221 now.

## In flight — the durable fix I can land without his hand
An admission webhook with `failurePolicy: Fail` and one replica is a cluster-wide single point
of failure: losing its node stops every apply in the estate, including the apply that repairs
it. cert-manager-webhook and external-secrets-webhook are both `replicas: 1`, no PDB, no
anti-affinity. Kyverno already has 2 + required anti-affinity, which is why it degrades to 50%
instead of 100%.

`bin/idp-availability-gate` already encodes exactly this standard (replicas >= 2, PDB as
maxUnavailable, required podAntiAffinity on hostname) but `grade_helm` reads only the
TOP-LEVEL chart keys, so a sub-chart deployment like `webhook.replicaCount` is invisible to it.
That is the blind spot to close.

Three-part change, one PR:
1. `bin/idp-availability-gate`: `grade_helm(hr, objs, component=None)` reads
   `values[component]` for replicaCount / podDisruptionBudget / affinity; `judge` passes it
   through; the `also_graded` loop reads an optional `component:` key and keys `settled` on
   surface+component.
2. `platform/edge/cert-manager.yaml` and `platform/secrets/external-secrets.yaml`:
   `webhook.replicaCount: 2`, `webhook.podDisruptionBudget {enabled: true, maxUnavailable: 1}`,
   `webhook.affinity` required podAntiAffinity on `kubernetes.io/hostname`.
3. `platform/availability.yaml`: two `also_graded` rows naming those webhooks + component.
4. A test beside `tests/test_the_availability_gate_sees_through_a_traefik_router.py` (same
   SourceFileLoader import pattern) proving `grade_helm` both ways on a component.

Chart keys verified with `helm show values`: cert-manager v1.21.1 and external-secrets 2.9.0
both expose `webhook.replicaCount`, `webhook.podDisruptionBudget`, `webhook.affinity`.

Honest limit: two replicas turns "never converges" into "converges on retry" (50% like
kyverno). The full cure is still the node.

## Still open, crew#920
- ephemeral/shadow cluster #2471, gated on #2470
- JIT broker end to end with a real tap (WJ.2/3/4) — the node-pool scale is the honest target
- ClickHouse still CrashLoopBackOff, 38 restarts
- second CNI plan in the tree: platform/cni/cilium-values.yaml + the cilium-replace playbook in
  bin/idp-oke-break-glass, offered to the founder, not started (glass-break gated)
- crossplane-providers fails on a missing oci.upbound.io/v1beta1 CRD; gates nothing

## RESUME HERE (session e5728c64, 2026-09-08 18:35Z)

Leaving: investor brief (published, artifact 7d2683e1-9afc-4d8b-a99e-04de4b63cfe4, version "Counted figures only").
Opening: worktree `fix/hindsight-offline-hub` for a two-line fix, hindsight-api hangs on an outbound call to
huggingface.co that the namespace egress fence never answers (SYN_SENT to 3.174.141.51:443 inside the pod).
Handoff for the DeepSeek lane: `docs/specs/2026-09-08-cyrus-and-knowledge-base-work-order.md` (Cyrus rolls every
ten minutes: GithubAccessToken generator at 10m plus Reloader auto=true; knowledge base moves to hindsight).
Founder record for DeepSeek's recovery: `~/.claude/docs/founder/2026-09-08T1817Z-update-entory-the-estate-platform-recovery-is-done-6089258a.md`.

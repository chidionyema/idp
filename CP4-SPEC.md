# crew#892 CP4 (idp slice) — gVisor cell for execute_code

State: grounding complete on branch `feat/crew892-cp4-gvisor-sandbox` off
origin/main `bd2c2e76` (live cluster esttare-crq7jwxsjxq: 2 Ready nodes, no
RuntimeClass today). This repo slice closes the tracked estate gap named in
ADRs/0023 line 55 ("No runtimeClassName anywhere in platform/ — Missing") and
implements zero-trust-boundary.md step 5 + deepseek-work-order.md item 12.

## Estate decree (authoritative, already written — I implement, not invent)
- zero-trust-boundary.md:150-185 step 5: "A RuntimeClass for gVisor, and
  admission that refuses a pod in a CELL namespace that does not name it or
  that asks for privileged: true. Kyverno already runs and this is ONE more
  policy, not a second engine." + "Default-deny egress on the cell, with the
  one allowed route being the gateway." Accept: a cell pod without the runtime
  class is refused at admission, proved both ways in one run.
- step 6: `bin/idp-ci` gains, IN AN EXISTING pass not a new pipeline:
  conftest over tenant dirs (a fence allowing internet egress FAILS) + a
  pod-security check (privileged:true, host networking, hostPath mounts, and a
  missing runtime class in a cell namespace each FAIL). Each with fixture pair
  + AGENTS.md row.
- deepseek-work-order item 12 row: "gVisor RuntimeClass and a Kyverno policy
  refusing a cell-namespace pod that does not name it or asks privileged:true;
  default-deny egress on the cell with the gateway the one allowed route."
  Accept: "admission refuses the bad pod and admits the good one in one run."
  14/18 items are REPO-executable with no cluster privileges.

## Ground truth / patterns to mirror
- Kyverno ClusterPolicy idiom (`platform/scheduling/capacity-affinity.yaml`):
  apiVersion kyverno.io/v1, kind ClusterPolicy, policies.kyverno.io/annotations,
  spec.rules match resources.kinds [Pod], validate/deny/preconditions.
- PSA on a Namespace: `pod-security.kubernetes.io/enforce: restricted` label.
- ns fences are GENERATED from platform/ns-fences/allowances.yaml via the
  generator (crew#839), never hand-written; adding a cell/sandbox namespace
  means an allowances entry the generator fans out, and admission refusing a
  pod violating its default-deny comes from the fence layer.
- bin/idp-ci gate shape: a named shell function proved on a .bad fixture
  (refused) and .good fixture (passes), plus a `policy` conftest policy pair;
  AGENTS.md table row has must-fail + must-pass fixtures.
- FLUX-ONLY lockdown (`platform/edge/flux-only-writes.yaml`): every key, agent,
  and person presenting to OKE is REFUSED at admission except one oke-check
  apply workflow service user. => I MUST NOT hand-`kubectl apply` any CP4
  resource against the live estate. my `can-i create` = yes but the ADMISSION
  policy still refuses a PERSON key; nothing lands except via Flux (repo → PR
  → Flux reconcile) or the excused apply user.

## Slice A (this build) — repo, testable without the cluster
1. `platform/gvisor/runtimeclass.yaml` — RuntimeClass name `gvisor`, handler
   `runsc` (gVisor). Pure manifest; harmless before the node carries it.
2. Escrow cell namespace (name TBD from existing cells story) with
   `pod-security.kubernetes.io/enforce: restricted` + its ns-fences allowances
   entry. See whether a `cells/` naming already exists (zero-trust "throwaway
   tenant" wording suggests generated tenant dirs exist today or are item 10's
   concern; DO NOT overbuild — CP4 needs one target namespace for execute_code).
3. `platform/edge/cell-gvisor-admission.yaml` — Kyverno ClusterPolicy: in the
   cell namespace(s), validate/deny a Pod that does NOT name
   `runtimeClassName: gvisor` or that sets `privileged: true`. Proved both ways.
4. Default-deny egress for the cell via the existing fence/NS mechanism, one
   allowed route = the gateway; repo fixture pair proving an internet-egress
   fence FAILS (step 6 conftest).
5. `bin/idp-ci` gains ONE existing-pass sub-check (gvisor-cell admission) +
   AGENTS.md table row with .bad/.good fixtures. See the deepseek-work-order
   item-12 "one run" accept criterion governing the fixture design.

## Operator-gated remainder (NOT this build; belongs to the tile's risk line)
- runsc INSTALL on the OKE node pool via cloud-init (platform/oci/* IaC) —
  gVisor on arm64 Oracle Linux is the ticket's own UNPROVEN risk; needs IaC
  owner + a real node.
- The LIVE drill (a Job the runtime pod runs printing `uname -r` and surviving
  a fork bomb) quoted on the tile — impossible until the runtime is on a node
  AND the claim is admitted through Flux.

Empirical-proof: Slice A is green when bin/idp-ci (or the targeted sub-gates)
passes on the GOOD state and the two fixtures behave (bad refused / good
admitted) in one run. NOT "DONE to the tile" until the live drill outputs a
`uname -r` line plus a fork-bomb-survived quote from an actual gVisor pod.

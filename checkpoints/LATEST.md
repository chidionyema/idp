## RESUME HERE — 2026-09-08T00:22:10Z

## The fire (LAW 1): the ClickHouse recreate loop

**Root cause, proven from two angles.** The Altinity operator writes the ClickHouse pod's own IP
into `observability/chi-signoz-clickhouse-common-usersd` on every reconcile; Stakater Reloader
(`reportingComponent=reloader-configmaps`) sees the mounted ConfigMap change and rolls the
StatefulSet; the new pod has a new IP; repeat, roughly every 40 seconds, `restartCount 0`
throughout because each one is a *new pod*, not a restarted container. Angle 1: the configmap
byte-churn (1488 -> 1487 bytes, a one-byte IP-string delta). Angle 2: the event chain, read live
(`UpdateCompleted ConfigMap` -> `Killing pod` -> `Scheduled`, ~13s apart).

**Fix merged.** PR #2426, squashed to `48240d12` at 2026-09-08T00:16:52Z. A third rule in
`platform/edge/require-auto-reload.yaml` reads `ownerReferences[].kind` off the object and sets
`reloader.stakater.com/auto: "false"` on any workload a custom resource owns — a derived property,
not a hand-kept namespace list.

**Measured since:** `ANNOTATION FLIPPED: reloader auto=false on the ClickHouse StatefulSet`.
Monitor `bz5wh5if7` is watching for the pod to outlive four ~40s cycles.

**Still to do after the loop stops, in this order.** idp-bb measured that the signoz HelmRelease is
`[Stalled] True RetriesExceeded` since 2026-09-07T22:33:57Z and **will not retry on its own** — it
needs an explicit reconcile kick. Behind it: langfuse is `DependencyNotReady`, and the whole
observability Kustomization is `HealthCheckFailed`, lastApplied `a38150d4` vs lastAttempted
`83c808ec`, ~30 commits behind main. Only after that: a real ClickHouse insert or a
`signoz-otel-collector` success line. **Nothing yet says SigNoz works.**

**Correction carried forward.** The ClickHouse memory ceiling is *not* 3.60 GiB. Git says `4Gi`
(values.yaml) but the live CHI and pod both declare **5632Mi** — the #2388 rollback never reached
the cluster, for exactly the stall reason above. So the ceiling is `maximum: 4.95 GiB` and the
tracker sits 1.15 GiB above real RSS, which is what a process killed every 40s looks like. Hold
the retention-or-third-node decision (LAW 11, founder's call) until after the loop stops; more RAM
would be buying capacity for a bug. Confirmed independently here: the receipt's placement row reads
`memory_request_mi: 5632`.

## The trap worth remembering: `kyverno test` passes an ungraded expectation

Writing #2426's refusing case turned this up. The first attempt was the real expectations against a
copy of the policy with the rule under test **deleted** — and `kyverno test` printed *"3 tests
passed"*. It scores a result naming a rule it cannot find as `Pass` with reason `Excluded`, so
`patchedResources` is never compared. A kyverno test can pass while proving only that kyverno
started. **A refusing case must perturb the EXPECTATION, never the rule's existence.**
`tests/fixtures/reloader-blind` does it the right way and fails, rc=1, measured.

## In flight: give bin/idp-fits-a-node a live input (crew#684 rung 3)

Unstaged in this checkout, moving to a worktree: `platform/state/cluster-state.yaml`,
`bin/idp-fits-a-node`, `.github/workflows/oke-check.yml`, `rules.yaml`.

The gate ran in **no CI job and no workflow** — only against its own fixtures — so it graded
nothing on 2026-09-07 while ClickHouse sat Unschedulable and the aggregate capacity row read fine.
The receipt now carries compact `placement` rows (per-pod cpu/memory requests, node, phase, owner,
scheduler reason, QoS class) so the gate has a live input. One algorithm, two input adapters —
`--receipt` rehydrates the same shapes, never a second copy of the rule. Proved faithful: both
paths over one snapshot differ only in the ledger path printed in the message text.

QoS is carried because `platform/scheduling/require-priority-class.yaml`
(`radio-room-set-is-guaranteed`, Enforce) requires `requests == limits` for the radio-room set, so
those workloads have no "small reservation, big ceiling" option (idp-bb, measured on #2429).

**Defect fixed in passing (LAW 8):** the existing `fits-a-node` rule row had two `note:` values in
flow mappings containing an unquoted comma, so YAML terminated the value and turned the remainder
into a stray null key — the notes were silently truncated. Both quoted; a scan of all 45 rows found
no other instance.

## The finding that needs the founder, not a gate

Wiring the gate makes a real pre-existing state visible: **11–14 workloads fit exactly one node
against a recorded budget of 2.** With two nodes both near full, almost anything of size fits
nowhere else — the estate has essentially no failure headroom, which is in tension with the
availability standard. This is a funding decision (LAW 11), not something to bury by raising the
budget. Do not raise the budget to make the gate green.

## Not mine, do not touch

`.github/workflows/estate-bootstrap-preflight.yml`, a backstage template skeleton and
`bin/idp-vault-put` are staged in this checkout by another session. PR #2432 (RBAC floor) is
glass-break under WJ.8: awaiting the founder's own review, no auto-merge, no self-approval.
observability/signoz HelmRelease Failed + ClickHouse -- idp-96 is on it (#2388, #2413).
`.github/workflows/estate-bootstrap-preflight.yml`, a backstage template skeleton and
`bin/idp-vault-put` are staged in the primary checkout by a third session.
## RESUME HERE — 2026-09-08, fixing the two red pull requests

**What is red and why.** #2456 and #2432 both fail `bdd-suites (tests)` and `bdd` on the same
pre-existing main breakage, not on anything either of them changed:

    tests/test_a_workload_that_holds_the_estates_own_url_declares_the_hop_to_edge.py:363
    AssertionError: these containers dial the public internet from inside a fence that renders
    no allow-internet-egress:
    assert not ['agent-workforce/laws dials raw.githubusercontent.com
                (platform/agent-workforce/cronjob.yaml)']

**The fix already exists**, written earlier this session and never pushed: local branch
`fix/agent-workforce-declares-its-internet-hop`, one commit `4af4b17c`, which adds
`egress_internet: [443]` to the `agent-workforce` row of `platform/ns-fences/allowances.yaml`
and the rendered `allow-internet-egress` NetworkPolicy in
`platform/ns-fences/network/agent-workforce.yaml`.

**Next step:** worktree at `scratchpad/wt-fence`, run that test file, push the branch, open the
pull request. Then #2456 and #2432 go green on a rerun.

**Do not** switch the checkout's branch: `feat/crossplane-operator` is checked out with a dirty
tree, and two stashes are live (`feat/crossplane-under-flux`, `fix/langfuse-startup-probe-right-size`).

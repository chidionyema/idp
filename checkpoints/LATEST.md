## RESUME HERE — 2026-09-07 ~21:05Z, session c2cd08cc (idp-1a)

### What is done and merged
- **#2357** kyverno batching + offline-gate moved pre-merge. offline-gate is now the 9th required
  context on ruleset 21473806 (backup: `$SCRATCH/ruleset-21473806.before.json`).
- **#2376** JIT RBAC false header (merged by the founder).
- **#2384** `bin/idp-kyverno-render` retries the policy fetch 3x, then BLIND (exit 2), never a
  plain red. Merged 20:38:18Z.
- **#2387** the reconcile-ledger deny list never matched a multi-line event: Go's regexp is not
  multi-line by default, so `^Kind/name configured$` missed every four-line message and 80 of the
  112 events/hour survived. Now `\A(...)+\z`. Test shells to `go run` and compiles the patterns
  with Go's own regexp. Merged 20:45:50Z.

### Since the last write (20:57Z)
- **#2391 MERGED 20:57:14Z**, about two minutes after opening, before the ordering could be run.
  I hold read-only on the cluster by design (`agent-reader` cannot patch a Kustomization), so
  ns-fences could not be forced to reconcile first. All four fences still read
  `owner=otto-golden` / `owner=otto-gateway`. Background task `bf7u4owcg` polls all four every
  20s and records the exact open/close times of any prune gap. If a fence is gone and does not
  come back within one interval, that needs a write on the cluster and is a founder call.
- **#2390 reviewed** (idp#2390 comment 5575565237): the widening claim says 632 files outside
  bin/ and the tree says 9, with `.estate-hooks` untracked here entirely; and run outside a git
  checkout the gate prints `ok ... 0 shell file(s)` and exits 0, having graded nothing. Fixing
  the second myself as a PR into `rules/pipeverdict-row` rather than handing it back.

### Open, mine
- **#2391** `flux/one-owner-per-fence`: `default-deny-all` and `allow-dns-egress` for otto-gateway
  and otto-golden were declared in BOTH `platform/<ns>/network-policy.yaml` and
  `platform/ns-fences/network/<ns>.yaml`. Two Kustomizations, byte-identical specs, contested
  `kustomize.toolkit.fluxcd.io/name` label — that flip was the 80 events/hour. Removed from the
  namespace files; ns-fences keeps them.
  **MERGE ORDER MATTERS:** after merge, reconcile `ns-fences` FIRST, then otto-gateway and
  otto-golden, then confirm all four NetworkPolicies still exist. Flux will not prune an object
  whose ownership label names another Kustomization — but that label is the thing that flips. If
  a fence does disappear, `bin/idp-kube apply -f platform/ns-fences/network/<ns>.yaml` restores
  it immediately; do not wait for the next interval.
- Background task `bo2lphf5j` is waiting for #2387 to reconcile, then measures 12 minutes of
  `notification-controller` traffic. The predicted rate is ~32 events/hour; quote the measured
  one, never the prediction.

### In flight, not mine
- **#2390** (idp-96) pipeverdict becomes a registry row and widens past `bin/`. I am reviewing it
  — the founder pasted the link. Worktree `$SCRATCH/wt-2390`.
- **#2388** (idp-96) rolls ClickHouse back to 4Gi. #2378 raised it to 5632Mi off a capacity
  paragraph that read `allocatable.memory` in Mi when the unit is Ki; the pod has been
  `Pending Unschedulable` since 20:35. Telemetry stays down either way. Leave ClickHouse alone
  until #2388 lands.

### Board
crew#102 comments 5575195987 and 5575465975. Nine instances of "a program states a fact it never
measured". The through-line: every claim was about something the claimant could not see from
where it stood, and the fix is always that the check runs on the far side.

### Not opened, needs the founder's say-so
38 of the last 100 main ci.yml runs are `failure`.
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

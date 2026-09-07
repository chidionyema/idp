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

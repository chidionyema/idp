# NodeSoftwareOperator — reconcile-loop spec (option c, milestone A)
#
# Companion to CRD-SPEC.md in this directory. CRD-SPEC.md is **what** the operator
# accepts; this file is **how** the controller behaves when it sees a
# RuntimeInstall CR. The implementation will be graded against both files plus the
# offline-gate fixtures in tests/fixtures/nodesoftware-operator/.
#
# This is the controller's behavioural contract, not its code. The code lands as
# a follow-up commit on this branch after review.

## One sentence

The controller observes a `RuntimeInstall` CR, picks the eligible nodes the
selector matches, runs a cordon/drain/install/verify/uncordon cycle on each node
one at a time in canary-then-rest order, and writes the result back to `status`.

## Top-level loop

```
for each RuntimeInstall CR the controller is responsible for:
    snapshot := observe(CR.spec, CR.status, eligible_nodes())
    if snapshot.phase == terminal:
        continue   # nothing to do; controller does not retry Verified/Failed/RolledBack
    action := decide(snapshot)   # returns one of the actions in "Actions" below
    execute(action)              # see "Execute" for the safe sequence
    snapshot.status = apply(action)
    update_status(snapshot)
    requeue_after(action.wait)
```

- `eligible_nodes()` is `clientset.CoreV1().Nodes().List()` filtered by the CR's
  `spec.selector.nodeSelector` and any `matchExpressions`. `tolerations` on the
  spec do not select nodes; they select **pods** (the controller's own probe pods).
- `decide(snapshot)` is pure: given the snapshot, returns the next action. No I/O.
- `execute(action)` is the only place that mutates the cluster. It is the cordon /
  drain / install / verify / uncordon sequence; everything in it has a measurable
  effect on the cluster, and the state machine in "States" governs the order.
- `requeue_after(action.wait)` schedules the next reconcile. Default 15s for
  pending work; the spec's `pauseDuration` overrides for canary pauses.

## States (the state machine)

```
Pending
  └── on first valid reconcile where selector matches ≥ 1 node → Canary
  └── on selector matching 0 nodes after a backoff window (default 5m) → Failed
                                                                with message: selector matches 0 nodes

Canary
  └── on canaryReplicas nodes verified successfully within pauseDuration → RollingOut
  └── on any canary failure → Failed
  └── on annotation `nodesoftware.estate.io/pause` → Paused

Paused
  └── on annotation removal AND not past pause time → resume previous phase
  └── on annotation removal AND past pause time → Failed
                                                       (no silent continuation)

RollingOut
  └── on each subsequent node verified successfully → continue
  └── on any subsequent node failure → Failed
  └── on annotation `nodesoftware.estate.io/pause` → Paused

Verified   (terminal)
  └── controller does not re-enter Verified under any condition

Failed     (terminal)
  └── on a human editing `spec` and removing the failure cause (e.g. corrected
      verification command) → Pending (re-evaluate from scratch)
  └── controller does not auto-retry Failed

RollingBack
  └── on every selected node rolled back successfully → RolledBack
  └── on rollback failure on any node → Failed (terminal, manual recovery)

RolledBack (terminal)
  └── controller does not re-enter RolledBack
```

Every transition writes `status.phase` and `status.message`. Every action that
takes the controller from one phase to another is logged with the structured
fields `phase_from`, `phase_to`, `node`, `runtime`, `outcome` so the rollout
history in `status.rolloutHistory` is greppable by the offline gate and by the
PR body that records the empirical proof.

## Actions (what `decide` returns)

```
type Action struct {
    Kind        string   // one of: "Cordon", "Install", "Verify", "Uncordon",
                         // "Rollback", "Pause", "Wait", "Done"
    Node        string   // target node, "" for cluster-wide actions
    Wait        time.Duration
    Reason      string
}
```

The state machine maps (current phase, current observation) → Action. The mapping
is:

| Current phase | Observation                       | Action                    |
|---------------|-----------------------------------|---------------------------|
| Pending       | selector matches ≥ 1              | Cordon (canary node 1)    |
| Pending       | selector matches 0 (after 5m)     | Wait (requeue 30s)        |
| Canary        | canary cordon done, not installed | Install (canary node)     |
| Canary        | canary installed, not verified    | Verify (canary node)      |
| Canary        | canary verified, pause not elapsed| Wait (requeue pauseDur)   |
| Canary        | canary verified, pause elapsed    | Cordon (next node)        |
| RollingOut    | node cordon done, not installed   | Install (node)            |
| RollingOut    | node installed, not verified      | Verify (node)             |
| RollingOut    | node verified, more nodes remain  | Cordon (next node)        |
| RollingOut    | all nodes verified                | Done                      |
| Failed        | reason fixed by spec edit         | Cordon (canary node 1)    |
| RollingBack   | node rollback not run             | Rollback (node)           |
| any           | `nodesoftware.estate.io/pause` set| Pause                     |

## Execute (the safe sequence)

Every action that touches a node goes through the same five-step sequence. This
is the lockdown's "every node mutation goes through the same cordoned-pod
pattern" property, encoded once and reused.

```
ExecuteCordonAndInstall(node, runtime, version):
    1. Cordon node (set node.spec.unschedulable=true)
    2. Drain node via eviction subresource
       - PDB-aware: honour existing PDBs; if a PDB would block the drain, the
         Operator stops, sets status.phase=Failed, message: "drain blocked by
         PDB <name>, not bypassed".
    3. Install via runtime handler
       - handler := runtime_handlers[runtime]
       - if handler is nil: status.phase=Failed, message: "unknown runtime"
       - result := handler.Install(node, version)
       - result is either {outcome: Success} or {outcome: Failed, error: ...}
    4. Verify via spec.verification
       - probe_pod := renderProbePod(spec.verification.probePod, node, runtime)
       - create probe_pod, wait up to spec.verification.timeoutSeconds
       - evaluate pod's logs against spec.verification.successCondition
       - result is either {outcome: Verified, log} or {outcome: Failed, error}
    5. If 3 or 4 failed: Rollback (handler.Uninstall), set phase=Failed
    6. Uncordon node (node.spec.unschedulable=false), record rolloutHistory

ExecuteRollback(node, runtime):
    1. Cordon node (already cordoned, but re-cordoning is idempotent)
    2. handler.Uninstall(node) via the runtime's shipped uninstall script
    3. If handler.Uninstall failed: status.phase=Failed, message: "rollback stuck,
       manual recovery required, see status.rolloutHistory[node].error"
    4. Uncordon node
```

The cordon/drain sequence is **never skipped**. Even for "simple" runtimes like
runsc where the install is a binary copy, the controller cordons and drains
first. The lockdown's "no surprise host mutation while a workload is running"
property depends on this being uniform.

## The runtime-handler interface (what each handler implements)

```
type RuntimeHandler interface {
    Install(node string, version string) (Outcome, error)
    Uninstall(node string) (Outcome, error)
    ProbeCommand() string                    // returns the shell command for
                                              // spec.verification.probePod spec
}
```

The handler for each runtime lives under `platform/nodesoftware-operator/
runtimes/<runtime>/`. The handler ships its own container image (digest-pinned)
that the controller runs **on the target node** via a privileged pod with a
hostPath mount — the **same** hostPath pattern that today lives in the option-b
DaemonSet at `platform/gvisor-runsc/daemonset.yaml`. The difference is **who
runs the pod**: the option-b DaemonSet schedules itself on every canary-labeled
node unconditionally; the Operator schedules it on the **specific node** the
reconcile loop has cordoned, one at a time, with verify and rollback around it.

The handler image is built and pinned per-runtime. The runsc handler's image
manifest is committed in this same branch (milestone A, follow-up commit). The
kata and nvidia handler images are deferred tickets (see CRD-SPEC.md "Why a
closed set").

## Failure handling (what the lockdown's "FailClosed" actually buys us)

A failure at any step transitions `status.phase=Failed` and stops the rollout.
No other node is touched. The CR stays in the cluster as a record; a human can:

- Read `status.rolloutHistory[node].error` to see what failed.
- Edit `spec` to fix the failure cause (correct verification regex, corrected
  selector, etc.) and the controller re-enters `Pending` on the next reconcile.
- Delete the CR if the rollout should be abandoned.

The Operator **never** retries a `Failed` rollout without a spec edit. This is
the "no autonomous retry on cluster mutation" property the lockdown enforces.
A failure is a human decision point.

For `failurePolicy=Ignore`, the Operator logs the failure, marks the node as
failed in `rolloutHistory`, and continues. This is gated by the
`nodesoftware.estate.io/allow-ignore: "true"` annotation, which is set only by
a human RBAC role.

## Why this loop, not a simpler one

A simpler "loop over selected nodes and install" gets the install done. It does
not give the platform:

- **Cordon/drain before every mutation.** Without it, a workload on the target
  node gets restarted mid-install and may fail in a way the Operator doesn't
  see. The lockdown's whole point is to keep mutations observable and bounded.
- **Verification before uncordon.** Without it, a half-installed node re-enters
  the pool and the failure surfaces as a workload crash hours later. Verification
  shortens the feedback loop from "hours" to "300 seconds, on this node, in
  this rollout".
- **Per-node rollout history.** Without it, a future audit (why is this node
  special?) is impossible. The history is the empirical proof the founder's
  "no claim without evidence" rule requires.
- **A closed runtime set.** Without it, the Operator is a remote-execution
  primitive — anyone who can create a CR can run anything on a node. With it,
  the Operator is a typed installer that the lockdown's audit story already
  knows how to read.

## What the controller does NOT do (out of scope, listed for clarity)

- It does not change node labels or taints. The lockdown reserves label/taint
  changes for a human fingerprint; the Operator selects nodes by labels but
  does not write them.
- It does not provision new nodes. IaC owns that (the option-(a) gold standard
  the user identified). New nodes that join with the right labels are picked up
  by the selector on the next reconcile.
- It does not uninstall a runtime that was not installed by the Operator. The
  `rollback` action runs the handler's `Uninstall` only when the controller
  itself installed the runtime (recorded in `rolloutHistory`).
- It does not bypass admission policies. The Operator's own SA does not get
  any PodSecurityAdmission relaxations; the runtime-handler pod's `securityContext`
  is fixed by the controller, not by the CR.

## Empirical proof (what the controller's logs must show for milestone D)

When this controller runs the runsc install end-to-end, the `status.rolloutHistory`
entries and the controller logs must carry:

- A line per node with `outcome=Verified` and the **probe pod's log line containing
  `uname -r`'s output**. The PR body (milestone D) quotes that line; without it,
  the rollout is not "Verified", the controller is wrong, and the lockdown re-binds.
- The fork-bomb survival proof (the probe pod runs `:(){ :|:& };:` and stays
  running under the gvisor kernel — see CRD-SPEC.md `verification.successCondition`
  for runsc).
- The canary node name. The PR body quotes it; without it, the canary-vs-rest
  distinction is not proven.

These three artefacts are the lockdown's "no claim without evidence" property,
now enforced by the controller's own status writes rather than by a human
remembering to paste a log line into a PR.

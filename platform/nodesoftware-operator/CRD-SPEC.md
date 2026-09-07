# NodeSoftwareOperator — CRD spec (option c, milestone A)
#
# This file is the spec the controller implementation will be graded against. It is
# NOT the implementation. The implementation lands as a follow-up commit on the same
# branch (feat/nodesoftware-operator) after this spec is reviewed and the
# offline-gate fixtures (tests/fixtures/nodesoftware-operator/{good,bad}.yaml) are
# agreed. See RECONCILE-SPEC.md in this directory for the controller loop and the
# state machine.
#
# Naming and grouping follow the platform's "product lives in platform/<name>/" rule
# (~/AGENTS.md LAW 1; AGENTS.md platform-row conventions). The Operator is one
# product, in one directory, with one Flux Kustomization, on one CRD.

## Why a CRD, not a HelmRelease

The estate's existing pattern (calico, cert-manager, traefik, ...) installs node-side
software as a Flux HelmRelease + a privileged DaemonSet (platform/calico/raw/
calico-node.yaml). That pattern works for the **first** install but cannot model:

1. Safe rollout (cordon / drain / install / verify / uncordon) without bespoke logic
   per chart.
2. Multiple software kinds (runsc, kata, nvidia-driver, custom security agents) without
   one DaemonSet per kind, each its own audit story, each its own policy exception.
3. Rollback that actually verifies the host is back to a known state.

The CRD lets the platform declare **what** to install on **which** nodes and lets the
Operator own **how** it is installed safely. Every property on the CRD is a parameter
the Operator must accept; every property the Operator accepts must appear here.

## API

```
apiVersion: nodesoftware.estate.io/v1alpha1
kind: RuntimeInstall
metadata:
  name: <unique within namespace nodesoftware-operator>
  namespace: nodesoftware-operator
spec:
  runtime: <see "runtime" below>
  version: <see "version" below>
  selector: <see "selector" below>            # required
  rolloutStrategy: <see "rolloutStrategy" below>   # required, default ProgressiveCanary
  canaryReplicas: <see "canaryReplicas" below>     # required when rolloutStrategy=ProgressiveCanary
  pauseDuration: <see "pauseDuration" below>       # required when rolloutStrategy=ProgressiveCanary
  verification: <see "verification" below>     # required
  rollback: <see "rollback" below>             # optional but strongly recommended
  failurePolicy: <see "failurePolicy" below>   # required
status:
  phase: <Pending | Canary | Paused | RollingOut | Verified | Failed | RollingBack>
  message: <human-readable>
  observedNodes: <int, count of nodes the Operator has touched>
  canaryResults: <list, see "canaryResults" below>
  rolloutHistory: <list of {node, startedAt, finishedAt, outcome, error}>
```

The CRD carries **no fields the controller cannot act on**. Any field that the Operator
could not honour is a field we should not put on the CRD.

---

## spec.runtime (required, string, closed enum)

The closed set of runtimes the Operator knows how to install. Adding a new runtime is
a controller code change + a spec amendment + a fixture update, not a CR change.

Allowed values (initial set; the webhook enforces this on admission):
- `runsc`      — gVisor. First shipped runtime. Installs `/usr/local/bin/runsc` from
                 `gcr.io/gvisor-release/runsc@<digest>`, writes
                 `/etc/crio/crio.conf.d/99-gvisor.conf`, reloads cri-o. Validated on
                 Oracle Linux 8.10 arm64 + cri-o (the spec's own unproven risk — see
                 RECONCILE-SPEC.md "verification").
- `kata`       — Kata Containers. Stub in this PR; follow-up ticket
                 `NodeSoftwareOperator: kata-runtime-handler` (deferred).
- `nvidia`     — NVIDIA device plugin + driver install on label-selected nodes. Stub;
                 follow-up `NodeSoftwareOperator: nvidia-runtime-handler` (deferred).

Validation: a CR that names any value outside this closed set is refused by the
admission webhook with `spec.runtime: Forbidden: <value>`. The offline gate
(bin/nodesoftware-operator-gate) catches the same case statically so a bad CR
never reaches the cluster.

Why a closed set: the Operator must not shell out to an arbitrary install script
based on a CR field. Every runtime in the closed set is one the Operator's code
executed, audited, and has a handler module for. An open set is the "rogue
mechanic" path the lockdown blocks.

---

## spec.version (required, string, semver-or-tag)

The exact version the runtime should be installed at. Image refs the controller
uses are digest-pinned (`<image>@sha256:...`), with `version` recorded for human
audit and for the rollback decision. Free-form is intentionally NOT allowed —
the controller picks the digest from a per-runtime version table it ships.

Validation: `version` must be a string the runtime's handler accepts. The handler
returns `spec.version: UnsupportedVersion: <runtime> <version>` for anything else.
The offline gate validates `version` against the same table the handler reads.

---

## spec.selector (required, nodeSelector + optional tolerations)

Which nodes are eligible for this install. Mirrors the standard K8s nodeSelector
shape so existing tooling (kubectl, Backstage, dashboards) reads it as familiar.

```
selector:
  nodeSelector:
    matchLabels:
      sandbox.estate.io/gvisor: "true"     # example
    matchExpressions:
      - key: kubernetes.io/os
        operator: In
        values: ["linux"]
  tolerations:                              # optional, list of v1.Toleration
    - key: nodesoftware.estate.io/canary
      operator: Exists
      effect: NoSchedule
```

Validation: `selector.nodeSelector` is required; `selector.tolerations` is optional.
The selector must select **at least one** node at reconcile time, or the CR stays
in `Pending` with `message: selector matches 0 nodes`. (No failure — the operator
waits for nodes to be labeled.)

The lockdown applies here: a CR that selects **all** nodes (no selector, or an
empty matchLabels) is refused by the gate. Node-level software must always be
opt-in per node, never opt-out for the whole fleet.

---

## spec.rolloutStrategy (required, enum, default ProgressiveCanary)

How to spread the install across the selected nodes. Three values:

- `ProgressiveCanary` (default; the only value this PR ships):
  install on `canaryReplicas` nodes, run `verification`, pause for `pauseDuration`,
  then continue one node at a time. Each new node repeats the cordon/drain/install/
  verify cycle. A failure pauses the rollout and surfaces in `status.phase=Paused`.
- `AllAtOnce`: install on every selected node in parallel (no canary). Refused by
  the gate unless `failurePolicy=FailClosed` and an explicit annotation
  `nodesoftware.estate.io/allow-all-at-once: "true"` is set. Default refusal because
  option-c's whole point is "no fleet-wide rollout without proof".
- `Manual`: do not progress past canary without a `spec.approvedAt: <RFC3339>` set by
  a human (gated by RBAC). Used for first-of-its-kind installs (like this one).

Validation: any value outside this set is refused by the webhook. The gate catches
the same case.

---

## spec.canaryReplicas (required int >= 1, only when rolloutStrategy != AllAtOnce)

How many selected nodes participate in the canary phase. The default is 1; the
spec ships with `canaryReplicas: 1` because option (c) starts with **one** canary
node per fleet.

Validation: must be ≥ 1 and ≤ `len(selected nodes)`. A canaryReplicas of 0 is
refused by the gate; a canaryReplicas larger than the selected set is refused
with `spec.canaryReplicas: exceeds selected node count`.

---

## spec.pauseDuration (required, duration string, only when rolloutStrategy=ProgressiveCanary)

How long the Operator waits between canary verification and the start of the rest of
the rollout, and between each subsequent node. Must be parseable by
`time.ParseDuration`. Examples: `15m`, `1h`, `24h`.

Validation: must be ≥ 30s (the Operator's own reconcile period is 15s; less than
30s means the canary pauses never actually pause). The gate refuses anything below
30s with `spec.pauseDuration: below minimum 30s`.

---

## spec.verification (required)

How the Operator proves the install actually works on the just-touched node before
it moves on. Two parts:

1. **probe pod template** — the controller creates a pod with
   `nodeSelector` pinning it to the target node and `runtimeClassName` set to the
   runtime the install just enabled. The pod's command (or sidecar) must produce a
   known-good output the controller can grep.
2. **success condition** — an inline shell expression or a regex that the
   Operator applies to the probe pod's logs. Example for runsc:
   `uname -r | grep -qE '[0-9.]+-gvisor-[0-9]+'`. Example for kata:
   `uname -r | grep -qE 'kata'`. Example for nvidia:
   `nvidia-smi -L | grep -qE 'GPU'`.

```
verification:
  probePod:
    metadata:
      name: nodesoftware-operator-probe-<node>     # templated, controller fills <node>
    spec:
      restartPolicy: Never
      runtimeClassName: <spec.runtime>             # the install just enabled it
      nodeSelector:
        kubernetes.io/hostname: <node>             # pinned to target
      containers:
        - name: probe
          image: gcr.io/distroless/static:latest   # tiny, audit-friendly
          command: ["/bin/sh", "-c", "<runtime-specific probe command>"]
          securityContext:
            allowPrivilegeEscalation: false
            capabilities: {drop: ["ALL"]}
            readOnlyRootFilesystem: true
            runAsNonRoot: true
            runAsUser: 65532
            seccompProfile: {type: RuntimeDefault}
          resources:
            requests: {cpu: 10m, memory: 16Mi}
            limits:   {memory: 32Mi}
  successCondition: "[0-9.]+-gvisor-[0-9]+"        # Go regexp; matched against probe stdout
  timeoutSeconds: 300                               # default; hard ceiling 1800
```

Validation: `probePod` and `successCondition` are both required. A CR without
either is refused by the gate. `timeoutSeconds` defaults to 300; the gate refuses
anything > 1800. `successCondition` is a Go regular expression (NOT a shell
expression — the Operator compiles it with `regexp.Compile` and uses `MatchString`
against the probe pod's stdout). Example for the runsc canary:
`[0-9.]+-gvisor-[0-9]+` matches the kernel version printed by `uname -r` inside a
runsc sandbox (which reports `6.1.0-gvisor-20240101.0-abcdef` or similar). The
gate additionally validates that the pattern compiles — a CR with a malformed
regex is refused at admission.

The verification pod's RBAC is **read-only** at the cluster level (only get/list
on its own pod). It does not get cordon/drain rights — the controller does that
around the pod, not from inside it.

---

## spec.rollback (optional, but strongly recommended)

What the Operator does if `verification` fails after install, or if the operator
removes the runtime from the node during a future cleanup. List of shell commands
the controller runs **on the host** via the same cordoned-pod pattern as the
install — never via direct hostPath writes from the controller pod.

```
rollback:
  commands:
    - /usr/local/bin/nodesoftware-<runtime>-uninstall     # runtime-specific script the
                                                          # handler ships; not user input
  timeoutSeconds: 120
```

Validation: free-form `commands` is **forbidden** by the webhook. The Operator
ships one `nodesoftware-<runtime>-uninstall` script per runtime, pinned to the
runtime version. A CR that names an ad-hoc script is refused with
`spec.rollback.commands: must use the runtime's shipped uninstall script`. This
keeps the lockdown's "no arbitrary host-side execution" property intact while
still letting the Operator uninstall cleanly.

---

## spec.failurePolicy (required, enum)

What happens when a single node's install fails. Two values:

- `FailClosed` (default; only value this PR ships): pause the rollout, set
  `status.phase=Failed`, do not touch any other node. The CR stays until a human
  inspects.
- `Ignore`: log the failure and continue with the next node. Refused by the gate
  unless an explicit annotation `nodesoftware.estate.io/allow-ignore: "true"` is
  set. Default refusal because the lockdown forbids silent ignores.

---

## status (controller-managed, read-only to humans)

The Operator writes these. The webhook refuses any field on `status` that a human
tries to set (status is subresource `status`, gated by the controller SA).

- `phase` — see enum above. The state machine in RECONCILE-SPEC.md governs the
  transitions.
- `message` — last human-readable explanation; overwritten on each phase change.
- `observedNodes` — count of nodes the Operator has actually touched (cordon +
  install + verify + uncordon complete) in this rollout.
- `canaryResults` — list of `{node, startedAt, finishedAt, outcome, log}` for each
  canary node, kept for the PR body that records the empirical proof (milestone D).
- `rolloutHistory` — list of `{node, startedAt, finishedAt, outcome, error}` for
  every node the Operator has touched, kept for audit.

---

## Annotations the Operator honours (admission-gated, RBAC-gated)

- `nodesoftware.estate.io/allow-all-at-once: "true"` — opt-in to
  `rolloutStrategy=AllAtOnce`. Set only by a human (RBAC: verbs=update on
  RuntimeInstall with a specific role, no SA gets it).
- `nodesoftware.estate.io/allow-ignore: "true"` — opt-in to
  `failurePolicy=Ignore`. Same RBAC shape.
- `nodesoftware.estate.io/pause: "<RFC3339>"` — pause the rollout until the named
  time. Set by the controller when `phase=Failed`, by a human otherwise.

These annotations are how the lockdown's "human fingerprint on risky changes"
property survives the new channel. Every annotation a human can set is one no SA
can set; the RBAC split is the lockdown's proof that the Operator is not
autonomously taking the same risks the lockdown used to block.

---

## Why these specific fields, not more

Every field on this CRD is one the Operator must accept. We could add
`priorityClass`, `nodeDrainTimeout`, `maxParallelUninstalls`, etc. — but each
field is a knob the lockdown's "no operator autonomy over fleet" spirit has to
vouch for. The CRD ships with the minimum set that lets the Operator do its job
safely, and every additional knob is a follow-up PR with its own RBAC story.

If a future need requires a new field, the change is a CRD version bump
(`v1alpha2`) + a controller update + a gate fixture update. The closed surface
is the lockdown's leverage; we keep it closed.

# NodeSoftwareOperator controller (C2 + C3)

This is the Go controller for the `RuntimeInstall` CRD defined in
[`platform/nodesoftware-operator/crds/runtimeinstall.yaml`](../crds/runtimeinstall.yaml)
(landed in PR #2338). The controller:

1. Watches `RuntimeInstall` CRs in the cluster.
2. Reads `spec.selector.nodeSelector` to find target nodes.
3. Walks the state machine in [`internal/controller/state.go`](internal/controller/state.go):
   `Pending` → `Canary` → `Paused` (optional) → `RollingOut` → `Verified` (or `Failed`/`RolledBack`).
4. **Per node** (filled in by C3): cordon → drain → install (handler pod) → verify (probe pod) →
   uncordon. Each step is idempotent and derived from cluster state on every reconcile.
5. Honours `spec.rollback` on verification failure when `spec.failurePolicy = FailClosed`.

## Closed runtime set

The controller knows how to install:

- **`runsc`** (gVisor) — shipped; the handler image runs the install/uninstall/probe scripts on
  the target node via a hostPath-mounted, short-lived Pod.
- **`kata`** — stub; the registry wiring in `cmd/main.go` is the only thing left to add when the
  kata handler lands.
- **`nvidia`** — stub; same as kata.

The closed set is locked at three layers:

1. **CRD enum** (`spec.runtime` in the CRD YAML) — the gate refuses a CR whose runtime is
   outside the enum.
2. **Go `ClosedRuntimes`** — the controller refuses again as defence-in-depth.
3. **`bin/lib/nodesoftware_operator_gate.py`** — the offline gate's python validator carries the
   same set, and a fixture drift test catches divergence between layers 1 and 3.

The contract test in [`internal/controller/crd_contract_test.go`](internal/controller/crd_contract_test.go)
catches divergence between layers 1 and 2 once the CRD YAML lands on origin/main (it skips
cleanly when the YAML isn't present).

## Success condition

`spec.verification.successCondition` is a **Go regular expression**, not a shell expression.
The controller compiles it and matches against the probe pod's stdout. This avoids the
controller spawning a shell to evaluate arbitrary CR input.

Example for the gVisor runsc canary: `[0-9.]+-gvisor-[0-9]+` matches the kernel version
printed by `uname -r` inside a runsc sandbox (which reports `6.1.0-gvisor-20240101.0-abcdef` or
similar).

## Per-node lifecycle

```
                      ┌─ node-level step loop ─────────────────────┐
                      │                                            │
sorted targets ──►    │  cordon  ──►  drain  ──►  install  ──►     │
                      │      │              │           │         │
                      │      ▼              ▼           ▼         │
                      │   node patch    Eviction     handler pod   │
                      │   (Unschedul-  subresource   (install       │
                      │    able=true)  for every     script)       │
                      │                 pod                         │
                      │                                            │
                      │  ◄────  verify  ◄──────────────────         │
                      │      probe pod runs,                       │
                      │      controller greps stdout               │
                      │      against successCondition               │
                      │      (regex match → continue)              │
                      │                                            │
                      │  ◄───  uncordon  ─────────────────         │
                      │      node.Spec.Unschedulable=false         │
                      │      append Verified entry to history      │
                      │      pick next sorted target               │
                      └────────────────────────────────────────────┘
```

Each step is a small handler in [`internal/controller/reconcile_actions.go`](internal/controller/reconcile_actions.go)
or [`reconcile_install.go`](internal/controller/reconcile_install.go):

| Verb | File | What it does |
|------|------|--------------|
| `Cordon` | `reconcile_actions.go` | patch `node.Spec.Unschedulable=true` |
| `Drain` | `reconcile_actions.go` | Eviction subresource per pod (PDB-aware); skip DaemonSet + mirror pods |
| `Install` | `reconcile_install.go` | create privileged hostPath-mounted pod running the install script; wait for Succeeded |
| `Verify` | `reconcile_install.go` | create probe pod from `Spec.Verification.ProbePod`, wait for Succeeded, regex-match stdout |
| `Uncordon` | `reconcile_actions.go` | patch `node.Spec.Unschedulable=false`, append `Verified` entry |
| `Rollback` | `reconcile_install.go` | create uninstall pod, on success write `Failed` entry + transition to `RolledBack` |

The Reconciler does NOT persist sub-state. On restart, it derives where each node is from cluster
state (node is cordoned? handler pod exists? probe pod Succeeded?) and picks up mid-flight.

## Building

```sh
cd platform/nodesoftware-operator/controller
go build ./...                  # compile
go test -count=1 ./...          # 26 sub-tests pass + 1 CRD contract test skips (activates post-#2338)
go vet ./...                    # static checks
gofmt -l .                      # formatting (should be empty)
```

The container image builds with the multi-stage `Dockerfile`:

```sh
docker build -t ghcr.io/chidionyema/controller:IMAGE_TAG .
```

`IMAGE_TAG` is substituted at Flux postBuild by the kustomize `images:` block in
`platform/nodesoftware-operator/kustomization.yaml` from the `$imagepolicy` marker in
`platform/image-automation/controller.yaml` (idp#140 image-automation). The image is published
as `ghcr.io/chidionyema/controller:main-<run>-<sha>` per the `bin/dockerfiles` dirname
basename convention; the deployment asks for that exact name.

Historical note (kept from the broken mechanism removed on 2026-09-08 by PR #2416): the Flux row
that previously claimed to substitute `IMAGE_TAG` from `Secret/ghcr-pull` could never have done
so -- that Secret's one key is `.dockerconfigjson`, which is not a legal envsubst variable name,
and it aborted the row's whole post-build. The cyrus-pattern `newTag:` above is what replaced it.

## What's NOT in this controller yet

The reconciler wires the state machine to cluster side effects for **Cordon / Drain / Install /
Verify / Uncordon / Rollback**. What remains:

- **C4 (runsc handler image)**: the multi-stage Dockerfile under
  `platform/nodesoftware-operator/runtimes/runsc/` that ships
  `/usr/local/bin/nodesoftware-runsc-install`, `-uninstall`, `-probe`. Pushed to ghcr by
  idp#140 image-automation. The controller code already invokes these via
  `internal/handler/runsc/runsc.go`; the scripts are what C4 ships.
- **D (empirical proof)**: deploy the controller + handler image to the cluster, flip
  `estate.estate.io/suspend: "false"` on the canary CR, capture the canary node's `uname -r` log
  line in the PR body.
- **E (prototype cleanup)**: delete `platform/gvisor-runsc/` DaemonSet +
  `gvisor-runsc-exception.yaml` PolicyException. The operator's lockdown grant replaces the
  time-bounded exception.

Without D, no node is touched — the controller code is ready, but the operator image is not
yet in ghcr and the suspend annotation is "true" on every CR.

## Layout

```
platform/nodesoftware-operator/controller/
├── Dockerfile                              # multi-stage build, distroless runtime
├── go.mod / go.sum                         # controller-runtime v0.22.4 + k8s.io/api v0.35.2
├── api/v1alpha1/
│   ├── groupversion_info.go                # SchemeBuilder
│   ├── runtimeinstall_types.go             # RuntimeInstall, RuntimeInstallSpec, RuntimeInstallStatus
│   └── zz_generated_deepcopy.go            # hand-written DeepCopy (no controller-gen)
├── internal/
│   ├── controller/
│   │   ├── state.go                        # PURE state machine (tested without a fake client)
│   │   ├── state_test.go                   # 21 sub-tests covering Decide / CanAdvance / ShouldFailClosed
│   │   ├── target.go                       # node-selection helpers (sorted by name, canary pin honoured)
│   │   ├── target_test.go                  # 4 sub-tests for sortedTargetNodes, pickNextTarget, buildSnapshot, isSuspended
│   │   ├── runtimeinstall_controller.go    # Reconciler entry point + dispatch
│   │   ├── reconcile_actions.go            # Cordon / Drain / Uncordon
│   │   ├── reconcile_install.go            # Install / Verify / Rollback + buildHandlerPod / readPodLog
│   │   ├── types.go                        # shared aliases (ctrlResult, etc.)
│   │   └── crd_contract_test.go            # CRD-YAML <-> Go-types contract test (skips when YAML absent)
│   └── handler/
│       ├── handler.go                      # Handler interface + Registry + ValidateClosedRuntime
│       └── runsc/runsc.go                  # gVisor runsc handler (Install/Uninstall/ProbeCommand)
└── cmd/main.go                             # controller-runtime manager wiring
```

## Suspend annotation

The reconciler honours `estate.estate.io/suspend` on each CR. Default behaviour: suspended
(annotation absent or `"true"`). The empirical-proof milestone D is the only place that flips
this to `"false"`, and it must cite the canary node's `uname -r` log line in the PR body before
the merge can land.

This is the operator's lockdown grant: while the CR is suspended, no node is touched. Flipping
the annotation is the audit-handle, not a console step.

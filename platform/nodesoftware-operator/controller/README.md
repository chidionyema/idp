# NodeSoftwareOperator controller (C2)

This is the Go controller for the `RuntimeInstall` CRD defined in
[`platform/nodesoftware-operator/crds/runtimeinstall.yaml`](../crds/runtimeinstall.yaml)
(landed in PR #2338). The controller:

1. Watches `RuntimeInstall` CRs in the cluster.
2. Reads `spec.selector.nodeSelector` to find target nodes.
3. Walks the state machine in [`internal/controller/state.go`](internal/controller/state.go):
   `Pending` → `Canary` → `Paused` (optional) → `RollingOut` → `Verified` (or `Failed`/`RolledBack`).
4. Per node: cordon → drain → install (via the runtime handler pod) → verify (via the probe pod)
   → uncordon.
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

## Building

```sh
cd platform/nodesoftware-operator/controller
go build ./...                  # compile
go test -count=1 ./...          # state machine + contract test
go vet ./...                    # static checks
gofmt -l .                      # formatting (should be empty)
```

The container image builds with the multi-stage `Dockerfile`:

```sh
docker build -t ghcr.io/chidionyema/nodesoftware-operator:IMAGE_TAG .
```

`IMAGE_TAG` is substituted at Flux postBuild from `Secret/ghcr-pull` (idp#140 image-automation).

## What's NOT in this controller yet

The reconciler in [`internal/controller/runtimeinstall_controller.go`](internal/controller/runtimeinstall_controller.go)
wires the state machine to controller-runtime and stops at compile-clean + state-machine
unit-tested. The side-effecting verbs (`ActionInstall`, `ActionCordon`, `ActionDrain`,
`ActionUncordon`, `ActionVerify`, `ActionRollback`) currently log and requeue; the full
install/cordon/drain pipeline is **milestone C3**, gated on the empirical proof (milestone D).

The empirical proof (D) is the PR that:

1. Flips `estate.estate.io/suspend: "false"` on `platform/gvisor-runtime/runtimeinstall.yaml`.
2. Deploys the controller image to the cluster (Flux reconciles the row).
3. Captures the canary node's `uname -r` log line (containing the `gvisor` kernel suffix).
4. Records `status.rolloutHistory[0].outcome = Verified` for the canary node.

Without (4), the controller's status would never leave `Pending` on a real cluster — which is
exactly the safety net: the empirical-proof PR cannot land without the proof.

## Layout

```
platform/nodesoftware-operator/controller/
├── Dockerfile                          # multi-stage build, distroless runtime
├── go.mod / go.sum                     # controller-runtime v0.22.4 + k8s.io/api v0.35.2
├── api/v1alpha1/
│   ├── groupversion_info.go            # SchemeBuilder
│   ├── runtimeinstall_types.go         # RuntimeInstall, RuntimeInstallSpec, RuntimeInstallStatus
│   └── zz_generated_deepcopy.go        # hand-written DeepCopy (no controller-gen)
├── internal/
│   ├── controller/
│   │   ├── state.go                    # PURE state machine (tested without a fake client)
│   │   ├── state_test.go               # 21 sub-tests covering Decide / CanAdvance / ShouldFailClosed
│   │   ├── runtimeinstall_controller.go# Reconciler: reads CR, calls Decide, applies verb
│   │   └── crd_contract_test.go        # CRD-YAML <-> Go-types contract test (skips when YAML absent)
│   └── handler/
│       ├── handler.go                  # Handler interface + Registry + ValidateClosedRuntime
│       └── runsc/runsc.go              # gVisor runsc handler (Install/Uninstall/ProbeCommand)
└── cmd/main.go                         # controller-runtime manager wiring
```

## Suspend annotation

The reconciler honours `estate.estate.io/suspend` on each CR. Default behaviour: suspended
(annotation absent or `"true"`). The empirical-proof milestone D is the only place that flips
this to `"false"`, and it must cite the canary node's `uname -r` log line in the PR body before
the merge can land.

This is the operator's lockdown grant: while the CR is suspended, no node is touched. Flipping
the annotation is the audit-handle, not a console step.

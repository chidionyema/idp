# Demo: nodesoftware-operator-gate

`bin/nodesoftware-operator-gate` reads a `RuntimeInstall` and refuses the three
ways one can be wrong before it ever reaches the cluster. It exists because a
`RuntimeInstall` is an instruction to install software onto the nodes
themselves — a sandbox runtime, a GPU driver — and a malformed one does not
fail loudly, it rolls quietly across the fleet.

Run it against the two fixtures. The good one passes:

```
$ bin/nodesoftware-operator-gate tests/fixtures/nodesoftware-operator/good.yaml
ok    1 RuntimeInstall doc(s) pass
```

The bad one carries three CRs, one per rule, and all three are named:

```
$ bin/nodesoftware-operator-gate tests/fixtures/nodesoftware-operator/bad.yaml
REFUSED  bad-unknown-runtime: spec.runtime: Forbidden: not-a-closed-set-value (closed set is ['kata', 'nvidia', 'runsc'])
REFUSED  bad-no-canary: spec.canaryReplicas: must be >= 1 (got 0)
REFUSED  bad-pause-too-short: spec.pauseDuration: below minimum 30s (got '5s' = 5s; the Operator's reconcile period is 15s so <30s means the canary pause is a no-op)
$ echo $?
1
```

The third refusal is the one worth reading twice. A `pauseDuration` under 30
seconds is not a small pause — the controller's reconcile period is 15 seconds,
so a pause shorter than two of them is a pause the controller never observes.
The rollout still says `ProgressiveCanary` and still behaves as `AllAtOnce`.
Nothing in the CRD's own schema catches that, because the value is a valid
duration; only this gate does.

It takes any number of files, so the estate's real CRs are graded the same way:

```
$ bin/nodesoftware-operator-gate platform/gvisor-runtime/runtimeinstall.yaml
ok    1 RuntimeInstall doc(s) pass
```

That third command is a case in `rules.yaml`, so the CRs actually committed to
this repository are graded on every run, not just the fixtures.

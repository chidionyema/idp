# Onboarding: nodesoftware-operator

## What it is

The NodeSoftwareOperator is the one controller that installs software onto the
nodes themselves. Its input is a `RuntimeInstall` custom resource naming a
runtime (`runsc`, `kata`, `nvidia`), a version and a node selector; it cordons
one node, installs, runs a probe pod on that node, and only then moves to the
next. `bin/nodesoftware-operator-gate` is its offline half: it grades a
`RuntimeInstall` in the repository, before Flux ever applies it.

```
bin/nodesoftware-operator-gate <file> [<file> ...]
```

Exit 0 if every document in every file passes, 1 if any is refused, 2 on usage.
Refusals are one line each and name the field.

## Why it exists

The CRD's own schema catches a misspelled field, and nothing else. The three
things that actually hurt all produce a schema-valid document:

- **A runtime outside the closed set.** The operator is not a remote-exec
  service; it installs the three things it knows how to install and probe.
  Anything else is an arbitrary instruction to run on every node.
- **A `ProgressiveCanary` rollout with `canaryReplicas: 0`.** A canary of zero
  is a fleet-wide install wearing the word canary. No fleet without proof.
- **A `pauseDuration` under 30 seconds.** The reconcile period is 15 seconds,
  so a shorter pause is one the controller never observes: the rollout
  silently regresses to all-at-once while still declaring itself progressive.

The contract these three mirror is
`platform/nodesoftware-operator/CRD-SPEC.md`. If the spec and the validator
drift, the fixture pair's two-way grading in `rules.yaml` goes red.

## When it runs

On every CI run, as the `nodesoftware` rule in `rules.yaml`. The row carries
three cases: the bad fixture must be refused, the good fixture must pass, and
`platform/gvisor-runtime/runtimeinstall.yaml` — the estate's first real
`RuntimeInstall` — must pass. Adding a new rule means adding it to the
validator and to `CRD-SPEC.md`, and adding a document to `bad.yaml` that the
gate now refuses; a rule with no refusing fixture is not graded.

## Related files

```
bin/nodesoftware-operator-gate                   the dispatcher
bin/lib/nodesoftware_operator_gate.py            the validator
platform/nodesoftware-operator/CRD-SPEC.md       the contract it mirrors
platform/nodesoftware-operator/crds/             the CRD itself
platform/gvisor-runtime/runtimeinstall.yaml      the first real CR
tests/fixtures/nodesoftware-operator/            bad.yaml, good.yaml
docs/tutorials/demo/nodesoftware-operator.md     the run, both ways
```

A Kyverno admission policy was considered for these three rules and rejected:
admission sees one object at a time and cannot say whether the CR that reached
the cluster is the one the repository holds. The break these three describe is
in the committed bytes, so the gate that reads them is a repository gate.

# Onboarding: ns-fence-gate

## What it is

`bin/ns-fence-gate [path]` reads every Namespace, ResourceQuota, LimitRange and
NetworkPolicy under `path` (a file or a directory of manifests) and refuses any
namespace that lacks a quota, a LimitRange, a both-ways default-deny
NetworkPolicy selecting all pods, or a DNS exception when egress is denied.
`bin/ns-fence-gate --live` grades the running cluster through `kubectl` and
prints BLIND when no cluster is reachable. Exit 0 is a pass, 1 is a defect list
naming the namespace and the missing fence.

## Why it exists

Founder, 2026-08-24: "Apply a Default Deny All NetworkPolicy to every
namespace" and "Apply strict ResourceQuota and LimitRange rules to data-ops so
a runaway pipeline cannot starve the cluster's brain". Before the gate, a pod in
one namespace reached a pod in another by IP with no credential in 4ms. The
gate checks the objects, not their names, so a policy that selects some pods by
label does not count as a default deny, and a quota without a LimitRange is
graded as a defect rather than a partial win, because that combination refuses
correct work (LAW 38).

## When it runs

`bin/idp-ci` runs the manifest mode on every push: the fixture pair
`tests/fixtures/ns-fence/{good,bad}.yaml` proves it both ways, and the run over
`platform/` is report-only while crew#191 fences the 19 namespaces it names
today. `tests/test_incident_crew191_ns_fence_gate_proves_both_ways.py` pins the
fixture verdicts. The live mode runs when a cluster is reachable, after an
apply.

## Adding a namespace

Ship the four objects with it in the same directory: a ResourceQuota, a
LimitRange with default requests and limits, one NetworkPolicy with
`podSelector: {}` and `policyTypes: [Ingress, Egress]`, and an egress rule to
port 53. `tests/fixtures/ns-fence/good.yaml` is the copyable example. Run
`bin/ns-fence-gate <dir>` before opening the pull request; `bin/idp-ci` runs
the same command.

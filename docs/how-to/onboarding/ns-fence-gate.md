# Onboarding: ns-fence-gate

## What it is

`bin/ns-fence-gate [path]` reads every Namespace, ResourceQuota, LimitRange and
NetworkPolicy under `path` (a file or a directory of manifests) and refuses any
namespace that lacks a quota, a LimitRange, a both-ways default-deny
NetworkPolicy selecting all pods, or a DNS exception when egress is denied.
Exit 0 is a pass, 1 is a defect list naming the namespace and the missing fence.

`bin/ns-fence-gate --live` grades the running cluster through `kubectl`. It
prints BLIND when no cluster is reachable, and — since crew#839 — it refuses to
report a pass at all when no CNI in `kube-system` enforces NetworkPolicy, because
on such a cluster the policy objects are stored and never read, and calling the
namespaces fenced would be a claim the cluster cannot support.

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

`bin/idp-ci` runs it over `platform/` on every push, and since crew#839 that run
is blocking rather than report-only.

It was report-only from 2026-08-27, when it found 76 defects across 19
namespaces, on the correct reasoning that a gate refusing every namespace on
main is itself the outage (LAW 38). The consequence was that it printed a `warn`
line every run for a week and nothing changed: thirty-eight namespaces had no
quota, no request defaults and no policy, and every pull request was green.
crew#839 generated the missing fences in one pass, which is what made turning
the row into a `FAIL` possible.

The live mode runs after an apply, when a cluster is reachable.

## Adding a namespace

Do not write the four objects by hand and do not put them beside the namespace.
Add the namespace's name to `platform/ns-fences/allowances.yaml` — its declared
traffic under `flows`, and a deliberate ceiling under `overrides` only if the
derived one is wrong — then run:

```
python3 bin/idp-ns-fence-gen
```

It writes every namespace's fence in one pass and is idempotent: a second run
over unchanged input produces byte-identical files. The quota and the LimitRange
land in `platform/ns-fences/` and the NetworkPolicies land in
`platform/ns-fences/network/`. All four kinds are applied by the one `ns-fences`
Flux row: the top-level kustomization lists `network` as a resource. The policies
were held back while flannel was the datapath and read no policy object; Calico
has been the enforcement layer since crew#839, and that directory's README says
how to read a denial when one of them stops a flow the scan never saw.

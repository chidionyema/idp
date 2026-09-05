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

`bin/idp-ci` runs it twice on every push. Once inside the AGENTS.md rule table,
where the fixture pair `tests/fixtures/ns-fence/{good,bad}.yaml` proves it can
tell a defect from a fence. Once over `platform/`, blocking, where a real
namespace missing a real fence fails the run.

That second run is new in crew#839, and its absence is why this gate was
worthless for months: it graded two fixture files and nothing else, so no defect
in the estate could fail it and no change to the estate could pass it
differently. Thirty-eight namespaces had no quota, no request defaults and no
policy the whole time, and the gate was green every day.

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
land in `platform/ns-fences/` and are applied by Flux. The NetworkPolicies land
in `platform/ns-fences/network/` and are deliberately not applied; that
directory's README says what has to be true about the cluster's CNI before they
are.

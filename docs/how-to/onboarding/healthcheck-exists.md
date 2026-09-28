# Onboarding: a health check must name an object something creates

`bin/idp-healthcheck-exists`, graded by the rule `healthcheck-names-a-real-object`.

## What it is for

The `tailscale` Kustomization waited on

```yaml
healthChecks:
  - kind: Deployment
    name: tailscale-operator
    namespace: tailscale
```

The release is named `tailscale-operator`. **The chart emits `Deployment/operator`.**
Nothing has ever created a Deployment by the other name, so the wait could not be
satisfied and the row reported, for days:

```
health check failed after 10m0.026651003s: timeout waiting for:
  [Deployment/tailscale/tailscale-operator status: 'NotFound']
```

`NotFound` is the tell. A health check on an object that is merely **unhealthy**
reports that object's status. A health check on an object that **does not exist**
reports `NotFound`, and does so forever.

Four rows depended on `tailscale` — guacamole among them — and were held out of
the cluster the entire time. CI was green throughout, because the manifest is
valid YAML naming a plausible object.

## How it decides

It compares a health check against the object list this estate's own compiler
renders from git:

```bash
bin/idp-compile-helm --out /tmp/compiled.json     # 33/33 releases, 646 objects
bin/idp-healthcheck-exists --root . /tmp/compiled.json clusters/oke/platform.yaml
```

Three answers, and the third is the one to keep:

| verdict | meaning |
|---|---|
| ok | the named object is rendered by a chart, or is a HelmRelease that rendered, or is a plain manifest in this tree |
| FAIL | **nothing in this tree creates it** — no chart, no manifest, and no operator input names it |
| ungraded | an operator makes it at runtime from a custom resource, or it is a kind this gate does not compare. **Counted and printed**, never silent |

The output always names both numbers:

```
ok    healthcheck-exists  37 checked health check(s) name an object this tree creates;
      7 ungraded (created at runtime by an operator, or a kind this gate does not compare)
```

## Why the compiler and not the cluster

A health check that names a missing object is exactly what the cluster will report
`NotFound` about, but grading against the cluster would need the cluster up — and
a test that needs the estate up is skipped precisely when the estate is down.
The compiled document is the only place, outside the running cluster, where the
real name exists. That is the same reason `bin/idp-compile-helm` exists at all.

## What it deliberately does not do

**It does not assume an operator made it.** An object may be created at runtime by
an operator from a custom resource — `Deployment/healing/estate` is made by the
k8sgpt operator from a `K8sGPT` object. That is ungraded, because the object does
exist and its row reports `Ready=True`. But the exemption requires a **custom
resource in this tree naming the object**. `tailscale-operator` had no chart, no
manifest and no operator input, so nothing saved it. "An operator probably makes
it" is the excuse that would have hidden this defect.

**It does not grade the cluster.** It grades what git says will exist.

## Adding a row

A row lives in `rules.yaml` and its two fixtures, never as a new gate script. The
fixtures are self-contained: each carries the tiny compiled document and the
cluster file it grades, so the rule is proved both ways in the offline gate
without a helm run.

## Tests

```bash
python3 -m pytest tests/bdd/test_healthcheck_names_a_real_object.py -q
```

Eight scenarios. Seven run anywhere: the shipped defect is refused, the corrected
name passes, the tailscale row in this tree names the chart's Deployment, a
HelmRelease check is satisfied by the release rendering, a missing HelmRelease is
refused, an operator-made object is ungraded **and said to be ungraded**, and a
Deployment nothing names is refused even when an operator exemption exists for
that kind. The eighth is skipped unless `docs/compiled-helm.json` is present, and
it says so.

# Onboarding: a Flux row's readiness signal

**Door (from the UI):** Backstage → **Catalog** → *idp* → **CI** — the gate runs inside
`bin/idp-ci` on every pull request, and the check is the door. There is no button to press
and nothing to run by hand.

You are adding or editing a `Kustomization` under `clusters/`. Two fields decide when Flux
calls that row ready, and they cannot both be used.

`healthChecks` is a list of specific objects. The row is ready when those objects are ready,
and nothing else in the path is consulted. This is what you want almost every time: it names
the thing that actually has to be serving before a dependent row starts.

`wait: true` means "wait on the health of every object this path applies". Use it only when
the row has no single object worth naming.

kustomize-controller treats them as mutually exclusive, and `wait` wins. If you write both,
your `healthChecks` list is silently ignored — the file reads as though you narrowed the wait,
and you did not. Nothing warns you. The gate is the warning.

## What to do

Adding a row that has one obvious readiness signal — a Deployment, a StatefulSet, a Service's
backing workload — name it in `healthChecks` and leave `wait` out entirely.

Adding a row with no such signal — a bundle of CRDs, a set of policies — set `wait: true` and
write no `healthChecks`.

Editing a row that has both, which the gate will refuse: delete the `wait: true` line. Keep
the checks. That is the direction the fix always goes, because the checks are the narrower and
more deliberate statement, and because the broad wait is what causes the outage.

## Why the broad wait is dangerous

Any object in the path can hold the row. A one-shot `Job` that fails, a `PersistentVolumeClaim`
that never binds, a `CustomResource` whose controller is not installed yet — each of them stops
the row applying, and with it every other change to that path. On 2026-09-10 a backfill job that
its own manifest calls optional held the whole `otto-gateway` path out of the cluster, including
the change that would have repaired the dependency the job was failing on.

If a row genuinely must wait on a Job, name that Job in `healthChecks` deliberately. Then the
dependency is a decision someone wrote down, not a side effect of a field they used for
something else.

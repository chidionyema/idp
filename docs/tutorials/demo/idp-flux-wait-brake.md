# Demo: the health checks Flux was throwing away

**Door (from the UI):** Backstage → **Catalog** → *idp* → **CI** — the gate is a row of
`bin/idp-ci`, so its verdict is the check on every pull request. Nothing to press.

Run the gate on the fixture that carries the shape that took Otto's gateway out, and on the
repository as it stands now.

```
$ bin/idp-flux-wait-brake tests/fixtures/flux-wait-brake/bad.yaml
tests/fixtures/flux-wait-brake/bad.yaml: Kustomization/otto-gateway sets wait: true and 1 healthCheck(s); wait wins, so those checks are ignored and the row waits on every object in its path -- drop wait: true and keep the checks
FAIL  idp-flux-wait-brake: 1 row(s) whose healthChecks Flux discards
$ bin/idp-flux-wait-brake
PASS  idp-flux-wait-brake: no Kustomization declares healthChecks that wait would discard
```

The bad fixture is the `otto-gateway` row exactly as it stood on 2026-09-10: one health check
naming `Deployment/otto-gateway`, and `wait: true` sitting above it. Read on its own the row
says "this path is ready when the gateway Deployment is ready". That is not what it did.
kustomize-controller treats the two fields as mutually exclusive and `wait` wins, so the health
check was dead text and the row instead waited on the health of every object the path applies.

One of those objects was `Job/otto-memory-store-6`, a one-shot backfill whose own manifest says
"If this never runs, nothing breaks". It timed out reaching the LLM router, went `Failed`, and
the row stopped applying with `failed early due to stalled resources`. Every otto-gateway change
in git then sat outside the cluster — including the change that repairs the router path the
backfill had failed to reach. An optional job braked the fix for the thing it depended on.

The good fixture keeps the health check and drops `wait: true`, and it carries a second row with
no health checks at all that keeps `wait: true` — because there, waiting on the whole path is the
only readiness signal that row has. That is the whole rule: the two never appear together, and
the fix is always to keep the narrower statement the author already wrote.

Forty-one of this estate's eighty-two Kustomizations were in the bad shape when the gate was
written. The second run above is what the tree looks like after that one pass.

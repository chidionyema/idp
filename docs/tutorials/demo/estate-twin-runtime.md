# Demo: estate-twin-runtime

`bin/estate-twin-runtime` is the estate's memory of itself. It reads what the estate already
collects — the `cluster-state` receipt every 15 minutes, plus git and the cluster's API
server — and writes it into `catalog/estate.db`, the asset database the estate already has.
It adds no store, no bus and no server.

It exists because of a measured fact. The estate had three inventories and every one
reported **declared** state as if it were **actual**: `docs/inventory.json`,
`catalog-info.yaml` and `dark-matter.yaml`. On 2026-09-12 none of them could name a single
one of: 1,523 unmerged branches, 722 files that exist on no commit of main, 11 zero-scaled
deployments, or three agents deployed and dead — `research` 0/1, `hindsight` 0/1,
`otto-gateway` 2/13. A dead pod is declared nowhere. Founder: *"tired of running my whole
estate blind."*

## The whole graph, in five seconds

```
$ bin/estate-twin-runtime --once --code --domains
ok  estate-twin-runtime  source=receipt deploy_short=3, pods_not_ready=19,
    secret_stale=7, flux_not_ready=11, branches=648, files_absent=94093,
    identity=3, network=95, certificates=5, capacity=2, cost=13, data=19,
    postgres=4, sessions=5, worktrees=154, bus=4 -> catalog/estate.db
```

Twelve domains, and every one carries a real reading behind it.

## What is broken, workloads first

```
$ bin/estate-twin-runtime --dead
  [MEASURED_FAIL] runtime: 330 of 1165 nodes not serving (dead=329, crashlooping=1, read 0s ago)
  crashlooping  k8s:pod:edge-runtime:expert-vibethinker-7db966fd89-kkhc2 restarts=7
  dead          k8s:deployment:commerce:lago-api ready=0/1
  dead          k8s:deployment:commerce:lago-webhook-worker ready=0/1
  also recorded, as evidence rather than failure: 480 event, 385 flux, 45 diagnosis, 19 alert
```

Workloads before pods, and never an event: an event carries status `dead` because it
*records* a failure, and 240 warning events ranked above a crash-looping pod is how a dead
list stops being read.

## The three-state rule

```
$ bin/estate-twin-runtime --state
  MEASURED_FAIL  code: 649 of 649 nodes not serving (stranded=649, read 2s ago)
  MEASURED_FAIL  runtime: 330 of 1165 nodes not serving (dead=329, crashlooping=1, read 0s ago)
  MEASURED_OK    bus: 4 nodes, all serving (read 11s ago)
```

A domain not read inside its window reads `UNKNOWN`, never `MEASURED_OK`:

```
$ sqlite3 catalog/estate.db "update freshness set updated_at=datetime('now','-30 days')"
$ bin/estate-twin-runtime --state
  UNKNOWN  code: last read 2592001s ago, window is 180s -- stale, so nothing here may be read as MEASURED_OK
```

## When did it break

```
$ bin/estate-twin-runtime --history k8s:deployment:commerce:lago-api
  2026-09-12 14:54:33  active -> dead  k8s:deployment:commerce:lago-api
```

One row per state *change*, not per sweep, so a pod dead for a day is one row and not
ninety-six.

## What dies with it

```
$ bin/estate-twin-runtime --blast-radius flux:Kustomization:flux-system/secret-store
  flux:Kustomization:flux-system/secret-store
  upstream (what it depends on):
    <- flux:Kustomization:flux-system/agent-workforce  (depends_on)
    <- flux:Kustomization:flux-system/backstage  (depends_on)
    ... 20 rows depend on it
```

Walked over `depends_on` edges taken from Flux's own `dependsOn` — the ordering the
controller honours *before* it reconciles, so a failure propagates along exactly these
edges.

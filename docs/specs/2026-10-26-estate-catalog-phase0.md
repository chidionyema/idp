# The estate catalog, phase 0 — the record, the join, and the bar

**Status:** implemented and measured, 2026-10-26. **Claim:** chidionyema/idp#7097.
**Implements:** `~/.estate/proposals/2026-10-24-estate-catalog.md` (the accepted
proposal), phase 0 only. **Does not implement:** the proposal's phases 1–3
(the graph query surface, the Backstage view, the trust graph), and nothing
here decides anything about them.

---

## 1. What phase 0 is

One record of what the estate actually runs, written by walking the estate, with
the join between the walk and the estate's own names measured rather than
asserted.

Four collectors — git, k8s, host, edge — see the estate from four sides. None of
them sees all of it: the cluster does not know about the launchd jobs, the
laptop does not know about the edge, and GitHub knows about neither the running
workload nor the process. The join is what turns four partial views into one
catalog, and the bar is the measurement of whether that join actually works.

The proposal's bar: **≥80% of live workloads joined via rules 2 or 4.**
**Measured 2026-10-26: 137/139 = 99%.**

## 2. The record: one Postgres, the estate's own

D1: the record is Postgres — the estate's existing CloudNativePG cluster — and
`catalog/estate.db` is a generated cache of it, never a second source of truth.
**"Do not create a second database."**

Measured against the live cluster on 2026-10-26:

| Fact | Value |
|---|---|
| CNPG cluster | `estate`, namespace `estate-db` |
| Read-write service | `estate-rw.estate-db` (this is the proposal's "estate-rw.estate-db") |
| Database | `estate` — exists, owner role `estate`, **zero tables** before this phase |
| Second database | none created, and the code refuses to create one |

So the record is the `estate` database of the cluster the estate already runs.
The catalog's tables live in a `catalog` **schema** inside it, not in `public`:
the database is shared by design (one database per consumer), and a table called
`nodes` in a shared database is a collision waiting for the day something else
wants a table called `nodes`.

`platform/estate-db/cluster/databases.yaml` now declares that database as a
CloudNativePG `Database` resource, so its address is declared in the one place
every other database's address is declared rather than left as a fact somebody
remembers.

### 2.1 The write path, and its debt

The census writes by running `psql` **inside the cluster's own Postgres pod**,
over the pod-local socket:

```
kubectl -n estate-db exec -i estate-1 -- psql -v ON_ERROR_STOP=1 -U postgres -d estate -f -
```

The script is piped in on stdin, so a quote in a workload name cannot break out
of its literal, and the rows come back as a JSON document produced by Postgres
itself — which is why no Postgres client library is needed on the laptop and why
no credential is handled anywhere.

**The debt, stated plainly:** that path is the cluster's *superuser* over a
pod-local socket. A least-privilege role for the catalog would be the right
shape, and it needs a vault entry, which is the founder's to make. Until then the
catalog writes as a superuser, and the code says so rather than pretending
otherwise. The CNPG `Database` resource declares the `estate` role as the
database's owner, so the role exists and owns its database; only its *password*
is not in the vault.

The path is also flaky: the laptop→API-server→kubelet hop drops connections
(measured 2026-10-26: `connection reset by peer`, then an `EOF` from the
kubelet's exec endpoint, on a node that stayed `Ready` throughout). Every
statement the record runs is idempotent — a read, an `IF NOT EXISTS` migration,
or one transaction of upserts — so the write path retries three times before it
gives up.

### 2.2 The cache

`catalog/estate.db` is a sqlite copy, **rebuilt** on every sweep rather than
updated. A cache that accumulates rows from every sweep is a second record that
nobody can reason about, which is the failure D1 exists to prevent. It is
untracked and gitignored: it is generated, and it can be deleted at any time
without losing anything.

## 3. The planes, and what each one can and cannot see

| Plane | Collector | Reads | Universe (the denominator) | TTL |
|---|---|---|---|---|
| `git` | `census-git` | `gh repo list` + the 43 repositories on disk + CODEOWNERS + each repo's Dockerfiles | repositories | 1 h |
| `k8s` | `census-k8s` | the cluster's workloads | **workloads only** (Deployments, StatefulSets, DaemonSets, Jobs, CronJobs) | 180 s |
| `host` | `census-host` | launchd plists, launchctl state, crontab, the runtime directory | processes and scheduled jobs | 15 min |
| `edge` | `census-edge` | Cloudflare (workers, zones, tunnels) and GHCR packages | edge routes and images | 1 h |

**The k8s universe is workloads, not Services.** The cluster has 302 Services
and 229 workloads. Services describe plumbing — a Service per Deployment, plus
the CNPG, the metrics server, the ingress controller — and a catalog whose
universe is plumbing is not a catalog of the estate's software.

**The host plane reads the launchd plists, not the process table**, and it
reads `*.plist` and `*.plist.disabled` alike (a disabled job is still a job the
estate owns, and its state is a fact about it). The `.pre-gate-*` backups are
skipped: they are history, not a job. The repository behind a job is found by
looking for the nearest `.git` above its program or working directory, so a job
in `~/Documents/code/idp/bin` is `idp` without anyone maintaining a mapping.

**Every collector is load-gated.** The 2026-10-24 outage was caused by
collectors reading the host while the laptop was at load 300. The collectors
refuse to run above the ceiling (`ESTATE_LOAD_MAX`, default 12) and say so,
rather than making the estate worse in order to describe it. The git collector
is also bounded: `gh repo list` is given 25 seconds, because the difference
between a sweep that finishes and a sweep that holds the API open for a minute
is the difference between a tool and a tax.

### 3.1 Blind is a row, never a zero

A plane that could not be read is **BLIND**, with the reason, and it is never
presented as a plane with nothing in it. Measured 2026-10-26:

| Plane | Blind reason |
|---|---|
| `edge` | `gh api packages failed rc=1: gh: You need at least read:packages scope to list packages. (HTTP 403); no Cloudflare token: the edge plane's workers, zones and tunnels were not read` |
| `git` (one sweep) | `gh repo list failed rc=124: gh timed out after 60s` — the sweep still ran, on the repositories on disk, and said it was half-blind |

A blind plane is the honest answer: the edge half of the catalog is **not yet
read**, and the record says so in a column instead of implying completeness.
Two things are missing and both are credentials, not code: `read:packages` on
the GitHub token, and a Cloudflare token in the vault.

## 4. The join

The proposal's rules, in its order, **first match wins, and all matches are
stored as evidence**. A node keeps every candidate the join considered, so a
join can be argued with after the fact.

| Rule | Name | What it uses |
|---|---|---|
| 1 | `estate.yaml` | a repository's own declaration of the services it runs |
| 2 | `k8s-label` | `app.kubernetes.io/name` on the workload |
| 3 | `otel-name` | the OpenTelemetry service name |
| 4 | `image-repo` | the image's repository name segment |
| 5 | `dockerfile` | a Dockerfile's declared image name |
| 6 | `codeowners` | the CODEOWNERS rule that covers the path |
| 7 | `launchd-label` | a launchd job's label |
| 8 | `manual` | a hand-written override |

Phase 0 implements rules 2, 3, 4, 5, 6, 7 and 8; rule 1 is the repository's
declaration file, and no repository has one yet.

### 4.1 The two classes, and why a disagreement is not a contradiction

The rules fall into two classes, and the classes are what make the ordering
coherent:

- **The service class** — rules 2, 3, 7 (and 1): the name the *estate* gives a
  running thing. `app.kubernetes.io/name: estate-scheduler` says "the estate calls
  this service estate-scheduler".
- **The artifact class** — rule 4: the name of the *thing that was built*.
  `ghcr.io/chidionyema/estate-scheduler` says "the artifact is called
  estate-scheduler".

Two service-class names that disagree are a contradiction and the node is
**ambiguous** — measured 2026-10-26, exactly two of 139 live workloads: the
estate-mcp service, which the cluster labels `estate-mcp` and which reports
itself to telemetry as `mcp-estate-refresh`. A service and an artifact that
disagree are not a contradiction at all: they are the same thing at two levels
of detail, and the estate's label wins because the label is what the estate
calls the *service*.

That is the whole reason the previous catalog's numbers were wrong: it treated
`estate-scheduler` (the image) and `dagster` (the service it runs) as two
different things, or as a contradiction, and then reported a join rate that
could not fail.

### 4.2 The image grammar, measured

Every cluster image in the `estate` namespace is **one segment** after the
namespace (`estate-scheduler`, `backstage`, `lago-api`, `epistemic-ingest`,
`router-events`, `estate-mcp`, `controller`, `edge-runtime`) — the estate's
images are published as `ghcr.io/chidionyema/<image>`, not with a repository
segment. So for the estate's own images, rule 4 resolves to the image name
itself, and the *repository* behind it is found the second way: the repository
whose Dockerfiles declare that image. `bin/dockerfiles` already computes that
mapping, and the census reproduces the same rule rather than inventing a second
one.

Resolution order for the repository behind an image:

1. the repository that **builds** the image (read from its Dockerfiles) — a
   measurement;
2. the image's own repository name segment — a name match;
3. the registry organisation as a last resort, recorded as such.

### 4.3 Ownership

CODEOWNERS first; the GitHub account owner as the fallback, recorded as a fact
with its source (`codeowners` or `github-owner`). The estate is a personal
account with no teams, so the fallback is what most repositories get — which is
why the fact carries its source: "chidionyema owns this" and "the CODEOWNERS
rule says so" are different claims.

## 5. The bar

> ≥80% of live workloads joined via rules 2 or 4

- **Denominator:** the long-lived workloads — Deployments + StatefulSets +
  DaemonSets = **139** measured 2026-10-26 (112 + 13 + 14). This is the
  proposal's own "live workloads 138" measurement (111 + 13 + 14 on the day it
  was written). A Job is an *execution* of something, not the something: 67 of
  the cluster's 229 workloads are Jobs, most of them one-shot dagster runs, and
  counting them would make the bar a measurement of the scheduler.
- **Numerator:** workloads whose join actually succeeded **on the rule that
  won** — rule 2 or rule 4. A candidate that was considered and rejected (an
  ambiguous join) is not a join. Counting it would be exactly the defect this
  phase exists to fix: a number that cannot fail.

Measured 2026-10-26:

```
live workloads joined by rule 2 or 4: 137/139 = 99% (bar: 80%)
  by rule 2 (app.kubernetes.io/name): 96
  by rule 4 (image repository name): 41
  ambiguous (two names disagree): 2
  unnamed (nothing could name it): 0
```

The breakdown is printed with the rate because a bare percentage cannot be
argued with: it says which rule did the joining, how many were ambiguous, and
how many could not be named at all.

The whole census, same sweep:

| Plane | Universe | Classified | Uncatalogued | Blind |
|---|---|---|---|---|
| git | 70 | 70 | 0 | 0 |
| k8s | 229 | 88 | 141 (139 `no_repo`, 2 `ambiguous_join`) | 0 |
| host | 55 | 31 | 24 (`no_repo`) | 0 |
| edge | 0 | 0 | 0 | 1 |

`no_repo` on the k8s plane means the workload runs an image that **no estate
repository builds** — third-party operators (cert-manager, calico, external-dns)
and the estate's own images whose repository the census could not resolve. That
is the useful signal, not a failure: it says the cluster runs 139 workloads the
estate's repositories do not account for.

## 6. The freshness contract

Every row carries when it was seen and when it goes stale, and the TTLs are the
proposal's: k8s 180 s, host 15 min, git and edge 1 h. A row without an expiry
is a snapshot wearing a fact's name. Expired rows are **not** deleted
automatically: the expiry is the mechanism, and a reader checks it. Deleting is a
policy the proposal does not state, and inventing one is how a record starts
lying about what it saw.

## 7. The doors

| Command | What it does |
|---|---|
| `bin/catalog-census` | walks the estate, joins it, writes the record and the cache, prints the coverage table and the bar |
| `bin/catalog-census --dry-run` | walks and prints, writes nothing |
| `bin/catalog-coverage` | reads the **record** and prints the coverage table and the bar |
| `bin/catalog-entity <name>` | reads the **record** and prints one thing: its node, its aliases, its edges, its facts |

`bin/catalog-coverage` and `bin/catalog-entity` read the record, not a local
file: the record is the thing, and a door that read a cache would be measuring
the cache.

## 8. The cluster half: `platform/catalog`

The census applies the DDL itself, so a census against a fresh cluster works
before Flux has converged. The estate's native path converges the schema
without a laptop:

- `platform/catalog/schema/001_catalog.sql` — the one copy of the DDL, mounted
  as a ConfigMap whose name carries a hash of its contents;
- `platform/catalog/schema-cronjob.yaml` — a **CronJob**, not a Job: a Job's
  pod template is immutable, so a changed DDL would make the apply fail, while
  a CronJob's template is not. The DDL is idempotent, so the daily run changes
  nothing after the first;
- `clusters/oke/estate-db.yaml` — the Flux row (`catalog`), depending on
  `estate-db`, with the CronJob as its health check.

The DDL is applied by the CronJob over the cluster's own `estate-rw` service,
with the superuser secret the vault already publishes into the namespace — no
new secret, no new vault entry, and therefore nothing waiting on the founder.

## 9. What is not done, and what is not knowable yet

- **The edge plane is blind.** It needs `read:packages` on the GitHub token and
  a Cloudflare token in the vault. Both are credentials, not code.
- **The catalog writes as the cluster's superuser.** A least-privilege role
  needs a vault entry (founder's to make).
- **Rule 1 (`estate.yaml`) is not implemented**: no repository declares its
  services that way yet, and the manual override table is the escape hatch
  until one does.
- **The proposal's phases 1–3 are untouched**: the graph query surface, the
  Backstage view and the trust graph are not part of phase 0, and nothing here
  forecloses them.
- **`bin/estate-discover` (lane `estate/discover-door`, #7168) is a capability
  VIEW, complementary to this record** — a different question with a different
  answer, and deliberately not duplicated here.

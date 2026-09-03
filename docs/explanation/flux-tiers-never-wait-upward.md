# A lower tier never waits on a higher one, and every long-running pod can be restarted

The founder's cluster blueprint (2026-09-03) sets two rules that this change enforces. First,
the cluster is built in tiers: bootstrap, then infrastructure, then core services, then
applications. A lower tier may never wait on a higher one, because a wait that points upward
is a deadlock the moment the higher tier is red. Second, every pod is disposable: the cluster
must be able to kill it and start a fresh one without a person noticing, which needs a
liveness check on every long-running workload.

## The two waits that pointed the wrong way

Flux applies the cluster as a graph of rows, and each row can wait on others. Two rows in
the infrastructure tier waited on rows above them.

- **The DNS row waited on the product.** The Cloudflare token that the DNS controller needs
  was declared inside the product's own folder, so the DNS row waited on the product row to
  bring the token into the cluster. A red product, which is an application-tier event,
  therefore froze DNS, which is infrastructure. The token's declaration now lives in the DNS
  folder, and the DNS row waits only on the secret store, the row that makes vault-backed
  secrets possible at all. The product folder no longer carries a platform secret.
- **The autoscaler row waited on observability.** The event-driven autoscaler needs the
  scheduling row, because it scales the scheduler's workers. It does not need the
  observability stack, which sits a tier above it and is the row most often red during an
  incident. The wait now names scheduling only.

Nothing else in the cluster depends on the DNS or autoscaler rows, so the two wrong-way
waits stalled only themselves. That is why they went unnoticed: the graph never deadlocked,
DNS and autoscaling just quietly stopped moving whenever a row above them was red.

One upward wait remains on purpose. The external-secrets row waits on the edge row, because
the certificate signer inside edge signs the certificate that external-secrets serves. That
is a real order, not a wrong-way wait. Moving the certificate signer into its own row, so
external-secrets can wait on that alone, is the named follow-up and needs the founder's word.

## Four workloads gained a liveness check

Measured on main before this change: 28 long-running workloads, 23 with a liveness check.
Of the five without one, four are real services and one is a placeholder pod that exists
only to reserve capacity, which is left alone on purpose.

| Workload | Liveness check added |
|---|---|
| The portal's Postgres database | `pg_isready` against its own database every 30 seconds |
| The store's Redis cache | `valkey-cli ping` every 30 seconds |
| The status page | its own index page over HTTP every 30 seconds |
| The memory service's Postgres database | `pg_isready` against its own database every 30 seconds |

Each check allows three failures in a row before the pod is restarted, so a slow query or a
busy moment never triggers a restart on its own. Each check also starts only after the
readiness check the workload already had, so a pod is never killed while it is still
starting up.

The blueprint also asks for an explicit graceful-shutdown period. Kubernetes already gives
every pod 30 seconds to shut down cleanly when no period is set, so writing 30 into every
file would change nothing and was not done.

## The guard

`tests/test_incident_crew539_platform_rows_never_wait_on_the_portal.py` now scans every
Flux row in `clusters/oke/` and fails the moment any platform row names the product in its
waits. The product's own application row is the one allowed exception, because that row is
the product. The existing test for the DNS row was repointed at the secret store and at the
token's new home.

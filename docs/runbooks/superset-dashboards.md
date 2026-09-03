# Runbook: Superset dashboards

The boardroom dashboards at https://superset.${ESTATE_ZONE} (decision 0018). Superset runs in the
observability area of the cluster from the Apache Helm chart, behind the shared gateway: the
gateway asks the login proxy about every request and hands Superset the signed-in email in a header. Superset
creates the account from that header; it holds no password for anyone.

## If the page does not answer

1. The founder surfaces probe (platform/monitoring/rules/founder-surfaces-probe.yaml) watches
   https://superset.${ESTATE_ZONE} and /health; check its alert first.
2. Flux owns the release: the chart install named `superset` reconciles from
   `platform/observability/`. A failed release shows in Flux's conditions for it.
3. The app database is the workload `superset-db` beside it; its password comes from
   the vault (`superset-db-password`, minted by Terraform in `platform/oci/superset.tf`)
   through the vault-fed secret `superset-db`.
4. The web pods must be 2, on different nodes (PodDisruptionBudget `superset`); losing one node
   is survivable by design.

## If sign-in misbehaves

Superset never shows its own login. If it does, the gateway header is not arriving: check the
`login-forward-auth` filter (`platform/observability/superset-httproute.yaml`) and the login proxy in
the identity area of the cluster. The hourly login drill (`bin/idp-login-drill`, door `superset`)
grades this road from a runner that holds no password, so a red here is an alert, not a
discovery. Identity questions are gateway questions (`docs/policy/auth-is-infrastructure.md`).

## One-time cleanup after the swap lands

The evicted Metabase leaves one thing behind (prune is off in this directory): the
PersistentVolumeClaim `pgdata-metabase-db-0` in observability, holding the dead Metabase
database. The recovery dump (`metabase-recovery-dump`, docs/explanation/metabase-recovery.md)
read it on 2026-09-03: 39 saved questions and 1 dashboard, every one of them Metabase's own
"Sample Database" demo content ("Aerodynamic Copper Knife trend", "Checkout funnel", ...) and
nothing of the founder's. Nothing references the volume after the swap.

The founder never types a cluster command (LAW 31): the volume is retired by the one-shot job
`metabase-volume-retire` (platform/observability/metabase-volume-retire.yaml), declared in git
with a role that may delete that one claim and nothing else. Deleting a volume cannot be
undone, so the job is wired into the observability kustomization by a change only the
founder merges; Flux runs it once and the job's log is the receipt.

## Human step

None in normal operation. The one hand ever needed was the founder's merge of the change that
installed it; accounts appear on first sign-in with no invitation step.

## The seeded boardroom dashboard

The "Boardroom" dashboard (model spend per day, spend by model and by prompt, call
volume, latency, trace volume) is not hand-built: the one-shot job
`superset-boardroom-seed` (platform/observability/superset-boardroom-seed.yaml)
renders a Superset import bundle against the live ClickHouse trace store and loads
it with Superset's own importer class, `ImportDashboardsCommand` (6.1 ships no `import-assets` command);
the bundle's `metadata.yaml` says `type: Dashboard`, the one type that importer accepts. Every object carries a fixed uuid, so re-running
the job overwrites the same rows — it never doubles charts. Jobs are immutable, so the Job carries
the Flux force annotation (`kustomize.toolkit.fluxcd.io/force: Enabled`): edit the manifest and
Flux recreates the Job in place; no name bump. Its log ends `BUNDLE-IMPORTED` then
`BOARDROOM-SEEDED Boardroom charts: 6`; anything else is a failed seed.

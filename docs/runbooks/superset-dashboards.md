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
`login-forward-auth` filter (`platform/observability/httproute.yaml`) and the login proxy in
the identity area of the cluster. Identity questions are gateway questions
(`docs/policy/auth-is-infrastructure.md`).

## One-time cleanup after the swap lands

The evicted Metabase left one thing behind: the PersistentVolumeClaim `pgdata-metabase-db-0` in
observability, holding the dead Metabase database. Flux cannot prune it -- the claim came from the
StatefulSet's volumeClaimTemplate, so it was never in Flux's inventory, and prune is off in this
directory besides (idp#648).

This runbook used to ask the founder to delete it by hand. It no longer does:
`platform/observability/metabase-volume-removal.yaml` is a Job that deletes exactly that one claim,
through an identity whose entire right is `get` and `delete` on the single resource name
`pgdata-metabase-db-0` in this one namespace. Running it again is boring -- a claim that is already
gone is success, not an error -- so the Job carries the Flux force annotation and re-runs safely
whenever the manifest changes. Nothing references the claim after the swap.

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
Flux recreates the Job in place; no name bump.

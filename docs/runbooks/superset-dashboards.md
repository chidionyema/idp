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

The evicted Metabase leaves one thing behind (prune is off in this directory): the
PersistentVolumeClaim `pgdata-metabase-db-0` in observability, holding the dead Metabase
database. The founder deletes it when he applies the change: `kubectl -n observability delete
pvc pgdata-metabase-db-0`. Nothing references it after the swap.

## Human step

None in normal operation. The one hand ever needed was the founder's merge of the change that
installed it; accounts appear on first sign-in with no invitation step.

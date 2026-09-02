# Boardroom dashboards from LLM traces

Superset reads Langfuse data and lets the founder build dashboards and explore traces interactively: drill down by prompt, model, cost, latency or any field in the trace, save queries, share charts with the team. It replaced Metabase because Metabase's free edition cannot accept the estate login's word for who is signed in (decision 0018).

## See it work

1. Sign in to Superset at https://superset.${ESTATE_ZONE} with your estate login — no second prompt, the gateway's word is the account.
2. Open "Settings" → "Database Connections" → "+ Database" the first time: PostgreSQL, host langfuse-postgresql.observability.svc.cluster.local, database langfuse, user langfuse, password in the vault under `langfuse-db-password`.
3. Open "SQL Lab" and pick the Langfuse database to query traces directly — the events table holds individual calls, observations holds spans.
4. Filter by date, model or cost, then "Create chart" from the result grid.
5. Save the chart and add it to a dashboard.

## What it proves

The dashboard connects to the live Langfuse database and reads trace data without a separate pipeline. Every call through the router is immediately queryable: no latency, no batch job, the same data Langfuse shows, with the flexibility to group, filter and chart however the founder needs — behind the one estate login, with no login of its own.

## Watch it

The machines record the dashboard layer from the real manifests on every relevant
push (`demos/superset.tape`): the five declared files, the public door on the shared
edge, and the availability declaration. The recording appears after the first green
render and refreshes itself:

![The superset dashboard layer, declared in git, recorded by the machines](../demos/superset.gif)

# Getting started with Superset dashboards

Superset is the boardroom view of LLM traces: query Langfuse data, build dashboards, share insights. The founder is enrolled as an admin automatically on first sign-in — the gateway tells Superset who you are (decision 0018), so there is no account to create and no password to hold.

## Steps

1. Open https://superset.${ESTATE_ZONE} in a browser.
2. Sign in with your estate login (one-click single sign-on, no password). You land in Superset already signed in as an admin.
3. The Langfuse data source and the "Boardroom" dashboard are already there — the
   `superset-boardroom-seed` job adds them from git on every estate sync. Trace data
   lives in ClickHouse (host signoz-clickhouse.observability.svc.cluster.local,
   database `langfuse`); Langfuse's postgres holds app metadata only.
4. Open "SQL Lab" to write a query, or "Datasets" to register a table for point-and-click charts.
5. The events table has individual calls; the observations table has spans and nested traces.
6. Save charts and gather them on dashboards for repeatable views.
7. Use filters to drill by date, model, cost or latency — every field in a trace is queryable.

## No second sign-in

Superset sits behind the estate login and takes the gateway's word for your identity — its own login page never appears. Once you sign in at the front door, you are in Superset as well. No separate credential, no additional password.

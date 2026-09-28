# Getting started with Superset dashboards

Superset is the boardroom view of LLM traces: query Langfuse data, build dashboards, share insights. The founder is enrolled as an admin automatically on first sign-in — the gateway tells Superset who you are (decision 0018), so there is no account to create and no password to hold.

## Steps

1. Open https://superset.${ESTATE_ZONE} in a browser.
2. Sign in with your estate login (one-click single sign-on, no password). You land in Superset already signed in as an admin.
3. The Langfuse data source and the "Boardroom" dashboard are already there — the
   `superset-boardroom-seed` job adds them from git on every estate sync. Trace data
   lives in ClickHouse (host signoz-clickhouse.observability.svc.cluster.local,
   database `langfuse`); Langfuse's postgres holds app metadata only.
4. The "Memory" dashboard is there too, from the `superset-memory-seed` job. It is the page for
   what the estate remembers: memories written per day, which channel each one came from, which
   conversation and which person, what kind of thing it was, the newest fifty in full, the store's
   own ingest queue, and the model calls that turn a conversation into facts. It reads Hindsight's
   store directly (the one estate Postgres, database `hindsight`) over a connection that is
   refused the ability to write. Hindsight records no per-call log of reads and writes today, so
   how often something recalls a memory is not on the page; what is drawn is what the store keeps.
5. Open "SQL Lab" to write a query, or "Datasets" to register a table for point-and-click charts.
6. The events table has individual calls; the observations table has spans and nested traces.
7. Save charts and gather them on dashboards for repeatable views.
8. Use filters to drill by date, model, cost or latency — every field in a trace is queryable.

## No second sign-in

Superset sits behind the estate login and takes the gateway's word for your identity — its own login page never appears. Once you sign in at the front door, you are in Superset as well. No separate credential, no additional password.

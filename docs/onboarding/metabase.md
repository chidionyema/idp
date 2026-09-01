# Getting started with Metabase dashboards

Metabase is the boardroom view of LLM traces: query Langfuse data, build dashboards, share insights. The founder is auto-enrolled as an admin on first sign-in.

## Steps

1. Open https://metabase.${ESTATE_ZONE} in a browser.
2. Sign in with your estate login (one-click OIDC, no password).
3. Metabase auto-detects you are an admin and lets you configure data sources if needed:
   - Source: PostgreSQL
   - Host: langfuse-postgresql.observability.svc.cluster.local (or ask for the connection string)
   - Database: langfuse
   - User: langfuse (or the user created by the Helm chart)
   - Password: in the vault, key `langfuse-db-password`
4. In the home screen, click "New" → "Question" to write a query.
5. Pick Langfuse as the database and start exploring: events table has individual calls, observations table has spans and nested traces.
6. Save questions and add them to dashboards for repeatable views.
7. Use filters to drill by date, model, cost or latency — every field in a trace is queryable.

## No second sign-in

Metabase sits behind the estate login. Once you sign in, you are in Metabase as well. No separate credential, no additional password.

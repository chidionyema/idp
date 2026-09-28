# Demo: The spend circuit breaker trips

Watch the breaker examine the last hour of model spend. It runs every five minutes as the
`spend-velocity-check` scheduled job in the `llm` area of the cluster; you can also trigger one run by hand:

```
kubectl -n llm create job spend-check-now --from=cronjob/spend-velocity-check
kubectl -n llm logs job/spend-check-now
```

When the hour's spend is under the limit, the log shows one line and exits:

```
SPEND_VELOCITY: OK - hourly spend $2.41 (limit $10.0)
```

When the hour's spend crosses the limit (10 dollars by default), the breaker opens and stays
open for its cool-off (30 minutes by default), counting trips:

```
SPEND_VELOCITY: ALERT - hourly spend $14.20 exceeds limit $10.0
SPEND_VELOCITY: Breaker OPEN for 1800s (trip #1)
```

Every hour on the hour the `spend-digest` scheduled job writes a one-page spend summary from the
same database. Read it the same way: `kubectl -n llm logs job/<latest spend-digest job>`.

# Demo: telemetry coverage

LAW 50 (founder, 2026-08-27): every workload emits to the central collector, and coverage is
proved by querying the backend, never by scanning files. `platform/observability/telemetry-coverage.yaml`
is that query. Every 15 minutes it lists the pods that have been Running for more than ten
minutes, asks ClickHouse (the SigNoz store) which pods wrote a log line or a metric sample in the
last hour, and writes the diff as a receipt to Object Storage from the node's own identity.

Read it from any session, no laptop, no kube path:

```
$ gh workflow run oke-check.yml -R chidionyema/idp -f mode=check
$ gh run view <run> --job telemetry-coverage --log | tail -3
ok      telemetry-coverage  ok telemetry-coverage at 2026-08-27T01:00:04Z pods=41 seen=41 missing=0 (4 min ago)
```

A pod the backend never heard from turns the row red and names it in the JSON body:

```
FAIL    telemetry-coverage  pods=41 missing=1: FAIL telemetry-coverage at ... pods=41 seen=40 missing=1
{"missing": [{"ns": "kini", "pod": "kini-worker-7c9d..."}], ...}
```

A backend that cannot be queried is `BLIND`, never green. The offline proof of both directions
is `python3 -m pytest -q tests/test_incident_crew320_telemetry_coverage_is_a_backend_query.py`.

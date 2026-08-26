# Onboarding: telemetry coverage

Nothing to install and nothing to declare. A workload is covered the moment its pod writes a
log line to stdout (k8s-infra collects it) or the kubelet samples it (k8s-infra metrics). The
receipt lands in `state/telemetry-coverage` in the drill-receipts bucket every 15 minutes.

When your pod shows up under `missing`:

1. It has been Running for more than ten minutes and neither logs nor metrics reached SigNoz.
2. Check the k8s-infra agent on its node: `kubectl -n observability get ds k8s-infra-otel-agent`.
3. If the pod writes nothing to stdout and has no kubelet metrics, it is not emitting. LAW 50
   says it must; add OTLP export to `signoz-otel-collector.observability.svc:4317`.

Tuning, all by env var on the CronJob container: `GRACE_MIN` (default 10), `WINDOW_SEC`
(default 3600), `CLICKHOUSE_URL` (default `http://signoz-clickhouse:8123`). The reader's
freshness limit is `TELEMETRY_COVERAGE_MAX_AGE_MIN` (default 60) on `bin/idp-telemetry-coverage`.

# AGENTS.md — ${{ values.name }}

Estate laws (~/AGENTS.md) apply. Add repo-specific rules below.

## OTel requirement (Kyverno Enforce — cannot be bypassed)

Any Deployment to OKE must declare `OTEL_EXPORTER_OTLP_ENDPOINT`:
```yaml
env:
  - name: OTEL_EXPORTER_OTLP_ENDPOINT
    value: "http://signoz-otel-collector.observability.svc:4318"
  - name: OTEL_SERVICE_NAME
    value: "${{ values.name }}"
```
Follow `hermes-v2/otto/obs/core.py` for in-process instrumentation. Traces appear in
signoz.mumchimp.com within seconds. The admission gate refuses Deployments without this env var.

## Deploy rule

Merge to `main` → CI → `bin/build-image` (amd64+arm64) → GHCR → Flux reconciles.
Never run `kubectl apply` by hand.

## Knowledge graph

Run `growmos context` at session start. Write findings with `growmos remember`.

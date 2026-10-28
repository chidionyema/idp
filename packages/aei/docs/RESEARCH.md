# P0 AEI — repository-grounded discovery (2026-10-28)

Source: `chidionyema/idp` main, inspected through the connected GitHub repository. This is repository evidence, not proof of current runtime health.

| Existing capability | Source | Repository finding | AEI decision |
|---|---|---|---|
| SigNoz | `platform/observability/signoz.yaml` | HelmRelease `spec.suspend: true`; comment attributes suspension to ClickHouse compute consumption on Always Free pool | Do not require SigNoz to start AEI; avoid new ClickHouse |
| Langfuse | `platform/observability/langfuse.yaml`, `platform/llm/config.base.yaml` | Langfuse Helm manifest and LiteLLM success/failure callbacks declared | Reuse for LLM-specific traces when live status is proven |
| OTel | `platform/observability-collector/k8s-infra.yaml`, `observability/otel-collector.yaml` | Collector configurations and k8s-infra instrumentation exist | Future exporter adapter, not a second collector deployment |
| Coverage | `platform/observability/telemetry-coverage.yaml` | Backend-queried coverage, explicit BLIND state when backend unavailable | Preserve unknown/missing distinction |
| Existing BDD | `features/assurance/trace-matrix.feature`, `docs/TRACE-MATRIX.md` | Repository tracks scenario-to-test binding; generated trace matrix reports unbound scenarios | Ship executable Python tests plus Gherkin feature; bind to estate spec gate during integration |
| Existing runtime traces | `packages/idp_concurrency/src/idp_concurrency/tracer.py`, `sovereign/engine/tracing.py` | Existing tracing adapters in source tree | Add thin integration adapter rather than replacing tracing |
| Router callbacks | `platform/llm/efficiency_gateway.py`, `platform/llm/config.base.yaml` | LiteLLM pre-call efficiency gateway and callback chain | Integrate at callback boundary after verifying actual invocation order |
| Aevum | `platform/observability/aevum.yaml`, `docs/decisions/0028-aevum-replaces-popdd-as-the-evidence-layer.md` | Existing evidence layer and architecture decision | Avoid creating a competing canonical evidence authority; AEI event ledger is a local append-only staging plane pending Aevum integration |

## Open verification gaps

- Whether Langfuse, OTel collectors, Aevum, SigNoz and Grafana currently accept events.
- Actual OTel attribute names and trace IDs used by each harness.
- Whether a single end-to-end trace survives a Mac → OKE boundary.
- Actual data retention and access policies for execution metadata.
- Production deployment sizing, alerting, backups, authentication gateway and concurrency load.

## Architectural boundary

AEI stores *observed, sanitised events*. It does not capture hidden chain-of-thought or claim the event sequence represents a model's private decision process. Evaluations are derived separately. The local SQLite store is a deployment-neutral staging implementation; in-cluster integration should use the estate's existing telemetry/evidence authority once verified. No live components were modified.

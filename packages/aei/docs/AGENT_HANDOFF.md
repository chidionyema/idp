# Agent handoff — P0 AEI

## First: prove the code works

```bash
cd estate-aei
python -m unittest discover -s tests -v
python -m aei.contract examples/router.manifest.json
python -m aei.demo --db output/aei.sqlite3
export AEI_API_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
python -m aei.server --db output/aei.sqlite3
```

Open http://127.0.0.1:8766/, enter the same API token, load runs and inspect `DEMO-run-001`. This is SYNTHETIC data and must not be represented as a production trace.

## Actual estate integration — ordered, bounded tasks

1. Confirm current OTel/collector/Langfuse/Aevum runtime status and storage budgets, not just GitOps manifests. Do not unsuspend SigNoz to satisfy AEI.
2. Select one real, safe harness task with an executable done-check. Instrument harness task, model, tool, and verification boundaries with `aei.client.Emitter`. Populate the six identity fields with actual identifiers. Record W3C trace IDs if available. Do not record prompts, tool arguments, outputs, secrets or personal data.
3. Propagate `run_id`, `task_id`, and `trace_id` across the harness-to-LiteLLM boundary via approved request metadata/trace context; ensure router callbacks emit model request, completion and cost evidence. Never forward an internal API token to model providers.
4. Run one real task and inspect waterfall, graph and evidence links. Missing events must be explicit. Compare with a second verified run of an identical fixture. Ensure cost and latency improvements do not worsen verification.
5. Validate the component manifest in CI and bind Gherkin scenarios to the estate's actual `bin/spec-gate` and trace matrix conventions. Do not claim a BDD scenario is executable merely because its `.feature` text exists; current Python tests exercise the same requirements but are not pytest-bdd bindings.
6. Integrate with existing Aevum/OTel evidence authority and Oracle API; keep a single canonical long-term telemetry backend. Retain SQLite only for local/offline spool where appropriate.
7. Complete security review: authentication, authorised access, backups, retention, schema evolution, ingestion quotas, rate limits, disk exhaustion, TLS at the ingress, scrubber fuzz tests, clock skew, event loss accounting, and controlled shutdown.
8. Deploy in a separate controlled environment, run load and outage tests, and only then submit reviewed GitOps changes. No unverified production rollout.

## Definition of acceptance

- At least one *real* task is traced end-to-end across harness, LiteLLM, tools and verification.
- Trace IDs and code revisions survive device boundaries; every visual item links to an observed event.
- No silent zeroes for unknown cost, no invented decisions or fake causal edges.
- Read-only runtime query/API works through estate authorisation; the collector outage does not stop agent work.
- Collection overhead, dropped events, retention, storage and sensitive data exposure measured under load.
- Two comparable verified runs and one independently measured optimisation.

## Known limits of delivered build

This is an **integration-ready reference implementation**, not production-certified estate-wide instrumentation. SQLite is local; HTTP is loopback-only and requires a bearer token. Client queue is bounded and best effort; event drops are counted in-process but not persisted if the process dies. Viewer is a single-file local UI, not integrated with estate SSO. No changes were made to GitHub or the cluster.

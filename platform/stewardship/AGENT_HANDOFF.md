# Shipping agent directive — Estate Stewardship P0

## Repository evidence already inspected (2026-10-28)

- `AGENTS.md`: no work without a GitHub issue and a live path claim; `bin/claim-open`, `bin/claim-gate`; operational proof on `/fleet`, not merely green CI.
- `docs/epics/2026-10-25-estate-master-epic.md`: R-14 failure -> ticket -> dispatch -> verify -> learn, R-16 research -> experiment -> prototype -> production, R-17 process self-improvement. Preserve one store per responsibility.
- `bin/estate-diagnose`: Bayesian diagnosis already exists. Reuse it, do not introduce a competing posterior engine.
- `sovereign/engine/tracing.py`: guarded Langfuse with signed anchors. Reuse evidence/receipt anchors.
- `packages/idp_concurrency/src/idp_concurrency/tracer.py`: OTel traced HTTP client and trace-derived receipt.

## Integration order

1. Create/claim an issue through existing workflow; check overlapping path claims.
2. Map canonical ticket, evidence and capability interfaces. Implement adapters; do not create duplicate ticket, tracing or approval services.
3. Make every harness emit observations with `task_id`, `run_id`, source refs, confidence grade and classification; do not block primary task on stewardship capture failure. Use bounded durable local buffering and report dropped events.
4. Implement deduplication by root-cause signature with evidence-backed merges and human/agent override. Never merge on error text alone.
5. Replace caller-supplied `claim_valid` and `independent_verification` flags with signed, current receipts verified at the execution boundary. The included policy is **not sufficient by itself to authorize production changes**.
6. Bind approved changes to existing `estate-execute` and claim gates, with scoped allowlists, dry run, budget ceiling, rollback and independent evaluator.
7. Attach experiment results to AEI baseline/task cohorts, including correctness, cost, p95 latency and safety regressions. Compare against representative workloads.
8. Publish API for Oracle and `/fleet` using the estate's existing identity and access control; expose BLIND for unavailable telemetry.
9. Run BDD feature through the estate's binding/trace-matrix mechanism, plus negative and end-to-end live scenarios.
10. Verify a real recurring problem through discovery -> research -> claim -> experiment -> delivery -> operational proof -> reusable learning. Only then report DONE.

## Non-negotiable negative tests

- No claim or stale claim -> refuse; no trusted verifier -> refuse; changed security boundary -> refuse; founder-reserved policy -> refuse.
- Backend outage must not block primary task; dropped evidence is visible.
- Improvement with lower verified quality -> reject even when faster or cheaper.
- Duplicate discoveries consolidate without erasing original evidence.
- No raw secrets in evidence; classification and access checks before export.
- Hash-chain tampering detected; externally anchored heads protect against privileged rewrites.
- Agents cannot self-approve by writing approval-shaped JSON.

## Status

Core ledger, bounded policy, comparison primitive and tests run locally. Live integrations and operational certification are NOT complete. No GitHub changes made.

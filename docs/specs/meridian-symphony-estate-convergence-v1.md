# MERIDIAN SYMPHONY — Canonical Estate Convergence & Living Graph
Version 1.0 · 2026-11-16 · Owner: authenticated FLOW/Legion fleet · Tracking: #8169
Status: PROPOSED, not operationally verified. This is a source-native execution contract, not a new platform.

## Mission
Make all Meridian capabilities operate as one evidence-driven orchestra. Every mission, component, agent, model, tool, compute resource, cost, decision, event, failure, PR, deployment and verified outcome is a typed node; relationships are causal, temporal, provenance-bearing edges. The founder can traverse the whole estate to one worker's operation, inspect actual resource cost, intervene with authorized controls, and follow verified effects back to the originating instruction.

## Non-negotiable invariants
1. Reuse IDP, Genesis, Face/OTTO, FLOW, Legion, QUAD, Battalion, Optimus, KARMA, Chronos/Tempo, BEAST/SPIDER/IO, Mini Backstage, existing memory, OTel/Langfuse and messaging infrastructure; no competing source of truth, event bus, graph DB or scheduler without documented deficiency and migration.
2. An issue/comment/spec/unmerged PR is NOT dispatch or delivery. Each job requires authenticated owner, lease, runner, accepted checkpoint, exact source SHA, merged/deployed SHA, outside-in verifier and recovery state.
3. Unknown, stale, estimated, allocated, direct and blind are distinct. No fixture data, fabricated metrics, implied live authority or fake zero cost.
4. Authorized execution is signed, scoped, fenced, idempotent, auditable and budget-bounded. Retain safe recovery; never bypass security for velocity.
5. Every predictable failure mode is falsified at earliest producer admission; never create blanket gates that deadlock legitimate recovery.
6. Keep user/private model prompts and transcripts access-controlled; never claim access to hidden chain-of-thought.

## System composition
- FLOW: canonical instruction-to-verified-yield state machine, nested recursively for subtasks, incidents, experiments and recovery.
- Legion: durable model-agnostic workforce, worker/session/lease/checkpoint lifecycle; OpenCode preferred, other harnesses via adapters.
- QUAD: policy, signed principal and spend/action authority.
- Battalion: model/compute supply discovery, routing matrix, resource allocation, quotas, full cost accounting and bounded fallback.
- Optimus: independent experiments, quality evaluation, uncertainty, calibration, Pareto optimization.
- KARMA: inherited obligations, recurrence-class elimination, failure economics, corrections and negative memory.
- Chronos/Tempo: scheduling, event-time and durable reconciliation.
- BEAST/SPIDER/IO: capability composition, dependency topology and transport as existing code proves; map actual implementations before assigning new authority.
- Mini Backstage: catalog and source/operational status of every admitted component.
- Genesis/Face/OTTO: one live, authenticated, semantic-zoom mission control; not an alternate backend.
- IDP/Greenlane: producer admission, CI, exact-SHA merge, deployment and independent outside-in verification.

## Typed, temporal graph
Node types: Objective, Mission, Task, Worker, Session, Model, Provider, Harness, Tool, Capability, Service, Resource, Policy, Decision, Event, Measurement, FinancialEntry, Experiment, Evaluation, FailureClass, Correction, Repository, Branch, PR, Commit, Build, Deployment, Probe, Effect, HumanIntervention.
Edge types: CONTAINS, DECOMPOSES_TO, DEPENDS_ON, ASSIGNED_TO, EXECUTES, CALLS, CONSUMES, COSTS, PRODUCES, EVALUATED_BY, CAUSED_BY, CORRECTED_BY, DEPLOYED_AS, VERIFIED_BY, GOVERNED_BY, DERIVED_FROM, SUPERSEDES.
Every entity: stable canonical ID, kind, schema version, source authority, provenance receipt, observed_at, valid_from/valid_to, classification, owner, status, last_verified, confidence/measurement grade, access policy. Every edge: ID, typed endpoints, causal/temporal semantics, origin evidence, time bounds, validity and revocation. Do not invent causal edges from temporal correlation; distinguish causal evidence from hypotheses.
Use bitemporal projections over existing authoritative sources, with replay, corrections, partial coverage and anti-entropy. A graph view is a projection, not an independently writable authority.

## Universal telemetry and economics
Four separate linked ledgers: (1) activity/execution; (2) physical consumption CPU/GPU/RAM/network/storage/model/tool/human when observed; (3) financial estimate/accrual/invoice/reconciliation with shared/idle costs; (4) evaluation and verified effect. Preserve one physical cost across parent/child rollups, time-versioned prices and invoice corrections. OTel GenAI trace semantics, FOCUS billing normalization and OpenCost Kubernetes allocation where applicable. Missing usage=BLIND, not zero. Connect meter receipts to FLOW mission/session/worker IDs and exact effects. Expose cost per verified outcome only within comparable cohorts and declared quality scales.

## Live visual experience
A visually ambitious, scientifically truthful living constellation/tree with six levels of semantic zoom:
L0 whole estate and health/coverage;
L1 domains/capabilities/dependencies;
L2 missions and agent formations;
L3 sessions/child tasks/transcript events;
L4 model/tool/compute spans, routing and spend;
L5 source→PR→CI→deployment→independent effect evidence.
Views: radial constellation, dependency DAG, causal tree, timeline/time travel, resource-flow Sankey, incident blast-radius, experiment comparison and failure recurrence. Use shared graph IDs and event-time; no independent fixture stores. Smooth progressive rendering, accessible keyboard/search, reduced-motion mode, screen-reader alternatives, responsive mobile, high-cardinality clustering, bounded stream update rates. Highlight BLIND/STALE, uncertainty, evidence grade, authorization and exact timestamps. Show the same state on Genesis and Face.
Interactions: select, drill, compare, search, time travel, inspect evidence, explain routing, trace cause, propose authorized steer, confirm, observe accepted→executed→verified receipt. Read-only when authorization or live connection unavailable; never simulate success.

## Orchestration protocol
Instruction → canonical objective/mission → discover/reuse capabilities → policy/cost admission → worker formation and lease → streamed execution and meter events → independent evaluation → signed Greenlane delivery → outside-in verified effect → KARMA correction → Optimus experiment → visible Genesis state. Every transition carries source receipt and timeout/recovery semantics. Ten-minute genuine no-progress detector distinguishes legitimate long-running tools, rate limits, idle queues and dead sessions. Failed or disconnected tasks remain durable and recoverable, never silently disappear.

## Fleet work packages
WP0 forensic census: main, branches, host, deployed runtime, Gemini/AI Studio recovery, existing graph/memory/metrics, authority; source→merged→deployed→verified SHA matrix and gaps.
WP1 canonical schema: typed graph projection and trace correlation, temporal replay, provenance, tenant access and schema evolution; adapters to existing sources.
WP2 real execution: one authentic mission with parent/child agent sessions, tool/model spans, resource usage, source commit, PR, deploy and independent probe.
WP3 Genesis/Face: six-level semantic zoom, search, timeline, causal graph, overlays, real stream and accessible performance, authenticated control with receipts.
WP4 Battalion/Optimus/KARMA: invoice-aware metering, model supply discovery, matched-cohort routing experiments, causal correction and decision explanations.
WP5 certification: adversarial falsifiers, performance/UX, security, recovery, operational runbooks and continuous coverage monitoring.
Each package has one authenticated owner, lease, exact SHA, acceptance, negative tests, independent witness and deploy receipt. No duplicate PRs or abandoned work.

## Adversarial falsification
Duplicate event/retry/parent-child double charge; forged evidence/authorization; stale head/unmerged PR; blind collector and replay; timestamp skew; source deleted/branch missing; partial Gemini exports; wrong model price/FX/invoice; shared GPU idle; unavailable reasoning tokens; prompt leakage; wrong graph permissions; disconnected Face; false-positive stall; worker crash; expired lease; budget race; unauthorized paid compute; model self-grade; skipped BDD; green CI with broken production; no-op verifier; graph scale overload; inaccessible controls; inaccessible visualization. Each needs reproducible test, expected/actual verdict, owner, evidence and root-cause elimination.

## Acceptance gates
G0 complete or explicitly BLIND inventory and authority map.
G1 one real mission across graph, agent, model/tool, resources and receipts.
G2 reliable replay, attribution, no duplicate charge, access control.
G3 Genesis/Face same live state and real authenticated control effect.
G4 exact SHA merge/deploy and independent external verified effect.
G5 measured Battalion optimization on >=3 comparable strategies, quality independently assessed.
G6 failure suite, accessibility, latency, budget/security and recovery canary pass.
G7 autonomous ownership, alerts, inherited correction and ongoing operational monitoring proven.
**Done** only when founder traverses a live mission from objective to independently verified effect, sees truthful metering and evidence, steers authorized workers, and proves improvement; not when documentation, visualization prototype or PR exists.

## Source and integration pointers
#8169 Symphony; #3525 Battalion; #8133 OMNIFLOW; #7819 Gemini recovery; merged #8164 recovery inventory; #8161 estate assurance. Existing original Battalion spec: docs/specs/2026-09-15-asymmetric-compute-leverage-spec-v0.1.md. Read canonical AGENTS.md and current Greenlane/FLOW admission before making implementation changes.

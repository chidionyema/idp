# P0 — Agent Execution Intelligence (AEI): founder directive

Source: founder directive, 2026-10-27, imported 2026-10-29 verbatim in substance. Priority: P0 estate
capability, not an optional dashboard. Visualisation is a first-class artifact of every instrumented
component. This is NOT permission to install overlapping monitoring products (AGENTS.md section 6:
exactly one of each layer, including traces). Inspect existing telemetry first and build on it.

Status of this file: a directive. What exists today is mapped in
`docs/specs/imports/2026-10-29-estate-master-vision-and-recovered-specifications.md` and ADR 0045
(`docs/decisions/0045-aei-is-an-observation-plane-not-a-second-evidence-authority.md`).

## Mission

Build an estate-wide, always-on instrumentation and optimisation capability that reveals how agents
solve problems, where they waste time and resources, and how to improve verified delivery
performance. It works across cloud, Kubernetes, local devices, LiteLLM, Hermes, Codex, Claude Code,
Otto, Temporal and custom harnesses.

## Three rules, immediately

1. Every execution produces evidence. A trace connects the original task, decisions, model calls,
   tool calls, retries, verification and outcome.
2. Every component declares its observability contract (events, metrics, trace relationships,
   visualisations, acceptance tests), versioned alongside its implementation.
3. Every optimisation is experimentally verified against a baseline on representative tasks,
   measuring speed, cost, quality and reliability together.

An agent, harness, router or workflow is not fully onboarded unless its execution can be inspected,
measured, compared and explained visually.

## 1. Architectural invariants

- One canonical telemetry contract across all runtimes.
- Every execution has a globally unique run_id, task_id, agent_id, harness_id, trace_id and code revision.
- Every model request, tool invocation, decision checkpoint, retry, state transition and verification
  is correlated with its originating task.
- The collector is not on the critical execution path: telemetry failure must not stop the agent.
- Raw events are append-only; interpretations and evaluator judgments are separate, versioned derived records.
- Every metric has a defined unit, provenance, collection method and reliability status.
- All components publish a versioned observability manifest and a machine-readable visualisation spec.
- Sensitive telemetry is classified and protected before export.

## 2. Discovery before deployment

Inspect existing LiteLLM callbacks, Langfuse configuration, OpenTelemetry collectors, tracing stores,
Grafana dashboards, Prometheus metrics, Temporal histories and harness logs. Reuse what works. Produce
a gap matrix: existing telemetry, missing events, instrumentation changes, evidence.

## 3. Instrumentation contract — minimum event families

task.created, task.started, task.completed, task.failed ·
context.assembled, context.retrieved, context.compacted ·
decision.proposed, decision.selected, decision.revised ·
model.requested, model.first_token, model.completed ·
tool.started, tool.completed, tool.failed ·
hypothesis.registered, hypothesis.tested, hypothesis.rejected ·
retry.started, recovery.completed ·
verification.started, verification.passed, verification.failed ·
human.intervention, approval.requested, approval.received

Record timestamps, parent-child relationships, attempt numbers, queue times, model routing, resource
consumption, cost, outcome and evidence references. Where internal decisions are inaccessible, record
observable checkpoints. Never fabricate private model reasoning or label inferred hypotheses as observed.

## 4. Mandatory component visualisation artifact

Every agent, harness, router and execution workflow declares: identity, version, owner, dependencies;
supported event and metric schemas; trace-to-task correlation rules; dashboard and execution-view
definitions; required latency, quality, cost and reliability indicators; links from visual elements to
evidence; coverage and freshness indicators; tests that the visualisation renders real data. Versioned
with the component and checked in CI. A component without it is not fully onboarded.

## 5. Required visualisations

A. Execution waterfall — task, model, tool, queue, retry, context, verification spans on one timeline; critical path and parallel work.
B. Problem-solving graph — hypotheses, decisions, tool actions, evidence, reversals, failures, verified outcomes; recorded events distinguished from evaluator-derived interpretations.
C. Harness comparison — equivalent tasks across harnesses, models, configurations, revisions, with difficulty and verification criteria.
D. Waste analysis — repeated reads, duplicate tool calls, unnecessary model calls, abandoned branches, retry loops, context churn, idle time.
E. Agent scorecard — verified throughput, cost per verified success, latency distributions, failure recovery, unattended completion, founder intervention.
F. Estate optimisation map — which components, models, tools and dependencies dominate time, cost, errors and failed outcomes.

## 6. Optimisation engine

Start with deterministic trace analysis: critical-path bottlenecks, repeated operations, excessive
context construction, inefficient routing, unnecessary sequential work, failed recovery patterns.
Generate proposals with baseline, expected impact, risks, test plan. Validate on representative
workloads before rollout; no optimisation succeeds if it degrades correctness, safety or completion.

## 7. Rollout

1. Instrument one real workflow end to end (harness -> LiteLLM -> tools -> verification); waterfall and raw export. First workflow: Otto's own recovery task.
2. Make the visualisation contract enforceable: schema validation, coverage checks, dashboard artifact.
3. Cross-harness comparison: second harness, common verified task suite, published results.
4. Estate-wide adoption without breaking running services.
5. Closed-loop optimisation: measured inefficiencies become bounded tasks with before/after evidence.

## 8. Acceptance criteria

- A real agent task is traced end to end across harness, LiteLLM and tool execution.
- Trace and task identifiers survive process and device boundaries.
- Every displayed metric links to underlying evidence.
- Missing instrumentation is reported, never shown as zero.
- The visualisation contract is checked automatically in CI.
- Two runs of the same task compare with verified outcomes.
- At least one inefficiency is identified, corrected and retested.
- Collection overhead, storage cost, dropped events and sensitive-data exposure are measured.
- Telemetry outages do not halt agent execution.

## Definition of done

The estate can answer, with evidence: what did this agent do, why this path, what did it cost, what
worked, what was wasted, and what verified change would make the next execution better — through
machine-readable records, an interactive visualisation, and an API for Oracle and other agents.

Priority note from the directive: this takes priority over new agent features because every later
improvement becomes measurable once it exists; do not block Otto recovery on the full rollout.

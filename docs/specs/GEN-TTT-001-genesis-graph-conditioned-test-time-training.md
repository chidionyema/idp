# GEN-TTT-001 — Genesis Graph-Conditioned Test-Time Training
**Status:** SPECIFIED / NOT EXECUTED / NOT VERIFIED  
**Date:** 2026-11-16  
**Authority:** founder authorization; IDP #8185; parent Living Intelligence Graph #8184; existing HELM #7908 and Symphony #8169.  
**Scope:** Genesis founder surface, HELM experimental science, Legion execution, QUAD identity, FLOW obligations, BEAST/SPIDER graph context, Optimus economics, KARMA lineage, Chronos reconciliation.  
**Normative precedence:** current main AGENTS.md, active infrastructure decision, authorized runtime policy, existing spec-gate and executable BDD. This document cannot confer permissions.

## 0. 720-degree evidence preflight
Before modifying code, generate a structured and timestamped eight-field estate brief: STATE, INTENT, HISTORY, GAPS, METRICS, DECISIONS, CONSTRAINTS, CAPACITY. Each field names authoritative source, evidence digest, observed time and freshness. UNKNOWN is explicit. Inventory Genesis source/deploy, argon branches, HELM/TTT prior work, model/runtime GPU/ARM capacity, actual training rights, existing experiment registries, graph/memory APIs, and current authorization. Do not infer absence from indexed search. Reuse deployed capability, repair disconnected capability, build only verified gaps. No OKE assumption.

## 1. Intent and outcome
An authenticated founder can start, inspect, compare, stop, resume or roll back a **real** test-time adaptation experiment from Genesis, initiated on any supported connected or disconnected surface. An existing approved execution gateway performs authorized effects. The graph provides verified context, not authority. A genuine weight/adapter or expressly classified learned-state update is evidenced, compared against frozen, graph-RAG and compute-matched baselines on leakage-resistant holdouts, and its cost, safety, generalization and causal uncertainty are visible in Genesis. Verified results enter Optimus/KARMA; failed experiments and negative results remain durable.

**Non-goals:** fake TTT toggles, ordinary prompt reflection mislabeled as training, a duplicate model router/registry/memory/ledger/scheduler, unauthorized production fine-tuning, automatic deployment of unverified adapters, new blanket gates, or any claim of improvement without independent holdout evidence.

## 2. Requirements register (each maps to BDD and oracle)
| ID | Requirement | Independent proof |
|---|---|---|
| TTT-R01 | Discover existing Genesis/HELM/TTT implementations, deployed paths and capacities before new build | Reproducible estate inventory with working/partial/dormant/absent classification |
| TTT-R02 | Single experiment identity, durable FLOW obligation, parent intent, accountable QUAD, lease and versioned policy | Terminate/restart worker; same obligation and identity persist |
| TTT-R03 | Expose real Genesis experiment launch, live state, cohort comparison, checkpoint and rollback controls | Authenticated browser action changes verified backend state |
| TTT-R04 | Support frozen base, graph-RAG, matched-compute/search, true parameter/adapter TTT, learned-state, combined graph+TTT | Actual cohort run IDs and explicitly differentiated update mechanisms |
| TTT-R05 | Require authoritative graph entities, typed predicates, evidence provenance, bitemporal state and UNKNOWN | Forged entity, stale edge and contradicted edge falsifiers |
| TTT-R06 | Train only on approved models, licenses, runtimes and permitted data; immutable base and bounded updates | Unauthorized weights/data/runtimes refused; audit evidence |
| TTT-R07 | Use task-local, session-local and approved longitudinal retention with reset and checkpoint lineage | Restore exact pre-adaptation behavior; no unintended cross-tenant retention |
| TTT-R08 | Independent temporal, component and failure-class holdouts with leakage protection | Canary labels/holdout hashes not exposed to adaptation |
| TTT-R09 | Capture true parameter/adapter deltas, loss/objective, optimizer, steps, seeds and checkpoint digest | No-op trainer fails actual-training proof |
| TTT-R10 | Measure correctness, causal calibration, recurrence, false prevention, latency, tokens, energy/compute, money and human time | Matched baseline with intervals and missing-data flags |
| TTT-R11 | Preserve adversarial failures, poisoning, forgetting, drift, contradiction and rollback results in KARMA | Failed experiments discoverable, not rewarded or erased |
| TTT-R12 | Optimus chooses evidence-based Pareto candidates, not a self-graded reward | Independent evaluator and cost-quality frontier |
| TTT-R13 | Legion supports model-agnostic specialist execution; new providers onboard through capability contracts | Substitute model/provider without rebuilding Genesis |
| TTT-R14 | Offline/disconnected entry preserves signed origin, idempotent reconciliation and authorization | Replay and conflicting writes do not duplicate effects |
| TTT-R15 | Genesis displays source freshness, provenance, uncertainty, missing telemetry and exact SHA/run evidence | Real browser readback against independent APIs |
| TTT-R16 | Recovery is bounded, failure-class mapped and verified; prevention precedes cure | Fault injection recovers or leaves owned BLOCKED state |
| TTT-R17 | Research stays fast and reversible; production promotion requires independent release proof | Unverified checkpoint cannot reach privileged production path |
| TTT-R18 | All changed code ships bound executable BDD and traceable tests | IDP spec-gate and CI tests prove scenarios executed |

## 3. Canonical architecture and contracts
**Genesis UI → authenticated intent API → existing FLOW/QUAD ledger → capability registry / authorized execution gateway → Legion experiment worker → approved model training runtime → independent HELM oracle → Optimus decision / KARMA memory → Genesis live readback.** BEAST/SPIDER provide typed context and hypotheses; Chronos reconciles stalled obligations through the existing scheduler. No graph edge grants authority.

### 3.1 Entities
Experiment, ExperimentArm, Task, Dataset, Split, Holdout, GraphSnapshot, OntologyVersion, Model, ModelRevision, Adapter, Checkpoint, TrainingUpdate, TrainingObjective, OptimizerConfig, Run, Evaluation, Oracle, Evidence, CausalHypothesis, CostObservation, Risk, PolicyDecision, Agent, QUADPrincipal, FLOWObligation, FailureClass, RecoveryAttempt, Deployment, Surface, Capability, Source.

### 3.2 Typed edges
EXPERIMENT_HAS_ARM, ARM_USES_MODEL, ARM_USES_GRAPH_SNAPSHOT, RUN_EXECUTES_ARM, RUN_HAS_UPDATE, UPDATE_PRODUCES_CHECKPOINT, EVALUATION_TESTS_CHECKPOINT, EVALUATION_USES_HOLDOUT, ORACLE_ATTESTS_RESULT, RUN_OWNED_BY_QUAD, RUN_SETTLES_FLOW, EVIDENCE_SUPPORTS_CLAIM, EVIDENCE_CONTRADICTS_CLAIM, RUN_INCURS_COST, FAILURE_TRIGGERS_RECOVERY, ADAPTER_DERIVES_FROM_MODEL. Each edge records authoritative source, evidence digest, actor, signature where available, observation/recording/valid times, ontology version, confidence and epistemic status. Schema validity does not prove truth or causation.

### 3.3 Minimal machine-readable experiment request
```json
{
  "schema_version": "genesis.ttt.experiment.v1",
  "intent_id": "required-authoritative-id",
  "flow_obligation_id": "required-authoritative-id",
  "quad_principal_id": "required-authoritative-id",
  "task_suite_ref": "approved-suite-id",
  "dataset_snapshot_digest": "sha256:...",
  "holdout_policy_ref": "temporal-component-failureclass-v1",
  "graph_snapshot_ref": "authoritative-snapshot-id",
  "arms": ["frozen", "graph_rag", "matched_compute", "parameter_ttt", "learned_state", "graph_ttt"],
  "model_capability_ref": "verified-capability-id",
  "adaptation": {"objective_ref": "approved-objective", "max_steps": 20, "max_duration_seconds": 300, "max_compute_budget": "approved-budget-ref", "retention": "task_local"},
  "policy_version": "verified-policy-version",
  "independent_oracle_ref": "approved-oracle-id",
  "idempotency_key": "caller-generated-unique-key"
}
```
Illustrative IDs are placeholders, not runtime evidence. Validate with versioned JSON Schema or existing canonical validator; reject missing authority rather than supplying defaults.

### 3.4 Event and evidence envelope
Each experiment state transition records experiment/run/arm IDs, parent FLOW instruction, QUAD actor, source/runtime/model returned revision (UNKNOWN if undisclosed), git SHA, checkpoint digest, dataset/holdout hashes, source time, observed/recorded/valid times, evaluator version, objective, before/after update digest, measured costs, signed or independently anchored evidence and state. Never store secrets or indiscriminate private task content.

### 3.5 State machines
Experiment: PROPOSED → PREFLIGHT → ADMITTED → QUEUED → RUNNING → EVALUATING → VERIFIED_RESEARCH_RESULT → {RETAINED, REJECTED, PROMOTION_CANDIDATE}; any stage may transition to BLOCKED, FAILED, CANCELLED or RECOVERING. Production promotion is a separate authorized workflow. No completion from UI assertion alone. FLOW obligation settles only on independently VERIFIED_YIELD for its declared scope.

## 4. Experimental design
**H1:** graph-conditioned genuine TTT improves independent held-out correctness over graph-RAG at matched compute.  
**H2:** improvement survives control for tools, tokens, inference-time search, graph freshness and training-set leakage.  
**H3:** gains transfer to unseen component/failure classes and persist only under explicit retention policy.  
**H4:** risk-adjusted value exceeds adaptation cost and does not degrade legitimate operational outcomes.

Arms: A frozen/no graph; B frozen+graph; C B+compute-matched reasoning/search; D B+actual trainable TTT; E B+learned-state (separately labelled); F graph+TTT+matched search. Run only feasible arms and explicitly report unavailable arms; never pretend a hosted model exposes weights. Use open-weight/licensed models or authorized trainable APIs. Stratify and randomize by incident difficulty, component, failure class and time. Pre-register objective, dataset split, sample size/power feasibility, budget and decision criteria. Use temporally and component-disjoint holdouts; independent evaluators must not see training answers. Compare paired tasks, bootstrap confidence intervals, error bars, calibration, generalization and cost-quality Pareto. Record negative/null results.

### 4.1 Adaptation methods
At least one genuine update to trainable parameters or LoRA/adapter weights; optionally self-supervised objectives, per-task fine-tuning, learned-state online adaptation and bounded continual learning. Each method defines update trigger, gradients/objective, optimizer, steps, data permission, base freeze, checkpoint and rollback. A learned hidden state is not silently counted as parameter TTT. Control for additional compute and memory.

### 4.2 Safety and economics
Default task-local ephemeral adaptation, no cross-tenant leakage, hard compute/time limits, no automatic privileged effects. Track token usage, GPU/CPU seconds, memory, energy if instrumented, billing, CI minutes, human interruptions, latency, failure recurrence, intervention costs and benefit. Missing measurements are UNKNOWN, never zero.

## 5. Genesis product contract
Navigation: **Research → Adaptive Intelligence / TTT** within existing Genesis, with entry points from BEAST entity, SPIDER incident, HELM experiment and FLOW mission. One canonical backing service.

Screens:
1. **Overview:** actual active runs, health, capacity, spend, pending obligations, verified gains, unknown coverage, freshness.
2. **Experiment composer:** choose authorized task suite, graph snapshot, model/runtime, arms, update budget, objective, retention, oracle and policy; preview constraints and cost ceiling; authenticated submit.
3. **Live run:** per-arm state, real update counters and checkpoint hashes, agent identity, graph lineage, resource consumption, failures, intervention and cancel/retry.
4. **Evidence comparison:** frozen/RAG/search/TTT cohort results with confidence intervals, leakage checks, holdout details, negative outcomes, Pareto plot and provenance drilldown.
5. **Model lineage:** immutable base, adapter genealogy, versioned training, rollback, expiry, approval, and deployment eligibility.
6. **Graph reasoning:** task→entity→source→hypothesis→experiment→evidence→obligation→outcome; disconnected/UNKNOWN nodes explicit.
7. **Recovery and audit:** signed events, stale jobs, owner leases, independent verification, failure classes and retained rejected hypotheses.
Controls must invoke real authenticated APIs; no fixture success, optimistic false-green states or self-awarded verified badges. Responsive, accessible WCAG AA, keyboard and screen-reader flows, mobile/voice parity where supported. Unavailable controls display reason and authorized recovery.

## 6. Interfaces and authority
Use existing API patterns and gateway; proposed semantic operations, not permission to invent parallel services:
- list capabilities/models with training-rights and resource budgets;
- create/list/get/cancel/retry experiments, idempotent and FLOW-bound;
- stream authoritative experiment events with reconnect/cursor and stale detection;
- list checkpoint lineage and request reversible rollback;
- retrieve independently attested evaluation, cost and graph evidence;
- request promotion through existing authorized release controls.
All write operations bind QUAD principal, policy decision, signed request when required, exact target version, idempotency key and auditable result. A read-only or disconnected client cannot escalate privileges. Explicit 401/403/409/429/503 and typed BLOCKED/UNKNOWN handling.

## 7. Failure mode register and preventative controls
| Class | Producer prevention | Independent falsifier |
|---|---|---|
| No actual training | Verify nonzero approved parameter/adapter delta and checkpoint | No-op optimizer returns no success |
| Evaluation leakage | Holdout sealing, disjoint splits and blinded oracle | Inject holdout label into context; reject run |
| Fake improvement | Matched budgets, paired holdouts, independent oracle | Self-scored gain alone rejected |
| Poisoned graph | Signed authoritative identity, source freshness and contradictions | Forged/stale graph edge cannot become VERIFIED |
| Catastrophic forgetting | Retention isolation and regression suites | Earlier benchmark degradation recorded |
| Unauthorized training | Capability/license/data/policy checks before runtime | Restricted model or dataset rejected |
| Cross-tenant bleed | Scoped adapters, storage isolation, retention expiry | Cross-tenant retrieval denied |
| Resource exhaustion | Admission budget, hard time/compute caps, reclaim | Runaway update stopped without orphaning |
| Lost worker / stale lease | Durable FLOW, idempotent resume, bounded recovery | Kill worker mid-checkpoint; no double execution |
| Disconnected replay | Signed origin, dedupe and conflict handling | Replay identical command; one effect |
| Fabricated provenance | QUAD signature and evidence digest verification | Forged trailer rejected |
| Misleading cost | Source-linked billing; missing=UNKNOWN | Drop billing record; no positive ROI |
| False UI success | Independent live API readback, freshness and state oracle | Mock 200 with wrong SHA; reject VERIFIED |
| Uncontrolled production promotion | Separate authorization, canary and rollback | Unverified adapter cannot promote |
| CI spec bypass | Executable BDD bound to tracked test, pre-admission | Missing/unused feature fails spec-gate |

## 8. Executable BDD acceptance suite
Feature files must be bound to tests that execute them (IDP `bin/spec-gate`), with independent oracles. Required scenarios:
- **S01 discovery:** Given an existing functional adaptation engine, when inventory runs, then reuse it and show no duplicate service.
- **S02 real TTT:** Given an approved trainable model and task, when experiment runs, then nonzero verified update and checkpoint are observed, independently.
- **S03 no-op:** Given an optimizer that performs zero updates, when results are adjudicated, then actual TTT proof fails.
- **S04 matched baseline:** Given equal evidence and matched budgets, when arms run, then paired holdout results and uncertainty are published without fabricated uplift.
- **S05 leakage:** Given an exposed holdout label, when admission/evaluation occurs, then contaminated evaluation is invalidated.
- **S06 false graph edge:** Given a forged or stale identity edge, when context resolves, then it is rejected or UNKNOWN.
- **S07 contradiction:** Given contradictory sources, when hypotheses are generated, then both evidence paths remain and no unverified cause becomes fact.
- **S08 worker death:** Given a running update, when worker terminates, then lease expires, state persists, safe resume or owned block follows with no duplicate effect.
- **S09 rollback:** Given an adapted checkpoint, when rollback is authorized, then exact prior model behavior/version is restored and verified.
- **S10 policy:** Given an unapproved model/data pair, when submit occurs, then execution is refused before any training side effect.
- **S11 disconnected:** Given a signed offline initiation replayed twice, when reconciliation occurs, then one FLOW obligation and one authorized effect exist.
- **S12 cost:** Given missing usage/billing evidence, when Optimus scores a result, then cost remains UNKNOWN and no positive ROI is asserted.
- **S13 founder UI:** Given a live run, when Genesis opens on mobile and desktop, then controls, source freshness, real state and evidence agree with backend.
- **S14 adversarial forgetting:** Given an adapted model that regresses prior tasks, when holdouts run, then negative result is retained and promotion is denied.
- **S15 healthy path:** Given a valid approved experiment, when all guards run, then it completes without false-positive obstruction.
- **S16 production boundary:** Given a research-only checkpoint, when promotion is attempted, then separate authorized release verification is required.
- **S17 recovery:** Given transient runtime failure, when bounded recovery runs, then verified outcome or durable owned BLOCKED state follows.
- **S18 continuity:** Given founder disconnect and agent generation change, when reconciliation runs, then mission owner, context, obligations and evidence remain accessible.

## 9. Work packages, dependencies and delivery
**WP0** inventory and exact authoritative spec/template discovery (Genesis/argon Spec Factory, generated `spec.json`+`SPEC.md`); reconcile with this spec; preserve evidence.  
**WP1** typed contracts/ontology/provenance and schema validator.  
**WP2** trainable runtime and baseline/TTT adapters, checkpoints, isolation.  
**WP3** HELM independent data splits, adversarial oracle, statistical analysis.  
**WP4** authorized Legion/FLOW/QUAD orchestration, resumability and budget.  
**WP5** Genesis full control/observability UI; live API and browser verification.  
**WP6** Optimus economics, KARMA longitudinal memory, Chronos reconciliation.  
**WP7** cross-domain second canary, disconnected-surface replay, promotion and estate-wide conformance.

Each package must have an actual authenticated executor, QUAD identity, lease, evidence location, dependencies, acceptance tests, checkpoint and bounded recovery; absent dispatch is BLOCKED_DISPATCH, never an imaginary handoff. Parallelize independent packages after WP0. First real internal canary should not wait for the entire programme. Chesed: run early; Geburah: falsify and refine.

## 10. Release, verification and completion
**Research canary accepted** only with real run ID, actual adapter/weight delta, exact model revision and checkpoint digest, frozen and matched baseline, independent holdout results, budget, negative controls, and durable KARMA/Optimus evidence.  
**Genesis integration accepted** only with authenticated live founder action, correct runtime revision, exact SHA, evidence freshness, responsive accessibility, rollback and failure readback.  
**Estate-wide verified yield** additionally requires second unrelated domain, offline entry/reconciliation, no unauthorized effects, recurrence measurements, independent deployment evidence and continued observation.  
**Programme remains OPEN** until all promised acceptance criteria have independently verified operational evidence. A spec, issue, green PR, generated UI, or screenshot alone is not yield.

## 11. Traceability and continuity
Every requirement ID maps to formal predicate/schema, BDD scenario, executable test, independent run ID, exact SHA, runtime/deployment, observed result, cost and KARMA obligation. Store source and negative outcomes durably. If stopped, emit structured current state, exact blocker, next authorized action, owner/lease, expiry, and resume checkpoint. No founder reminder required. Machine-readable `spec.json` and generated `SPEC.md` must use the **actual** Argon Spec Factory schema when discovered; do not invent a schema and call it canonical.

## 12. Current evidence and honest status
As of authoring, IDP main AGENTS.md and `bin/spec-gate` were inspected; Argon AGENTS.md identifies the Genesis operating protocol. The canonical Spec Factory template path/schema, Genesis live TTT runtime, actual training updates and deployed Genesis controls have NOT been verified. This document is a full requirements/assurance specification on an isolated branch, **not** an executed experiment, canonical generator output, or deployment receipt.

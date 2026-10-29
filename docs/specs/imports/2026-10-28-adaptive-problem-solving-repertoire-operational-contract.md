# Estate adaptive problem-solving repertoire — operational contract v0.1

## Status and authority
Local prototype and executable baseline tests only. NOT integrated, deployed, production-observed, or independently certified. `AGENTS.md` governs any integration. No new orchestration, router, memory, verification, or telemetry service.

## Objective
Given an evidence-backed problem fingerprint, recommend a bounded, context-appropriate problem-solving method and its proof obligation; select a different method or stop when evidence contradicts the approach. Beat a fixed Bayesian-first baseline on held-out, representative Estate cases at matched cost/risk budgets.

## Integration topology
1. Existing context compiler and capability registry furnish versioned problem fingerprints and available prerequisites, with provenance/freshness. Do not use LLM guesses as evidence.
2. Existing decision layer calls a **pure method selector** as a library; its output is a recommendation, not execution authorization. Every action names the decider and authority.
3. Existing governed executor invokes approved tools/method adapters. Each method declares preconditions, risk, budget, tool scopes, evidence output, stop/switch conditions and verifier.
4. Existing NSVEE/evidence infrastructure independently verifies artifacts and records counterexamples; a generated explanation never counts as verification.
5. Existing memory stores graded, time-bounded, re-executable observations. Do not promote self-reports to verified facts.
6. Existing event spine and Fleet observation surface display fingerprint, candidates, selected method, decider, budget, actions, evidence, refusal, switch and independently verified outcome.

## Candidate arsenal and research backlog
Regression: delta debugging, git bisect, differential testing, metamorphic testing. Incidents: causal graphs, fault trees, five whys with evidence, counterfactual experiments. Uncertainty: Bayesian inference when likelihoods are calibrated, active learning, sequential hypothesis testing, value of information. Formal: SAT/SMT, model checking, property-based testing. Optimisation: branch and bound, A*, constraint programming, Pareto optimisation. Performance: profiling, queueing theory, bottleneck analysis. Architecture: dependency graphs, tradeoff analysis, scenario planning. Strategy: minimax regret, multi-criteria decision analysis, robust optimisation. Novel problems: decomposition, analogy with transfer validation, morphological analysis, first-principles models. Complex adaptive systems: feedback-loop mapping, system dynamics and sensitivity analysis. Every addition requires references, applicability/anti-patterns, benchmark fixtures, cost profile, and independent evaluation.

## Hard invariants
- No recommendation without a matching problem type, required evidence, risk approval and sufficient budget.
- No method recommendation grants write or production authority.
- No LLM-generated confidence score becomes a probability without calibration evidence.
- No agent self-certifies its outcome; independent verifier required.
- Missing evidence yields abstention or a governed evidence-gathering action, never invented prerequisites.
- Max attempts and wall-time are bounded; contradictory evidence forces reassessment.
- No duplicate scheduler, routing plane, event spine, memory store or verification service.
- Any data from customers/tools is untrusted until validated at the boundary.

## Contracts
Input: `problem_id`, `kind`, `source_revision`, `evidence_refs`, `risk_tier`, `budget`, `uncertainty`, `authority`, `deadline`, `idempotency_key`, `provenance`.
Output: `method_id`, `method_version`, `rank`, `reason_codes`, `prerequisites_checked`, `expected_evidence`, `estimated_cost`, `risk`, `decider`, `policy_decision`, `trace_id`.
Outcome: `attempt_id`, `artifact_refs`, `verifier`, `verdict`, `counterexamples`, `actual_cost`, `elapsed`, `switch_reason`, `next_fingerprint`.
Reject unknown schema versions and malformed/out-of-range fields. Version contracts before wiring.

## Selection algorithm
Stage 0: deterministic policy, authority, data validity and risk gate. Stage 1: classify problem and identify available observations with provenance. Stage 2: filter catalogue by applicability, prerequisites and limits. Stage 3: rank using documented baseline heuristics; no false claims of optimality. Stage 4: estimate value of further computation or information gathering. Stage 5: governed execution, independent verification and bounded reassessment. Stage 6: learn from held-out, verified outcomes; keep a rollback to the deterministic baseline.

## BDD acceptance
- Given a reproducible regression with history, when selection runs, then bisect is eligible and Bayesian updating is not chosen by default.
- Given a formal invariant without a model, then the solver is refused with missing-prerequisite evidence.
- Given high-risk production context, then experimental actions require explicit authorization; recommendation never executes them.
- Given exhausted budget, then no method is scheduled.
- Given contradictory observations, then the current approach is reassessed.
- Given a claimed success without independent verification, then outcome remains unverified.
- Given replay of the same idempotency key, then no second side effect occurs (executor integration test).
- Given missing context or stale evidence, then system abstains or requests a bounded probe.
- Given router, verifier or memory unavailable, then the system degrades safely and reports the missing dependency.

## Evaluation
Create ≥100 held-out tasks across regressions, incidents, invariants, performance, architecture and uncertain decisions; include adversarial and unsolvable cases. Compare fixed Bayesian-first, fixed single-method, LLM-only selector, deterministic selector, and learned selector. Primary: independently verified resolution rate; secondary: cost per verified resolution, time, false-confidence rate, policy violations, abstention quality, recovery and switching efficiency. Report confidence intervals and per-domain results; avoid leakage between training and test cases. Promotion requires non-inferiority on safety, statistically supported improvement on primary metric, and operational traces from real callers.

## Landing plan
SF-0: pin repo SHA; inventory existing context/decision/router/verifier/memory/telemetry contracts and open claims. SF-1: implement typed schemas and deterministic baseline as library with negative tests. SF-2: wire read-only shadow recommendations into existing decision layer. SF-3: create representative fixture suite and independent evaluator. SF-4: gated canary on low-risk tasks; compare against baseline. SF-5: route verified outcomes to existing memory and Fleet; operational proof on real tasks. All code must enter via issue/claim, `lane/<name>`, `estate-execute lane-submit`, Greenlane and Flux; no direct PR/main push.

## Explicit blockers
GitHub issue creation through the current integration returned HTTP 403 (`Resource not accessible by integration`). No ticket/claim or authorized lane exists. Thus repo write, governed merge, live execution and production certification have NOT happened. Local prototype below is an isolated engineering seed, not an Estate deployment.

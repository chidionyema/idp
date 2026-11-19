# Feature Specification: Estate recursive adversarial assurance

**Feature Branch**: `research/7523-frontier-assurance` (proposed; not a promotion lane)
**Created**: 2026-11-19  
**Status**: Source candidate for #7523; not promoted or deployed  
**Input**: Founder requests frontier-calibrated supervisor, judge, red-team and pre-PR assurance across the estate; ChatGPT builds core, authenticated fleet delivers.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — No unverified PR (Priority: P1)
Builder submits a lane; Greenlane creates a PR only after the independently owned contract and mandatory tests pass on its exact candidate and current base. A refusal leaves the lane recoverable.
**Why this priority**: Stops preventable red PRs at source.
**Independent Test**: Observe actual GitHub PR-create call count and lane state under stale, forged, failed, missing and valid evidence.
**Acceptance Scenarios**: Given a candidate with missing, stale or false evidence, when promotion is attempted, then no PR is created. Given valid independent proof, when admitted, then exactly one PR is created for the proved head. Given a moved base or head, then proofs are invalidated before effect authorization.

### User Story 2 — Falsifiable verification (Priority: P1)
Red-team and independent verifier execute meaningful tests on frozen candidate and baseline. The candidate cannot control oracle execution, evidence or signing. Solver demonstrates legitimate utility.
**Why this priority**: Prevents self-certification and false success.
**Independent Test**: Run known-bad mutants, missing tests, early process success, runner error and valid alternatives against same contract.
**Acceptance Scenarios**: Given a required mutant survives or no tests run, when the verifier issues its verdict, then no admission. Given independent positive and negative controls both pass, then evidence is eligible for admission. Given infrastructure is unavailable, then INCONCLUSIVE, retained work and bounded recovery, not a defect attribution.

### User Story 3 — Calibrated judgement (Priority: P1)
Optimus evaluates judges against independent labelled holdouts; no missing measure is interpreted as neutral evidence.
**Why this priority**: Prevents self-improvement from optimizing fictitious metrics.
**Independent Test**: Confusion matrices with imbalanced marginals, all-one labels, missing observations, invalid scores, known perfect and imperfect raters.
**Acceptance Scenarios**: Given only passing gold labels, then calibration is inconclusive. Given measured binary decisions, then Cohen kappa uses empirical marginals. Given no transcript or missing score, then no numerical reward is invented. Given uncertain or conflicting judgements, then route for independent evidence rather than override deterministic failure.

### User Story 4 — Recovery and recursive assurance (Priority: P1)
Supervisor preserves work, transfers custody, and recovers when base, verifier, CI or cluster is unhealthy.
**Why this priority**: Prevents verification from becoming a circular dependency.
**Independent Test**: Fault-inject base red, lost worker, stale lease, unavailable judge and unavailable verifier while testing positive recovery.
**Acceptance Scenarios**: Given base red, then bounded authorized recovery is assessed against baseline and non-regression invariants, not blanket bypass. Given lost worker, then a fenced successor resumes existing obligation. Given drift, then only affected privileged capability is quarantined and safe diagnosis remains available.

### User Story 5 — Estate-wide convergence (Priority: P2)
Every registered effect surface uses the same contract through existing doors; Genesis projects real evidence and KARMA retains failure class.
**Independent Test**: Replay through IDP, Argon and representative non-code effect surfaces; compare actual effect counters and signed receipts.
**Acceptance Scenarios**: Given the same counterexample on two supported surfaces, then both refuse with identical semantics. Given real operational effect, then AEE operation/integration/objective evidence and FLOW closure are independently verified; no closure from a green PR alone.

### Edge Cases
- Candidate/base changed between proof and PR creation; duplicate delivery; stale or revoked identity; replayed nonce; cross-repo receipt; empty/partial scope; untrusted test harness; all tests skipped; timeout; tool missing; mutation output malformed; metadata-only changes; untrusted prompt injection; baseline already broken; verifier deployment itself broken; correlated judge errors; gold set leakage; repeated statistical peeking.

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001**: Freeze repository, base, head, tree, contract, expected test scope, policy, verifier environment and instruction/lease at admission; independently derive mandatory checks from protected authority, not candidate metadata.
- **FR-002**: Require independently authenticated signed evidence and authorized role/key, expiry, fence, nonce, exact context and explicit test execution; consume promotion authorization atomically; reject replay.
- **FR-003**: Run mandatory checks before PR creation, including those previously PR-only; check current head/base immediately before effect; reverify changed context. No worker PR credentials. Use existing Greenlane only.
- **FR-004**: NSVEE must refuse empty/no-op/failed/missing mandatory verification. External isolated oracle execution is separate from candidate-controlled process. No untrusted candidate on same-user fallback for release assurance.
- **FR-005**: Mutation report must distinguish killed, survived, timeout, equivalent, unsupported, invalid and unavailable; no unknown-to-green conversion; every required known-bad control killed and legitimate control admitted.
- **FR-006**: Supervisor owns durable recovery and fencing, not ability to waive deterministic admission. No model dependency for mechanical recovery.
- **FR-007**: Judge measures observed behaviour; unknown/N/A distinct; calibrated per risk stratum; empirical chance agreement; abstain if no evidence, insufficient discrimination, stale calibration or disagreement; never override deterministic safety.
- **FR-008**: Red team attacks specification, implementation, tests, judge, governance and recovery through authorized isolated fixtures; classify actual effect, not payload text. Solver preserves utility.
- **FR-009**: ParEval preregisters strata, practical margins, cluster unit, horizon or anytime-valid method; unknown is not tie; publish uncertainty, cost and negative results.
- **FR-010**: Reuse QUAD, NSVEE, AEE, Legion, FLOW, KARMA, Greenlane, Optimus, Chronos, Genesis and Argon adapters. No second authority, queue, ledger or scheduler.
- **FR-011**: Retain every confirmed failure class with executable falsifier, sibling sweep, fleet broadcast and recurrence evidence. On mandatory verifier failure deny privileged effect, preserve diagnosis and recovery.
- **FR-012**: Production closure requires exact landed tree/commit mapping, independent real-caller readback, no false closure, and measured outcome. Rollout effect-scoped, canary first.

### Key Entities
- Candidate: repository, base, head, tree, effect and trusted contract.
- Verification contract: risk stratum, required predicates, independent test inventory, policy and environment digest.
- Evidence: executable result with assertion IDs, positive/negative controls, artifact digest and independently authenticated provenance.
- Admission receipt: QUAD identity, role, instruction, fencing token, nonce, bounds, evidence digest and verdict.
- Counterexample: failure class, reproducible input, expected and observed effect, owner and regression lineage.
- Calibration cohort: judge/revision, labelled independent holdout, stratum, confusion matrix and uncertainty.

## Success Criteria *(mandatory)*

- **SC-001**: Zero PR create calls in the negative admission matrix; exactly one for each valid unchanged candidate, including concurrent duplicate requests.
- **SC-002**: All predeclared known-bad controls rejected; valid alternative implementations admitted; mandatory tool failure/timeout never green.
- **SC-003**: Every deployed effect surface declares and proves actual admission boundary, or explicitly reports UNBOUND (not silently covered).
- **SC-004**: Judge reports empirical confusion counts and uncertainty per stratum; unavailable/ambiguous data never a numerical success. Proposed risk calibration threshold: upper one-sided 95% false-accept bound <1% for high-risk strata, with independent representative trials and sufficient failure examples; not a claimed result.
- **SC-005**: Every planted outage class produces recovered work or explicitly durable refusal with custody, without founder intervention during canary; baseline and candidate differentiated.
- **SC-006**: Measure paired yield, false rejection, latency and cost against existing baseline; enforce only after authority-approved canary succeeds.

## Assumptions
- Existing issue #7523 owns integration; #8076, #7734, #8103, #6061, #7927 related. No duplicate claim or bypass.
- Trusted expected scope, key registry, signature verifier, nonce store and runner are supplied by existing estate authorities; a local adapter is not authority by itself.
- Candidate code is untrusted. Experiments isolated and no production mutations without existing authority. Risk and thresholds proposed for canary, not immediate new blanket gate.

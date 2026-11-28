Zero-Shot Preventive Control, Runtime Assurance and Autonomous Settlement
Classification: P0 — Critical infrastructure
Organisation: Meridian Intelligence
Version: 1.0
Status: Proposed implementation specification
Architecture: Intelligent Estate / Bounded Workers
Deployment: Cloud-first, zero laptop dependency
Primary repository: chidionyema/idp

1. Executive mandate
Transform the estate from a reactive, agent-mediated operating environment into an invariant-preserving autonomous production system.

Known classes of operational failure must be prevented at the earliest enforceable boundary. Unexpected failures must trigger bounded recovery and produce independently verified, mechanically inherited preventive corrections.

The founder must not function as the estate’s runtime exception handler.

The estate shall own:

Instruction custody.
Operational planning.
Resource allocation.
Provider eligibility.
Execution authority.
Budget enforcement.
Failure containment.
Recovery strategy.
Independent verification.
Settlement.
Continuous preventive improvement.
Workers shall execute bounded assignments within externally enforced operational envelopes.

Workers may propose changes to those envelopes but shall possess no unilateral authority to modify them.

The estate decides. The worker executes. Independent evidence establishes the outcome.

2. Non-negotiable engineering constraints
No new competing orchestration engine, scheduler, policy language, ledger or control plane.
Reuse existing FLOW, Temporal, Greenlane, Chronos, Legion, KARMA, Optimus and policy infrastructure.
Preserve the existing OPA/OPAL adoption decision, subject to measured deployment and security suitability.
No reliance on prompt compliance for critical invariants.
No new paid infrastructure or inference lanes without explicit authorisation.
No laptop-hosted production services, CI execution or authoritative state.
No worker-controlled settlement.
No silent instruction loss.
No routine founder intervention for machine-resolvable failures.
No operational acceptance based solely on source code, tests, merges or deployment status.
No weakening of protected governance boundaries to expedite delivery.
No global paralysis caused by a locally inadmissible operation.
3. Architectural foundations
The implementation shall combine:

Supervisory control: constrain permissible transitions without unnecessarily restricting productive operations.
Runtime assurance: isolate complex intelligence from deterministic safety enforcement.
Forward invariance: preserve admissible operating states.
Mechanism design: remove incentives and opportunities for unauthorised operational behaviour through structural constraints.
Reference-monitor architecture: mediate every protected effect.
Formal verification: establish safety, conservation and conditional liveness properties.
Fault containment: prevent failures from propagating across independent operational domains.
Continuous learning: convert discovered failure classes into independently tested preventive controls.
The architecture must distinguish conceptual principles, reference architecture, protocol contracts and replaceable implementation machinery.

Do not introduce a separate infrastructure component for every conceptual principle.

4. Control-plane decomposition
4.1 Plane 1 — Session, identity and jurisdiction
Responsibilities:

Authenticate the principal.
Establish worker identity.
Resolve jurisdiction and authority.
Determine permitted resources.
Bind the current policy revision.
Establish revocation and expiry semantics.
No worker may manufacture or extend its jurisdiction.

4.2 Plane 2 — Intent, conception and continuous valuation
Responsibilities:

Preserve the original objective.
Discover relevant context.
Generate candidate execution strategies.
Estimate expected yield.
Evaluate alternative recovery paths.
Calculate urgency, opportunity cost and resource demand.
Plane 2 is advisory.

It possesses no direct authority to produce consequential effects, allocate expenditure or weaken operating constraints.

4.3 Plane 3 — Commitment and effect
Responsibilities:

Deterministic admission.
Resource reservation.
Authority sequencing.
Fenced execution.
Effect mediation.
Independent verification.
Reconciliation.
Settlement.
Only this plane may authorise protected operational transitions.

Continuous intelligence informs discrete authority. It does not replace it.

5. Formal operating model
Define estate state as:

X = (I, A, B, R, T, C, P, E)

Where:

I = instruction custody.
A = authority and capabilities.
B = budgets and reservations.
R = resource availability.
T = dependency topology.
C = context validity.
P = active policy.
E = operational evidence.
Define an admissible operating region S through the conjunction of mandatory invariants.

A proposed transition is permitted only when:

The current state is sufficiently known.
The actor possesses valid authority.
The proposed effect is within scope.
Required resources have been reserved.
The applicable policy permits the transition.
The resulting state preserves the mandatory invariants.
Validation and effect execution must be atomic where supported. Otherwise, use version fencing, conditional writes and reconciliation to prevent time-of-check/time-of-use violations.

Every rejection must preserve the originating obligation and return a machine-actionable verdict.

Unexpected disturbances may move the estate outside its desired operating region. In that case, only authorised containment, diagnosis and recovery transitions may proceed within the affected domain.

6. Three operational regimes
Regime A — Zero-shot prevention
Known forbidden transitions are rejected before consequential execution.

Examples:

Cross-class credential substitution.
Unauthorised expenditure.
Predictable storage exhaustion.
Invalid dependency construction.
Stale-state mutation.
Unverified settlement.
Regime B — One-shot recovery
Unexpected failures trigger immediate, bounded reconciliation and recovery.

The original objective survives:

Worker failure.
Provider failure.
Transport failure.
Session termination.
Process restart.
Deployment failure.
Execution paths may terminate. The originating obligation may not disappear.

Regime C — Continuous preventive improvement
Each established failure class must enter the following transaction:

CURE → PREVENT → TRANSLATE → GENERALISE → INDEPENDENTLY VERIFY → ENFORCE

The correction becomes estate capability rather than agent-specific knowledge.

A single discovery must be capable of protecting every equivalent execution surface.

7. Mandatory preventive barriers
B01 — Authority conservation
Invariant: No protected effect occurs outside currently valid authority.

Implement:

Short-lived, scoped capabilities.
Explicit effect classes.
Resource-specific permissions.
Policy revision binding.
Monotonic authority epochs.
Immediate revocation enforcement within the supported activation window.
Denial of direct credential access by untrusted workers.
All protected effects must traverse trusted enforcement points.

A successful policy evaluation without actual enforcement is insufficient.

Falsifiers: forged identity, expired capability, direct API bypass, revoked authority, stale lease, scope expansion and replay.

B02 — Economic conservation
Invariant: No operation creates financial liability outside an authorised resource lane.

Every provider credential shall carry an authoritative billing classification.

Minimum classification:

MONTHLY_SUBSCRIPTION
API_CREDIT
FREE_ALLOWANCE
FOUNDER_AUTHORISED_EXCEPTION
Provider eligibility must include:

Billing class.
Subscription state.
Remaining quota.
Remaining allocated budget.
Permitted workloads.
Capability requirements.
Current provider health.
Authorised fallback relationships.
The budget ledger must reserve maximum permitted exposure before dispatch.

Concurrent reservations must not exceed available allocation.

Reservations shall transition through RESERVED, COMMITTED, RELEASED or RECONCILIATION_REQUIRED.

Uncertain provider charges must remain reserved until reconciled.

Provider fallback shall never silently cross billing classes.

Current founder-directed routing:

DeepSeek API credit: DSH Web reserve recovery.
Claude monthly subscription: governed engineering execution.
Exhausted Z.ai GLM allowance: excluded until eligibility is independently restored.
These are policy data, not permanently hard-coded provider assumptions.

Falsifiers: concurrent overspend, exhausted quota, invalid fallback, credential substitution, duplicated request and unknown billing status.

B03 — Resource conservation
Invariant: Managed workloads cannot consume capacity reserved for critical estate operations.

Implement:

Hard storage quotas where supported.
Per-subsystem storage allocation.
Bounded logs and caches.
Bounded context and token consumption.
Concurrency ceilings.
Memory and CPU limits.
Admission-time capacity reservations.
Reserved emergency operating capacity.
Deterministic eviction of explicitly disposable resources.
Backpressure before resource exhaustion.
Proposed initial storage policy:

70%: early pressure detection.
80%: controlled shedding of disposable data.
90%: deny nonessential storage-growing operations.
Emergency reserve: inaccessible to ordinary workloads.
These percentages are configurable initial thresholds, not a substitute for hard quotas. Reserve sizing must reflect maximum burst consumption, reclamation latency and filesystem overhead.

No automated deletion of authoritative state, evidence, credentials or user data.

Production infrastructure must not depend on Mac storage availability.

Falsifiers: ENOSPC, rapid concurrent writes, runaway logs, cache expansion, exhausted memory and failed eviction.

B04 — Topological independence
Invariant: A recovery function must remain reachable under the defined failure classes of the system it recovers.

Maintain an authoritative dependency graph containing:

Services.
Hosts.
Network routes.
Identity providers.
Credential stores.
DNS and TLS dependencies.
Storage dependencies.
Provider dependencies.
Administrative and recovery surfaces.
Shared physical and logical failure domains.
A critical recovery path must not depend exclusively on the component it is intended to recover.

Validate dependency reachability at source admission and against deployed topology.

Test actual runtime independence through fault injection.

The Mac is a replaceable access terminal, not an operational dependency.

Falsifiers: kill pennyd, disable the primary router, disconnect the Mac, revoke primary credentials, break DNS/TLS and remove the primary inference route.

B05 — Instruction custody
Invariant: Every accepted instruction retains an immutable identity and durable obligation until verified settlement or authorised termination.

Mandatory fields:

instruction_id
principal_id
original_objective
objective_hash
accepted_at
authority_scope
parent_instruction_id
current_state
current_epoch
policy_revision
active_attempt_id
evidence_references
next_action
accountable_machine_owner
progress_deadline
Workers may create subordinate obligations within scope.

They may not overwrite the original objective or declare it irrelevant.

Transfers and delegation must preserve identity, causation and accountability.

Falsifiers: process crash, duplicate delivery, worker replacement, session loss, orphaned subtasks and unauthorised termination.

B06 — Progress and liveness
Invariant: No unresolved instruction may remain without an accountable owner, next transition and bounded progress deadline.

Implement:

Durable deadlines.
Event-driven wakeups.
Execution lease expiry.
Automatic verifier dispatch.
Recovery strategy selection.
Reconciliation of uncertain effects.
Failure-class retry limits.
Fenced reassignment.
Escalation for genuine authority or external resource constraints.
Reuse the existing 10-minute stagnation doctrine as an outer progress watchdog, not as permission to wait ten minutes before reacting.

Recoverable faults shall trigger recovery immediately.

The existing 30-second emergency recovery objective must be measured on supported, reachable operational surfaces.

If no authorised path currently exists:

Preserve the obligation.
Record the precise unavailable prerequisite.
Assign machine ownership.
Subscribe to relevant recovery events.
Continue independent authorised work.
Do not fabricate progress or violate safety to satisfy liveness.

Falsifiers: dead worker, absent verifier, permanent provider outage, lost acknowledgement, stale recovery signal and exhausted retry budget.

B07 — Context validity
Invariant: No consequential operation may execute against a materially invalidated decision context.

Every consequential plan must bind:

Relevant source revision.
Policy revision.
Resource versions.
Authority epoch.
Dependency versions where applicable.
Relevant evidence and freshness requirements.
Immediately before effect execution, validate material dependencies.

When context changes:

Invalidate affected assumptions.
Preserve unaffected work.
Replan only the invalidated execution segment.
Re-admit the revised operation.
Do not discard entire sessions because one assumption changed.

Falsifiers: stale repository base, changed provider eligibility, concurrent resource mutation, revoked permission and contradictory documentation.

B08 — Operational truth
Invariant: No instruction settles without independent evidence establishing its actual acceptance predicate.

Distinguish:

Generated.
Tested.
Submitted.
Merged.
Deployed.
Operationally verified.
Settled.
These are separate states.

A cryptographically valid receipt is evidence of an authenticated assertion. Its truth depends on the verification authority, observation method and predicate.

The verifier must observe the actual target rather than a proxy representing an intermediate artifact.

The verification contract must bind:

Instruction and attempt identity.
Execution epoch.
Objective and acceptance-predicate hashes.
Exact target identity.
Deployed artifact identity.
Observation timestamp.
Evidence expiry.
Observation method.
Effect evidence.
Verifier identity.
Policy revision.
Signature.
For non-deployment objectives, bind the relevant external object or transaction rather than requiring a meaningless commit SHA.

Falsifiers: proxy-green result, forged receipt, valid signature over false evidence, stale deployment, incorrect target and replayed proof.

B09 — Recurrence suppression
Invariant: A certified-prevented failure class must not be knowingly readmitted through an equivalent operational surface.

Create canonical failure fingerprints from:

Causal failure class.
Violated invariant.
Relevant resource and actor class.
Candidate identity.
Policy revision.
Material environmental state.
Do not fingerprint merely by error message.

A materially unchanged failure must not generate endless retries.

Changed causal conditions may permit re-admission.

The prevention mechanism must undergo independent counterexample testing before being promoted into mandatory fleet policy.

Falsifiers: renamed error, different provider with equivalent failure, unchanged retry loop and overbroad suppression of valid operations.

B10 — Governance integrity
Invariant: No untrusted worker may unilaterally alter the mechanism that constrains, observes or certifies its own effects.

Separate:

Policy authorship.
Policy authorisation.
Policy enforcement.
Verification authority.
Deployment authority.
Audit custody.
Workers may propose patches and supply test evidence.

Protected enforcement changes require existing trusted authorisation and independent validation.

Policy bundles and release artifacts must be signed, versioned and protected against rollback replay.

Emergency recovery must preserve the minimum safety floor.

Falsifiers: self-approved policy weakening, disabled gate, modified acceptance test, forged policy revision, compromised worker credential and direct enforcement bypass.

8. Canonical obligation lifecycle
Primary lifecycle:

ACCEPTED → ADMITTED → READY → EXECUTING → VERIFYING → EFFECT_VERIFIED → SETTLED

Recovery lifecycle:

RECOVERY_REQUIRED → RECONCILING → REPLANNING → RE_ADMISSION → READY

Exceptional states:

WAITING_FOR_AUTHORITY
WAITING_FOR_EXTERNAL_PREREQUISITE
AUTHORISED_TERMINATION
Exceptional states must retain explicit ownership, deadline and wakeup conditions.

BLIND is an observation verdict, not a successful terminal state.

Every transition must produce a persisted event containing:

Previous and next state.
Instruction and attempt IDs.
Actor and authority.
Expected state version.
New state version.
Timestamp.
Causation ID.
Policy revision.
Evidence reference.
Machine-readable reason.
Use atomic state transitions and fencing.

Exactly-once logical effects shall be claimed only where external idempotency or reconciliation semantics support the guarantee.

9. Admission contract
Before consuming meaningful inference or execution resources, the estate shall evaluate:

Is the objective durably recorded?
Is authority valid?
Is the execution scope permitted?
Is an eligible provider available?
Is the billing class correct?
Can maximum authorised expenditure be reserved?
Is sufficient operational capacity available?
Is relevant context current?
Does the proposed path preserve topology constraints?
Is a credible verification and recovery path available?
Permitted admission verdicts:

ALLOW
DENY
DEFER
RECONCILE
BLIND
Every non-ALLOW verdict must contain:

Violated predicate.
Causal evidence.
Recovery classification.
Responsible machine owner.
Next permitted action.
Deadline or event subscription.
No free-text refusal shall function as an operational control verdict.

10. Complete mediation and enforcement placement
Enforce each invariant at the lowest authoritative boundary capable of controlling the effect.

Boundary

Required enforcement

Instruction ingress

Identity, custody and authority

Provider gateway

Eligibility, billing and reservation

Execution scheduler

Capability, resource capacity and leases

Filesystem/container

Resource ceilings and isolation

Network gateway

Permitted destinations and effect routes

GitHub submission

Scope, source identity and hermetic preflight

Greenlane

Candidate integrity and promotion

Deployment boundary

Artifact identity and topology validity

Runtime effect door

Current authority and transition validity

Settlement boundary

Independent operational proof

OPA supplies policy decisions.

Existing trusted enforcement points must apply those decisions.

Infrastructure-native mechanisms must enforce resource limits and atomic reservations.

OPAL, if approved through fit testing, distributes policy and data revisions. OPA signed bundles remain the upstream fallback.

Agents must have no route around the protected effect doors.

11. Immediate correction to PR #8591
Verified affected files:

sovereign/engine/activities.py
sovereign/engine/workflow.py
sovereign/engine/worker.py
sovereign/engine/test_instruction_id.py
Preserve the merged independent Ed25519 verification mechanism.

Extend the implementation to address:

11.1 Indefinite verification waiting
The inspected _retain_instruction() implementation waits for an external proposal without an explicit verification deadline.

Replace unmanaged waiting with:

Durable verifier work dispatch.
Explicit verification deadlines.
Automatic retry or reassignment.
Bounded reconciliation.
Event-driven progress monitoring.
No model inference should be consumed merely waiting for evidence.

11.2 Conditional protection
Audit all workflow entry points.

Prevent consequential work from bypassing mandatory custody and settlement because instruction_id is absent or a legacy workflow is unpatched.

Preserve Temporal replay compatibility.

Use explicit migration or supported workflow versioning rather than altering historical execution semantics unsafely.

11.3 Verification semantics
Bind receipts to effect-specific acceptance predicates and independently observed targets.

Separate evidence of successful effect from evidence authorising safe retry.

A worker exit, valid signature or nonempty effect reference cannot independently prove the objective was achieved.

11.4 Signal integrity
Audit:

Lost or prematurely delivered verification signals.
Invalid proposal flooding.
Duplicate receipts.
Stale attempts.
Worker-controlled stop or refill paths.
Verifier key configuration and rotation.
Legacy workflow bypass.
Workflow restart and replay behaviour.
These are mandatory falsification targets, not claims that every listed vulnerability currently exists.

11.5 Integration acceptance
Exercise the actual Temporal workflow against a test server and subsequently deployed cloud infrastructure.

Static assertions against source strings alone do not constitute behavioural proof.

12. Integration with existing estate work
Existing work

Responsibility

IDP #7452

OPA/OPAL and decision assurance

IDP #7794

Universal admission

IDP #8415

Durable instruction-to-effect lifecycle

IDP #8455

Hermetic deployment and Greenlane control

IDP #7940

Preventive failure suppression

IDP #7443

Proof-bearing completion

IDP PR #8591

Temporal independent settlement

Do not create duplicate ownership domains.

Reconcile current source, protected paths, deployment status and outstanding claims before modification.

The existing parent obligations remain open until independently verified.

GitHub issues are work-tracking records, not substitutes for authenticated operational authority.

13. Formal assurance
Extend the estate’s existing formal assurance work using TLA+ and executable property tests.

Mandatory safety properties:

Authority conservation.
Budget conservation.
Resource reservation conservation.
No duplicate logical settlement.
No settlement without valid external evidence.
No silent instruction loss.
No unauthorised policy weakening.
No stale execution lease producing a protected effect.
Mandatory conditional liveness properties:

Admitted work eventually progresses when authorised resources and required external services remain available.
Recoverable failures eventually enter a permitted recovery path.
Unavailable prerequisites cannot silently erase obligations.
Unaffected operational domains continue progressing.
Recovery does not cause unbounded repeated expenditure.
Model:

Concurrent workers.
Duplicate delivery.
Network partition.
Lost acknowledgements.
Delayed verification.
Stale authority epochs.
Resource exhaustion.
Worker crashes.
Policy revision changes.
Permanent external failure.
Record all environmental and fairness assumptions.

Do not report unconditional liveness where the environment cannot support it.

14. Production acceptance matrix
Test

Required outcome

Inject exhausted monthly credential into API lane

Rejected before provider invocation

Concurrent requests exceed allocated budget

Excess reservations rejected atomically

Kill pennyd

Independent recovery surface remains reachable

Disconnect Mac

Cloud execution and authoritative state continue

Fill managed storage to quota

Workload contained; critical reserve preserved

Kill worker mid-effect

Obligation retained; effect reconciled before retry

Disable verifier

No false settlement; bounded recovery activates

Submit stale signed receipt

Rejected

Provide green CI for wrong deployment

Operational predicate remains unsatisfied

Change base revision before mutation

Re-admission or conditional write rejection

Repeat unchanged causal failure

Retry suppressed without losing objective

Worker modifies its own policy

Protected mutation denied

Restore prerequisite

Eligible obligation resumes automatically

Execute valid authorised workload

Completes without unnecessary denial

Both negative and positive controls are mandatory.

A mechanism that prevents every operation is not an acceptable safety solution.

15. Delivery sequence
Phase A — Establish actual enforcement coverage
Discover and reconcile:

Protected effect doors.
Direct-access bypass paths.
Runtime dependency topology.
Active provider lanes.
Budget authority.
Deployed policy revisions.
Verifier availability.
Existing recovery machinery.
Produce machine-readable coverage evidence using existing registries.

Do not substitute documentation for deployed-state discovery.

Phase B — Restore and protect operational oxygen
Prioritise:

Economic isolation.
Independent recovery connectivity.
Storage/resource conservation.
Durable instruction progress.
Independent runtime settlement.
Execute through authorised cloud lanes.

Contain affected domains without freezing unrelated productive work.

Phase C — First production vertical slice
Complete one real, low-risk, preauthorised instruction through:

Chronos → FLOW → Admission → Legion → Effect → Optimus → KARMA → Settlement

Repeat with:

Worker termination.
Provider failure.
Verifier interruption.
Duplicate delivery.
No routine founder assistance.

Phase D — Fleet inheritance
Extend proven preventive predicates across all equivalent effect doors.

Integrate failure-class discovery and prevention into KARMA.

Measure positive throughput alongside denial effectiveness.

Retire superseded mechanisms only after independently verified replacement.

16. Economic measurement
The primary economic objective is independently verified operational value relative to total operational cost.

Record separately:

Actual provider charges.
Subscription quota consumption.
Infrastructure cost.
Inference tokens.
CI consumption.
Rework.
Failed attempts.
Founder interventions.
Founder attention time.
Settled operational obligations.
Time to verified effect.
Do not invent monetary valuations for unmeasured founder attention.

Compare equivalent workload cohorts before and after enforcement.

Required operational targets:

Zero known forbidden transitions admitted.
Zero unauthorised financial liability.
Zero silent instruction losses.
Zero self-certified settlements.
Zero unmanaged stagnation.
Zero recurrence of certified-prevented failure classes within their demonstrated enforcement scope.
Zero routine machine-owned work returned to the founder.
These are engineering targets, not statements of current performance.

17. Definition of done
Every barrier must produce three converging classes of evidence:

Proof 1 — Structural

The enforcement mechanism exists at the authoritative operational boundary, and its bypass surfaces have been examined.

Proof 2 — Behavioural

Independent tests demonstrate that forbidden transitions are rejected and legitimate transitions remain possible.

Proof 3 — Operational

The deployed mechanism demonstrates the same properties under real or controlled production-equivalent fault injection.

Mandatory receipts:

Exact source and deployed artifact identities.
Active policy revision.
Enforcement-point identity.
Test and fault-injection evidence.
Independent external observations.
Resource and cost measurements.
Instruction settlement records.
Remaining limitations and environmental assumptions.
No PR, merge, passing CI run or agent report alone satisfies this contract.

18. Final governing principle
Intelligence is allocated to discovering opportunities, producing value and identifying previously unknown failure classes.

Deterministic infrastructure is allocated to enforcing what is already known.

Every verified discovery must reduce future operational friction.

Every recovered failure should reduce the probability or reachability of its recurrence.

Every instruction remains an estate obligation until independently verified resolution or authorised termination.

The estate must progressively become less dependent on intelligence for routine survival and more capable of deploying intelligence towards productive work.

Get better at getting better.



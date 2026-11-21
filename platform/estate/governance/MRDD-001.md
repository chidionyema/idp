# Meridian Recursive Decision Dynamics (MRDD-001)

**Status:** mathematical research prototype; no live estate interaction, credentials, authority or rollout. 2026-11-21.

## 1. The object to be modelled

The object is **not** a person's intelligence score or a generic prompt template. It is a *reusable correction-generating decision process*: given a problem, it (a) examines why a proposed intervention is not executable or not high leverage, (b) changes the causal level of analysis, (c) selects the cheapest discriminating experiment or safe action, (d) observes an independent effect, and (e) updates the decision rule.

The founder's observed examples (as hypotheses for modelling, not validated population estimates) repeatedly replace local fixes with restoration of broader capacity, reject plans depending on unavailable workers, and demand that each explanation induce an observable next action. The original user prompt, lossless spelling-corrected transcription, interpretation, decision alternatives, empirical receipt and later correction must remain different fields. The corrected text is not permission to overwrite the original.

## 2. Two coupled systems

Operational world time is `t`. Policy/reasoning revision is `k`.

- Hidden state `s_t = (D_t, C_t, Q_t, G_t, A_t, R_t, theta_t)`: durable obligation set, genuinely available capacities, quotas/resources, dependency hypergraph, externally authorised effects, retained evidence/receipts, unknown failure causes.
- `y_t` is an observation from an independent read (API state, deploy receipt, current quota, signed claim), not a model's self-report.
- `b_t(s,theta) = P(s_t=s,theta | y_0:t,a_0:t-1)` is a belief distribution, with explicit UNKNOWN where a likelihood is not supportable.
- `pi_k` is the current intervention policy. Its parameters may contain founder preference features and an empirical transition model, which are **distinct** sources of knowledge.

Real world transition:

    s_(t+1) ~ T_theta(. | s_t, a_t)
    y_(t+1) ~ O(. | s_(t+1), a_t)
    b_(t+1) = BayesUpdate(b_t, a_t, y_(t+1))

Policy-learning transition, only after independent evidence has been retained:

    pi_(k+1) = AuditAndUpdate(pi_k, decision, forecast, observation, correction)

`AuditAndUpdate` must be a candidate policy proposal; actual promotion requires holdout benefit, safety checks, and existing authority.

## 3. Recursive reasoning operator

A problem representation `P^(0)` names the visible failure. Recursion acts on the **decision mechanism**, not merely on the subject:

    P^(j+1) = Lift(P^j, dependencies(choose_action(P^j)), counterexample(P^j))

For example:

    worker failure → worker restart → worker-restart depends on missing worker
    → restore independent execution authority → validate deterministic execution
    → capture the surviving AI Studio output → verify durable receipt

The recursive *search* is bounded by (i) remaining time/quota, (ii) known causal depth, and (iii) additional expected value of information. It **terminates in an independent world observation**, not another conceptual layer.

Thus the loop has two directions:

    Kether (objective/constraints) → action selection → Malkuth (world effect)
    Malkuth (observed result) → posterior/model correction → Kether (revised policy)

A loop that leaves the policy and world unchanged is stagnation, not learning.

## 4. Dependencies and asymmetric capacity

Use an AND/OR dependency hypergraph, not a simple list of blocked issues. A capability `v` is feasible only if at least one *authorised* route `p` has all prerequisites active:

    feasible(v; s) = OR_(p in routes(v)) AND_(u in prerequisites(p)) active(u;s)

Let `F(s)` be the set of *feasible* capabilities, and `V(s)` the subset with a current independent operational proof. These sets must never be conflated.

For intervention `a`, expected capacity leverage is the weight of additional feasible paths **conditional on their actual other preconditions**, adjusted by an estimated likelihood of subsequently verifying them:

    L(a | b) = E_theta [sum_v w_v 1{v in F(s_after(a)) \ F(s_before)} | b]

This is not realised yield. Realised yield counts `V` under independent proof. A repair with many declared downstream dependants but no credentials, no release path or no independent evidence is often worth zero in practice.

The finite example in `example_config.json` activates `capture → custody → replay → recovery` after repairing intake **only if** all other stated prerequisites are available. Removing GitHub authorisation collapses most of the effect. `free_web_delivery` remains blocked until `free_web_auth` is present. Those conditions are simulated assumptions, *not* a finding about live Meridian infrastructure.

## 5. Safe sequential choice under uncertainty

We treat diagnosis, repair and deferral as different actions. The mathematically natural objective is a constrained Bayes-adaptive partially observable control problem:

    V_t(b) = max_(a in Safe(b)) [ -cost(a)
          + sum_y P(y | b,a) { observed_reward(b,a,y) + gamma V_(t+1)(Update(b,a,y)) } ]

The safety set `Safe` is determined by externally validated scope, authority, actual budget, custody, and effect policies. A model's self-declared `VERIFIED` value is not a signature and cannot open a production door.

For short, bounded decisions, the exact *net expected value of sample information* from a probe `e` is:

    NEVSI(e) = sum_y P(y|e) max_a E[U(a,theta) | y,e]
               - max_a E[U(a,theta)] - cost(e)

Do not add a second information bonus to an exact belief-state Bellman objective: it already values useful information through future decisions.

**Synthetic calculation** (arbitrary value units; not measured case probabilities):

- Root-cause priors: missing receiver route .50, CORS preflight .30, ingest secret .20.
- Correctly targeted repair yields 10 units; wrong repair yields no benefit; costs 3, 2, 1 units respectively.
- Direct best repair: fix receiver; expected net `0.5*10 - 3 = 2.000`.
- A hypothetical 3-way diagnostic is right 90% of the time and costs 0.300 units.
- Exact Bayesian calculation: repair-after-probe expected net (after probe cost) `6.445`.
- **NEVSI = 6.445 - 2.000 = +4.445** units, making the diagnostic decisively better in this hypothetical case.
- If the diagnostic is non-informative and costly, the policy correctly rejects the probe. If all repairs have negative expected net value, it can abstain rather than force a repair.

In real Meridian, priors, actual diagnostic availability, test reliability, effort, risk, downstream dependencies and quota cost must come from evidence—not these placeholder numbers.

## 6. Self-recovery as viability, not magic

Let `K` be the set of permitted states where accepted obligations remain durably recoverable, permissions are not violated, and spending remains bounded. The *viability kernel* contains states from which some admissible policy can keep these constraints true under a specified bounded fault model.

With **zero AI workers** the machine cannot guarantee AI-generated code or inference. It *can*, provided independent deterministic infrastructure survives, retain obligation custody, examine state, reject stale leases, probe for returning capacity and resume when capacity reappears. Claims of unconditional liveness with no compute, no network and no surviving store are impossible.

Safety properties for an accepted obligation `i`:

    G(accepted(i) -> (durable(i) W settled(i)))
    G(settled(i) -> independently_verified_effect(i))
    G(execute(a) -> valid_authority(a) AND within_budget(a))

Here `G` means always and `W` is **weak until**: if the obligation never settles it must remain durably open, not vanish.

Conditional liveness requires explicit assumptions: an eventually available eligible executor, valid authority, a reachable independent store, feasible work, and fair scheduling. Without those assumptions, liveness cannot be proven.

The included in-memory toy automaton tests only the safety assertion that losing an AI worker does not delete a tracked obligation. It does **not** test a live replicated ledger or cross-host persistence.

## 7. Mathematical model of founder corrections

Collect comparisons `D = {(context_j, preferred_j, rejected_j, rationale_j, outcome_j)}` from the founder. Preserve verbatim source text, a separately corrected transcription, provenance and revision history.

One falsifiable preference model is:

    P(preferred=a | a,b,context,w) = sigmoid(w^T (phi(context,a)-phi(context,b)))

`phi` should measure, rather than label, features such as:

- downstream independent *feasible* capacity recovered
- cost/remaining quota and time-to-first-verified-effect
- depth of unverified dependency chain / common-cause exposure
- reversibility, verified authority and obligation survival
- expected information gain and failure recurrence risk
- difference between model claims and actual world observations

This learns **which choices resemble founder corrections**. It does *not* establish their real-world optimality. To test effectiveness, maintain separate held-out incidents with externally graded outcomes. Pairwise preference accuracy and operational improvement are different metrics.

The model must be allowed to challenge a founder preference if independent counterevidence accumulates: imitation is not intelligence.

## 8. Promotion criteria

Compare baseline policy to candidate policy on a prespecified holdout set (simulated failures first; safe shadow and controlled canaries later). Measure:

- time and total cost to first independently verified effect
- recovered feasible/operational capabilities per approved unit of spend
- recurrence and repeated failed-action rate
- calibration of success probabilities and falsifiable hypotheses
- founder intervention frequency and minutes
- zero-worker custody/continuity survival
- violation count for protected authority and financial limits (must remain zero)

Require a statistically supported improvement on the primary metric, no safety regression, and multiple independent failure classes before promotion. A hand-curated preference dataset cannot certify generalisation.

## 9. Real data Meridian must now measure

1. Inventory actually accessible AI Studio output and source hashes, *without spending another inference call*.
2. Observe live intake endpoint methods/OPTIONS, CORS headers, authentication state and GitHub commit readback. Mark each observation with timestamp and source.
3. Independently read the GitHub branch/ref, current CI/execution permissions and receipt validity.
4. For each candidate repair, measure real costs and causal probabilities from bounded tests.
5. Compare the proposed action with all competing safe actions, including defer and read-only probe.
6. Recover an interrupted instruction after fresh process/session restart and obtain external proof.
7. Log the prediction error and update only the proposed decision policy; promote after a held-out test.

**Falsifier:** if after two audited cycles the candidate method does not lower time/cost to verified effect or reduce repeated unsupported choices, the proposed decision method has not established improvement—even if every agent uses its vocabulary.

## Run

```sh
python3 recovery_model.py example_config.json > result.json
python3 -m unittest discover -v -s . -p 'test_*.py'
```

No network calls; no AI prompts; no account access. To operationalise, connect *real receipts* and model-estimated likelihoods to existing authorised gates; do not elevate this prototype to a control authority.
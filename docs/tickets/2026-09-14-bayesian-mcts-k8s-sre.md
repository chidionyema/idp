# Essay: Bayesian reasoning + MCTS for Kubernetes SRE root-cause analysis

**Status:** open
**Opened:** 2026-09-14
**Laws:** LAW 2 (proof before action), LAW 9 (stay on the job), LAW 11 (never decide alone what you cannot undo alone), THE EMPIRICAL PROOF RULE
**Source:** deferred essay #2 from the founder (2026-09-14 reasoning-gateway conversation). One of three essays that were on the same day; the gateway ticket now ranks #1, this is #2 and `2026-09-14-mcts-mcp-server.md` is #3.
**Essays destination:** `docs/essays/2026-09-14-bayesian-mcts-k8s-sre.md` (new folder; the ticket is the ledger row, the essay is the artifact).
**Binding:** none yet. The essay has to pick the form before any gate is added.

## Why this essay exists

The Reasoning Gateway ticket proved that step-level supervision, compute-budgeting and
contract gating remove the three named reasoning failures. The gateway is at the
*agent's* reasoning loop. This essay is about what sits underneath it for one specific
class of problem: a Kubernetes outage where a chain of recent events has cascaded into
an observable fault and the SRE has to find the root cause under time pressure.

The conventional approach is log-grep + KQL/Splunk queries driven by an LLM. Measured,
it has two structural weaknesses: it does not track uncertainty over its own hypotheses
(Bayesian), and it does not plan which probe to run next against the expected
information gain (MCTS). Both are mature techniques; the essay asks what their
composition looks like against an estate that already has Temporal, the Sovereign Bus
and the catalogue as inputs.

## What the essay must answer (founder's scope, three questions)

1. **What is the prior over fault classes, and where does it come from?** The estate
   catalogue, the Flux twin, the Langfuse trace store, and the Aevum evidence ledger
   each carry signal. The essay has to name a prior and a posterior update rule, not
   ask the LLM to invent one.
2. **What is the search algorithm — ReST-MCTS, vanilla MCTS, or a Bayesian-network
   variant — and which budget per branch?** This is the bridge to the Gateway's
   D2 budget deliverable. The essay picks one and gives the pseudo-code, not the
   product card.
3. **What concrete K8s incident does this beat on the first run, and what does
   "beat" mean?** Without a measured counter-example, the essay is speculation.
   The empirical proof rule binds: a recorded run on a recorded incident, with the
   time-to-root-cause and the false-positive rate, both as numbers.

## What already exists, so the essay does not reinvent

- Reasoning Gateway ticket (`docs/tickets/2026-09-14-reasoning-gateway.md`) — D1
  Process Reward Model, D2 Compute Budget, D3 Contract; the essay hands its MCTS
  branch budget upstream to the Gateway instead of inventing one.
- Estate twin (`bin/estate-twin-runtime`): the 15-minute cluster-state receipt that
  gives MCTS its state vector (workload states, flux rows, recent events).
- Flux `--once --code` twin output, the catalogue `catalog/estate.db`, the Aevum
  evidence chain and Langfuse traces — every input the essay might use already has a
  reader; no second store.
- Deterministic Verifier (`sovereign/verifier.py`) — the propose/verify/seal/admit
  shape is the right shell for a MCTS proposal, no re-implementation.
- Mediator model-routing from `AGENTS.md` `[routing] consensus` — the three voters
  (deepseek, minimax, gemini) and the cheap lane that the essay's branches should
  draw on.

## What the essay is NOT

- Not a product card. Not a vendor comparison.
- Not a reinforcement-learning policy. The estate has no environment to learn a
  policy against, and inventing one would be the failure mode.
- Not a request for a budget. The essay is bounded by the founder's existing
  approvals; it asks for exactly zero new services, agents, or spend.

## Definition of Done — in commands

1. **`docs/essays/2026-09-14-bayesian-mcts-k8s-sre.md` exists**, ≤ 4,000 words, and
   answers the three questions with primary references (papers or code), not product
   pages.
2. **`bin/` adds no new binary for the essay itself** — the essay points at the
   three estate mechanisms it would compose (gateway, twin, verifier), not at new
   scripts.
3. **One recorded incident is named** and the time-to-root-cause + false-positive
   rate for the essay's algorithm is given as a number, not a sentence.
4. **The essay is referenced from the Gateway ticket's D2 row** so the two stay
   bound: the gateway owns the budget mechanic, this essay owns the algorithm that
   consumes it.

## Open questions for the essay

- Which K8s incident is the empirical proof? The `rca/` directory in the catalogue
  has past tickets; one needs to be the test case.
- Is the search tree per-incident (vanilla MCTS) or shared-across-incidents (a
  Bayesian-network prior that warms up)?
- Does the SRE's narrative stay in the loop (human-in-the-loop at every branch) or
  only at the verdict (autonomous with veto)?

## Risks

- The essay could read as research when the founder asked for product. A scope
  reminder, not a hedge: the essay has to end on "what lands this quarter," not
  "what might be possible next year."
- Bayesian reasoning over a small, biased catalogue can be more confident than
  warranted. The essay has to name the failure mode (overconfident posterior) and
  the calibration check.

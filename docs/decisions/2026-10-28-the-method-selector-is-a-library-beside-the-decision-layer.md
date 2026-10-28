# The method selector is a library beside the decision layer, not a second one

**Date:** 2026-10-28
**Status:** accepted (SF-1 landed; SF-2 onward not started)
**Claim:** [idp#7342](https://github.com/chidionyema/idp/issues/7342) (lane `lane/method-selector`)
**Spec:** the founder's operational contract, `~/Downloads/OPERATIONAL_SPEC.md` v0.1 (the estate adaptive problem-solving repertoire)
**Related:** [idp#7344](https://github.com/chidionyema/idp/issues/7344) (the context substrate that will feed this library typed evidence) · [2026-10-27-the-estate-context-broker-is-the-only-door.md](2026-10-27-the-estate-context-broker-is-the-only-door.md)
**Evidence:** `packages/method_selector/tests/` · `features/assurance/method-selector.feature` · `bin/method-select`

## Context

The estate already chooses between ways of attacking a problem: `bin/estate-diagnose` and the
`hypotheses.race` intent run a Bayesian comparison of hypotheses; `bin/tlc-check` explores a
model; `bin/idp-verify` re-executes a claim; `nsvee/engine.py` verifies. Each of those is a
*tool*, and a tool only runs when something decides to run it.

The founder's contract asks for one more thing, and asks for it carefully: given an
evidence-backed problem fingerprint, recommend a bounded, context-appropriate method and its
proof obligation, or abstain; beat a fixed Bayesian-first baseline on held-out representative
cases at matched cost and risk. It also states, as hard invariants, that there must be no new
orchestration, router, memory, verification or telemetry service.

So the question this record answers is narrow: **where does the selector live, and what is it
forbidden from doing?**

## Options considered

1. **A new service (a "method-solver" deployment).** Rejected: it would be a second
   orchestrator and a second router, and the contract forbids both. It would also need its
   own store, its own health surface and its own place in the request path - all of which the
   estate already has, elsewhere.
2. **Fold the selector into `sovereign/policy.py` or the engine.** Rejected: policy decides
   *whether an action is allowed*; a selector decides *which approach to try*. Merging them
   would make the policy engine's blast radius include method choice, and would put a
   research-shaped component (a catalogue, a ranking heuristic, an evaluation harness) into
   the path of every governed action.
3. **A pure library beside the decision layer (chosen).** The library is a function from a
   validated request to a recommendation. The estate's existing decision layer calls it; the
   existing executor runs what it approves; the existing verifier judges the result.

## Decision

The method selector is a **pure, deterministic library** at `packages/method_selector`, with
one entry point, `select(request) -> MethodSelection`.

- It holds no authority. Every selection names its `decider` (`method_selector.deterministic.v1`),
  the caller's `authority`, and its `policy_decision`. A recommendation is not an
  authorization; the `RECOMMENDATION_ONLY` reason code says so on every selection.
- It executes nothing, writes nothing, opens no socket and holds no credential. It cannot.
- It is deterministic: the same request produces the same fingerprint, the same method, the
  same ranking and the same trace id. That is what makes it safe to run in shadow and what
  makes the spec's idempotency clause true rather than aspirational.
- It abstains instead of guessing. Missing or stale evidence yields `ABSTAIN` with a bounded,
  governed probe request (or `REFUSE` when only a human's authorization or a downed
  dependency stands in the way). A missing prerequisite is never invented.
- It is honest about what it knows. Every catalogue entry is `evaluation_status = UNVERIFIED`
  until the fixture suite and the independent evaluator land (the spec's SF-3). The selector
  may recommend any of them and may call none of them proven.

### What it sits next to, and what it must never become

| Concern | Owner | The selector's relationship |
|---|---|---|
| Bayesian method choice / hypothesis racing | `bin/estate-diagnose`, `hypotheses.race` | consumes the same evidence; does not re-implement posteriors |
| Policy and authorisation | `sovereign/policy.py`, the executor | is called *by* the decision layer; never grants authority |
| Verification | `nsvee/engine.py`, Aevum | names the verifier a method's output would need; never verifies |
| Memory of outcomes | unified memory, the estate graph | writes nothing; receives `SelectionOutcome` in a later slice |
| Typed evidence about a problem | the context substrate (#7344) | will be fed `estate_context_resolve_v1` sources; builds no retrieval of its own |
| Telemetry / the event spine | the estate's own spine | emits nothing of its own |

### The catalogue

SF-1 ships 28 methods across the spec's families (regression, incident, uncertainty, formal,
optimisation, performance, architecture, strategy, novel, adaptive). Each entry carries its
references, its problem kinds, its prerequisites, its anti-patterns, its cost profile, its
risk, its expected evidence, its stop and switch conditions, and the independent verifier that
would judge its output. The catalogue is data, not behaviour: the selector reads it, and
nothing else in the estate does.

## Consequences

- **Accepted**: a deterministic, testable, dependency-free recommendation path that any agent
  can call, and that no agent can use to bypass the executor.
- **Accepted**: the library is useless on its own. Until SF-2 wires it into the decision layer
  in shadow mode, it is a library with no callers - which is honest, because the spec's own
  plan puts the shadow wiring in the next slice.
- **Not accepted**: claiming the selector is *better* than the Bayesian-first baseline. That
  claim needs SF-3's fixtures and SF-4's canary, and until then the honest statement is
  "a deterministic baseline that has not been evaluated against the baseline it is meant to
  beat".
- **Watch**: the ranking weights (`W_EVIDENCE_FIT`, `W_COST_FIT`, `W_PRIORITY`) are a
  documented heuristic, not a learned model. If they are ever tuned against outcomes, that
  tuning is a new decision, with its own evaluation, not a quiet edit.

## The one-line version

The selector chooses; the executor runs; the verifier judges; the decision layer decides. Four
roles, one of them new, and none of them allowed to do another's job.

# Runbook: the method selector

**What this is.** `packages/method_selector` recommends a bounded problem-solving method for an
evidence-backed problem. It is a pure library: it reads typed data, it writes nothing, it opens
no socket, it holds no credential, and it executes no method. The estate's decision layer calls
it; the estate's executor runs what it approves; the estate's verifier judges the result.

**Status.** SF-1 only. The library exists, is tested and is deterministic. It has **no callers
yet**: the shadow wiring into the decision layer is SF-2, and it has not started. Nothing in the
estate depends on this package today, and nothing breaks if it is deleted.

## Call it

From the repository root:

```bash
bin/method-select request.json          # a selection on stdout
cat request.json | bin/method-select    # the same, from stdin
```

Exit status: `0` when a selection was produced (`ALLOW`, `REQUIRE_AUTHORIZATION`, `REASSESS`,
`ABSTAIN`), `2` when the request was refused, `1` when the request could not be read.

From Python (the way the decision layer will call it):

```python
from method_selector import select, select_safe

selection = select(payload)      # raises ContractError on a malformed request
selection = select_safe(payload)  # never raises: a malformed request becomes a REFUSE
```

## The request

```json
{
  "schema_version": "method_selector.request.v1",
  "problem_id": "prob-001",
  "kind": "regression",
  "source_revision": "0123456789abcdef0123456789abcdef01234567",
  "evidence_refs": [
    {"source_id": "src-1", "source_type": "git", "kind": "repo_history",
     "revision": "0123456789abcdef0123456789abcdef01234567",
     "observed_at": "2026-10-28T09:00:00Z", "freshness": "fresh", "verified": true}
  ],
  "risk_tier": "low",
  "budget": {"max_attempts": 12, "max_cost_usd": 1.0, "max_wall_seconds": 900, "exhausted": false},
  "uncertainty": 0.4,
  "authority": "maintainer",
  "deadline": "2026-10-29T00:00:00Z",
  "idempotency_key": "idem-001",
  "provenance": {"source": "issue-7342"},
  "contradictions": [],
  "unavailable_dependencies": [],
  "authorized_actions": []
}
```

`kind` is one of `regression, incident, formal, performance, architecture, optimisation,
uncertain, strategy, novel, adaptive`. `risk_tier` is `low, medium, high, critical`. `authority`
is `developer, maintainer, operator, sre, founder`. `freshness` is `fresh, stale, unknown`.

The evidence shape is deliberately the context substrate's source shape (source type, immutable
revision or observation time, freshness, verification), so `estate_context_resolve_v1` can feed
this library later without a second evidence vocabulary.

**What is refused, never guessed:** an unknown `schema_version`, an unknown `kind`, `risk_tier`
or `authority`, an out-of-range `uncertainty`, a non-integer or negative budget, a malformed
evidence ref, a missing required field.

## The selection

```json
{
  "schema_version": "method_selector.selection.v1",
  "method_id": "git_bisect",
  "method_version": "1.0.0",
  "rank": 1,
  "reason_codes": ["KIND_MATCH", "PREREQUISITES_SATISFIED",
                   "RANKED_BY_DOCUMENTED_HEURISTIC", "RECOMMENDATION_ONLY"],
  "prerequisites_checked": {"repository_history": "SATISFIED", "reproducible_check": "SATISFIED"},
  "expected_evidence": ["first_bad_commit", "bisect_log", "reproduction_check"],
  "estimated_cost": 0.02,
  "risk": "low",
  "decider": "method_selector.deterministic.v1",
  "policy_decision": "ALLOW",
  "trace_id": "ms-3f9c1b2d4e5a6f70",
  "fingerprint": "sha256:...",
  "fingerprint_version": "fp.v1",
  "authority": "maintainer",
  "abstained": false,
  "alternatives": [{"method_id": "delta_debugging", "eligible": false, "reason": "MISSING_PREREQUISITE"}]
}
```

### What each decision means

| Decision | Meaning | What happens next |
|---|---|---|
| `ALLOW` | a method is recommended and needs no extra authorisation | the decision layer may schedule it through the governed executor |
| `REQUIRE_AUTHORIZATION` | the method is experimental and the caller named it in `authorized_actions` | a human still has to authorise it; the library never does |
| `REASSESS` | the evidence contradicts the current approach | reassess first; the recommendation names what to try next |
| `ABSTAIN` | the estate does not know enough to choose | read `probe_request`: a bounded, governed request for evidence |
| `REFUSE` | nothing may be scheduled | exhausted budget, an unknown authority, or no eligible method at all |

### Reason codes you will see

`KIND_MATCH`, `PREREQUISITES_SATISFIED`, `RANKED_BY_DOCUMENTED_HEURISTIC`,
`RECOMMENDATION_ONLY`, `AUTHORIZATION_REQUIRED`, `CONTRADICTORY_OBSERVATIONS`,
`BUDGET_EXHAUSTED`, `NO_METHOD_SCHEDULED`, `NO_EVIDENCE`, `STALE_EVIDENCE`,
`MISSING_PREREQUISITE`, `ANTI_PATTERN`, `DEPENDENCY_UNAVAILABLE:<name>`, `RISK_ABOVE_TIER`,
`ATTEMPT_LIMIT`, `COST_LIMIT`, `NO_ELIGIBLE_METHOD`, `PROBE_REQUESTED`,
`CONTRACT_REJECTED`, `UNKNOWN_SCHEMA_VERSION`.

## Operational notes

- **Determinism.** The same request bytes produce the same fingerprint, method, ranking and
  trace id. `deadline` and `idempotency_key` are deliberately excluded from the fingerprint: a
  replay must select the same method, or the spec's idempotency clause is a lie.
- **A recommendation is not an authorization.** Every selection carries `RECOMMENDATION_ONLY`.
  The executor still decides, and the verifier still judges. No agent self-certifies its own
  outcome: an outcome with no independent verifier stays `UNVERIFIED`.
- **Cost is a plan, not a bill.** `estimated_cost` is the catalogue's per-attempt figure.
  `actual_cost` belongs to the outcome contract, filled in by whoever ran the method.
- **Nothing here is proven.** Every catalogue entry is `evaluation_status = UNVERIFIED` until
  the fixture suite and the independent evaluator land (SF-3). The selector may recommend any
  method and may call none of them proven. It does not claim to beat the Bayesian-first
  baseline; that claim needs SF-3 and SF-4.
- **Missing evidence is a fact.** The selector abstains and asks for a bounded probe; it never
  invents a prerequisite, and it never pretends a stale observation is a fresh one.

## Run the tests

```bash
python3 -m pytest -q packages/method_selector/tests
```

The suite binds `features/assurance/method-selector.feature` (the founder's BDD acceptance
clause) to the real library and adds the negative tests: every "I do not know" path is pinned as
a refusal, an abstention or an error.

## What is deliberately not here

- No service, no deployment, no scheduler, no store, no event, no credential.
- No execution: the executor already exists and keeps that job.
- No retrieval: the context broker already exists (#7344) and keeps that job.
- No shadow wiring: that is SF-2, and it lands in the decision layer, not here.

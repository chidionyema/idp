# 0030 — JevLayer: a unified confidence-and-decision service across the estate

Founder, 2026-09-21: "utilise jev priority ordering across all layers where relevant and applicable."

## The decision

The estate deploys **one JevLayer service** that every decision point — guards, agents, hooks,
consensus engine, verifier — calls instead of local best-guess logic or binary pass/fail.
No repository calls the Jev API directly; every call goes through the layer.

The layer is a single MCP tool (`mcp__jev__choice`, `mcp__jev__score`, `mcp__jev__noul`)
hosted in the estate MCP server (`mcp/`), backed by TypeSafe's `jev-1.13.0` model.
All other repositories (sovereign, hermes, verdict, prospector, agent-foundry, agent-workforce,
agent-guard, estate) are JevLayer **consumers only**.

---

## Why one layer, not scattered calls

The Jev capability map (`docs/jev-capability-map.md`) audited 50+ decision points across
8 repositories and found the same five patterns repeating:

| Pattern | Count | Current behaviour | JevLayer behaviour |
|---|---|---|---|
| Binary Allow/Deny | 18 | No confidence field | `{choice, confidence, probabilities}` |
| Hard threshold (0.74=fail, 0.75=pass) | 11 | Discrete bands | Continuous probability |
| Explicit best-guess ("the guess is only a guess") | 6 | Silent fallthrough | `{choice, confidence: 0.3, escalated: true}` |
| Fail-closed on unknown | 8 | `None → clean` | `{uncertain, confidence: 0.0}` |
| Expensive pre-check, full run then fail | 5 | 20–30s LLM call, then fail | 70–500ms noul gate first |

Scattering Jev calls into each repository creates:
- **Duplicated retry/fallback logic** (each repo reinvents the unavailable-Jev fallback)
- **No cross-decision audit trail** (a decision in sovereign's verifier cannot see that
  hermes' scheduler just refused the same operation)
- **Inconsistent confidence floors** (0.7 in one repo, 0.5 in another, 0.0 in a third)
- **API key sprawl** (JEV_API_KEY embedded in each repo's secrets)

A single layer solves all four.

---

## Architecture

```
Decision point (guard / agent / hook)
        │
        ▼
   JevLayer MCP tool
   ┌──────────────────────────────────────┐
   │  mcp__jev__choice(state, question,  │
   │                 options, confidence)  │
   │  mcp__jev__score(state, question,    │
   │                 levels)               │
   │  mcp__jev__noul(state, question,     │
   │                 threshold)            │
   └───────────────┬──────────────────────┘
                    │
          ┌─────────▼─────────┐
          │  estate.db        │
          │  jev_decisions    │
          │  (id, repo,       │
          │   decision_type,   │
          │   question,       │
          │   answer,        │
          │   confidence,   │
          │   latency_ms,    │
          │   escalated,     │
          │   created_at)   │
          └─────────┬─────────┘
                    │
          ┌─────────▼─────────┐
          │  TypeSafe Jev     │  ← JEV_API_KEY only lives here
          │  jev-1.13.0 API   │
          └───────────────────┘

Fallback (when Jev unavailable):
  Each tool returns {choice: "unavailable", confidence: null, escalated: true,
                     _fallback: "<original-behaviour>"}.
  The estate MCP door (BLIND mode) also routes here when MCP_GATEWAY_KEY is unset.
  Every fallback is written to jev_decisions with confidence = null.
```

---

## State schema

Every JevLayer call carries this state envelope:

```python
@dataclass
class JevState:
    repo: str              # "sovereign" | "hermes" | "estate" | ...
    layer: str             # "guard" | "agent" | "hook" | "consensus" | ...
    decision_id: str       # "law32_feature_name" | "verifier_z3_gate" | ...
    context: dict          # free-form, Jev reads it as structured input
```

The `context` dict is the only thing Jev sees; it is seeded by the decision point
and never includes secrets or credentials.

---

## Decision types

| Type | JevLayer method | Returns | Escalation threshold |
|---|---|---|---|
| Choose one of N options | `jev.choice()` | `{choice, confidence, probabilities, escalated}` | confidence < 0.7 |
| Rate on a scale | `jev.score()` | `{score, level, confidence, probabilities}` | confidence < 0.7 |
| True/false with confidence | `jev.noul()` | `{decision: bool, confidence: float, escalated}` | confidence < threshold |

Every decision also carries a `latency_ms` field. Calls exceeding 2000ms are
logged as `timeout` and treated as `escalated: true`.

---

## Escalation paths

When `escalated: true` (low confidence, unavailable, or timeout):

| Decision domain | Escalation |
|---|---|
| Guard (PreToolUse, PostToolUse, Stop) | Guard returns `NoVerdict` → door blocks → human review |
| Consensus vote | Fall back to 2/3 majority (existing behavior) + log `jev_escalated` |
| Verifier symbolic stage | Run full Z3 solver (existing behavior) + log `jev_gate_failed` |
| Inventory classification | Flag for async human review via `jev_decisions` dashboard query |
| Scheduler routing | Route to `review` lane + log `jev_low_confidence` |

---

## What this rejects

- **Direct Jev API calls from guard/agent/hook code.** All calls go through the MCP tool.
  A guard that calls TypeSafeClient directly is refused by `scope-guard`.
- **Hard-coded confidence floors per repository.** The floor is one value, set in
  `sovereign/policy.py`'s `[jev]` section, and overridable per decision type via env var.
  The estate twin reads this config and reports drift if a repo's floor diverges.
- **Binary pass/fail as the only response shape.** Every JevLayer call returns confidence.
  A decision point that discards confidence and returns only Allow/Deny fails its
  BDD test (LAW 46: no assertion without proof; LAW 38: a gate that cannot fail is not a gate).

---

## What this requires

1. **`JEV_API_KEY`** seeded into estate-secrets and loaded by the estate MCP server.
   No other repository holds this key.
2. **`mcp/plugins/jev.py`** — the MCP tool plugin exposing the three methods above.
   Written in the same pattern as `mcp/plugins/estate_twin.py` (propose/execute, idempotent).
3. **`estate.db jev_decisions table`** — created by `bin/db-gen`, UPSERT on `decision_id`.
   The estate twin queries it for the `jev_decisions` domain state row.
4. **`sovereign/policy.py`** — new `[jev]` section: `default_confidence_floor = 0.7`,
   `timeout_ms = 2000`, `escalate_on_timeout = true`.
5. **BDD tests** in `sovereign/tests/bdd/test_jev_layer.py` covering:
   - Available path: confidence returned, written to `jev_decisions`
   - Unavailable path: fallback shape returned, logged with `_fallback`
   - Timeout path: `escalated: true`, original behaviour runs
   - Escalation threshold: confidence < floor → escalated flag set
   - No secret leakage: `JevState.context` never contains credentials

---

## Implementation order

| # | Work | Where |
|---|---|---|
| 1 | MCP plugin `jev.py` + `estate.db` table | `mcp/plugins/jev.py`, `bin/db-gen` |
| 2 | Tier-1 guards: `prospector/verify.py` verdict gate, `hermes/reply_judge.py`, `estate/law32-default` | `sovereign/`, `estate/` |
| 3 | Consensus pre-screen: `sovereign/consensus/models.py` fan-out gate | `sovereign/consensus/` |
| 4 | Symbolic verifier gate: `sovereign/verifier.py` Z3 pre-screen | `sovereign/verifier.py` |
| 5 | Agent routing: `hermes/scheduler.py`, `otto/router/core.py` | `hermes/`, `otto/` |
| 6 | Remaining decision points from capability map | All repos |
| 7 | `scope-guard` blocks direct TypeSafeClient calls | `guards/scope-guard.py` |

---

## Proof

```
gh run list -R chidionyema/idp --workflow ci.yml --limit 10 --json conclusion
  → no failed runs on main

SELECT decision_id, AVG(confidence), COUNT(*) FROM jev_decisions
  GROUP BY decision_id HAVING AVG(confidence) < 0.7;
  → lists any decision type with a confidence problem (actionable)

bin/idp-laws-guards-report
  → every guard with a JevLayer call shows "JevLayer" in the Tools column
```

# JEV Tier-1 Integration — four highest-impact, lowest-risk decision points

**Status:** open
**Opened:** 2026-09-21
**Laws:** LAW 0 (one of each layer), LAW 38 (a gate that cannot fail is not a gate),
         THE EMPIRICAL PROOF RULE
**Source:** `docs/jev-capability-map.md` Tier 1 section
**Depends on:** `2026-09-21-jev-layer-core-mcp-plugin-and-database-table.md`
**Spec:** `docs/decisions/0030-jevlayer-unified-confidence-and-decision-service.md`
**Module:** `sovereign/`, `estate/guards/`, `hermes/`
**Binding:** BDD tests per decision point, updated `sovalan/policy.py`

---

## The failure this removes

Four decision points that are simultaneously: high frequency (run on every agent session or every
commit), high uncertainty (acknowledge they are guessing), and expensive (run full LLM calls or
large git traversals before failing).

| # | Decision point | Frequency | Uncertainty | Cost |
|---|---|---|---|---|
| 1 | `prospector/verify.py` verdict gate | Every admission check | Binary pass/fail, no confidence | 20–30s LLM call |
| 2 | `hermes/reply_judge.py` | Every reply judged | `None → clean` (false safety) | LLM call |
| 3 | `estate/guards/hooks/law32-default` feature name | Every push | "The guess is only a guess" | O(n) commits |
| 4 | `sovereign/consensus/models.py` fan-out | Every consensus vote | 3-model fan-out always runs | 30s consensus |

---

## D1 — `prospector/verify.py` verdict gate → Jev noul pre-screen

**Current behaviour** (`verify.py:480`): full LLM verdict call, then pass/fail.

**New behaviour**: Jev noul gate first (70–500ms). If `confidence >= 0.7`, return verdict
immediately. If `escalated: true`, fall through to full LLM call.

```
State: {repo: "prospector", layer: "verifier", decision_id: "verdict_gate",
        context: {claim: "...", sources: [...], domain: "..."}}

Question: "Is this claim supported by the provided sources at a confidence above 0.7?"
Options: ["admissible", "not_admissible"]

If jev.noul() confidence < 0.7 → escalate → run full LLM verifier.
If jev.noul() unavailable → run full LLM verifier + log jev_unavailable.
If jev.noul() returns confidence >= 0.7 → return verdict directly (saves 20–30s).
```

**Verification**: `SB_BDD_STRICT=1 pytest prospector/tests/ -k jev -v` — available, escalated,
and unavailable paths all tested.

---

## D2 — `hermes/reply_judge.py` → Jev choice replacing `None → clean`

**Current behaviour** (`reply_judge.py:66`): `None` (no clean signal) → treats all as clean.

**New behaviour**: Jev choice with three options. Returns `{choice, confidence}`.
`confidence < 0.7` → escalate to human review lane.

```
State: {repo: "hermes", layer: "agent", decision_id: "reply_judge",
        context: {reply: "...", claim: "...", sources: [...]}}

Question: "Does this reply accurately represent the evidence and make no unsupported claim?"
Options: ["clean", "uncertain", "violation"]

If jev.choice() returns "uncertain" or confidence < 0.7 → escalate.
If jev.choice() returns "violation" → block regardless of confidence.
```

**Verification**: `SB_BDD_STRICT=1 pytest hermes/tests/ -k jev -v` — all three paths tested.

---

## D3 — `estate/guards/hooks/law32-default` feature name → Jev choice replacing "guess"

**Current behaviour** (`law32-default:128`): parses `feat:` message, admits "the guess is
only a guess", falls back to any complete pair in push.

**New behaviour**: Jev choice over the complete doc pairs in the push, with confidence.
`confidence < 0.7` → flag for async human review (don't block the push, but raise a flag).

```
State: {repo: "estate", layer: "hook", decision_id: "law32_feature_name",
        context: {commits: [...], docs_pairs: [...], feat_message: "..."}}

Question: "Which feature does this push implement, based on the commit messages and docs pairs?"
Options: [list of feature names from docs_pairs, "unknown"]

If jev.choice() confidence >= 0.7 → use that name, proceed.
If jev.choice() confidence < 0.7 → escalate, use name with flag, don't block push.
If jev.choice() returns "unknown" → block push (explicit unknown = don't guess).
```

**Verification**: `SB_BDD_STRICT=1 pytest estate/tests/ -k jev -v` — known feature, unknown feature,
escalation, and unavailable paths all tested.

---

## D4 — `sovereign/consensus/models.py` fan-out → Jev noul pre-screen

**Current behaviour** (`models.py:106`): 3-model fan-out always runs, 30s total.

**New behaviour**: Jev noul gate first. If `confidence >= 0.7` that consensus is likely,
proceed with 3-model vote. If `escalated: true` or unavailable, run full vote anyway
(log `jev_gate_*: skipped, running full consensus`).

```
State: {repo: "sovereign", layer: "consensus", decision_id: "consensus_pre_screen",
        context: {operation: "...", destructive: bool, budget_remaining: float}}

Question: "Is consensus likely to be reached on this operation without timeout?"
Options: ["likely", "unlikely"]

If jev.noul() confidence < 0.7 → escalate, log jev_low_confidence, run full vote.
If jev.noul() unavailable → run full vote, log jev_unavailable.
If jev.noul() returns True with confidence >= 0.7 → proceed to 3-model vote.
```

**Verification**: `SB_BDD_STRICT=1 pytest sovereign/tests/bdd/ -k consensus_jev -v` —
all paths tested.

---

## Definition of Done — in commands

1. `SB_BDD_STRICT=1 pytest sovereign/tests/bdd/test_jev_layer.py -v` → all core scenarios green
2. `SB_BDD_STRICT=1 pytest prospector/tests/ -k jev -v` → verdict gate paths green
3. `SB_BDD_STRICT=1 pytest hermes/tests/ -k jev -v` → reply judge paths green
4. `SB_BDD_STRICT=1 pytest estate/tests/ -k jev -v` → law32 feature name paths green
5. `bin/idp-ci` → green on the branch
6. `SELECT decision_id, AVG(confidence) FROM jev_decisions GROUP BY decision_id` →
   returns rows for all four decision points with non-null confidence

---

## What "operational" means here

Tier-1 is operational when all four decision points call the JevLayer MCP plugin and write
rows to `jev_decisions` with real confidence scores from TypeSafe Jev. A query on the live
system shows confidence distributions per decision type, and decisions with average confidence
below 0.7 are flagged for the next sprint.

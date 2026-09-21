# JEV Layer Rollout — remaining decision points across all repositories

**Status:** open
**Opened:** 2026-09-21
**Laws:** LAW 0 (one of each layer), LAW 38 (a gate that cannot fail is not a gate),
         THE EMPIRICAL PROOF RULE
**Source:** `docs/jev-capability-map.md` Tier 2 and Tier 3 sections
**Depends on:**
  - `2026-09-21-jev-layer-core-mcp-plugin-and-database-table.md`
  - `2026-09-21-jev-tier-1-four-highest-impact-integrations.md`
**Spec:** `docs/decisions/0030-jevlayer-unified-confidence-and-decision-service.md`
**Binding:** BDD tests per repo, scope-guard updated to block direct TypeSafeClient calls

---

## The failure this removes

The Jev capability map found 50+ decision points across 8 repositories. Tier 1 (4 decisions) is
covered by the depends-on ticket. This ticket covers Tier 2 (7 decisions) and Tier 3 (the long tail).

---

## Tier 2 — High impact, moderate effort

### T2-A — `agent-foundry/nodes.py` price extraction → return candidates:N with confidence

Current: first regex match, no count.
New: Jev choice over price candidates, returns `{choice, confidence, candidates: N}`.

### T2-B — `hermes/grounding.py` → continuous score replacing binary threshold

Current: `grounding_min_overlap=0.5` → binary pass/fail.
New: Jev score with continuous confidence. No artificial cliff at 0.5.

### T2-C — `hermes/bayesian_ab.py` → probability margin replacing hard 0.90

Current: `prob >= 0.90` → binary promote/extend.
New: Jev score with confidence on probability. 0.89 with confidence 0.95 behaves differently
from 0.89 with confidence 0.51.

### T2-D — `sovereign/verifier.py` Z3 pre-screen gate

Current: Z3 solver runs for 20s on every verification.
New: Jev noul gate first. "Is this query obviously satisfiable?" with high confidence →
skip Z3 entirely.

### T2-E — `hermes/scheduler.py` streak → continuous score

Current: `streak >= 3` → binary "needs review".
New: Jev score with continuous failure probability + confidence.

### T2-F — `hermes/otto/router/core.py` lane selection → Jev score with confidence

Current: default fallback to a lane with no confidence signal.
New: Jev score over lane options, confidence on routing decision.

### T2-G — `sovereign/engine/ops.py` classify → Jev choice replacing UNKNOWN_CLASS fallback

Current: `UNKNOWN_CLASS` returned as fallback → treated as destructive.
New: Jev choice with explicit `{unknown, confidence}` signal. Low confidence → escalate.

---

## Tier 3 — Broad coverage, long tail

### T3-A — All `Decision` enums → add confidence field

Every repository has `Decision::Allow/Deny` enums. Replace with `Decision` carrying
`{variant, confidence: Option<f64>, escalated: bool}`. Enforced by `scope-guard`.

### T3-B — All hard thresholds → Jev score with continuous confidence

11 hard thresholds across hermes, prospector, sovereign. Each replaced with a Jev
score call. No discrete bands at 0.4/0.75/0.9.

### T3-C — All acknowledged best-guess heuristics → formal Jev calls

6 code comments saying "this is a guess": law32, sovereign/permissions.rs, agent-workforce,
prospector/adaptive.py, prospector/golden.py, sovereign/config.rs.
Each becomes a Jev noul or choice call with explicit uncertainty.

### T3-D — All fail-closed unknowns → uncertainty propagation

8 locations where `None → clean` or `unknown → deny`. Each returns `{uncertain, confidence: 0.0}`
so the failure mode is visible and not silent.

### T3-E — `scope-guard.py` blocks direct TypeSafeClient calls

After all above, any guard/agent/hook code that calls TypeSafeClient directly is refused.
Only `mcp/plugins/jev.py` holds the API key.

---

## Decision points by repository

| Repository | Tier | Decisions |
|---|---|---|
| sovereign | T1, T2-D, T2-G, T3-A, T3-C | verifier Z3 gate, classify, engine/ops, Decision enums |
| hermes | T1, T2-B, T2-C, T2-E, T2-F | reply_judge, grounding, bayesian_ab, scheduler, router |
| estate | T1, T3-B | law32, shell-strict, python-strict, estate-gate |
| prospector | T1, T2-A, T3-B, T3-C | verify gate, price extraction, adaptive, golden |
| verdict | T3-B | moderation-free, quality-score, credit-guard |
| agent-foundry | T2-A, T3-C | nodes price, currency mismatch |
| agent-workforce | T3-C | main.py traces, board.py banned words |
| agent-guard | T3-C | agent-reap, launchd-lint, load-probe |

---

## Definition of Done — in commands

1. All T2 decisions: BDD tests green for each repo
2. All T3 decisions: `grep -r "TypeSafeClient" guards/ agents/` → empty (only in MCP plugin)
3. `scope-guard` test: guard that calls TypeSafeClient directly is refused with exit 2
4. `bin/idp-laws-guards-report` → every guard shows "JevLayer" in Tools column
5. `bin/idp-ci` → green on the branch
6. `SELECT repo, AVG(confidence) FROM jev_decisions WHERE confidence IS NOT NULL
   GROUP BY repo` → all 8 repos represented

---

## What "operational" means here

The JEV layer is fully operational when every decision point in the capability map calls the
JevLayer MCP plugin, every call writes a row to `jev_decisions`, and no repository holds a
`JEV_API_KEY`. The estate twin's `domain_states()` can query `jev_decisions` for any decision
type and get a real confidence distribution. That is the audit trail, and it is proof.

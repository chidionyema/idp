# Jev × Estate Capability Map (Full Estate Audit)

**Jev** is TypeSafe AI's "System One" model (released 2026-09-15) that returns **structured typed values** instead of natural language text. Claims 40–400× speed/cost improvement over frontier LLMs.

- Docs: https://docs.typesafe.ai/
- Pricing: $42/Btok input, free output; $0.042/Mtok
- Context: 64k tokens; 70–500ms response times
- Rate limits: 250k tok/s, 1200 req/min

---

## Cross-Repository Decision Patterns

From auditing sovereign, estate, hermes (agent/config/operator/v2), verdict, prospector, agent-foundry, agent-workforce, agent-guard:

### Pattern 1: Binary Deny/Approve with No Confidence
Every repo has decision functions that return only Allow/Deny without confidence scores:

| Repo | File | Decision | Current Output |
|------|------|----------|---------------|
| sovereign | sentinel/guardrails/mod.rs:34 | Decision::Allow/RequireApproval/Deny | No confidence field |
| hermes | authz_mixin.py:386 | Cascading allowlist checks | No confidence per path |
| hermes | lifecycle_guard.py:98 | safe vs unsafe classification | Binary only |
| verdict | credit-guard.ts:76 | 6-layer defense verdict | No per-layer confidence |
| prospector | kill_filter.py:20 | hard_fail gate | Binary with threshold |
| idp | sovereign/engine/ops.py:62 | Op classification | UNKNOWN_CLASS fallback |

**Jev mapping**: Every decision wrapped in `jev.choice()` returning `{choice, confidence, probabilities}`

---

### Pattern 2: Hard Thresholds with No Uncertainty Margin
Every repo has numeric thresholds that treat 0.74 and 0.75 as completely different outcomes:

| Repo | File | Threshold | Problem |
|------|------|-----------|---------|
| hermes | grounding.py:43 | `grounding_min_overlap=0.5` | Binary pass/fail on token overlap |
| hermes | bayesian_ab.py:135 | `prob >= 0.90` | 0.89 = "extend", 0.90 = "promote" |
| hermes | scheduler.py:152 | `streak >= 3` | 2 failures = fine, 3 = "needs review" |
| hermes | normalize_confidence | bands at 0.75 and 0.4 | 0.74 = "low", 0.75 = "high" |
| prospector | kill_filter.py:9 | `confidence_floor=0.0` | Any confidence kills |
| prospector | admissibility.py:402 | `min_domains=2` | 1 domain = fail, 2 = pass |
| verdict | moderation-free.ts:64 | `capsRatio > 0.7` | Arbitrary boundary |
| idp | sovereign/consensus/decide.py:66 | quorum check | Binary, no margin |
| estate | estate-gate:36 | `MAXLOAD = NCPU * 2` | Arbitrary multiplier |

**Jev mapping**: `jev.score()` returns continuous probabilities, not discrete bands

---

### Pattern 3: Best-Guess Heuristics Explicitly Acknowledged
These are the most urgent — code that admits it is guessing:

| Repo | File | Comment | What It Guesses |
|------|------|---------|-----------------|
| estate | law32-default:128 | "The guess is only a guess" | Feature name from feat: message |
| sovereign | permissions.rs:20 | README claims fail-closed | `screen_recording_granted() → true` |
| agent-workforce | main.py:121 | "assumes 0 traces = failure" | Langfuse lag vs genuine failure |
| prospector | adaptive.py:54 | "asserted formula" | baseline severity from p_thresh |
| prospector | golden.py:1017 | hardcoded values | adversarial confidence (0.8/0.2/0.5) |
| sovereign | config.rs:30 | static defaults | all config values |

**Jev mapping**: `jev.noul()` with confidence < 0.7 triggers escalation or wider uncertainty bands

---

### Pattern 4: Fail-Closed Without Uncertainty Propagation
When these systems don't know, they assume "clean" or "safe":

| Repo | File | Returns | Should Return |
|------|------|---------|---------------|
| hermes | reply_judge.py:66 | `None` → all clean | `uncertain` + confidence |
| hermes | gateway/core.py:133 | Unknown tool → denial | `confidence` on schema validation |
| agent-foundry | nodes.py:203 | `comparable: False` | `uncertainty: currency_mismatch` |
| prospector | verify.py:761 | `confidence=0.0` for unverifiable | Distinguish no-evidence vs contradict |
| idp | sovereign/engine/ops.py:72 | Unknown op → destructive | `confidence` on classification |

**Jev mapping**: Every `None`/fail-closed response needs an uncertainty field

---

### Pattern 5: Expensive Operations with No Pre-Screen
These operations run in full before failing:

| Repo | File | Operation | Pre-screen Opportunity |
|------|------|-----------|----------------------|
| sovereign | verifier.py:290 | Z3 SMT solver (20s) | Jev noul: "obviously true/false?" |
| sovereign | consensus/models.py:106 | 3-model fan-out (30s) | Jev noul: "consensus likely?" |
| prospector | verify.py:480 | LLM verdict call | Jev choice: "admissible?" first |
| hermes | reply_judge.py:66 | Verify-lane LLM call | Jev noul: "clean claim?" first |
| estate | inventory.py:389 | `gh issue list` (30s timeout) | Jev noul: "issues exist?" |

**Jev mapping**: `jev.noul()` as gate before expensive calls — 70-500ms vs 20-30s

---

## Detailed Capability Mappings by Repo

### IDP (sovereign)

| Location | Current | Jev Improvement |
|-----------|---------|-----------------|
| `engine/ops.py:62` classify() | Lookup in sets, unknown→destructive | Choice with confidence, low conf→escalate |
| `engine/ops.py:75` check() | Numeric budget compare | Score with urgency level |
| `engine/fsm.py:101` can() | Set lookup | Choice with confidence on transition |
| `verifier.py:290` stage_symbolic() | Z3 solver 20s | Noul gate first: "obviously satisfiable?" |
| `consensus/decide.py:66` policy eval | Binary allow/deny | Choice + confidence per violation |
| `consensus/models.py:60` is_destructive() | Keyword substring match | Noul with calibrated confidence |
| `consensus/models.py:141` tally() | Proposal counting | Score with margin/probability |
| `engine/termination.py:65` evaluate() | Threshold comparisons | Score with continuous severity |
| `engine/kini.py:94` classify() | Returncode mapping | Choice with confidence |
| `mcp/plugins/estate_twin.py:88` domain_states() | 3-state rule | Noul + Score with confidence |
| `mcp/plugins/estate_executor.py:606` simulate_command() | Hard-coded refusals | Noul + Choice for novel patterns |

---

### Estate

| Location | Current | Jev Improvement |
|-----------|---------|-----------------|
| `guards/hooks/law32-default:128` | "The guess is only a guess" feature name | Choice with confidence, explicit "uncertain" |
| `guards/bin/estate-gate:36` | `MAXLOAD = NCPU * 2` | Score with confidence on load health |
| `guards/hooks/law32-default:37` | `max_range=500` | Noul: "push size normal?" with confidence |
| `guards/hooks/shell-strict-default:69` | Aggregate 5 checks | Score with per-check confidence |
| `scripts/inventory.py:591` | `referenced` via basename | Noul with confidence on match quality |
| `guards/hooks/law32-default:63` | DEMO_DIRS/ONBOARDING_DIRS paths | Choice with confidence on dir type |

---

### Hermes (agent/config/operator/v2)

| Location | Current | Jev Improvement |
|-----------|---------|-----------------|
| `authz_mixin.py:386` | Cascading allowlist checks | Score with per-path confidence |
| `authz_mixin.py:621` | fail-open when no allowlist | Noul: "intentional allow?" with confidence |
| `response_filters.py:56` | Silence detection marker matching | Noul with confidence on intentional silence |
| `lifecycle_guard.py:98` | binary safe/unsafe | Score with ambiguity band |
| `lifecycle_guard.py:468` | magic number binary detection | Choice with confidence on binary vs script |
| `scheduler.py:152` | streak >= 3 threshold | Score with continuous failure probability |
| `scheduler.py:336` | substring error classification | Choice with confidence on error type |
| `otto/router/core.py:145` | lane selection default fallback | Score with routing confidence |
| `otto/router/core.py:172` | budget exhaustion binary | Score with remaining budget confidence |
| `otto/router/contract.py:37` | confidence band edges | Remove bands, use continuous confidence |
| `otto/router/grounding.py:43` | token overlap threshold | Score with continuous grounding |
| `otto/verify/reply_judge.py:66` | None → all clean | Choice with confidence, not fail-closed |
| `otto/gateway/core.py:175` | human approval gate | Noul: "approval genuinely sought?" |
| `otto/boot/pipeline.py:287` | prefix route hint matching | Noul with confidence on intent |
| `config/scripts/bayesian_ab.py:135` | prob >= 0.90 threshold | Score with probability margin |
| `config/scripts/memory_retrieval.py:85` | threshold 0.5 | Score with calibrated threshold |

---

### Verdict

| Location | Current | Jev Improvement |
|-----------|---------|-----------------|
| `moderation-free.ts:44` | asserted confidence (1.0, 0.9, 0.8) | Derived from evidence quality |
| `moderation-free.ts:64` | capsRatio > 0.7 single threshold | Score with confidence band |
| `quality-score.ts:46` | weighted composite thresholds | Score with per-dimension confidence |
| `quality-score.ts:225` | discrete tier bands | Score with continuous tier probability |
| `credit-guard.ts:76` | 6-layer defense | Score with per-layer confidence |

---

### Prospector

| Location | Current | Jev Improvement |
|-----------|---------|-----------------|
| `verify.py:91` _calc_confidence | Algorithmic formula | Score with uncertainty propagation |
| `verify.py:761` | confidence=0.0 for unverifiable | Distinguish no-evidence vs contradict |
| `admissibility.py:222` | strict "every" rule | Score with margin on good sources |
| `admissibility.py:402` | min_domains=2 threshold | Score with domain count confidence |
| `adaptive.py:20` | kill-rate deviation | Score with deviation confidence |
| `kill_filter.py:9` | confidence_floor=0.0 | Score with calibrated floor |
| `golden.py:1017` | hardcoded 0.8/0.2/0.5 | Calibrated from outcome history |
| `prescreen.py:154` | "kept on uncertainty" | Explicit UNCERTAIN state with confidence |
| `classify.py:35` | LLM fallback = confidence 0.0 | Track fallback explicitly |

---

### Agent Foundry

| Location | Current | Jev Improvement |
|-----------|---------|-----------------|
| `nodes.py:160` | `order_of_appearance[0]` fallback | Choice with candidates:N and confidence |
| `nodes.py:203` | currency mismatch → False | Score with uncertainty: currency_mismatch |
| `nodes.py:148` | regex first match, no count | Return candidates:N alongside price |
| `worker.py:201` | flat attempt counter | Score with retry velocity confidence |
| `worker.py:233` | bare except Exception | Noul: "is this expected error type?" |

---

### Agent Workforce

| Location | Current | Jev Improvement |
|-----------|---------|-----------------|
| `main.py:65` | created_at as priority | Score with throughput-weighted priority |
| `main.py:119` | 0 traces = exit 4 | Noul: "traces genuinely missing?" with latency |
| `main.py:67` | CLAIM_MARK binary check | Score with claim freshness confidence |
| `crew.py:85` | guardrail_max_retries=2 | Score with guardrail pass rate confidence |
| `tools/board.py:13` | banned-word regex | Score with word severity classification |

---

### Agent Guard

| Location | Current | Jev Improvement |
|-----------|---------|-----------------|
| `agent-reap:12` | `*node*` glob over-match | Choice with path validation confidence |
| `launchd-lint:24` | BLIND = unreadable | Choice: permissions vs corruption vs not-found |
| `load-probe:11` | speed < 100 warning | Score with throttle frequency trend |

---

## Priority Implementation Order

### Tier 1: Highest Impact, Lowest Risk
1. **`prospector/verify.py` verdict gate** — pre-screen LLM call with Jev Noul first (saves 20-30s)
2. **`hermes/reply_judge.py`** — replace `None→clean` with confidence-scored verdict
3. **`estate/law32-default` feature name** — explicit confidence instead of "guess"
4. **`idp/sovereign/consensus/models.py`** — pre-screen consensus vote with Jev

### Tier 2: High Impact, Moderate Effort
5. **`agent-foundry/nodes.py` price extraction** — return candidates:N and confidence
6. **`hermes/grounding.py`** — continuous score vs binary threshold
7. **`hermes/bayesian_ab.py`** — probability margin instead of hard 0.90
8. **`sovereign/verifier.py` stage_symbolic** — Z3 pre-screen gate

### Tier 3: Broad Coverage, Longer Tail
9. All `Decision` enums across repos — add confidence field
10. All hard thresholds — replace with Score with confidence
11. All "best-guess" acknowledged heuristics — formalize as Jev calls
12. All fail-closed → unknown propagation — add uncertainty field

---

## Implementation Pattern

```python
# Standard Jev wrapper for estate decisions
import os
from typesafe_sdk import TypeSafeClient

JEV_API_KEY = os.environ.get("JEV_API_KEY", "")
JEVD = "jev-1.13.0"

def jev_choice(state: dict, question: str, options: list[str], required_confidence: float = 0.7) -> dict:
    """Returns {choice, confidence, probabilities, escalated}"""
    with TypeSafeClient(api_key=JEV_API_KEY) as client:
        result = client.evaluate(
            model=JEVD,
            state=state,
            questions=[{
                "id": "decision",
                "type": "choice",
                "question": question,
                "options": options,
            }]
        )
    decision = result["decision"]
    if decision["confidence"] < required_confidence:
        decision["escalated"] = True  # route to human or deeper analysis
    return decision

def jev_score(state: dict, question: str, levels: list[str]) -> dict:
    """Returns {score, confidence, probabilities}"""
    with TypeSafeClient(api_key=JEV_API_KEY) as client:
        return client.evaluate(
            model=JEVD,
            state=state,
            questions=[{
                "id": "rating",
                "type": "score",
                "question": question,
                "levels": levels,
            }]
        )

def jev_noul(state: dict, question: str, threshold: float = 0.7) -> tuple[bool, float]:
    """Returns (decision, confidence)"""
    with TypeSafeClient(api_key=JEV_API_KEY) as client:
        result = client.evaluate(
            model=JEVD,
            state=state,
            questions=[{
                "id": "truth",
                "type": "noul",
                "question": question,
            }]
        )
    prob = result["truth"]["noul"]
    return prob >= threshold, prob
```

---

## Key Benefits Summary

| Pattern | Current State | Jev State | Benefit |
|---------|---------------|-----------|---------|
| Binary decisions | `Allow/Deny` | `{choice, confidence, probabilities}` | Risk-aware routing |
| Hard thresholds | `0.74=fail, 0.75=pass` | Continuous probability | No artificial cliffs |
| Explicit guesses | "The guess is only a guess" | `{choice, confidence: 0.3}` | Actionable uncertainty |
| Fail-closed unknowns | `None → clean` | `{uncertain, confidence: 0.0}` | No silent false safety |
| Expensive pre-checks | Full computation then fail | Noul gate first (70-500ms) | 40-400× cost reduction |
| Flat counters | Attempt count = N | Retry velocity + confidence | Adaptive backoff |

---

## Integration Requirements

1. **Secrets**: Add `JEV_API_KEY` to estate-secrets
2. **Rate limiting**: 1200 req/min handles estate query volume
3. **Fallback**: When Jev unavailable, fall back to current behavior + log `jev_unavailable`
4. **Confidence threshold**: Per-decision configurable, default 0.7
5. **Escalation path**: Low-confidence decisions route to human review or deeper analysis
6. **Logging**: Every Jev call logged with `{decision, confidence, latency, api_key_scope}`

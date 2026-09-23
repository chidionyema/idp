# JEV Layer Core — MCP plugin + estate.db table

**Status:** open
**Opened:** 2026-09-21
**Laws:** LAW 0 (one of each layer), LAW 38 (a gate that cannot fail is not a gate),
         THE HEADLINE (no second store, no second bus, no second server)
**Source:** `docs/jev-capability-map.md` (full audit), `docs/decisions/0030-jevlayer-unified-confidence-and-decision-service.md`
**Spec:** `docs/decisions/0030-jevlayer-unified-confidence-and-decision-service.md`
**Module:** `mcp/plugins/jev.py` (new), `bin/db-gen` (updated), `sovereign/policy.py` (updated)
**Binding:** `sovereign/tests/bdd/test_jev_layer.py` (new), `sovereign/policy.py` [jev] section

---

## The failure this removes

50+ decision points across 8 repositories each make best-guess decisions in isolation:
- Binary Allow/Deny with no confidence score
- Hard thresholds (0.74 = fail, 0.75 = pass) with no continuity
- Explicit guesses ("the guess is only a guess") that return no uncertainty signal
- Fail-closed on unknown: `None → clean` with no confidence = 0
- Expensive pre-checks: 20–30s LLM calls run in full before failing

Every repository calls Jev directly → API key sprawl, inconsistent fallback logic,
no cross-decision audit trail.

---

## The fix, in one sentence

**One JevLayer MCP plugin that every decision point calls; the estate holds the API key; every call is written to `estate.db`.**

---

## What already exists

- `docs/jev-capability-map.md` — full audit of all 50+ decision points across sovereign, estate,
  hermes, verdict, prospector, agent-foundry, agent-workforce, agent-guard
- `mcp/plugins/estate_twin.py` — the pattern for an MCP plugin with propose/execute and idempotent UPSERT
- `estate.db` — the estate's SQLite asset graph, written by `bin/db-gen`
- `sovereign/policy.py` — already parses TOML blocks; `[jev]` section goes there with the floor and timeout
- `sovereign/consensus/models.py` — already calls `TypeSafeClient`; this ticket abstracts that to the layer

---

## Deliverables

### D1 — `mcp/plugins/jev.py` (new MCP plugin)

Three tools, matching the estate MCP door pattern (propose/execute, idempotent):

```
mcp__jev__choice(state, question, options, required_confidence=0.7)
  → {choice, confidence, probabilities: {option: float}, escalated, latency_ms}

mcp__jev__score(state, question, levels, required_confidence=0.7)
  → {score, level, confidence, probabilities: {level: float}, escalated, latency_ms}

mcp__jev__noul(state, question, threshold=0.7)
  → {decision: bool, confidence: float, escalated, latency_ms}
```

Each tool:
1. Writes a `jev_decisions` row to `estate.db` (UPSERT on `decision_id`)
2. Calls TypeSafe `jev-1.13.0` with the state and question
3. Returns structured response with `escalated` flag when confidence < floor
4. On timeout (> 2000ms) or unavailable API: returns `{escalated: true, _fallback: "<behaviour>"}`

State envelope per call:
```python
JevState = (repo, layer, decision_id, context: dict)
# context is decision-point-supplied; Jev reads it as structured input
# context must NOT contain credentials or secrets
```

### D2 — `estate.db jev_decisions` table (new)

```sql
CREATE TABLE jev_decisions (
  id           TEXT PRIMARY KEY,     -- "hermes:guard:reply_judge:2026-09-21T..."
  repo         TEXT NOT NULL,
  layer        TEXT NOT NULL,        -- guard|agent|hook|consensus|verifier
  decision_id  TEXT NOT NULL,       -- "law32_feature_name" | "verifier_z3_gate" | ...
  question     TEXT NOT NULL,        -- the question passed to Jev
  answer       TEXT,                 -- Jev's chosen answer
  confidence   REAL,                 -- null when Jev unavailable
  probabilities TEXT,                -- JSON {option: float} or null
  escalated    INTEGER NOT NULL DEFAULT 0,
  latency_ms   REAL,
  created_at   TEXT NOT NULL        -- ISO8601
);
CREATE INDEX idx_jev_decisions_repo ON jev_decisions(repo);
CREATE INDEX idx_jev_decisions_confidence ON jev_decisions(confidence) WHERE confidence IS NOT NULL;
```

`bin/db-gen` is updated to run this CREATE TABLE IF NOT EXISTS.

### D3 — `sovereign/policy.py` [jev] section (new TOML block)

```toml
[jev]
default_confidence_floor = 0.7
timeout_ms = 2000
escalate_on_timeout = true
fallback_log = "jev_unavailable"
```

This replaces the hard-coded `0.7` floors scattered across 11 repositories.

### D4 — `sovereign/tests/bdd/test_jev_layer.py` (new BDD test)

Scenarios:
- **available path**: Jev returns confidence 0.9 → `{escalated: false}`, row in `jev_decisions`
- **low confidence path**: Jev returns confidence 0.4 < 0.7 floor → `{escalated: true}`
- **unavailable path**: TypeSafeClient raises → `{escalated: true, _fallback: "original"}`, row written with `confidence = null`
- **timeout path**: response > 2000ms → `{escalated: true}`, `latency_ms` logged
- **escalation routing**: guard with `escalated: true` → `NoVerdict` raised
- **no secret leakage**: context dict with `password` key → stripped before Jev call, `password_redacted: true` in row

---

## Definition of Done — in commands

1. `python -c "from mcp.plugins.jev import jev_choice, jev_score, jev_noul; print('import ok')"` → import ok
2. `sqlite3 estate.db ".schema jev_decisions"` → table exists with correct columns
3. `bin/db-gen` → silent success, no duplicate rows in `jev_decisions`
4. `SB_BDD_STRICT=1 pytest sovereign/tests/bdd/test_jev_layer.py -v` → all scenarios green
5. `grep -r "TypeSafeClient" sovereign/ guards/` → only in `mcp/plugins/jev.py` and `mcp/plugins/jev_test.py`
   (no direct calls in guard/agent/hook code)
6. `bin/idp-ci` → green on the branch
7. `bin/idp-laws-guards-report` → every guard that should call JevLayer shows "JevLayer" in Tools column

---

## What "operational" means here

The JevLayer MCP plugin is operational when the three tools are registered in the estate MCP server,
`estate.db` has the table, and every call path returns `{choice, confidence, escalated}`.
Calling `mcp__jev__choice` with a real state/question and getting back a structured decision
with a `confidence` field proves the layer is live.

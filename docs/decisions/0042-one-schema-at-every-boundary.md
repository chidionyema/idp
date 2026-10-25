# 0042 — One schema at every boundary: extend `intent-compile`, ratchet into CI, receipt the repair

- **Date:** 2026-10-25
- **Claim:** idp#7089 · agent `estate-agent`
- **Spec:** `docs/specs/2026-10-25-one-schema-three-boundaries.md`
- **Research:** `docs/research/2026-10-25-constrained-formats-research.md`

## Context

An agent action crosses three boundaries — decode (the lane's `response_format`), validate (the
door's `resolve_args`), repair (the caller's retry) — and at all three the estate accepted any
payload whose syntax parses. Measured 2026-10-25: the typed lane's schema is
`{"type": "object", "additionalProperties": true}`, `resolve_args` honours an argument no intent
declares and coerces only `int`, and 74 violations sit across the 96 committed intents (110 across
the 340 installed ones), including 3 intents that are not parseable YAML.

The estate already owns the right mechanism: `schema/intent/*.schema.json` + `bin/intent-compile`
validate typed JSON payloads with `jsonschema.Draft202012Validator` and refuse an unknown field by
name.

## Decisions

**D1. Extend `bin/intent-compile` and `schema/intent/*.schema.json`; build no second validator.**
AGENTS.md §6: one of each layer. A second validator is stitching, and it would drift from the one
already applied to cluster payloads. The change here adds a *measurement* (`bin/schema-conformance`)
and, in step 2 of the spec's ladder, an args schema in the same directory validated by the same
library.

**D2. Ship the ratchet, not strict mode, as the CI verdict.**
Strict mode fails on `main` today at 74 violations, so a strict rung would be red before any lane
touched anything — a gate every lane must bypass, which is how a gate stops being a gate. CI runs
`--baseline docs/research/2026-10-25-constrained-formats.baseline.json`: red on a **new** violation,
`fixed` lines when a lane pays one down, exit 2 (BLIND, and therefore FAIL) when the baseline cannot
be read. Strict mode remains available and is asserted to fail by test, so the corpus can never be
described as clean.

**D3. Do not tighten `resolve_args` in this change.**
The door is one file every agent calls, with 74 known violations behind it. Tightening it today
refuses correct work in every lane (R38). The spec's ladder puts enforcement in steps 3-4, after
the corpus has started shrinking, and pins the defect with a test that must be **inverted, not
deleted**, on the day the door learns to refuse.

**D4. A repair must declare itself.**
`2608.04355v1` measures that format repair masquerades as self-correction. The estate's PoBR receipt
(`litellm-local/callbacks/pobr_enforce.py`; the live copy is `mcp/plugins/pobr_*.py`, see D6)
already fails closed on a missing receipt, so the repair boundary is one added field —
`repaired: true`, with the failing schema and field — not a new receipt format.

**D5. The lane's `response_format` schema and the caller's validation schema are one object.**
`2605.04107v1`: the wire schema is the only contract the model sees. Two copies of the shape (one
for decoding, one for validation) is the estate's §6 defect applied to a schema.

**D6. Boundary 2 lives at the door, and the router's copy is the orphan to delete.**
Asked whether shape enforcement should ride the routing layer so every surface inherits it at once,
the measured answer is: for boundary 1 yes, for boundary 2 no. `platform/llm/front.py` is a
221-line bytes-only forwarder (`rg 'json|schema'` over it returns nothing) and is deliberately the
process that never restarts — the opposite of a validator, on every agent's hot path. And the
estate already answered this by building: `litellm-local/callbacks/pobr_enforce.py` fails closed by
design, `pobr_schema.py` is 522 lines, `pobr_gate.py` 364 — and **no config loads any of them**
(`rg pobr platform/llm/config*.yaml` is empty). The live copy is `mcp/plugins/pobr_*` (wired at
`estate_mcp.py:16,340,359,375`) and the two have drifted (522 vs 520 lines; hashes differ). So: the
door owns the shape, the router copy is deleted (spec §4 ladder step 5), and the shape is inherited
everywhere because every surface reaches the estate through the door or the executor.

**D7. Scope is four shapes, not twenty surfaces.**
Every surface — agent action, discovery and capabilities, services, cluster, source control, CI and
CD, the greenlane, research, claims, JEV, Otto, the concierge face, the fleet view, voice, memory,
file and code read/write/diff — is a caller of one of four shapes (intent call; receipt/envelope;
doc/claim; catalog/graph node) at one of the same three boundaries. Per-product schemas would be
the eleventh copy (AGENTS.md §6) and are refused: `docs/research/2026-10-25-constrained-formats-surfaces.md`.

## Consequences

- The estate can now say, with a number, whether its agent door describes itself — and CI goes red
  when a lane makes it worse.
- `bin/idp-ci` gains rung 1c.3. It is diff-scoped like the rungs around it, and it runs the gate's
  own proof suite, so "the gate that cannot fail" cannot happen one level up.
- The baseline at `docs/research/2026-10-25-constrained-formats.baseline.json` is a debt record, not
  a target: step 2 of the ladder regenerates it as part of its own change.
- A research digest can no longer name a project the harvest did not measure: `bin/oss-harvest
  --verify` refuses one, because a number without a harvested row is an assertion.
- R4 is documented as measuring the **documentation gap** the door is about to enforce, not a
  runtime difference: `resolve_args` does not read `required` today.
- The digest's headline numbers are rows in the witness store (`bin/estate-claim-check add`),
  so `bin/idp-ci`'s facts rung re-executed them while they were live -- `facts.jsonl: 4/4 active
  facts re-executed, verdict: PASS`, measured 2026-10-25. They were written with
  `valid_for_s=86400` and have since aged into `retired`, which is the store working as designed:
  a measurement is a fact with a validity window, not a permanent assertion. That is why the
  permanent check on the documents is `--verify` (citations) and the gate's baseline (violations),
  and not a remembered number.
- The estate-wide ledger turns "structured formats" from a proposal into a map with one open cell
  (shape 1, validate — this change) and one live duplicate (shape 2's two PoBR copies), so the next
  lane does not have to re-derive either. Its citations are held to the same rule as the digest:
  `bin/oss-harvest --verify` and `bin/arxiv-harvest --verify` run over it by test.
- The verifier learned to tell a command from a citation (a fenced block is stripped): the first
  document to contain shell made it report 8 unharvested repos that were a branch, a directory and
  five prose slash-pairs. The fix narrows *where* it looks, not *how hard* — the same token in
  prose still fails, and a test asserts both halves.

## Alternatives rejected

- **A strict-only rung.** Red on `main` before any lane acts; every lane bypasses it.
- **A new schema library or format (Pydantic at the door, BAML, a grammar file).** A second layer,
  and none of them is already in the estate's request path.
- **Prompt-level instruction to emit valid args.** `2608.24569v2`: constraints decay across
  handoffs; a prompt is a handoff, a validated payload is not.
- **Fixing the 74 violations in this change.** It would turn one reviewable measurement into a
  74-file diff across other agents' lanes.

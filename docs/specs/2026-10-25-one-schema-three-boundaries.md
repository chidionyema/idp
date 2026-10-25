# One schema at three boundaries

**Status:** proposal, with the measurement landed · claim idp#7089 · 2026-10-25
**Companion research:** `docs/research/2026-10-25-constrained-formats-research.md`
**Estate-wide ledger:** `docs/research/2026-10-25-constrained-formats-surfaces.md` (which surface
crosses which shape at which boundary — measured, per surface)
**Decision record:** `docs/decisions/0042-one-schema-at-every-boundary.md`

---

## 1. Problem

An agent in this estate crosses three boundaries on every action, and at each one the estate
accepts whatever parses:

| Boundary | Where | What is accepted today | Measured 2026-10-25 |
|---|---|---|---|
| **decode** | `platform/llm/config.yaml` lane `minimax_json` | `{"type": "object", "additionalProperties": true}` — no field required, none refused | 1 lane, 0 constraints |
| **validate** | `platform/estate/bin/estate-execute` `resolve_args` | any `k=v`; `int` coerced, nothing else; `required` never read; omission becomes `""` | 96 committed intents: 74 violations; 340 installed: 110 (R0 3, R1 42, R3 10, R4 55) |
| **repair** | the caller's retry loop | a repaired answer is indistinguishable from a first-pass one | no receipt field distinguishes them |

The evidence for why this matters is not architectural taste. `2609.23742v1` measures that
constrained decoding removes structural failure and leaves the semantic gap; `2608.24569v2` and
`2605.06445v2` measure that constraints decay across handoffs and loose specifications;
`2608.04355v1` measures that format repair masquerades as self-correction.

**The decode row is worse than "0 constraints", and the estate can prove it.** The enforcement
layer for boundary 1 was built and never loaded: `litellm-local/callbacks/pobr_enforce.py`
(fail-closed by design — it refuses every completion when its wrapper is missing) plus
`pobr_schema.py` (522 lines) and `pobr_gate.py` (364), and `rg pobr platform/llm/config*.yaml`
returns **zero matches**. A second copy lives at the MCP door (`mcp/plugins/pobr_schema.py` 520,
`pobr_gate.py` 362, wired at `estate_mcp.py:16,340,359,375`) and the two have already drifted
(`pobr_schema.py` 522 vs 520; the hashes differ). AGENTS.md §6 reproduced inside the one layer
that is supposed to stop it. That is measured in
`docs/research/2026-10-25-constrained-formats-surfaces.md` §5.

## 2. Goal

One schema per payload, enforced at the boundary that can actually refuse it, with a measurement
that fails when the estate gets worse. Nothing new is invented: `schema/intent/*.schema.json` +
`bin/intent-compile` already validate typed JSON payloads with `jsonschema`'s
`Draft202012Validator` and refuse an unknown field by name. This spec **extends that mechanism to
the agent's own arguments** and to the lane's `response_format`.

## 3. The three boundaries and their acceptance criteria

### B1 — decode

- A typed lane's `response_format.schema` is a `$ref` to a committed file under `schema/`, the same
  file callers validate the response against.
- `additionalProperties: false`, an explicit `required` list.
- A typed-lane call with no schema is refused **before dispatch**, naming the lane.
- **Accepted when:** a production router log line refuses such a call, and a typed response
  validates against the file its request declared.

### B2 — validate

`resolve_args` refuses, naming the intent and the argument:

1. an argument the intent does not declare (`intent x declares no arg 'branch'`);
2. a value that does not match the declared type (no coercion to `0`);
3. an omission of a `required: true` argument (no silent `""`);
4. an intent file that does not parse (parser line, not a traceback).

- **Accepted when:** a production executor log line shows a named refusal, and
  `tests/test_schema_conformance.py::test_the_live_executor_accepts_an_undeclared_arg` has been
  **inverted** (asserting the refusal) — never deleted, because the inverted test is the pin.

### B3 — repair

- Every repair emits the PoBR receipt the estate already verifies: attempt index, failing schema,
  failing field, escaping used.
- A repaired answer is reported as `repaired`, never as a first-pass success.
- **Accepted when:** a production log line carries `repaired: true` plus the failing field, and a
  repaired answer counted as first-pass fails a test.

## 4. The ladder (why this change ships the measurement, not the tightening)

| Step | Change | Refuses | Ships in |
|---|---|---|---|
| 1 | `bin/schema-conformance` + baseline + rung 1c.3 of `bin/idp-ci` | a *new* violation | this change |
| 2 | per-intent args schema generated from `args:`, validated by `intent-compile`'s validator | nothing yet (reporting only, in the same ratchet) | next |
| 3 | `resolve_args` refuses undeclared + wrong type | the two defects in §1 | next |
| 4 | `resolve_args` enforces `required`; unparseable intent refused by the parser | the remaining two | after the corpus is clean |
| 5 | delete the orphaned `pobr_*` copy under litellm-local, so boundary 1's owner is the door's copy | the duplicate (AGENTS.md §6) | next lane — the directory holds no loaded config, so the deletion is provable by one grep |

**Why the tightening is not in this change:** 74 violations sit in `main`. Turning enforcement on
today refuses correct work in every lane — the guard-that-refuses-correct-work defect (R38) — and
the door is one file every agent calls. Step 1 makes the corpus measurable and the regression
impossible; steps 2-4 are separate changes against a corpus that is already shrinking, each with a
test that must be inverted rather than added.

## 5. The rules the gate measures

| Rule | Statement | Why it is a rule here |
|---|---|---|
| R0 | an unparseable intent is never clean | the door hands `yaml.safe_load` a file it cannot read and raises `ScannerError` |
| R1 | every declared type is one `resolve_args` coerces (`string`, `int`) | 42 args are `bool`/`number`/`boolean`/`float` and arrive as strings |
| R2 | every `{{var}}`/`<<var>>` is declared or supplied by an earlier step | an undeclared placeholder is `""` at runtime |
| R3 | `<<var>>` (raw) is refused | `{{var}}` is `shlex.quote`d; `<<var>>` is the unquoted path |
| R4 | an arg with no default says `required: true` | measures the documentation gap the door is about to enforce; `resolve_args` does not read `required` today |

Two modes: **strict** (exit 1 on any violation — fails on `main` today, asserted by a test) and
**ratchet** (`--baseline`, exit 1 only on a new violation; exit 2 when blind). CI runs the ratchet.

## 6. Non-goals

- No second validator, schema language or registry (AGENTS.md §6).
- No new receipt format: PoBR's envelope is extended by one field, not replaced.
- No change to `resolve_args` in this change (§4).
- No model, provider or routing change.
- **No validator in `platform/llm/front.py`.** It is a 221-line bytes-only forwarder whose own
docstring says it never changes so it never restarts (`rg 'json|schema'` over it returns nothing),
and it sits on every agent's hot path. Boundary 1 reaches the inference server as a request field;
boundary 2 belongs at the door. `docs/research/2026-10-25-constrained-formats-surfaces.md` §5.
- **No schema per product.** Otto, the concierge face, the fleet view, JEV and voice are callers
of the two doors, not owners of a shape: 6+2 intents between them, all counted in the same 96.

## 7. Proof plan

| Claim | Instrument |
|---|---|
| the gate can fail | `test_the_strict_mode_fails_on_main_as_it_stands`, `test_the_ratchet_refuses_a_new_violation` |
| the gate is not blind | `test_the_ratchet_is_blind_without_its_baseline` (exit 2, not 0) |
| the defect is live, not described | `test_the_live_executor_accepts_an_undeclared_arg` loads `estate-execute` itself |
| the numbers are re-executable | `bin/schema-conformance intents --json`; the digest's §8 ledger |
| the digest cites nothing unharvested | `bin/oss-harvest --verify` (a named project without a harvested row is refused) |
| CI enforces it | rung 1c.3 of `bin/idp-ci`, scoped to the paths that can change the verdict |

## 8. Falsifiers and risks

- If a lane can be made safe by a bigger model rather than by a schema, B2 is a performance
  decision. `2608.24569v2` / `2605.06445v2` say constraint loss is a property of handoffs and
  specifications, not parameter count.
- If constrained decoding closed the semantic gap at this estate's sizes, B2 would be redundant;
  `2609.23742v1` is the counter-evidence.
- Grammar-constrained output is a **capability** funnel, not a safety one (`2606.11817v1`): B1 must
  never be described as a jailbreak defence.
- A ratchet can ossify a baseline. Mitigation: the gate prints `fixed` counts, and step 2 of the
  ladder regenerates the baseline as part of its own change.

## 9. Estate-wide scope: four shapes, three boundaries

When the question is "does this cover the estate?", the answer is a table rather than a list of
products. Every surface named — agent action, discovery and capabilities, services, cluster,
source control, CI and CD, the greenlane, research, claims, JEV, Otto, the concierge face, the
fleet view, voice, memory, file and code read/write/diff — resolves to one of **four shapes**
(intent call; receipt/envelope; doc/claim; catalog/graph node) crossing one of the same **three
boundaries**. Twenty surfaces, four shapes; most surfaces are callers and inherit a fix at the
door.

| Shape | Owner | Enforced today? |
|---|---|---|
| intent call | `schema/intent/*.schema.json` + `bin/intent-compile` | **no** — this change measures it |
| receipt / envelope | `schema/mutation-envelope.schema.json` + `bin/idp-reversibility-gate` | partly, and in two divergent copies (§1) |
| doc / claim | `bin/claim-gate` | yes, by regex |
| catalog / graph node | `schema/catalog-ontology.json` + `bin/idp-catalog-spec-type-gate` | yes for catalog |

This change closes exactly one cell: **shape 1, validate**. The ledger says why the other cells are
not this change's, and what each would need.

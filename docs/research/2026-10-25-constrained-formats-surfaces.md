# Structured formats across the estate: four shapes, three boundaries, one unplugged slot

Companion to `docs/research/2026-10-25-constrained-formats-research.md` (the literature and the
ecosystem) and `docs/specs/2026-10-25-one-schema-three-boundaries.md` (the change). This document
answers a different question: **where, in this estate as it actually exists today, does a shape
cross a boundary — and is it enforced there or merely parsed?**

Every number below was measured by a committed instrument, this session, on this checkout
(the schema-contract lane, on top of the main branch at `04e3609bd`). Section 7 lists the commands.

---

## 1. Method, and the one rule it follows

The rule: **a surface counts as covered only if a named tool refuses a malformed value on it.**
A type hint is not coverage. A docstring that says `args: {task, repo}` is not coverage. A parser
that reads a field and falls back to a default is not coverage — it is a parser.

That rule is the whole reason this document is short. Applied to the estate's twenty-odd named
surfaces it collapses them into four shapes, because most surfaces are *callers* of a shape, not
owners of one. Otto, the concierge face, the fleet view, JEV and voice all reach the estate
through the same two doors (the MCP plugin and the executor), so a shape fixed at the door is
fixed for all of them at once — and a shape fixed only in one caller is fixed nowhere.

## 2. First principles: hallucination has exactly three places to enter a call

An agent that acts on this estate produces a value that must survive three transitions. Each
transition is a boundary, and each boundary fails in its own way:

| Boundary | The question it asks | The failure when absent | What it costs to hold |
|---|---|---|---|
| **Decode** | may the model emit this token at all? | the model is free to write prose where a value belongs; the defect is born here | grammar / JSON-schema handed to the inference server, per model |
| **Validate** | is this value legal here? | an illegal call is *accepted*, then fails later or silently does something else | a schema at the door that refuses, plus a gate that fails CI |
| **Repair** | is this attempt distinguishable from the last? | attempt 3 is reported as a success; nobody can tell a first-pass answer from a third-try one | the attempt number and the violated rule in the receipt |

The literature in the companion digest is almost entirely about boundary 1; the estate's measured
defects are almost entirely at boundary 2; and boundary 3 is where the estate is thinnest of all —
a repaired call and a clean call produce the same receipt today.

**Why this framing matters for scope:** boundaries 1 and 2 have different owners and cannot share
an implementation. Boundary 1 lives where tokens are chosen (the inference server, behind the
router). Boundary 2 lives where calls are admitted (the door). Any proposal that puts both in one
place is wrong about one of them.

## 3. The estate has four shapes, not twenty

Measured inventory. "Owner" means a file that would have to change if the shape changed.

| # | Shape | Owner today | Size | Enforced? |
|---|---|---|---|---|
| 1 | **intent call** — a YAML intent's args, at the moment an agent invokes it | `schema/intent/*.schema.json` (4 files) + `bin/intent-compile` (368 lines) | 96 committed intents | **No.** `bin/schema-conformance` measures 74 violations; the door's `resolve_args` coerces only `int` and ignores unknown keys |
| 2 | **receipt / envelope** — what an action leaves behind | `schema/mutation-envelope.schema.json`, read by `bin/idp-reversibility-gate` (260 lines) | 1 schema, 2 divergent copies of the PoBR implementation (§5) | **Partly.** Enforced at the MCP door; the router copy is loaded by no config |
| 3 | **doc / claim** — a markdown artifact that asserts work | `bin/claim-gate` (534 lines) | every commit on a lane | **Yes, by regex.** A `Claim: <owner>/<repo>#<n>` line is required; the *content* of a doc is unconstrained |
| 4 | **catalog / graph node** — a typed entity and a predicate | `schema/catalog-ontology.json`, read by `bin/idp-catalog-spec-type-gate` (221 lines); `growmos` for the graph | 1 ontology | **Yes for catalog.** The graph accepts a free-text predicate |

So of the four shapes, **two have a gate** (claim, catalog), **one has a gate that is not the
door** (envelope), and **one has a schema file that nothing on the call path consults** (intent).
That is the entire estate-wide scope. It is not twenty schemas; it is four shapes and three of
them already have an owner that needs a call path, not a rewrite.

## 4. The surface ledger

Each surface the founder named, mapped to its shape and boundary. "Coverage" is what exists
today, measured.

| Surface | Shape it crosses | Boundary held today | Measured state |
|---|---|---|---|
| **Agent action (intents)** | 1 | validate | **gap** — 74 violations; gate now fails CI on new ones |
| **Discovery / capabilities** | 1 | validate | **gap** — `estate_list` returns intents; an intent whose args are unparseable is still listed |
| **JEV** | 1 | validate | **gap** — 2 intents (`jev.decide`, `jev-setup`); counted in the 96, so the same 74 apply |
| **Voice / face / concierge / Otto / fleet** | 1 | decode + validate | **gap** — 6 intents; these are callers of the door, so fixing shape 1 fixes all six at once |
| **Services / cluster mutation** | 2 | validate | **partly** — `idp-reversibility-gate` reads the envelope; two implementations disagree (§5) |
| **Source control** | 3 | validate | **held** — `claim-gate` refuses a commit with no claim |
| **CI and CD** | 3 + 2 | validate | **held** — a rung fails; receipt is the CI log |
| **Greenlane / lanes** | 3 | validate | **held** — same claim gate, run inside `lane-submit` |
| **Research** | 3 | validate | **held, and it is the model to copy** — `bin/arxiv-harvest --verify` refuses a digest that cites an id it did not harvest; `bin/oss-harvest --verify` refuses a project it did not measure |
| **Claims** | 3 | validate | **held by regex** — shape enforced, content not |
| **Memory / recall** | 4 | validate | **partly** — `remember` takes typed fields (`kind` ∈ 5 values); free text elsewhere |
| **Diff and code write** | — | **none** | **no boundary in the estate** — patch tooling (`git apply`, `rescued_patches2/*.patch`) trusts the patch; the constraint is git's own |

The last row is the honest finding: **reading, writing and diffing files and code is the one surface the estate
does not shape at all**, because it delegates to git. The literature behind each row is in §9. That is defensible (git is a strict
validator with a 20-year adversarial record) — and it means the research on patch formats is
*informing*, not actionable inside this platform today.

## 5. The routing-layer question: the slot is cut, and it is empty

The founder's question — *do we use the routing layer so the shape slots in everywhere?* — has a
measured answer, and it is not the one the proposal assumed.

**Every laptop harness reaches models through `127.0.0.1:4000` → `platform/llm/front.py` → LitellM
on 4001 or 4002.** That is the one choke point every agent shares, so it is the obvious place for
an estate-wide shape. It cannot hold boundary 2, for a reason that is in the file: `front.py` is
221 lines whose own docstring calls it a **bytes-only forwarder** — `rg 'json|schema'` over it
returns **nothing**. Teaching it to validate would make it a JSON-aware proxy: a new layer, on the
hot path of every agent, with its own failure mode. The router is also deliberately the thing that
*never restarts*, which is the opposite of what a validator wants to be.

Boundary 1 is a different matter: that is exactly where a grammar belongs, because it must reach
the inference server as part of the request. `platform/llm/config.base.yaml:150` already discusses
`response_format` as a pass-through field, so the plumbing exists.

**And here is the finding that settles it.** The estate already built the router-side enforcement
layer, and never plugged it in:

| Copy | Lines | Wired? | Evidence |
|---|---|---|---|
| `pobr_enforce.py` in the litellm-local callbacks dir (+ `pobr_schema.py` 522, `pobr_gate.py` 364, `pobr_gate_wrapper.py`) | 107 + 886 | **No** — `rg pobr platform/llm/config*.yaml` returns zero matches | loaded by no LitellM config |
| `mcp/plugins/pobr_{schema 520, gate 362, orchestrator, grant}.py` | 882+ | **Yes** — `estate_mcp.py:16,340,359,375` (`pobr_submit`, `pobr_status`) | live at the MCP door |

Two copies of one layer, and they have already drifted: `pobr_schema.py` is 522 lines at the
router and 520 at the door, `pobr_gate.py` 364 and 362, and the hashes differ. This is
AGENTS.md §6's "one of each layer; a second copy is stitching and gets deleted" reproduced in the
one place the estate least wants it — the schema layer itself.

The architectural reading is unambiguous: **the estate already decided, by building it, that
boundary 2 belongs at the door and not at the router.** The router copy is the orphan. The right
move is not to route shape enforcement through the router; it is to delete the orphan and let the
door own the shape. `pobr_enforce.py`'s fail-closed design (it refuses *every* completion when its
wrapper is missing) is the correct instinct in the wrong place.

### The split that follows

```
model ──[decode: grammar or response_format]──> router ──> agent
                                                          │
                                          [validate: the door]  ← intents, receipts, claims, catalog
                                                          │
                                          [repair: the receipt] ← attempt number + violated rule
```

- **decode** — inference server, reached through LitellM's `response_format` or guided-decoding field.
  One implementation, per model, no estate code on the hot path.
- **validate** — the door (`mcp/plugins/estate_mcp.py`, executor `resolve_args`), one schema per
  shape, plus a CI rung per shape. **This is the boundary this change ships.**
- **repair** — the receipt. An attempt carries its number and the rule it violated, so "passed"
  and "passed on the third try" are different facts.

## 6. Scope that works, and scope deliberately refused

**In scope, now:** shape 1 validate. It is the only shape with a schema file, no call path, and a
measured 74 violations. One gate, one rung, one baseline.

**In scope, next, in this order** (each is a file that already exists):

1. `resolve_args` refuses an undeclared key — currently held by claim #7085; not this change.
2. delete the orphaned copy of `pobr_*` under the litellm-local callbacks dir, so shape 2 has one owner.
3. `response_format` actually populated for the JSON lanes, so boundary 1 is real rather than a
   comment on line 150.
4. the attempt number in the receipt, so boundary 3 exists at all.

**Refused, with reasons:**

- **A schema per product.** Otto, face, fleet and voice are callers, not owners. Per-product
  schemas would be the eleventh copy (AGENTS.md §6).
- **A validator in `front.py`.** §5: it is a bytes-only forwarder by design, and every agent's
  request would then depend on a schema check on the hot path.
- **Constraining prose.** The claim and research shapes are enforced where they can be (a required
  line, a verified citation) and left free where they cannot. A schema over a document's argument
  would fail on the first honest exception.
- **Shaping the diff.** Delegated to git, which refuses more than any schema this estate would
  write.

## 7. How to re-measure every number here

```bash
ls platform/estate/intents/*.yaml | wc -l                      # 96
ls schema/intent/*.schema.json | wc -l                          # 4
bin/schema-conformance intents --root platform/estate/intents \
  --baseline docs/research/2026-10-25-constrained-formats.baseline.json   # 74 known
wc -l platform/llm/front.py                                     # 221
rg 'json|schema' platform/llm/front.py                          # (no output: bytes-only)
rg -n pobr platform/llm/config*.yaml                            # (no output: never loaded)
wc -l litellm-local/callbacks/pobr_schema.py mcp/plugins/pobr_schema.py   # 522 / 520
shasum litellm-local/callbacks/pobr_schema.py mcp/plugins/pobr_schema.py  # differ
rg -n pobr mcp/plugins/estate_mcp.py                            # 16, 340, 359, 375
for f in bin/idp-reversibility-gate bin/idp-catalog-spec-type-gate bin/claim-gate bin/intent-compile; do wc -l $f; done
ls platform/estate/intents/ | grep -icE 'jev'                   # 2
ls platform/estate/intents/ | grep -icE 'voice|face|otto|concierge|fleet'   # 6
```

## 8. What this document does not claim

It does not claim the estate is unsafe today: three of the four shapes are gated, and the
ungated one (intent args) has a door that coerces and defaults rather than executing arbitrary
input. It claims that the *shape* is not enforced where the literature says hallucination is born,
that two copies of the envelope layer disagree, and that every number above is reproducible with
section 7's commands on any checkout.

---

## 9. Appendix: the literature behind each row of §4

A second live harvest, `bin/arxiv-harvest --queries
 docs/research/2026-10-25-constrained-formats-surfaces.queries.txt --out
 docs/research/2026-10-25-constrained-formats-surfaces-harvest.json`: **19 queries, 446 records, 0
failed queries, harvested 2026-10-25**. As with the companion digest, each record is an id, a
published date and the **first sentence of the abstract** — abstracts were not read in full, so
nothing below is attributed to a paper's body. The newest record per query, which is what §4's
rows rest on:

| §4 row | Query theme | Newest record | Published | What its opening line says |
|---|---|---|---|---|
| Agent action | tool calling | 2610.22511v1 | 2026-10-15 | a unified evaluation spine for benchmarking and judging agent tool use |
| Agent action — **boundary 2** | function calling + schema + error | **2610.10062v1** | 2026-10-07 | "Loud Failures, Quiet Failures" — tool faults that raise versus faults that pass silently |
| Agent action — **boundary 2** | agent handoff, context loss | **2608.24569v2** | 2026-08-25 | "When 'Must' Becomes 'Maybe'" — the erosion of workflow constraints |
| Discovery / capabilities | tool retrieval | 2609.18283v1 | 2026-09-16 | where agents should live, by energy and memory characterisation |
| Discovery / capabilities | skill discovery | 2608.01851v1 | 2026-08-03 | weights versus skills: a survey of robot-learning transfer |
| CI and CD | CI + agentic repair | 2610.07289v1 | 2026-10-05 | low-latency agentic program repair, catching developers in the flow |
| CI and CD | build-failure repair | 2602.20284v1 | 2026-02-23 | PhantomRun: auto repair of compilation errors in embedded software |
| Source control | pull request + agent | 2610.21914v1 | 2026-10-15 | code health predicts the token cost of agentic code review |
| Claims / research | provenance, claim, verification | **2610.21144v1** | 2026-10-15 | "Plausible Is Not Enough" — trust and evidence in AI-authored pull requests |
| Research | literature review agent | 2605.26340v1 | 2026-05-25 | ScientistOne: human-level autonomous research via chained workflow |
| Memory | agent memory + structured | **2610.30755v1** | 2026-10-22 | is complex agentic memory needed at all, or is naive RAG stronger |
| Observability | telemetry, semantic | 2610.28611v1 | 2026-10-20 | semantic observability for autonomous-system diagnostics |
| Multi-agent | multi-agent protocol | 2610.06192v1 | 2026-10-05 | how LLM aggregators count restated claims (copies versus sources) |
| Code edit | code editing agent | 2610.29641v1 | 2026-10-21 | recursive code evolution for task-oriented semantic communication |
| Code edit / repo | repository-level generation | 2610.30188v1 | 2026-10-20 | agentic verified optimisation of real-world software |
| File read and write | file read plus write agent benchmark | 2610.13000v1 | 2026-10-09 | structured advice distillation steering executor agents |
| Diff / patch | patch generation | 2610.11578v1 | 2026-10-08 | Chronos: code agents reasoning over software evolution |
| Diff / patch | diff + code review | 2607.17532v1 | 2026-07-20 | CommitLLM: a fine-tuned pipeline for git commit messages |
| Voice | speech + agent + tool | 2610.25344v1 | 2026-10-18 | TOMORI: tool-orchestrated interaction with REAPER |

Three of these bear directly on the argument rather than decorating it. **2610.10062** names the
failure this ledger measures — a *quiet* failure, where a call is malformed and nothing raises.
**2608.24569** names the mechanism by which a shape decays: a constraint stated once as "must"
becomes "maybe" as a workflow is edited, which is exactly what the estate's 74 violations are (a
schema file that exists while the call path does not enforce it). **2610.30755** is the useful
counterweight to this whole line of work: it reports that elaborate agentic memory is often not
worth its complexity — the same scepticism applies here, and is why §6 refuses a schema per
product and why the ladder in §6 has four steps and not fourteen.

Verify any citation above against the committed harvest:

```bash
bin/arxiv-harvest --verify docs/research/2026-10-25-constrained-formats-surfaces-harvest.json \
  docs/research/2026-10-25-constrained-formats-surfaces.md
```

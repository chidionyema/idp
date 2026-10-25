# Structured formats as a hallucination brake

**What the literature shows, what the ecosystem ships, and what this estate has actually broken.**

Claim: idp#7089 · agent `estate-agent` · on the `schema-contract` lane · 2026-10-25
Evidence: two live harvests committed beside this file, and one gate that fails.

---

## 0. The claim, in one paragraph

The estate does not have a hallucination problem in the abstract. It has a **shape** problem at
three boundaries an agent crosses on every action, and at all three the estate currently accepts any
payload whose *syntax* parses. A model can name an argument that nothing declares and the door runs
it; a model can answer on the only lane configured to force JSON, and that lane forces
`{"type": "object", "additionalProperties": true}` — JSON, with no field required and no field
refused; a model can have its malformed output quietly repaired, and the repair is indistinguishable
from reasoning in the record afterwards. The literature harvested below is unusually direct about
this: constrained decoding removes **structural** failure and leaves the **semantic** gap standing
(`2609.23742v1`); constraints that hold inside one call **decay** across handoffs and across
iterations (`2608.24569v2`, `2605.06445v2`); format repair **masquerades** as self-correction
(`2608.04355v1`). The proposal is therefore not a new framework. It is one schema, applied at the
three boundaries the estate already owns — decode, validate, gate — with the estate's own
`bin/intent-compile` as the worked example and `bin/schema-conformance` as the measurement.

---

## 1. How this was produced, and what it does not claim

| Artifact | What it is | Live measurement |
|---|---|---|
| `docs/research/2026-10-25-constrained-formats-harvest.json` | arXiv harvest, written by `bin/arxiv-harvest` | 1,244 unique records, 32 queries, 0 errors, `harvested_at` **2026-10-25T00:48Z** |
| `docs/research/2026-10-25-constrained-formats.queries.txt` | the 32 queries, so the set is reproducible | 9 themes: `agent-workflow` 184, `schema-guided` 169, `structured-reasoning` 165, `spec-driven` 159, `hallucination` 143, `constrained-decoding` 141, `verification-loop` 124, `evaluation` 85, `typed-prompting` 74 |
| `docs/research/2026-10-25-constrained-formats-oss.json` | GitHub + PyPI harvest, written by `bin/oss-harvest` | 31 reachable projects + 1 deleted, 20 PyPI packages, 7 GitHub searches, `harvested_at` **2026-10-25T00:56Z** |
| `bin/schema-conformance` + `docs/research/2026-10-25-constrained-formats.baseline.json` | the gate and its ratchet baseline | 74 violations over 96 committed intents; 110 over the 340 installed ones |
| `tests/test_schema_conformance.py` | the gate's own proof that it can fail | 24 tests, each executing the estate's own code |

**What the arXiv harvest stores** is the id, title, published date, the first sentence of the
abstract, and the query that found it. It does **not** store full abstracts, and this digest has not
read the papers. Where it says *"the record's opening line says"*, that is exactly the evidence
behind it — a citation, not a claim about what the paper proved.

**What the OSS harvest stores** is stars, forks, last push, latest release tag and date, licence and
archived flag per project, read from the API on the harvest date. Stars prove adoption and a push
date proves maintenance. **Neither proves the tool works**, and no benchmark number in this digest
comes from a harvest file.

**Every number below is from one of those files or from a command run on 2026-10-25.** Section 8 is
the ledger, with the instrument for each.

---

## 2. The defect, measured before any paper is cited

### 2.1 The door accepts an argument nobody declared

`platform/estate/bin/estate-execute` (`resolve_args`, from line 247) is the only thing between an
agent and every intent in the estate. Its whole arg handling is 26 lines:

```python
for arg in raw_args:
    if "=" in arg:
        k, v = arg.split("=", 1)
        resolved[k] = v            # <- no check that the intent declares k
...
for name, spec in arg_defs.items():
    if name not in resolved:
        resolved[name] = spec.get("default", "")   # <- an omitted arg is ""
    if spec.get("type") == "int":
        try:    resolved[name] = int(float(str(resolved[name])))
        except: resolved[name] = 0                 # <- a wrong type becomes 0
```

Measured on the live module — `tests/test_schema_conformance.py` loads the door itself through a
`SourceFileLoader`, not a copy of its logic:

- `resolve_args({"args": {"repo": {...}}}, ["repo=chidionyema/idp", "branch=main", "--dry-run=1"])`
  returns `branch: "main"` and `--dry-run: "1"`. **No refusal.** An invented argument is silently
  honoured.
- `resolve_args({"args": {"count": {"type": "int"}}}, ["count=lots"])` returns `count: 0`. A wrong
  type becomes a plausible value — and `0 failures` reads exactly like `0 successes`.
- `resolve_args({"args": {"repo": {"type": "string"}}}, [])` returns `repo: ""`.
- `required` appears **nowhere** in the file (`grep -n required platform/estate/bin/estate-execute`
  finds nothing). An intent that marks an arg `required: true` documents a refusal the door does not
  make.

### 2.2 The intent corpus does not describe itself

`bin/schema-conformance intents` on the 96 intents committed under `platform/estate/intents`:

```
intents                96
  with args            85
  args declared        263
  args typed           233
  args required        2
  undeclared {var}     0 intent(s)
  raw <<var>>          5 intent(s)
  unreadable           0
violations             74
```

and on the 340 intents the agent actually calls on this machine (`~/.estate/intents`):

```
intents                340
  with args            104
  args declared        314
  args typed           272
  args required        5
  undeclared {var}     0 intent(s)
  raw <<var>>          7 intent(s)
  unreadable           3
violations             110      (R0 3, R1 42, R3 10, R4 55)
```

The 42 un-coercible declarations are not a rounding error, they are a taxonomy. Of 314 declared
args: `string` 246, `int` 26, `bool` 35, `number` 3, `boolean` 2, `float` 1, untyped 1. **Every
`bool`, `number`, `boolean` and `float` arrives at its step as a string**, because `resolve_args`
coerces `int` and nothing else.

The three `R0` intents are the sharpest finding in this section: `merge-gate-to-main`, `pobr-gate`
and `test-commit` are **not parseable YAML** (an unquoted `": "` inside `description:`), and calling
one produces a `ScannerError` traceback, not a refusal:

```
$ ~/.estate/bin/estate-execute test-commit
Traceback (most recent call last):
  File ".../estate-execute", line 508, in cmd_run
    intent = yaml.safe_load(f)
ScannerError: mapping values are not allowed here
```

A door that crashes is not a door that refuses. `pobr-gate` is the intent behind the PoBR receipt
checker (`platform/llm/callbacks/pobr_enforce.py`) — that statement is about the shape of the files,
not the behaviour of the callback, and both are worth having.

### 2.3 The one lane that forces JSON is configured to force nothing

`platform/llm/config.yaml:99-114` defines `minimax_json`, the constrained-decoding variant of the
primary lane (MUM-289). Its whole contract:

```yaml
response_format: { type: json_schema, json_schema: { name: estate_json, schema: { type: object, additionalProperties: true } } }
```

`additionalProperties: true` with `{"type": "object"}` and no `required` list is the weakest schema
JSON Schema can express: it refuses **nothing** and duplicates nothing. The estate pays for a
constrained lane and receives the shape `{}` — precisely the gap `2609.23742v1` measures between
structural validity and semantic correctness.

The same file records the mirror-image failure at line 815: `deepseek-v4-flash answered 97 and
failed 24, all 24 being one message ("This response_format type is unavailable now") from a caller
that sets a parameter Otto never sends.` The estate therefore has both halves of the problem in one
file: a lane whose schema constrains nothing, and a lane that refuses a `response_format` the caller
never asked for. **The structured-output contract is per-lane and per-caller, and nothing in the
router checks that the two agree before dispatch.**

### 2.4 What the estate already got right

Prior art exists, and this proposal extends it instead of shadowing it:

- `bin/intent-compile` — a deterministic compiler for typed JSON intents, `additionalProperties:
  false`, refusing an unknown field **by name**, with exit status 0, 1 or 2. It already imports
  `jsonschema` and
  validates with `Draft202012Validator` (line 335) against `schema/intent/*.schema.json`. **This is
  the estate's worked example of exactly what section 6 proposes**, and it covers four cluster-config
  payloads.
- `platform/llm/callbacks/pobr_enforce.py` — a LiteLLM `CustomLogger` that injects a PoBR envelope
  instruction pre-call and verifies the receipt post-call, deliberately **fail-closed**: no wrapper,
  every call refused. The structural-refusal pattern is already in the request path.
- `mcp/plugins/estate_memory.py` — a structured ingest format for memories, so a memory has fields
  rather than prose.
- `facts/estate.jsonl` + `bin/estate-claim-check` — every stored number must re-execute, and CI goes
  red on STALE, CONTRADICTED, UNWITNESSED or TAMPERED. This digest is held to that rule by section 8.

---

## 3. What the literature says (1,244 records, 32 queries, read at the abstract's first line)

### 3.1 Structure works at the token boundary — and stops exactly at meaning

The most useful record in the harvest for this estate is `2609.23742v1` — *Constrained Decoding
Eliminates Structural Failures in Small LLMs but Reveals a Scale-Dependent Semantic Gap*
(2026-09-20). Its opening line frames the exact deployment this estate is in: small models used for
JSON, function calling and extraction. The title carries the finding, and that finding is why a
schema alone is not the answer.

Around it the engineering is real and current:

| id | date | what its opening line says |
|---|---|---|
| `2608.10137v2` | 2026-08-10 | grammar-constrained decoding masks non-conforming tokens at each step — the mechanism, stated plainly |
| `2608.03065v1` | 2026-08-04 | LLMs are widely used for structured output; this makes the masking cheap enough to deploy |
| `2607.18357v1` | 2026-07-20 | models write code "increasingly inside agents and serving systems that compile, execute, or dispatch generated code without line-by-line review" — the estate's own situation |
| `2610.29749v1` | 2026-10-21 | metamodel-guided decoding for DSLs: constrain to the *metamodel*, not merely the grammar |
| `2608.12574v1` | 2026-08-12 | selection from a finite set of valid strings — the trie and finite-automaton case |
| `2607.11951v1` | 2026-07-11 | enterprise SQL wants validity **plus** per-role policy **plus** a compliance-grade record of every decision |

`2607.11951v1` is the strongest architectural statement available to us: the enterprise requirement
is not "syntactically valid SQL", it is valid **and** policy-respecting **and** auditable. That is
this proposal's three boundaries, arrived at independently in a different domain.

### 3.2 Constraints decay across handoffs — the estate's actual failure mode

If one paper should change how this estate builds, it is `2608.24569v2` — *When "Must" Becomes
"Maybe": Erosion of Workflow Constraints in LLM Agent Handoffs* (2026-08-25). Its opening line:
agents "build on one another's work through summaries, plans, and other intermediate artifacts."
Every handoff in this estate is a summary — a brief, a plan, a claim comment, a PR description, a
memory. A `must` in the original becomes a `maybe` in the summary, and the summary is what the next
agent reads.

`2605.06445v2` — *Constraint Decay: The Fragility of LLM Agents in Backend Code Generation*
(2026-05-07) — names the same shape from the code side: agents do well "under loose specifications",
and the constraints that matter are the ones a loose specification omits.

`2606.09395v1` (*Empirical Study for Structured Output Control in LLMs for Software Engineering*,
2026-06-08) opens on why a schema belongs at the boundary rather than in the prompt: "LLM-generated
outputs in software engineering rarely exist in isolation." They are consumed by a tool, a gate, or
another agent. `2606.11470v2` (survey, 2026-06-09) is a map of reasoning paradigms and failure modes
— useful for names, not for proof.

**Consequence:** a structured payload at the *door* (validate the args of the call) outlives a
structured instruction in the *prompt* (ask the model to be careful), because the payload cannot
decay into a summary. That is the whole argument for boundary 2 in section 6.

### 3.3 Repair is not correction

`2608.04355v1` — *The Calibration Floor: Format Repair Can Masquerade as Self-Correction at
Small-to-Mid Scale* (2026-08-05) — opens: "Accuracy changes after language-model self-revision are
usually interpreted as changes in reasoning." The finding, in the title, is that making a malformed
answer well-formed changes the measured accuracy while changing nothing about reasoning.

This is the most dangerous of the three boundaries precisely because it *looks* like the fix. A
pipeline that retries until the JSON parses reports a better number and has learned nothing. The
proposal's answer is not "never repair" — it is **repair as a separate, counted, visible step**,
never folded silently into the answer, and never counted as the first attempt's success.

`2605.13076v3` (*TruncProof*, 2026-05-13) covers the adjacent failure: JSON generation that runs out
of tokens. A truncated object is invalid JSON, and a schema-validating retry loop calls that a model
failure when it is a budget failure.

### 3.4 The schema is the agent's interface, not its prompt

`2605.04107v1` — *TSCG: Deterministic Tool-Schema Compilation for Agentic LLM Deployments*
(2026-05-04) — opens with the observation this estate should take literally: production agent
frameworks transmit tool schemas as JSON, "a format designed for machine parsing, not for
interpretation by language models." The schema in the wire format and the schema the model reads are
two different artifacts. `2608.02650v1` (*HyperAgent*, 2026-07-31) plans over tool-schema hypergraphs;
`2605.26165v1` (2026-05-24) shows tool schemas competing with retrieved context for the window;
`2604.25359v1` (*The Structured Output Benchmark*, 2026-04-28) is the closest thing to a grading
instrument for extraction.

The practical reading: **the schema the door enforces and the schema the model is shown must be the
same object.** In this estate the model is shown `{"type": "object", "additionalProperties": true}`
(section 2.3) and the door enforces nothing (section 2.1). Neither end carries the contract.

### 3.5 Spec to code is a solved-enough pattern to copy, not invent

| id | date | opening line |
|---|---|---|
| `2609.39568v1` | 2026-09-30 | LLMs "may generate unreliable code on corner cases missed by testing, while formal verification can provide machine-checkable guarantees" |
| `2609.06041v1` | 2026-09-05 | models "still struggle with challenging programming tasks that require understanding rich natural language requirements" |
| `2609.00568v1` | 2026-09-01 | requirements-driven agents for code generation |
| `2609.12012v1` | 2026-09-10 | tests "increasingly participate in the decisions made by" models and agents |
| `2608.13077v1` | 2026-08-13 | formal specs give strong guarantees; their cost is what limits adoption |

### 3.6 Compiles is not correct, and green is not proof

`2610.28675v1` — *Compilation Is Not Correctness* (2026-10-19) — is the paper AGENTS.md section 3
would have written: a program that compiles and executes has been shown to compile and execute.
`2609.26749v1` (2026-09-22) is the measured version of the same complaint: "compile rate is a
commonly reported proxy for progress: whether the generated patch compiles" — and the paper is about
that proxy failing. `2609.09315v1` (2026-09-08) asks whether traditional test criteria even detect
bugs in generated code. `2609.16604v1` (2026-09-15) supplies the positive version: execution feedback
is useful *because* unit tests are objective.

**For the estate:** a green gate is a claim about the gate. The gate in this change is written so it
fails today (section 2.2) and is ratcheted so it fails again the moment a lane makes the shape worse
— and `tests/test_schema_conformance.py` proves both directions, because a gate that cannot fail is
decoration.

### 3.7 Preempt at decode rather than correct afterwards

`2609.15745v1` (*Look Before You Leap*, 2026-09-14) opens: early factual errors "compound through
autoregressive generation in a snowballing effect that neither post-hoc correction nor weight-level
intervention can effectively preempt." Repairing a hallucinated *field* after the fact is the cheap
version of this problem; the expensive version is that the wrong value is already in the sentence.

### 3.8 The adversarial edge — where this approach does not save you

Three records keep the proposal honest:

- `2606.11817v1` — *Grammar-Constrained Decoding Can Jailbreak LLMs into Generating Malicious Code*
  (2026-06-10). A grammar is a **capability** funnel, not a safety one: constraining the shape of
  output can make harmful output easier to elicit, because the hard part (syntax) is done for the
  model.
- `2605.07698v1` (2026-05-08) — masking plus speculative decoding does not sample from the
  grammar-conditional distribution users usually intend. **The distribution you get is not the
  distribution you asked for**, which rules out any claim of the form "the constrained lane is just
  the normal lane with a guard".
- `2606.21619v1` — *The Alignment Problem in Constrained Code Generation* (2026-06-19) — opens on
  the ordinary failure: generated code "frequently contain[s] syntax or type errors that result in
  compilation failures". Constraining syntax does not align intent to output.

---

## 4. The ecosystem, measured (31 live projects, 20 packages, 2026-10-25)

### 4.1 Constrained-generation engines

| repo | stars | last push | latest release | released | licence |
|---|---:|---|---|---|---|
| `guidance-ai/guidance` | 21,808 | 2026-05-21 | `0.3.2` | 2026-03-18 | MIT |
| `dottxt-ai/outlines` | 15,974 | 2026-09-21 | `1.3.3` | 2026-08-06 | Apache-2.0 |
| `eth-sri/lmql` | 4,224 | 2025-05-22 | `v0.7.3` | 2023-10-14 | Apache-2.0 |
| `noamgat/lm-format-enforcer` | 2,040 | 2026-04-04 | `v0.11.2` | 2025-08-09 | MIT |
| `mlc-ai/xgrammar` | 1,973 | 2026-10-23 | `v0.2.8` | 2026-09-24 | Apache-2.0 |
| `microsoft/llguidance` | 899 | 2026-10-14 | — | — | MIT |

The engines are small next to the serving stacks that embed them — `vllm-project/vllm` 95,343 stars
(`v0.32.0`, 2026-10-18), `sgl-project/sglang` 37,800 (`v0.5.22`, 2026-10-16) — and that is the
adoption fact that matters: **grammar-constrained decoding now ships inside the inference server**,
not as a bolt-on. `ggml-org/llama.cpp` (132,254 stars, `v0.7.0`) carries grammars in `main`, and
`huggingface/transformers` (168,101 stars, `v5.20.2`) carries the tokenizer-side machinery.

### 4.2 Typed-output layers over the provider APIs

| repo | stars | last push | latest release |
|---|---:|---|---|
| `stanfordnlp/dspy` | 38,773 | 2026-10-23 | `3.4.1` |
| `openai/openai-python` | 31,940 | 2026-10-23 | `v3.37.0` |
| `pydantic/pydantic-ai` | 20,841 | 2026-10-24 | `v2.61.0` |
| `567-labs/instructor` | 14,060 | 2026-10-20 | `v1.17.0` |
| `boundaryml/baml` | 9,432 | 2026-10-24 | `baml-language-0.22.3-nightly.20261023.a` |
| `microsoft/TypeChat` | 8,691 | 2026-10-24 | — |
| `guardrails-ai/guardrails` | 7,558 | 2026-10-24 | `v0.11.0` |
| `NVIDIA/NeMo-Guardrails` | 7,361 | 2026-10-24 | `v0.24.1` |
| `anthropics/anthropic-sdk-python` | 4,003 | 2026-10-23 | `v2.3.0` |

### 4.3 What is current at the package level

`outlines 1.3.3` (2026-08-06), `guidance 0.3.1` (2026-02-03), `xgrammar 0.2.8` (2026-09-24),
`llguidance 1.9.1` (2026-09-30), `lm-format-enforcer 0.11.3` (2025-08-24), `instructor 1.17.0`
(2026-09-09), `pydantic 2.14.1` (2026-10-11), `pydantic-ai 2.61.0` (2026-10-24), `dspy 3.4.1`
(2026-10-12), `jsonschema 4.26.0` (2026-01-07), `openai 3.37.0` (2026-10-22), `anthropic 2.3.0`
(2026-10-23), `mcp 2.3.0` (2026-10-02). `lmql`'s last PyPI upload was **2023-10-14**: the engine with
the most elegant idea is the one that stopped.

### 4.4 Maintenance, adoption, and one deletion

Of the 31 reachable projects, **23 were pushed within 30 days** of the harvest and 26 within 90; 14
of the 27 with a release cut one in the last 30 days; none is archived. One project in the registry
is gone: **`sourcegraph/cody` returns HTTP 404** — the repository no longer exists, and the harvest
records that as an error rather than dropping the row. The estate's own lesson, restated: a
maintenance claim needs a date, and a dependency is a bet on a project's continued existence.

### 4.5 What the ecosystem does not sell

No project in this harvest promises that a valid payload is a **correct** one. The gap the literature
names in section 3.1 is exactly the gap the tooling leaves open — which is why boundary 2 has to
live in the estate's own door and not in a library purchase.

---

## 5. What this estate already owns (so nothing here is built twice)

AGENTS.md section 6: one of each layer, and a second copy is stitching. Applied to this proposal:

| Layer | The estate's one copy | What this change does |
|---|---|---|
| Typed schema + validator | `schema/intent/*.schema.json` + `bin/intent-compile` (jsonschema `Draft202012Validator`) | **extends**: an args schema in the same directory, validated by the same library |
| Request-path structural refusal | `platform/llm/callbacks/pobr_enforce.py` (fail-closed receipt) | **extends**: the receipt is where a repair step declares itself |
| Structured payload for memory | `mcp/plugins/estate_memory.py` | unchanged |
| Re-executable numbers | `facts/estate.jsonl` + `bin/estate-claim-check` | **feeds**: this digest's numbers become instruments in that store |
| Agent-action door | `platform/estate/bin/estate-execute` | **the place boundary 2 lands** (laddered in the spec, not in this change) |
| Measurement | *nothing existed* | **new**: `bin/schema-conformance`, with a ratchet baseline |

No new validator, no new schema language, no new receipt format, no second registry.

---

## 6. The proposal: one schema, three boundaries

### Boundary 1 — decode: a lane declares the shape it enforces, or it is not the typed lane

**Today:** `minimax_json` declares `{"type": "object", "additionalProperties": true}`
(section 2.3) — JSON in, JSON out, nothing refused.

**Change:** a typed lane's `response_format` schema is the *same* schema the caller validates
against afterwards — one object, two uses. `additionalProperties: false`, an explicit `required`
list, and a `$ref` to a committed file under `schema/` so the decode-time contract and the
validate-time contract cannot drift. A call routed to a typed lane with no schema is refused before
dispatch, because a lane that always refuses is latency, not redundancy — the rule this file already
applies to dead failover hops at line 815.

**What refuses:** the router, pre-dispatch, naming the lane and the missing schema.
**What proves it:** a production router log line refusing the call, and a typed call whose response
validates against the same file its request declared.

### Boundary 2 — validate: the door refuses an argument the intent never declared

**Today:** `resolve_args` honours any `k=v`, coerces only `int`, ignores `required`, hands `""` for
an omission, and crashes on an unparseable intent (sections 2.1-2.2).

**Change:** an intent's `args:` block compiles to a JSON Schema through the same code path that
already compiles intent payloads — `bin/intent-compile`'s `jsonschema` call, aimed at args instead of
at a cluster payload. Then:

1. an undeclared `k=v` is **refused by name** (`intent x declares no arg 'branch'`);
2. a type mismatch is **refused**, not coerced to `0`;
3. `required: true` is **enforced**, so an omission is a refusal rather than `""`;
4. an intent that does not parse is refused with the parser's line, not a traceback.

The ladder is deliberate and lives in `docs/specs/2026-10-25-one-schema-three-boundaries.md` section
4: measure (landed in this change), then the per-intent schema gazetteer, then enforcement rule by
rule with the corpus fixed repo by repo. The test
`tests/test_schema_conformance.py::test_the_live_executor_accepts_an_undeclared_arg` **executes
today's defect** and is written to be **inverted, never deleted**, on the day the door learns to
refuse — it is the pin that stops the fix being quietly undone.

**What refuses:** `estate-execute`, before the first step runs.
**What proves it:** a production executor log line refusing a named undeclared argument.

### Boundary 3 — repair is a step with a receipt, never a silent retry

**Today:** a malformed response can be repaired and counted as success, and the record afterwards
cannot tell the two apart (section 3.3).

**Change:** every repair attempt emits the PoBR receipt the estate already verifies — attempt index,
the schema that failed, the field that failed, the escaping used — and a repaired answer is reported
as `repaired`, never as a first-pass success. `platform/llm/callbacks/pobr_enforce.py` already
refuses a call with no receipt; this adds the field that distinguishes `answered` from `answered
after repair`. Nothing new is built: the receipt exists, the fail-closed check exists.

**What refuses:** the PoBR verifier, when a response was repaired and the receipt does not say so.
**What proves it:** a production log line whose answer carries `repaired: true` and the failing
field.

### The gate: what makes this operational rather than a document

`bin/schema-conformance intents` measures the corpus against four rules, each one a rule the estate
already believes elsewhere:

- **R0** an unparseable intent is never clean;
- **R1** every declared arg names a type the door actually coerces (`string`, `int`);
- **R2** every `{{var}}` / `<<var>>` a step interpolates is declared, or supplied by an earlier step;
- **R3** `<<var>>` (raw, unquoted) is refused — it is the one path by which a caller-supplied string
  reaches a shell unquoted, where `{{var}}` is `shlex.quote`d;
- **R4** an arg with no default says `required: true`.

Two modes, both tested:

- **strict** — exit 1 on any violation. It fails on `main` today at 74 violations, and
  `test_the_strict_mode_fails_on_main_as_it_stands` asserts that, so nobody can claim the corpus is
  clean.
- **ratchet** — `--baseline docs/research/2026-10-25-constrained-formats.baseline.json`, exit 1 only
  on a violation the baseline does not carry. This is the mode CI can run on day one without failing
  74 innocent lanes, and a lane that fixes intents gets `fixed` lines rather than a stale exemption.
  `test_the_ratchet_refuses_a_new_violation` proves it can fail;
  `test_the_ratchet_is_blind_without_its_baseline` proves it exits 2 rather than 0 when it cannot see.

It runs as rung 1c.3 of `bin/idp-ci`, beside the facts re-execution rung (1e) and
scoped to the diff that can change its verdict, so the gate is enforced by CI rather than by
a promise in this document: on a lane that adds a violation the run goes red, and on a lane
that pays none of the 74 down it stays green.

---

## 7. What would falsify this

1. If the undeclared-argument path were already refused somewhere upstream of `resolve_args`,
   section 2.1 would be measuring defence in depth rather than a gap. It is not: `grep` for
   `additionalProperties`, `jsonschema` and `required` in that file finds nothing.
2. If the typed lane's `additionalProperties: true` were an intentional lax default with a stricter
   schema applied by each caller, section 2.3 would be a documentation defect. The harvest says the
   opposite — the wire schema is the only contract (`2605.04107v1`).
3. If constrained decoding were shown to close the semantic gap at the sizes this estate runs,
   boundary 2 would be redundant. `2609.23742v1` is the counter-evidence, and it is the record this
   digest most wants to be wrong.
4. If a lane could be made safe by a bigger model instead of a schema, the three boundaries would be
   a performance decision. `2608.24569v2` and `2605.06445v2` say constraint loss is a property of
   handoffs and specifications, not of parameter count.

---

## 8. Ledger — every number, and the instrument that produced it

| Number | Instrument | Where it is now |
|---|---|---|
| 1,244 records · 32 queries · 0 errors · 2026-10-25T00:48Z | `bin/arxiv-harvest` | `docs/research/2026-10-25-constrained-formats-harvest.json` |
| 96 committed intents · 74 violations | `bin/schema-conformance intents --root platform/estate/intents --json` | this change's CI rung, baseline file |
| 340 installed intents · 110 violations (R0 3, R1 42, R3 10, R4 55) | `bin/schema-conformance intents --root ~/.estate/intents` | machine-local, quoted in section 2.2 |
| 314 args: string 246 · int 26 · bool 35 · number 3 · boolean 2 · float 1 · untyped 1 | `bin/schema-conformance intents --json \| jq .stats.types` | section 2.2 |
| 3 unparseable intents, `ScannerError` traceback | `~/.estate/bin/estate-execute test-commit` | quoted verbatim in section 2.2 |
| 4 accept-anything behaviours in `resolve_args` | `tests/test_schema_conformance.py` (loads the live door) | section 2.1 |
| 31 reachable projects · 1 HTTP 404 · 20 packages · 2026-10-25T00:56Z | `bin/oss-harvest` | `docs/research/2026-10-25-constrained-formats-oss.json` |
| 23 pushed ≤30d · 26 ≤90d · 14 of 27 released ≤30d · 0 archived | `bin/oss-harvest` output recomputed | section 4.4 |
| stars and dates per project | GitHub REST via authenticated `gh api` | section 4 tables |
| package versions and upload dates | PyPI JSON API | section 4.3 |
| 97 answered / 24 refused on `deepseek-v4-flash`; 24,955 log lines on gemini over 2h | `platform/llm/config.yaml:800-830` (recorded there when measured) | section 2.3 |

Quoted from a harvest file rather than measured by this change: the arXiv records' titles and
opening sentences (section 3), and the recorded router measurements (section 2.3). Both are labelled
as such where they appear.

---

## 9. References

**arXiv** (ids as committed in the harvest): `2609.23742v1`, `2608.10137v2`, `2608.03065v1`,
`2607.18357v1`, `2610.29749v1`, `2608.12574v1`, `2607.11951v1`, `2608.24569v2`, `2605.06445v2`,
`2606.09395v1`, `2606.11470v2`, `2608.04355v1`, `2605.13076v3`, `2605.04107v1`, `2608.02650v1`,
`2605.26165v1`, `2604.25359v1`, `2609.39568v1`, `2609.06041v1`, `2609.00568v1`, `2609.12012v1`,
`2608.13077v1`, `2610.28675v1`, `2609.26749v1`, `2609.09315v1`, `2609.16604v1`, `2609.15745v1`,
`2606.11817v1`, `2605.07698v1`, `2606.21619v1`.

**Projects** (as harvested, stars and dates in section 4): `guidance-ai/guidance`,
`dottxt-ai/outlines`, `eth-sri/lmql`, `noamgat/lm-format-enforcer`, `mlc-ai/xgrammar`,
`microsoft/llguidance`, `vllm-project/vllm`, `sgl-project/sglang`, `ggml-org/llama.cpp`,
`huggingface/transformers`, `stanfordnlp/dspy`, `openai/openai-python`, `anthropics/anthropic-sdk-python`,
`pydantic/pydantic-ai`, `567-labs/instructor`, `boundaryml/baml`, `microsoft/TypeChat`,
`guardrails-ai/guardrails`, `NVIDIA/NeMo-Guardrails`.

**Inside the estate:** `bin/intent-compile`, `schema/intent/`,
`platform/estate/bin/estate-execute`, `platform/llm/config.yaml`,
`platform/llm/callbacks/pobr_enforce.py`, `mcp/plugins/estate_memory.py`, `facts/estate.jsonl`,
`bin/estate-claim-check`, `bin/schema-conformance`.

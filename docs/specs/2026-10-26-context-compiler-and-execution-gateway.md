# The estate's Context Compiler and Intelligence Broker — one gateway, one context plane

**Date:** 2026-10-26
**Status:** **ACCEPTED as the estate's direction** (founder, 2026-10-26: "document this as very
important") · implementation staged, not started
**Importance:** VERY IMPORTANT — this is a first-class estate specification, not a note
**Decision:** [`docs/decisions/2026-10-26-one-context-compiler-and-one-execution-gateway.md`](../decisions/2026-10-26-one-context-compiler-and-one-execution-gateway.md)
**Measured surface:** [`docs/reference/estate-agent-surface-map.md`](../reference/estate-agent-surface-map.md)
**Measurement script:** `bin/estate-surface-map` (re-runnable; the map is not a hand-maintained
snapshot)

---

## 0. The founder's ask, in the founder's terms

1. **Document the vision as very important.** A Context Compiler and an Intelligence Broker,
   impact-aware, are the estate's direction — they belong in the estate's own spine, in a
   document the estate cites, not in a consultant's slide.
2. **Do not duplicate what the estate already owns.** Before building anything, measure the
   existing execution boundary and the existing code/impact layers, and build on them.
3. **The first architectural question is the gateway:** does the estate already have a central
   execution gateway through which Pi, Claude Code and other coding agents operate, or can they
   independently reach filesystem, shell, Git and model providers?

**Answer, measured on 2026-10-26 (see the reference map for the evidence):** *No, the estate does
not have one central gateway.* Pi reaches the estate through an intents-only MCP server **and**
through a free-form `estate_execute` door; Claude Code reaches the shell through its own Bash
tool, where the only estate gate is session discipline (a declared plan), not policy; the two
runtimes sit on different model routes (the cloud estate provider vs the laptop fallback
router). There is no component that every agent call passes through, so there is nowhere
universal to insert a compiler or a policy.

**Consequence:** establishing that boundary is not a side quest. It is the first engineering
task, and it is what makes the rest of this document possible.

---

## 1. What the two components are

### 1.1 The Context Compiler (CC)

An **impact-aware context assembler**. Given a task, it resolves the task to a **bounded,
ranked, provenance-carrying set of sources** and a **token budget**, and it hands that to the
model instead of the model's own wandering reads.

It is not a summarizer and it is not a retriever bolted onto search. Its unit of work is the
**task → source set** decision, and it answers three questions the estate currently answers
badly:

- **What matters for this task?** Impact, not similarity. The estate already computes impact:
  `bin/idp-affected-graph` (AST + import edges, prompt/schema coupling, graph topology, decided
  by Jev) and `bin/catalog-projection` (a deterministic, content-addressed component/edge graph).
  The compiler consumes them; it does not build a second index.
- **How much of it fits?** A budget per task, per surface, per tier. The estate already has the
  request-side ceiling (`platform/llm/request_ceiling.py`, 200k tokens by default) and a
  per-call outcome ledger (`platform/llm/efficiency_gateway.py` → `~/.estate/efficiency-ledger.jsonl`).
  The compiler moves the budget **upstream**, to where the source set is chosen.
- **Where did each piece come from?** Every assembled item carries its source, its hash and the
  impact score that selected it. An answer that cannot cite its sources is not assembled context;
  it is a guess.

**Anti-goal of the CC:** it is *not* a second code index. The estate already owns the AST/symbol
layer (ZeroEdge's TTCS tree-sitter code graph) and the deterministic component graph
(`catalog-projection`). A new tree-sitter index is a stitch and is deleted in the same change
(AGENTS.md §6).

### 1.2 The Intelligence Broker (IB)

The **mediator between an agent and a model**. Everything an agent asks a model to do passes
the broker, and the broker decides — deterministically, with a recorded reason — four things:

| The broker decides | Today |
|---|---|
| **Whether the call is allowed** | Scattered: intents-only in the Pi MCP path, the plan gate in Claude Code, nothing in the raw command door. |
| **Which model/lane serves it** | The router does this, but the *client* pins the lane and can bypass the cloud route (measured: Claude Code on the laptop fallback). |
| **What context rides with it** | The read-shunt compresses a file *after* the model asked for it, fail-open. |
| **What it costs and what it buys** | `max_budget` is enforceable only where the router holds the state (the cloud route). |

The broker is the estate's **single decision point**: it is where "intents only", "cloud is the
default route", "context budget", "impact-aware source selection" and "cost ceiling" become
properties of the *system* rather than habits of individual agents.

### 1.3 The Execution Gateway (EG)

The **single door** between an agent and the machine: filesystem, shell, Git, model providers.
The estate has the pieces — the executor daemon (`platform/executor/daemon.py`, 100s ceiling,
recorded in `~/.estate/logs/mcp.jsonl`), the intent registry (`~/.estate/intents/*.yaml`, 346
intents on the measured day), the MCP plugin (`mcp/plugins/estate_mcp.py`, intents-only tools),
the plan gate (`platform/estate/memory/plan.py`) — but no agent is *required* to pass through
them. The EG is the component that makes that requirement true, and the IB is what sits behind
it.

**One sentence:** *the broker decides, the compiler assembles, the gateway is the only way in.*

---

## 2. Contracts (normative)

These are the shapes. A component that cannot satisfy them is not the component.

### C1 — Context Compiler contract

```
resolve(task: str, *, surface: str, budget_tokens: int,
        tier: "free" | "standard" | "frontier") -> ContextPlan
```

`ContextPlan` **must** carry:

| Field | Meaning |
|---|---|
| `items[]` | each with `source` (path or URL), `sha256`, `tokens`, `impact_score`, `rank`, `why` (the impact evidence that selected it) |
| `budget_tokens` | the ceiling this plan was built against |
| `used_tokens` | the measured cost of the plan (never an estimate presented as a measurement) |
| `coverage` | the impact nodes in the task's blast radius that the plan does **not** cover (omissions are stated, not hidden) |
| `plan_hash` | `sha256` over the ordered items — the same task and the same graph state produce the same plan |

**Invariants:** deterministic for a given `(task, surface, graph_state, budget)`; every item
carries provenance; `used_tokens ≤ budget_tokens`; the plan never exceeds the surface's
`per_request_token_ceiling`.

### C2 — Intelligence Broker contract

```
decide(call: ModelCall) -> Decision
```

`Decision` **must** carry: `allow` (bool), `route` (lane + provider + endpoint), `transform`
(the request as it will be sent — possibly rewritten, truncated or refused), `budget_cost`
(estimated and measured), `reason` (the decision's ground, in one sentence), `policy_ref`
(which invariant decided it).

**Invariants:** every model call in the estate carries a `Decision`; a `Decision` that refuses
says what would have been allowed; the broker never mutates a call without recording the
transformation.

### C3 — Execution Gateway contract

```
execute(intent: str, args: dict, *, agent: str, surface: str) -> Result
```

**Invariants:** the gateway accepts **intents**, not command strings; a command that has no
intent is *refused with the name of the intent it should have been*; every execution is
recorded (who, which surface, which intent, ceiling, outcome); the gateway's refusal path is
the only way an agent's machine access is stopped, on every surface.

---

## 3. Invariants (falsifiable — each names the thing that would catch its violation)

| # | Invariant | The falsifier |
|---|---|---|
| I1 | **No agent reaches a model without a broker decision.** | A counter over `~/.estate/efficiency-ledger.jsonl`: rows without a `policy_ref` (once the field exists) — the check fails while the count is non-zero. |
| I2 | **No agent reaches the machine except through the gateway.** | The gate refuses any free-form command entrance (the `estate_execute` shape) on any surface; the refusal is a test, not a convention. |
| I3 | **Context is assembled, not accumulated.** | Every task's model call carries a `ContextPlan` hash; the plan's `used_tokens` is measured, not estimated. |
| I4 | **Impact decides relevance.** | Every selected source carries an `impact_score` whose evidence is the estate's own affected-graph, not a similarity score. |
| I5 | **One index.** | A tree-sitter/AST index exists in exactly one place (ZeroEdge's TTCS) and one deterministic component graph (`catalog-projection`). A second AST index is refused at review. |
| I6 | **The cloud route is the default; the laptop is the fallback.** | The router config renders from its registry (`bin/idp-vendor-render --check` is green) and no client pins a lane that bypasses the cloud route. |
| I7 | **Cost is enforceable where it is spent.** | The router that serves the surface holds the virtual key and the budget state; a call over budget is observed refusing. |
| I8 | **The context plane is measurable.** | The efficiency ledger carries tokens-in, tokens-selected, tokens-dropped, cost and outcome per call, and the ratio is read, not asserted. |
| I9 | **Refusal is a first-class outcome.** | Every refusal names the invariant it hit and what would have been allowed. |
| I10 | **The map is re-measured, not remembered.** | `bin/estate-surface-map` runs in CI on a schedule and its output is stored; a change to the estate's surface that does not move the map is a missing measurement, not a silent change. |

---

## 4. Placement against the measured estate (reuse, not duplication)

| What the estate already owns | Role in this design | What is **not** built |
|---|---|---|
| `bin/catalog-projection` (deterministic, content-addressed component/edge graph) | the substrate the compiler ranks over | a new AST/symbol index |
| `bin/idp-affected-graph` (three-layer impact, Jev-decided) | the impact signal (`impact_score`, `why`) | a second impact analyser |
| ZeroEdge + TTCS (tree-sitter code graph) | symbol/AST retrieval for the compiler | a new tree-sitter service |
| `platform/llm/request_ceiling.py` (200k) | the hard ceiling the compiler budgets under | a second ceiling |
| `platform/llm/efficiency_gateway.py` + `~/.estate/efficiency-ledger.jsonl` | the measurement substrate for I1, I8 | a second ledger |
| `~/.estate/hooks/idp-read-shunt` (350-line threshold, fail-open) | becomes a **fallback** compression under the compiler, not the selection mechanism | — |
| `platform/executor/daemon.py` (100s ceiling, recorded) | the execution substrate of the gateway | a second executor |
| `~/.estate/intents/*.yaml` (346) | the only vocabulary the gateway accepts | — |
| `platform/estate/memory/plan.py` (plan gate) | the session-discipline gate; it stays, it is not a policy gate | — |
| `platform/llm/config.yaml` + `bin/idp-vendor-render` | the route registry the broker draws from | a second router config |

**The one genuinely new component is the broker's decision point** — a single place that every
model call passes through, which the estate does not have today. The compiler is a new
*composition* of existing pieces. The gateway is the existing executor, made mandatory.

---

## 5. The sequence (staged; each step has a done-check that can fail)

**m1 — Measure (done, 2026-10-26).** `bin/estate-surface-map` prints the agent surface and the
named gaps. *Done-check:* the script runs and its output is stored in
`docs/reference/estate-agent-surface-map.md`.

**m2 — Close the wide door.** The free-form command entrance (Pi's `estate_execute`) becomes
intents-only, or becomes an intent that names itself. *Done-check:* a command with no intent is
refused with the name of the intent it should have been; the refusal is witnessed in the
ledger.

**m3 — Put the broker in the path of every model call.** One decision point, in front of the
cloud route, recording `policy_ref` per call. *Done-check:* the I1 counter is zero across a
measured day of real traffic.

**m4 — Move the context decision upstream.** The compiler resolves task → bounded source set
using the estate's own impact graph and content-addressed catalog, and the read-shunt's
fail-open digest becomes the fallback for what the compiler could not select. *Done-check:* a
measured day shows tokens-selected ÷ tokens-in, and the quality gate (agreement on a fixed
probe set) does not fall against the current baseline.

**m5 — Make the map part of the estate's measurement.** The surface map runs on a schedule, is
stored, and a change to the surface that does not move the map is a red check. *Done-check:* the
scheduled run exists and its output is committed by the same pipeline that commits the rest of
the evidence.

**m6 — Move the remaining runtimes onto the cloud route and the gateway.** Claude Code's
`ANTHROPIC_BASE_URL` moves from the laptop fallback to the cloud route, and its shell calls
become gateway calls. *Done-check:* the estate's own budget enforcement is observed refusing on
that surface (I7), and the laptop router still answers (the fallback stays).

---

## 6. Non-goals

- **Not** a second code index, a second router, a second ledger, or a second executor.
- **Not** a replacement for the read-shunt, the plan gate, the claim gate or the affected-graph.
- **Not** an LLM that "decides what to read" on its own: selection is deterministic over the
  estate's own graph, with a model used only where the estate already uses one (digesting,
  summarising, judging) and always with the free lane first.
- **Not** a change to the founder's workflow: the founder still speaks, still watches `/fleet`,
  still gets a voice answer. The compiler and the broker are invisible to him except that the
  estate gets cheaper and sharper.

---

## 7. Open questions for the consultant

1. **Where exactly does the broker sit** — in front of the router (estate-wide) or in the
   client (per-surface)? The estate's answer so far is "in front of the router, on the cloud
   route", because that is where budget and cache state live.
2. **Does the compiler run on the task side (an agent asks "compile context for X") or the
   response side (the broker decides what rides with the call)?** The estate's answer so far is
   both: the compiler is a service the broker calls.
3. **How is "impact" scored for a task that is not a code change** (a founder question, a
   production incident)? The affected-graph fails open toward running; the compiler must not
   ship an empty context in that case.
4. **What is the right budget ladder?** Free tier first (`ollama`, `groq`, `cerebras` …), then
   standard, then frontier — the numbers live in the router registry, not in the compiler.

---

## 8. What "done" looks like for this work

The vision is done when **every** model call in the estate carries a broker decision with a
`policy_ref` (I1), **every** machine action carries an intent (I2), **every** task's context
carries a plan hash and a measured token count (I3, I8), and the surface map is re-measured by
CI rather than remembered (I10). Until then, this document is the estate's direction and the
measured map is its honest starting position.

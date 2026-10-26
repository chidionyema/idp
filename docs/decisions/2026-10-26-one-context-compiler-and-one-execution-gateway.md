# One context compiler, one broker, one gateway — and no second index

**Date:** 2026-10-26
**Status:** accepted (founder, 2026-10-26 — "document this as very important")
**Spec:** [`docs/specs/2026-10-26-context-compiler-and-execution-gateway.md`](../specs/2026-10-26-context-compiler-and-execution-gateway.md)
**Evidence:** [`docs/reference/estate-agent-surface-map.md`](../reference/estate-agent-surface-map.md) ·
measured by `bin/estate-surface-map`
**Issue:** #7252

## Context

The estate's law is one sentence: **if an action is not a YAML intent, the agent cannot perform
it** (AGENTS.md §7). The machine does not match the law. Measured on 2026-10-26:

- **Pi** reaches the estate two ways — an intents-only MCP server (`estate_list`, `estate_show`,
  `estate_invoke`, plus approval-gated `estate_create`) *and* `estate_execute`, which takes a
  **free-form command string** and runs it through the executor daemon (100s ceiling, recorded).
- **Claude Code** reaches the shell through its own Bash tool. The only estate gate in the path
  is the **plan gate** (`platform/estate/memory/plan.py`): it refuses a shell call when the
  session has no declared plan or no BDD scenario for the active sub-goal. That is session
  discipline. It does not inspect *which* command runs. `permissions.deny` is empty and
  `autoMode.allow` carries ten broad grants (read any file, run `python3`, `git`, `gh`, merge).
- The two runtimes sit on **different model routes**: Pi on the estate (cloud) provider,
  Claude Code on the laptop fallback router at `127.0.0.1:4000` — where the virtual key and
  budget state do not live, so cost cannot be enforced where that runtime spends.
- Nothing decides **what an agent may read**. The read-shunt compresses a large file to a digest
  *after* the model asked for it, and it is fail-open by construction. The 200k request ceiling
  refuses an oversized call; it does not put the right source in it.

So the estate has the *parts* of a gateway — executor, intents, router, ledger, impact graph —
and none of the *whole*. Every agent runtime has its own door, and enforcement is therefore
per-surface and uneven.

## Decision

**The estate builds one Context Compiler, one Intelligence Broker and one Execution Gateway, and
it builds them out of what it already owns.**

1. **One context compiler.** Task → bounded, ranked, provenance-carrying source set, decided by
   **impact**, not similarity. It ranks over the estate's own deterministic component graph
   (`bin/catalog-projection`) and the estate's own affected-graph (`bin/idp-affected-graph`).
2. **One intelligence broker.** Every model call passes one decision point that answers: is this
   allowed, on which lane, with what context, at what cost — with a recorded reason and the
   invariant that decided it.
3. **One execution gateway.** Intents, not command strings. The existing executor daemon and the
   346-intent registry are the gateway; the wide entrance is closed.
4. **No second index.** The AST/symbol layer stays where it is (ZeroEdge's TTCS); the component
   graph stays where it is (`catalog-projection`). A second tree-sitter index is a stitch and is
   deleted in the same change (AGENTS.md §6).
5. **The map is measured, not remembered.** `bin/estate-surface-map` prints the agent surface
   and the named gaps, and its output is the evidence every claim in this record rests on.
6. **The design is placed against measured work in flight, not against a static estate.** The
   map carries a **flux section**: what landed on `main` in the window, and which live claim
   holds which paths. On 2026-10-26 (three-day window) that measurement read 95 commits across
   95 pull requests, 13 specs and 8 decisions touched, and a board of LIVE 7 / RECOVERABLE 49 /
   LANDED 58 over 70 claims. No lane in flight was building a context compiler, a broker or a
   mandatory gateway; the three that touch this design touch it as substrate to reuse (the
   capability registry, the impact graph, the affected-graph) or as law already decided
   (cloud-first, machine-first T-7). Nothing was duplicated, and the one shared file — the
   generated registry snapshot — is resolved by regenerating it, which the registry's own drift
   gate demands.

## Alternatives rejected

| Alternative | Why not |
|---|---|
| **Enforce per-runtime** (keep hooks per agent, add a Claude Code deny list) | Leaves two enforcement regimes and one free-form command entrance. A gate that exists on one surface is not a gate. Cost: a policy change becomes N changes, N surfaces drifting. |
| **Build a new AST/tree-sitter index for the compiler** | The estate already owns it (ZeroEdge's TTCS) and already owns a deterministic content-addressed component graph. A new index is the estate's most repeated mistake. |
| **Let the model decide what to read** (an LLM summariser in front of the reads) | Non-deterministic, uncostable, and it re-does on every call what the affected-graph already computes deterministically. The model may be used to digest and judge — never to be the index. |
| **Enforce at the read hook only** (upgrade the read-shunt into a gate) | The read-shunt is fail-open by design and only sees reads. It cannot see shell, Git or the model route — three of the four doors. |
| **Make the laptop router the default** (so every runtime shares one router) | Superseded by the founder's 2026-10-26 ruling: cloud is the default, the laptop is the fallback. The laptop route also lacks the virtual-key state that makes `max_budget` enforceable. |
| **Wait for a bigger refactor** | The wide door (`estate_execute`) is the cheapest high-value fix available today and is independent of everything else in this record. |

## Consequences

**Positive.**

- Every invariant in the spec becomes a property of the system instead of a habit of one agent.
- Context spend becomes measurable at the place where it is chosen, not only at the router where
  it is refused.
- The estate's existing layers (catalog, affected-graph, ledger, executor, intents) get used
  rather than replaced — no second of anything.
- A consultant designing against the estate can point at one map and one spec instead of
  reverse-engineering the runtime.

**Negative, and accepted.**

- m2 (closing the wide door) **will** break callers that use `estate_execute` with a raw
  command. That is the point, and the cost is paid once.
- A single decision point is a **single point of failure**. It must fail **closed for
  authorization** and **open for observation**: a broker fault must not take the estate's
  ability to work down, and must not take it silently either.
- The compiler's quality is the estate's quality. The impact graph currently **fails open
  toward running**; the compiler must never ship an empty context because of that.

**Risks to watch.** The drift between the installed runtime and the tree (measured gap G7: the
live Pi extension runs `growmos context` at session_start and the repository copy does not) is
exactly the failure mode a measured map catches and a written document does not.

**A second risk, measured on 2026-10-26:** the estate's own registry gate refused `main` after
`bin/estate-surface-map` was added to the tree — the registry snapshot is a pure function of the
tree, so a new executable must be registered and the snapshot regenerated, or the gate fails the
merge. That refusal is correct and it is the mechanism working. The lesson this record carries
forward is the one the estate already wrote down: **the registry is not an artefact you update,
it is a measurement you regenerate.** A generated file that two lanes touch is not a conflict to
argue about; it is a file to regenerate from the tree after the tree settles.

## Links

- Spec: `docs/specs/2026-10-26-context-compiler-and-execution-gateway.md`
- Measured map: `docs/reference/estate-agent-surface-map.md`
- Measurement: `bin/estate-surface-map` (`--json`, `--check`)
- Existing layers reused: `bin/catalog-projection`, `bin/idp-affected-graph`,
  `platform/llm/efficiency_gateway.py`, `platform/llm/request_ceiling.py`,
  `platform/executor/daemon.py`, `~/.estate/intents/`, `platform/estate/memory/plan.py`,
  `platform/llm/zeroedge_gateway.py`

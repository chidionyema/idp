# Essay: `mcts-mcp-server` (angrysky56) — fit, gap, or pass for the Reasoning Gateway

**Status:** open
**Opened:** 2026-09-14
**Laws:** LAW 2 (proof before action), R3 (never make the same mistake twice), R43 (never reinvent the wheel and do a worse job), THE HEADLINE (one platform layer underneath; no second bus, no second server)
**Source:** deferred essay #3 from the founder (2026-09-14 reasoning-gateway conversation); the gateway ticket is #1, `2026-09-14-bayesian-mcts-k8s-sre.md` is #2, this is #3.
**Upstream:** `github.com/angrysky56/mcts-mcp-server` (MIT, verified real, not a hallucinated handle)
**Essays destination:** `docs/essays/2026-09-14-mcts-mcp-server.md`
**Binding:** none yet. The essay names the choice before any code lands.

## Why this essay exists

The Reasoning Gateway's D2 compute-budget row is a budgeter. It does not pick the
search algorithm; it stops the loop when the budget runs out. The K8s-SRE essay
(#2) picks the algorithm for one domain. This essay is the one ABOVE them: how
does a general-purpose Monte-Carlo Tree Search engine, surfaced as an MCP tool, fit
into the estate — *if it fits at all*.

`mcts-mcp-server` is the only open-source MCTS engine on the open MCP registry that
the agent has surfaced in conversation, and the founder's flag is the gateway's
"buy vs build" line on a reasoning engine: a measured engine, surfaced over MCP,
that the Gateway's branches can call as a tool — instead of inventing one.

## What the essay must answer (founder's scope, three questions)

1. **Is `mcts-mcp-server` worth integrating on its own merits?** It is 17 stars,
   MIT, single-author, last touched in 2025-08 — measured, not remembered. Is it
   maintained, does it have a licence compatible with LAW 40 (build so it could be
   sold), does its dependency tree carry any LICENCE that blocks a sale?
2. **Does it expose enough over MCP for the Gateway to use?** Real tool list, real
   request/response shape, latency, determinism guarantees. The essay has to show
   `mcp__mcts__*` calls in a transcript, not promise them.
3. **Is the integration the platform rule from THE HEADLINE?** It must land on the
   Sovereign Bus (MUM-288 / ADR 0006), not spawn a second bus. It must use the
   existing executor daemon (propose / simulate / execute), not a second run path.
   It must mint no second store. If any of those fails, the essay's verdict is
   "pass — do not integrate."

## What already exists, so the essay does not reinvent

- `mcp/` directory and the estate MCP server (`bin/idp-mcp-server`, ADR 0006). The
  essay's fit-check is a one-command install if the upstream passes the bar.
- `bin/idp-simulate-gate`: every state-changing MCP tool needs a `simulate_*` twin.
  The essay has to show how a `mcts.simulate` tool would pair with an `mcts.execute`
  one — that pairing is the estate's `propose / execute` shape, not a new shape.
- `bin/idp-otto-door-key-agrees` rule, the Otto gateway's key derivation — the
  MCTS surface would be inside Otto's tool list, sharing the same identity.
- Mediator `[routing] consensus` voters — if MCTS needs models, it draws from the
  same lanes.

## What the essay is NOT

- Not a recommendation to merge or run `mcts-mcp-server` blind. The essay ends on
  "integrate", "don't integrate", or "wait and revisit" with reasons, not a yes.
- Not a patch to the upstream project. We buy or use, per R43.
- Not a new scheduler, broker, or storage layer. If the engine needs any of those,
  the essay says no.

## Definition of Done — in commands

1. **`docs/essays/2026-09-14-mcts-mcp-server.md` exists**, ≤ 1,500 words.
2. **The essay shows the MCP handshake in a recorded run**, not a description:
   `pip install mcts-mcp-server`, `mcp serve`, an `estate__` call into it, the
   answer, and a deterministic re-run with the same answer.
3. **The dependency tree is checked** (`pip-licenses --format=json` or the local
   equivalent) and **the essay names every licence, including transitive** — no
   "looks MIT" hand-waves.
4. **A "fit / gap / pass" verdict is recorded**, with the rule it tripped
   (simulate-twin requirement, headline rule, sale-blocker licence, determinism).

## Risks

- A second MCP bus is what the rule forbids. The essay has to spell out how the
  engine registers with the existing server, not how a new server is added.
- The 17-star project may not have a maintenance policy. Single-author MIT
  projects die quietly. The essay names what `pass` looks like if the upstream
  goes stale.
- Determinism: MCTS with an LLM leaf is by definition non-deterministic. The
  essay must show the seed-and-record path that satisfies the empirical proof
  rule, not promise it.

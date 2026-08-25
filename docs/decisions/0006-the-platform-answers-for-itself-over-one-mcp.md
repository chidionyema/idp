# 0006. The platform answers for itself over the one estate MCP server

- Status: DECIDED 2026-08-25. Founder: "the platform should be self aware ... it has all the maps
  and internal state to be able to answer any question about itself ... one interface, MCP or
  otherwise, where you could just query and it responds accurately." Tracked in crew as the
  self-aware platform ticket (filed the same day; the checkpoints live in
  `features/self-aware-platform/`).
- Date: 2026-08-25
- Deciders: founder (asked), session 130c903b (recorded)
- Affects: `mcp/` (the estate MCP server), `crew/STATE.md` (the hourly snapshot), the Sovereign Bus
  (`sovereign/`, crew#213), the Backstage catalog, `catalog/ports.yaml`

## The problem

Every session re-measures the estate by hand. A question like "is the storefront up and why not"
costs eight shell commands, five minutes and about fifteen thousand tokens, and six sessions that
cannot see each other each pay it again. The maps already exist: the catalog knows the owner, the
repo and the dependencies; `STATE.md` holds the live rows; launchd and colima hold the desired and
actual state. Nothing joins them, so agents act as typists reverse-engineering a black box.

## The decision

1. **One voice.** The estate MCP server in `mcp/` (already wired into Claude Code as
   `mcp__estate__*`) is extended. No second MCP server, no per-product query script (headline rule
   and LAW 43).
2. **Fat tools, summarised by default.** `get_workload_state(app)` returns catalog, vitals and
   desired-vs-actual state in one payload under a byte ceiling. Raw logs and timeseries never ride
   in it; `get_workload_logs(app, tail)` is the drill.
3. **Schema first, drift exposed.** Tools read typed catalog annotations, never grep strings.
   `get_catalog_drift()` lists every live resource the catalog does not name, so nothing applied by
   hand goes dark.
4. **Push, debounced.** State changes reach agents as events through the Sovereign Bus behind
   Temporal. A storm of N events in T seconds arrives as one aggregated event, never N.
5. **Propose and execute are two calls, joined by a state hash.** `propose_action()` records the
   hash of the state it was computed on inside the signed receipt; `execute_action()` refuses when
   the live hash differs and sends the agent back to re-evaluate. Approval stays on the phone
   through Otto.
6. **Substrate first, cluster later.** Every checkpoint is proved on the laptop against launchd
   and colima. The Kubernetes adapter (OKE, ADR 0004) is the last checkpoint and waits for a
   cluster to exist.
7. **The receipt is tokens.** Done means a script prints tool calls and tokens for three recurring
   questions before and after, and the after column is smaller.

## Rejected

- A second, "AI-only" MCP server beside `mcp/`: two copies of a platform layer is the stitching the
  headline forbids.
- Polling from the agent side: the platform tells the agent, not the reverse.
- Pasted command output as proof of the token saving: numbers come from the script, not memory.

## Consequences

- `AGENTS.md` carries the rule that platform queries go through the estate MCP tools, that any
  new query tool summarises by default, and that any executing tool checks a state hash.
- `STATE.md` becomes an input the tools read, not a page sessions quote.

# FleetView, part two: the live mind, the terminal, the steering wheel, and the board view

Founder, 2026-09-08 23:29Z, pasted a "God Mode command deck" spec and asked for it to be
improved; 23:33Z: "this has to work for all, we could use the executive/board dashboard also".
Record: `~/.claude/docs/founder/2026-09-08T2329Z-okspec-tis-out-se-hpwww-f-youcan-inprove-d0dfe40a.md`.

This document is a delta to `docs/specs/2026-09-08-fleetview-backstage-offering.md` (merged in
#2619), which already carries the board, the four signals (stop, approve, deny, steer), every
runtime on one page, and the offering. The pasted spec restates those and adds four things
worth keeping: a live graph of what an agent is doing, a live terminal, steering mid-flight,
and voice. It also proposes five things the estate must not build. Both lists are below.

## What the pasted spec gets right, and what the estate already has for it

| pasted spec | what exists on main today (measured 2026-09-08) | the delta |
|---|---|---|
| a low-latency event bus (NATS or Redis) | NATS, `platform/event-bus/nats.yaml`, with a schema-per-subject contract under `platform/event-bus/contract/` | new subjects, no new bus |
| agents broadcast state instead of printing | Claude Code sessions already write one ledger row per tool call (`session_live.py`, `~/.claude/state/hook-outcomes.jsonl`); Otto and the sovereign engine trace to Langfuse; every workload emits to the collector (LAW 50) | one adapter per runtime turns what it already emits into the session event |
| a live mind map of the agent's reasoning | the trace tree Langfuse already stores: one span per model call, one child per tool call | render the live trace, do not invent a second graph |
| the raw terminal of the container | `kubectl logs -f`, which Backstage's Kubernetes plugin already wraps for a catalog entity | a log pane on the session drawer, scoped to the session's pod |
| steer mid-flight | `steer` is signal four of CP3, with an audit row | the steering wheel is wired to each runtime's native pause point (below) |
| dictate the steering command | superwhisper's free tier dictates into any text field | nothing to build |
| the executive view | the Health page at `/ops` (crew#684) and the Reports module in `modules/home` | one board page, sourced from the same session records |

## What the pasted spec gets wrong, and is rejected

1. **Hundreds of frames per second.** An agent changes state at a tool boundary, a few times a
   minute. A firehose no one reads is LAW 28's dead instrument and a NATS bill. Events are
   emitted at tool boundaries and phase changes, and the page coalesces them.
2. **A 50 ms polling interrupt in every agent loop.** Each runtime already has a pause point
   where a message is read: Claude Code reads a mid-turn message at the next tool result
   (this very spec was steered that way); the sovereign engine takes a Temporal signal; Cyrus
   reads the next Linear comment on its issue; Otto reads the next Telegram message. The
   steering wheel publishes one message and the runtime's adapter delivers it on that channel.
   No agent loop gains a timer.
3. **MCP as the "universal translator" of agent output.** MCP is a tool and resource protocol
   for models, not a telemetry format. Telemetry is OpenTelemetry (the collector the estate
   runs); the estate MCP server (ADR 0006) is the door the page uses to ask questions and to
   propose-then-execute a steer, and that is its whole role here.
4. **A second WebSocket server beside Backstage.** The FleetView backend plugin's SSE stream
   (`/api/fleetview/stream`, CP1) is the one push channel; it subscribes to NATS server-side.
5. **"God Mode".** The product is FleetView, already named, already on the marketing index.
   A deck that can steer every agent is also the highest-value target in the estate, so the
   name a buyer's security reviewer reads is the sober one.

## The event contract: one subject family, one schema

Subjects `estate.agent.<runtime>.<session_id>.<kind>`, kinds `phase`, `tool`, `wait`, `done`,
`steer`. Schema `platform/event-bus/contract/estate.agent.event.json`, `additionalProperties:
false`, validated in CI like the commerce contract. Fields: `session_id`, `runtime`
(`claude-code | sovereign | cyrus | otto | dagster | github-actions`), `tenant`, `at`,
`phase` (`planning | executing | waiting | done | failed`), `tool` (name, target: file, command
or URL, never its output), `trace_id` (Langfuse), `needs` (what a `waiting` phase waits for,
in one sentence), `steer` (text, author identity, the audit row id).

Adapters (CP4's, extended): the Claude Code adapter tails the hook ledger through the estate
MCP server; the sovereign adapter maps Temporal workflow history; the Cyrus adapter reads its
session API; the Otto adapter is its Langfuse trace; Dagster and GitHub Actions map run states.
An adapter that emits a row the schema refuses fails CI (CP4 scenario already written).

## The live mind: a trace rendered as it grows

The session drawer gets a graph pane. Nodes are the trace's spans (a model call, a tool call,
a sub-agent), edges are parent to child, the newest node is highlighted, a `waiting` node is
amber and carries its `needs` sentence with the approve and deny buttons beside it. The data
is the Langfuse trace for `trace_id`, refreshed on each NATS event for the session, so the
graph grows as the agent works. Rendering library: React Flow, mature, MIT, already the
convention for this in Backstage plugins; the estate does not write a layout engine.

## The terminal: the pod's log, scoped

The drawer's log pane streams the session pod's stdout and stderr through the Backstage
Kubernetes plugin the portal already loads, scoped by the session's pod label. Sessions with no
pod (a laptop Claude Code session) show the ledger's last twenty rows instead, and say so.
Secrets never reach the pane: the collector's redaction processor sits in front of it (LAW 21).

## The steering wheel: one door, native delivery, an audit row first

Pressing Steer (or Approve-and-modify, which is approve plus a steer text) posts to the CP3
signal door. The door writes the `fleetview_audit` row, publishes `estate.agent.<runtime>.
<id>.steer`, and the runtime's adapter delivers it: a mid-turn message to a Claude Code session,
`workflow.signal("steer")` to a sovereign workflow, a Linear comment to Cyrus, a Telegram
message to Otto. The page shows the steer as a node on the graph the moment the runtime
acknowledges it, and an amber "not yet read" badge until it does. A steer from a caller with no
portal identity is 401 with no audit row (CP3 scenario). Approvals for the un-undoable stay on
the existing propose-then-execute road of the estate MCP server; the page is a client of it.

Voice: superwhisper (free tier, local Whisper models) dictates into the steer field. No estate
code. A voice note to Otto on Telegram is already transcribed by faster-whisper 1.2.1 in
`hermes-agent-gateway`; MUM-284 surfaces it.

## The board view: the same records, rolled up for an executive

"This has to work for all": every runtime is on one board (CP4), and the same session records
feed a second page, `/board`, for the founder-as-executive and for a buyer's board:

- fleet now: agents running, waiting on a person, failed, by runtime and by lane;
- the day's outcomes: pull requests landed, issues closed, drills passed, each linked;
- spend: LiteLLM cost by agent and by tenant against the `[budget]` block in AGENTS.md;
- waiting on you: the same list the Health page carries, with the one button each;
- 30-day trend of the four, from the CP5 history store.

It is one page in `modules/home` beside `Ops.tsx`, reading `/api/fleetview/sessions` and the
existing LiteLLM and Linear enrichers; it holds no data path of its own. The laptop board
(`board_serve.py`, MUM-286) is retired into `/ops` and `/board`.

## Checkpoints, each with the command that says it is done

CP6 The contract and the adapters. `estate.agent.event.json` in the contract directory, the
    Claude Code and sovereign adapters publishing to NATS. Done: `nats sub "estate.agent.>"`
    prints a real tool event from this session within 5 s of the tool running.
CP7 The live mind and the terminal. Graph pane and log pane on the drawer. Done: the founder
    opens a running session, watches a node appear as the agent runs a tool, and the log pane
    shows the same tool's output line; `features/fleetview/cp7_live_mind.feature` passes.
CP8 The steering wheel. Done: a steer typed on the page reaches a live Claude Code session
    and a sovereign workflow within 10 s, each acknowledges it, and the newest
    `fleetview_audit` row names the press; dictated through superwhisper once, on video.
CP9 The board view. Done: `/board` opens behind SSO, every tile reads live and says when it
    cannot, and a second tenant sees only its own fleet (decision 0021).

Lanes: CP6 two DeepSeek lanes (contract, adapters), CP7 two (graph, log), CP8 one per runtime
(four), CP9 one. All behind the CP1 to CP5 work already on the board.

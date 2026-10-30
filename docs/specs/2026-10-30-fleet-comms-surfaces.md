# Fleet communications: one core, many doors (voice first)

Founder, 2026-10-30: invoke this from anywhere (Telegram, FleetView face, console, voice), part of the
founder core toolkit, tied into unified memory, future-proof, enterprise-ready. Voice first.
Builds on idp#7481 (`bin/estate-fleet`: JetStream stream `ESTATE_FLEET`, durable acked inbox).

## What already exists (do not rebuild)
| Need | Existing owner | Fact |
|---|---|---|
| Telegram | `platform/otto-gateway` | Single-writer rule (`OWNER.yaml`): nothing else calls `getUpdates`/`setWebhook`. Others read the NATS `otto.ingress` subject or otto-gateway's internal HTTP API. `sovereign/otto/card.py` already edits a pinned card. |
| Voice in/out | `fleetview_backend/voice_media.py` (`hear(pcm, session, author)`, `say(text)`), `bin/idp-voice`, `voice-router` | Whisper + Kokoro, streaming `/voice/ws` (#7191), health via `bin/voice-watch`. |
| Face | FleetView backend/frontend | Already hosts `/voice/*`; executor link via `executor_link.py`. |
| Founder view | `bin/estate-founder`, `bin/estate-founder-intake` | God's view; the founder inbox belongs beside it. |
| Memory | growmos + estate-memory (`estate-memory-mcp`) | `directive` already writes a growmos DECISION. |
| Customer surfaces | `factory/surfaces/*` | Order-intake for tenants. NOT the founder channel; keep separate. |

## Architecture
```
 doors (adapters, thin)                core                       memory
 voice  -> hear() -> text -+
 telegram -> otto.ingress -+   envelope{id,from,to,kind,   +-> growmos DECISION (directive)
 face   -> POST /fleet/msg +-> text,ts,channel,reply_to} --+
 console -> bin/estate-fleet +   JetStream ESTATE_FLEET     +-> ack ledger (who applied/refused)
 MCP tool (agents) --------+   durable consumer per agent
                                      | egress fan-out
        voice say() / Telegram via otto-gateway / FleetView panel / session-start inbox
```
Rules:
1. One envelope, one stream. A door converts to/from the envelope and holds no state of its own.
2. Telegram goes through otto-gateway only (`otto.ingress` in, otto-gateway HTTP out). No Bot API calls from here.
3. Voice is a door: speech -> `hear()` -> `directive`; pending directives and acks are spoken back with `say()`.
4. Acks are first-class: a directive is "applied" only with a per-agent ack or refusal on record. Publication is not receipt.
5. Offline is BLIND, never an empty inbox. Cloud reach needs a non-laptop NATS (see #7387) with a mirror of the stream.

## Delivery order
1. Envelope + `kind`/`channel`/`reply_to` fields in `bin/estate-fleet`; ack ledger and `estate-fleet status <seq>` (who acked).
2. MCP tool `fleet_send/fleet_inbox/fleet_ack` so every agent harness shares one path (touches `mcp/plugins/estate_mcp.py`, held by #7480: coordinate, do not race).
3. Voice door: `bin/estate-fleet-voice` = hear -> directive, and spoken inbox/ack summary.
4. Telegram door: `otto.ingress` subscriber -> envelope; egress to otto-gateway; slash commands `/say /inbox /status`.
5. FleetView door: `/fleet/messages` read + post, inbox panel.
6. Reachability: NATS leaf/mirror off-laptop so cloud agents see the same stream.
Each step lands with a test and a proof on the real path (a message injected at one door, acked at another).

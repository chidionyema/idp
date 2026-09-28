# Voice 2100 — the Intent Plane

**Date:** 2026-09-22
**Status:** Phase 0 shipped (commit `05b3c634e`); Phase 1 in flight; Phase 2–3 outlined below.
**Why:** the founder's bar — "I want to be the go-to for voice in the plenty for the next 100 years, and the gap I want to leave is not one that can be caught." Two product lines share one architecture: the consumer/npm tier where compute is free on the user's GPU and the LPU hop costs pennies, and the enterprise tier where every byte stays on the buyer's network.

---

## The asymmetry, in one paragraph

Audio is the largest payload in the estate by orders of magnitude, so it must die on the user's hardware. The server only ever sees a text string — first an ASR partial, then a JSON intent that is structurally Schema v2 and is therefore impossible to prompt-inject past. The user pays their own GPU for transcription and synthesis; the estate pays only for the speculative intent compiler, which runs on the cheapest free lane the router can reach. Enterprise buyers route that same compiler at Ollama on their own box, and the architecture is unchanged.

## What already exists (today)

| Layer | Path | Notes |
|-------|------|-------|
| Strict Schema v2 (prompt-injection armor) | `backstage/plugins/fleetview-backend/schemas/intent-v2.json` | `additionalProperties: false`; required: `action`, `confidence`, `session_id` |
| Outbox + 15-minute TTL | `backstage/plugins/fleetview-backend/src/outbox.py` | Singleton writer; SQLite WAL |
| JetStream stream provisioning | `backstage/plugins/fleetview-backend/src/nats_adapter.py` (`_ensure_stream`) | `estate.agent.>`, `max_age = 900s` |
| Browser client (VAD + Whisper + Kokoro) | `packages/voice/src/{vad,asr,tts,intent,VoiceClient}.ts` | Silero VAD, Xenova/whisper-tiny.en, Kokoro-82M, SmolLM2-135M intent |
| Steer endpoint with strict validation | `POST /voice/steer` (`voice_media.py::steer`) | <50ms response; never publishes on the request path |
| MCP voice tools | `mcp/plugins/voice.py` | `voice_intent_stream`, `voice_speak`, `voice_last_intent` |
| Consumer npm package | `packages/voice` (`@fleetview/voice` v0.1.0) | `npm create fleetvoice@latest` ships in the next phase |
| Enterprise Helm chart | `deploy/helm/fleetview-voice/values-enterprise.yaml` | air-gapped, `sso.provider=okta`, `nats.ttl=900` |

## What this commit ships

| Gap closed | File |
|-----------|------|
| Server-side `/voice/speculate` fallback for browsers without WebGPU | `voice_media.py::speculate`, `routes.py`, `serve.py` |
| Clarification handshake (`confidence < 0.90`) on both client and server | `VoiceClient.ts` (callback), `voice_media.py::speculate` (heuristic), MCP `voice_clarify` tool |
| MCP tool that asks the user for a targeted clarification | `mcp/plugins/voice.py` |
| Tests that gate the schema, the confidence floor, and the MCP surface | `tests/test_speculate_and_clarify.py` |
| This doc — the architecture lives in git, not in chat | `docs/specs/2026-09-22-voice-2100-architecture.md` |

## Phases (from the master synthesis)

### Phase 0 — Stabilize the Path  ✅

- Outbox + singleton NATS publish, 15-min JetStream TTL on `estate.agent.>`.
- Steer durability: a 200 OK means a pending outbox row exists.
- Evidence (committed in `05b3c634e`): `tests/test_voice_on_the_bus.py::test_a_steer_reaches_the_durability_boundary_not_just_the_response`, `test_the_first_caller_provisions_the_stream_with_the_outboxs_15_minute_ttl`.

### Phase 1 — The Intent Compiler  (this commit)

- `POST /voice/speculate`: takes `{partial, session_id, author?}`, returns Schema v2 with `partial: true` and the server's confidence estimate.
- Routing: router alias `intent-speculative` → `groq` (consumer) or `ollama` (enterprise). One endpoint, two physical lanes.
- Client (`VoiceClient.ts`): if client-side `confidence < 0.90` AND not `partial`, fire `onClarificationNeeded(intent)` so the consumer wires it to TTS ("did you mean X?").
- MCP `voice_clarify(text, candidate)` tool: an agent framework asks the user one question and gets back the answer.
- Evidence: `tests/test_speculate_and_clarify.py` grades (a) `/voice/speculate` validates against Schema v2; (b) a payload without the required fields is 400; (c) `confidence < 0.90` triggers the clarification flag; (d) MCP `voice_clarify` lands a row on the bus and the response references the same `session_id`.

### Phase 2 — Cross-Platform & Auto-Adapter

- WebGPU/ONNX edge inference on every browser the consumer touches (already shipped via `VoiceClient.ts`).
- Cloud fallback via `/voice/speculate` (shipped here) for Safari iOS and other WebGPU-absent clients.
- Auto-Adapter: a `POST /voice/connect` that reads an OpenAPI or MCP spec and binds a new tool. Target: <5 minutes from spec to live tool.
- Evidence: a production transcript from a Windows or Linux machine, and an external tool consuming a voice event via MCP.

### Phase 3 — Commercial Surface

- SDKs (JS/TS already shipped in `packages/voice`; Go and Python in Phase 3).
- MCP server already shipped (`mcp/plugins/voice.py`).
- Admin dashboard: a Backstage plugin page listing active voice sessions, clarification rate, average latency.
- Federated learning opt-in: Local Differential Privacy on the user's corrected intents; only masked weight updates leave the device.
- Evidence: NPS > 70; telemetry "time to first integrated event" < 5 min for new developers.

## The five open questions, answered

1. **Latency bound for the intent compiler?** The browser emits a partial every `partialInterval` ms (default 500). For each partial, `intent.ts` calls `parse()` against SmolLM2-135M locally (~50–100ms on WebGPU). On WebGPU-less clients, `/voice/speculate` falls back to a router call to the cheapest free lane. Hard ceiling: `partialInterval` plus one round-trip.
2. **Continuous eval?** Clarification rate is logged per session. Every clarification (browser OR MCP) writes a `voice.clarify` row to the outbox with both the original intent and the user's correction. The eval harness reads those and turns them into a regression set.
3. **Prompt injection?** Schema v2's `additionalProperties: false` is the armor. The transcript is treated as untrusted user data, never as system instructions; the LLM's output is validated against Schema v2 before it touches the outbox, and any undeclared field rejects the payload with a 400. The browser never sends audio or raw text to the server — only the schema-validated intent.
4. **Audit without retaining spoken input?** Schema v2 payloads and transcripts go to the operational bus with a 15-minute TTL. Cold-storage audit is opt-in, isolated, and never includes raw PCM — audio is destroyed the millisecond ASR returns.
5. **Federated learning without compromising privacy?** Local Differential Privacy on the user's device when they correct an intent: only masked weight updates leave the user's hardware. The cold-storage audit vault never holds the raw correction.

## The business model

The free tier is the consumer npm package and the Groq-backed `/voice/speculate`. It is genuinely free to the developer: their GPU does the ASR and TTS, the speculative intent is on Groq's free tier, and MCP tools cost nothing to subscribe to. The enterprise tier is the air-gapped chart: same SDK, same MCP surface, but the router alias `intent-speculative` is pinned to `ollama` on the buyer's network, and SSO/RBAC/audit are wired through the buyer's identity provider.

## What this architecture deletes

- The 127-second NATS defect (Phase 0): publish is off the response path.
- The 8899-port duplicate server (`voice_media.py`'s docstring is the full account).
- Server-side faster-whisper and server-side Kokoro — both still present as fallback for clients that cannot run WebGPU, but the primary path is the browser.
- The "intent compile waits for speech end" UX — partials drive an optimistic UI from the first 200ms of speech.

## What this architecture refuses to do

- Accept any payload that does not match Schema v2 (`additionalProperties: false`).
- Publish a row on the request path (the outbox is the durability boundary).
- Trust the client's `author` field (server overrides from the authenticated session).
- Ship a feature whose evidence is a green test instead of a real log line (house rule, AGENTS.md: "No green test substitutes for a real log line.").

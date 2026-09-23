# ADR 0033 — Edge compute for the voice loop is the target, not the current state

- **Status:** Proposed
- **Date:** 2026-09-22
- **Deciders:** founder
- **Supersedes / relates:** `docs/specs/2026-09-20-fleet-2100-hud-architecture.md`,
  `docs/founder/fleetview-voice-revisit.md`

## Context

A target-state memo describes a voice experience where **Whisper/ASR, an intent model, and
TTS (Kokoro) all run on the edge** — browser WebGPU, a phone, a Pi, a Mac mini — so the
common case is "full offline, zero latency, complete privacy." It frames the deliberate
federation (Spanner / Aurora / CockroachDB) as unnecessary because *one* region is enough
for a fleet of hundreds, and treats **ephemeral state with a 15-minute TTL** plus
**idempotent writes** as the commercial moat.

That memo is a **desired end state**. The house rule (AGENTS.md, "built and operating are
different facts") requires we say which fact we mean, so this ADR records what is **true in
the tree today** against that target.

### What is verified true today (in-session, before the session's tool channel failed)

- The voice loop is **server-side and utterance-batched**, not edge and not streaming.
  The browser client uses **Silero VAD in the browser** (the estate's CPU defence),
  detects speech end, and sends **one complete audio buffer per utterance**
  (`ws.send(audio.buffer)`) to `/voice/stream`. There are no interim/partial transcripts
  crossing the wire.
- The engine ASR path is **batch transcribe**, not a streaming decoder.
- The event contract `platform/event-bus/contract/estate.agent.event.json` has
  `required = [session_id, runtime, kind, at, phase]` and **`additionalProperties: false`**.
  Any new top-level field is therefore a **breaking, CI-enforced** change, not a free add.
- An `author` field **already exists inside the `steer` payload**
  (`backstage/plugins/fleetview-backend/src/voice_media.py:211`). It is **not** a top-level
  contract field.
- The estate **already has** the idempotency primitive the memo sells as a moat: the Go
  outbox sets **`Nats-Msg-Id`** on publish, and JetStream's duplicate window is documented
  as **15 minutes** ("the relay may publish twice, the stream stores once" —
  `platform/messaging/cloudevent/cloudevent.go:44`).
- CI gates that will judge any change here:
  `tests/test_estate_agent_event_contract.py`,
  `tests/test_idp_voice_is_a_conversation_loop.py`.

### What is NOT verified (recorded honestly, do not treat as fact)

- The real JetStream **stream retention / `MaxAge`** in `platform/event-bus/nats.yaml`
  (only the *library comment* naming a 15-minute window was read).
- Whether `bin/idp-voice` publishes **through the outbox** or **directly** to NATS.
- The exact scope of `docs/specs/2026-09-20-fleet-2100-hud-architecture.md`.

## Decision

1. **Name the state truthfully.** The edge voice loop is a **target**, not a shipped
   capability. No document, PR, or demo may describe WebGPU ASR/TTS or offline voice as
   operating until a production log line proves it (AGENTS.md: built ≠ operating).

2. **Do not re-buy idempotency.** The 15-minute TTL idempotency the memo calls a moat already
   exists as `Nats-Msg-Id` dedup in the outbox. The commercial story is **reuse of existing
   machinery**, and any "new" event-moat work must first prove the existing relay cannot
   carry it.

3. **Treat the contract as frozen-by-default.** Because `additionalProperties: false`, adding
   provenance/attribution fields at the top level is a **breaking change** with a CI gate
   behind it. New fields go through the same two-way proof as any other contract edit.

4. **Sequence by proof, not by ambition.** Bet A (wire today's facts onto the existing
   outbox) precedes Bet B (the WebGPU edge spike), because Bet A is proven against running
   infrastructure while Bet B is gated on a median-device kill criterion.

## Consequences

- **Positive:** the estate stops confusing the 2100 picture with today's loop; the
  idempotency/TTL claim is grounded in code that already exists; contract edits are known to
  be breaking and are gated accordingly.
- **Negative / cost:** the headline "zero-latency, fully offline, complete privacy" promise
  is explicitly **not** deliverable today; the current experience is utterance-batched and
  network-bound on the ASR/LLM/TTS legs.
- **Follow-ups:** Bet A plan and Bet B spike spec (see `docs/founder/`), each carrying its own
  kill criterion. Stale verification TODOs above must be closed by a fresh session.

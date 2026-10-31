# 0039 — One mouth: the voice router owns the estate's voice

Date: 2026-10-23
Status: accepted
Related: 0037 (deterministic twin), 0038 (one scene contract),
`docs/specs/2026-10-23-estate-as-movie-director-engine.md` §7.2,
`docs/specs/2026-09-22-voice-intent-plane-architecture.md`

---

## Context

The estate is voice-first, and the founder now wants a film that speaks and can be interrupted.
The voice code today has two shapes, and both are visible in the measurements:

- **One module-global clause sink.** `backstage/packages/app/src/modules/home/useEstateVoice.ts`
  holds a single `clauseSink` (`:382`), set by whoever mounts a face (`setClauseSink`, `:383`),
  read by the voice engine (`:991`) and stopped on barge (`:679`). It is a global with a
  last-writer-wins policy: *"the face that mounted last"*.
- **Two engines on one surface.** `/fleet` mounts both the legacy `useEstateVoice` and the
  duplex `useVoiceRouter` (the comment at `FleetReactorApp.tsx:741` says so plainly: *"Two
  engines, one surface"*). `/face` picks between them with a `localStorage` flag
  (`FacePage.tsx:42`).

The duplex router is the one that matters: one WebSocket at `/voice/ws`, partials every 0.56 s
while the founder speaks, first audio at a median 2.26 s, and barge-in that drops audio at or
below the last barge (`useVoiceRouter.ts:21`, `:352`). The literature agrees this is the
architecture to be on: barge-in is a property of the duplex model, not a feature bolted on
later (`2505.15670v4`, `2205.15060v4`).

The problem a film creates: **narration is a broadcast, and the founder is talking over it.** If
the film's voice and the founder's replies come from two engines on two sinks, they overlap, the
founder cannot interrupt what he is watching, and the interruption — the whole point — never
happens. `useVoiceRouter.ts:201` already names the trap: *"the face's sink queues clauses on its
own clock; a barge must clear those too"*.

## Decision

**One mouth. The duplex router (`useVoiceRouter` / `/voice/ws`) is the estate's voice, and it is
the only one the film uses.**

- The legacy `useEstateVoice` loop is **not** mounted on the film's surfaces. The Face's
  `estate.face.voice = legacy` flag remains for the legacy path, but the film never selects it.
- **The server is the single source of narration.** The scene frame carries the line
  (`line.text`, `line.source.id`); whoever holds playback speaks it. A surface that is not the
  focused one does not play audio.
- **Focus is explicit**: the surface that last received a user gesture owns playback; the others
  mute. This is a rule, not a heuristic, and it is asserted in a test rather than inferred.
- **Barge-in cuts the narration.** A barge clears the queued clauses in the clause sink as well
  as the in-flight audio; narration is *replaced*, never queued behind. Target: audio stops
  ≤ 250 ms (requirement RP3).
- The clause sink's last-writer-wins global becomes an **explicitly owned sink**: one registered
  speaker per surface, and the film's line goes through the same door as the founder's replies.

### Why the server speaks once

Two tabs are two audio contexts; the bus is one. If each surface played the line itself, opening
the phone and the desk at once would double the narration. One publication, one owner of the
audio, is the only arrangement that survives that.

## Consequences

**Positive.** The founder can interrupt the film the way he interrupts an agent. One voice, one
socket, one barge path. The estate's duplex investment is the one the film rides.

**Negative, accepted.**

1. **The legacy voice loop and the film cannot coexist on one surface.** Accepted: the film
   surfaces use the router only. Anything still on the legacy loop keeps working for whoever uses
   it; it just is not the film.
2. **Focus has to be tracked.** A small amount of state per surface (last gesture) and a rule for
   the phone arriving while the desk is focused. The rule is "the surface the founder just
   touched", which is also the honest behaviour.
3. **A silent second surface is a behaviour change for someone who expects sound on both.** The
   founder gets the sound where they are; the other screen shows the film. Accepted.

## Enforcement

- A test asserts that opening `/fleet` and `/face` together produces **one** narration stream
  (requirement RI3).
- The film's surfaces mount exactly one voice engine; a grep of the film's components finds one
  `useVoiceRouter` and no `useEstateVoice`.
- A barge during narration is asserted to stop the audio within 250 ms, measured in the browser
  (requirement RP3) — not in a unit test with a fake sink.
- The clause sink is registered explicitly; a second registration without an explicit handover is
  refused rather than silently overwriting the first (law L4).

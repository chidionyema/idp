# FleetView voice interaction -- revisit later

Recorded 2026-09-15. `mcp__estate__remember` was unreachable when this was written (memory
store down alongside Langfuse/LiteLLM on this machine at the time), so this is a plain file
instead of an estate memory -- move it into `remember` once the store is back up.

## What was asked

Interact with agent sessions by voice, in addition to the ten-item FleetView plan; pointed at
`mums-concierge` as existing building blocks; asked for a serious "unified harness" answer if
voice is not uniformly possible across runtimes (claude-code, pi, gemini, sovereign, ...).

## What is true right now

- `mums-concierge` (`~/dev/code/mums-concierge`) is real and substantial: 18 modules, 302 tests,
  several pieces proven live (voice biometrics, TTS, browser automation). It has never carried a
  real call. Its own ticket states the phone number and OpenAI Realtime API access are
  **founder-only** provisioning steps -- an engineer cannot hold these.
- CORRECTED (2026-09-15, same day, on closer reading): `~/.claude/scripts/directive-capture.py`'s
  `sweep_queued` is **not** an injection mechanism. It is a throttled, best-effort background
  transcript-miner that recovers mid-turn terminal input for logging only
  (`~/.claude/directives/*.jsonl`). The actual mid-turn delivery ("queued_command") is a
  claude-code **terminal-UI** behaviour -- a person types into the still-open terminal while a
  turn runs, and the harness itself delivers it to that turn. No file, socket or API exists
  anywhere in `idp` or `~/.claude/scripts/*` that an external process (a FleetView backend, say)
  could write to and have it land inside a *running* turn, for any harness. The nearest real
  precedent is `memory-loop.py`, which injects at **SessionStart/PostCompact** -- next turn, not
  live -- and that is the template the notes mailbox below actually follows.
- Conclusion: a true unified cross-harness voice channel does not exist yet, and cannot be built
  today without either (a) new founder-provisioned voice infrastructure or (b) a live,
  mid-turn injection mechanism that does not exist today for any harness, claude-code included.

## Decision (founder, 2026-09-15): text option for now

Build the buildable slice first: a text-based "leave a note for a running session" feature.
Offered as a claude-code-specific / idp-repo-scoped hook; founder rejected that scope explicitly
("we are model agnostic and this is enterprise wide, not repo wide"). Built instead as
`backstage/plugins/fleetview-backend/src/notes.py`: a `session_notes` table in the estate's one
existing store (`catalog/estate.db`, additive, same file `bin/estate-twin-runtime` extends),
keyed by `(session_id, runtime)` so it works the same for a runtime that does not exist yet.
`GET/POST /api/fleetview/notes` and a per-row fold on the FleetView board (`Fleet.tsx`) are live.
Delivery is honestly async: nothing reads this table into a running process automatically today,
for any runtime -- a person, or that session's own next-turn tooling, reads it back later. Live
voice stays deferred until Twilio/OpenAI-Realtime accounts are provisioned for the estate -- the
same founder-only step `mums-concierge` is already blocked on.

## Revisit when

The Twilio/OpenAI-Realtime provisioning happens, or a live per-runtime read-side for
`session_notes` gets built (e.g. a claude-code SessionStart hook that tails it) -- either one
changes what "unified" or "delivered" can honestly mean here.

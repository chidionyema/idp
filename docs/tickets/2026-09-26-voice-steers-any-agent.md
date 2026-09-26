# Voice steers any agent — speak on the Fleet page, the chosen agent receives it

**Status:** in progress
**Opened:** 2026-09-26
**Laws:** LAW 0 (one of each layer), THE EMPIRICAL PROOF RULE
**Specs:** `docs/specs/2026-09-22-voice-intent-plane-architecture.md`
**Depends on:** `mcp/plugins/voice.py`, `backstage/plugins/fleetview-backend/src/fleetview_backend/voice_media.py`, `nats_adapter.py`

---

## What this is

The founder's work surface is the Fleet page. Today they type to agents; the goal is to speak to
them instead, whichever agent and whichever model (the estate is model-agnostic, not Claude Code
only). The design already exists end to end on paper:

```
Fleet page: Steer / Dictate on an agent card (RadialMenu.tsx)
  -> /voice/hear  (transcript)
  -> steer event {text, author, session_id}  (estate.agent.event contract)
  -> JetStream  estate.agent.sovereign.<session>.steer
  -> mcp/plugins/voice.py  (voice_intent_stream / voice_last_intent / voice_speak)
  -> any MCP-speaking agent, any model
```

## Where it broke (measured 2026-09-26 on the founder's laptop)

| # | Break | Evidence |
|---|---|---|
| 1 | Hearing and speaking were unusably slow | real page turns in the friction panel: hear 81s / 165s, first word 207s |
| 2 | No bus on the laptop | `nats-server` downloaded, not running; backend had no `NATS_URL`; every steer `published: false` |
| 3 | No agent listens | `mcp/plugins/voice.py` registered in no agent's MCP config |
| 4 | No addressing | the plugin subscribes to `sovereign.*.steer` — every agent would receive every steer |
| 5 | Page load stalls | `/voice/voices` took 18.6s (loads Kokoro), voice shows unavailable meanwhile |
| 6 | Friction panel recorded the browser's guess of the engine, not the engine that served | `answered()` took `engine` from the request body |

## Done so far (uncommitted, branch `fix/local-claude-max-router`)

- **#1 hearing:** `/voice/hear` tries router lane `voice-asr` (Groq whisper-large-v3-turbo) first, then
  the local engine. Measured on the live backend, 3/3 turns: hear 0.47–2.87s.
- **#1 speaking:** `/voice/say` tries `voice-tts` (Groq Orpheus), then macOS `say` (~1s/clause), then
  Kokoro. Measured 3.5–4.8s for a whole multi-clause answer. Orpheus is blocked on a founder
  action: accept the model terms at the Groq console.
- Lanes `voice-asr` / `voice-tts` added to `platform/vendors/consoles.yaml`, rendered, loaded on
  litellm-local :4000.
- Every leg logs `voice.<leg> engine=<name> seconds=<n>` to `~/.estate/fleetview-backend.err.log`,
  and router refusals log their reason.
- **#6:** the turn log records the engine that actually served (`hear:<x> say:<y>`).
- **#2 (started):** `launchd/ai.estate.nats.plist.tmpl` (JetStream on 127.0.0.1:4222) and
  `NATS_URL` on the fleetview-backend template.

- **Grounding (voice said "all five stopped" — false):** three causes, all fixed and measured:
  `parents[4]`→`parents[5]` repo root in 7 `fleetview_backend` modules (sessions read an empty
  catalog); `bin/estate-session-recorder` dead since 21 Sep (missing python, exit 78) — reinstalled;
  recorder excluded claude-code by default — now `pi,claude-code,estate`. `fleet_summary` now says
  what working/idle/stuck mean; `max_tokens` 220→1024 (reasoning lane spent the budget, empty
  replies). Measured 3/3: "Three agents are working right now", tasks named correctly.
- Traps recorded in growmos (`gotcha/trap-*`) and cross-pointers added in both `fleet_summary`s.

## Direction (founder, 2026-09-26): voice + conversation is ONE platform capability

Perfected once, consumed by FleetView, hermes, concierge, agents. Today it exists 5+ times
(hermes-agent tools/tts_streaming + transcription_tools, fleetview_backend voice/voice_media,
sovereign/voice/engine, packages/voice, ambient-os/sovereign/voice, hermes-v2/otto/ingress).
Follow-up ticket to pick the gold standard and delete the rest.

## Remaining

- [ ] #2 load the nats agent, verify the ESTATE_AGENT stream's real retention (the
      `max_age` seconds/nanoseconds comment in `nats_adapter.py` is unverified), add to installer
- [ ] #4 steers filtered to the listening agent's own session
- [ ] #3 voice MCP plugin registered in the MCP config every agent reads
- [ ] #5 `/voice/voices` answers without loading Kokoro
- [x] Fleet answers are fast but wrong ("all five stopped, so failing") — grounding (see above)
- [ ] Real time: board + voice driven by bus events, not the 60s recorder poll
- [ ] rebuild `installer/IDP-Estate.pkg`

## Acceptance

Measured, not asserted:

1. A steer spoken through the page's own endpoint is read back off JetStream.
2. The target agent's `voice_last_intent` returns it; a second agent does **not** receive it.
3. The turn appears in the Fleet page friction panel with real per-leg seconds and the engine that served.
4. A fresh machine reaches all of the above through `IDP-Estate.pkg` alone.

## Non-goals

- Not a rewrite of the browser-first design in the spec; server hearing/speaking is the path that
  works on this Intel/no-GPU laptop today, and the browser engine remains a later layer.

**Voice router (self-hosted, zero API cost):** [`2026-09-26-voice-router-self-hosted.md`](2026-09-26-voice-router-self-hosted.md)

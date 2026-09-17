# FleetView voice -- correction (2026-09-17)

Supersedes the 2026-09-15 entry below. That entry was an agent error: it invented a
Twilio/OpenAI-Realtime dependency the spec never asked for, and wrongly marked voice as deferred.

The spec is clear (`docs/specs/2026-09-08-fleetview-live-mind-steering-and-the-board-view.md`, line 22):

> "dictate the steering command | superwhisper's free tier dictates into any text field | nothing to build"

And line 88:

> "Voice: superwhisper (free tier, local Whisper models) dictates into the steer field. No estate code.
> A voice note to Otto on Telegram is already transcribed by faster-whisper 1.2.1 in hermes-agent-gateway."

Voice is solved. Superwhisper is local, free, and works in any browser text field today -- including
the steer input on the Fleet drawer. Otto's Telegram channel already transcribes voice through
faster-whisper 1.2.1 in the estate. No Twilio. No OpenAI Realtime. No paid dependency. Nothing deferred.

---

## Original 2026-09-15 entry (kept for record, superseded above)

*[previous content was wrong -- it claimed voice needs Twilio/OpenAI-Realtime provisioning. It does not.]*

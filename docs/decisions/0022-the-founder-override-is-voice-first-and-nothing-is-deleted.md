# 0022 — The founder override is voice-first, and nothing is deleted

- Status: DECIDED 2026-09-05 on the founder's instruction in session. Founder's words across the
  override: "founder wants voice", "override the spec", "he override covers all three. Do not
  compromise the features to save time ... No more questions, go build it." Founder's record of
  the original spec: `~/.claude/docs/founder/2026-09-05T2023Z-spec-for-deepseek-to-get-everything-done-and-a8f82afe.md`.
- Deciders: founder
- Supersedes: only Decision 1 of `docs/specs/otto-five-capabilities-finished.md` (merged as PR
  #1876, `bb5752db`), which said "Voice replies stay off by default; `/voice on` is the switch."
  This override is the founder's replacement ruling. Sections of the spec *not* overridden stay
  in force: STT keeps the estate router as the fallback root, vision is proved by a live photo
  (hermes-v2 #86), and voice replies must still arrive as real audio before the capability is
  claimed finished.
- Affects: `hermes-v2` release (the bot's image and shipped `config.yaml`) and the `idp` deploy
  (`platform/hermes-agent/`), and the `bench` lane's meaning.

## The instruction

> founder wants voice ... override the spec ... the override covers all three. Do not compromise
> the features to save time. Voice ON by default ... Local STT: update the image. Add ffmpeg and
> faster-whisper to the Dockerfile. A bleeding-edge model must be capable of local transcription;
> the estate router is a fallback, not an excuse ... Keep the flags: do not delete the bench or
> screenshot_handler flags. Instead of deleting bench because it lacks code, write the
> telemetry/TTFT code to make the bench flag actually work.

Recorded verbatim in session `2026-09-05`. Three decisions, each intended to raise the bar, not
lower it: a bleeding-edge model answers in voice, transcribes on its own, and proves its lanes
with numbers rather than deleting the proof.

## The decision

Three rules replace the parts of PR #1876 they touch. Nothing that was merged in code is deleted
by this ADR — the flags ride unchanged because the founder ruled they must be made to work, not
removed.

### 1. Voice replies are ON by default

Voice is an opt-*out* experience, not opt-in. Rejected (now): voice off by default with `/voice
on` as a per-chat switch to be proved. The founder's stated position is voice-first.

Mechanism (native, no new engine): the live gateway reads `voice.auto_tts` from the shipped
`config.yaml` as the global default for every chat
(`hermes-agent/gateway/run.py` `_sync_voice_mode_state_to_adapter`, line ~7581: `bool(
(_full_cfg.get("voice") or {}).get("auto_tts", False))`). Setting it `true` turns voice on for
chats that have no per-chat mode. The per-chat opt-out is untouched and still wins: a chat that
ran `/voice off` is held in `_auto_tts_disabled_chats` and is checked before the global default
(`run.py` ~22175-22190, `_should_auto_tts_for_chat`).

So the whole change is one value in `hermes-v2/config.yaml`:

```yaml
voice:
  auto_tts: true
```

The voice *path* is the existing edge-tts + Telegram `send_voice` pipeline already in the image
(`--extra edge-tts` in the Dockerfile). `/voice on` / `/voice off` remain the per-chat controls.

Definition of done: a message the founder sends from his phone to the customer bot is answered
with audio without him typing `/voice on` first, and the forwarded-lane cluster log carries the
voice-send line for his chat.

### 2. Speech-to-text is local-first in the image; the router is the fallback

The pinned fork (`hermes-agent`, `chidionyema/hermes-agent`) already encodes local-first STT:
`tools/transcription_tools.py` resolves providers in this order — `local` when
`_HAS_FASTER_WHISPER` is true (`faster_whisper` importable), then `local_command`,
lazy-install local, then cloud (`groq`/`openai`/...), else `none`. `_HAS_FASTER_WHISPER` is an
import probe (`_safe_find_spec("faster_whisper")`). So the fork already prefers the local model;
the image just never shipped one.

The fix is the image, not new resolver code:
- the fork's `voice` extra installs `faster-whisper==1.2.1` (+ `sounddevice`, `numpy`);
- ffmpeg (+ `libgomp1`, a ctranslate2 runtime dep, and `libsndfile1`) decodes the incoming
  Opus/OGG voice note and holds the codec edge-tts needs.

Add `--extra voice` to the Dockerfile `uv sync` line and install the apt packages. The estate
router stays as the fallback the code already uses when local decode fails — the exact
"local-first, router as fallback" shape the founder named, built on the fork's own chain rather
than a second, parallel STT road.

### 3. The `bench` and `screenshot_handler` flags stay, and `bench` gains a meaning

The flags are not deleted. Their gates in `idp/platform/hermes-agent/estate.yaml`
(`features: bench: off`, `features: screenshot_handler: off`) remain the on/off switch, so a lane
still costs nothing until it is flipped on (that is `bin/features` + `bin/install-cron.py` in
hermes-v2: an off lane creates no job). "Keep the flag" and "the lane is inert until it is on"
are the same mechanism; keeping the flag does not mean running the lane.

`bench` is the on-demand local lane ("§6b ... runs nothing by itself. You start it."). Making it
real means a runner that, when `bench: on`, measures what the founder cares about — live model
lane telemetry (time to first token and tokens/second through the estate's lanes) — and reports a
number instead of being a name. This is the telemetry/TTFT work the founder explicitly asked for
in place of deletion. Screenshots already reach the model through the `screenshot-to-story`
skill; `screenshot_handler: off` merely means no separate cron/issue-writing lane is installed,
which the founder's override does not disturb.

### What this does NOT do

- It does not delete any code. PR #1876 merged no code, and this ADR merges none that strips a
  feature; its later "delete the decorative flags" instruction (spec step 3) is superseded only in
  the sense that this ADR replaces that recommendation with "keep and make bench meaningful."
- It does not add a second TTS or STT road. Both capabilities use the fork's existing native
  paths (`edge-tts` extra; the local→router STT chain).
- It does not claim the capabilities are finished: voice and STT are only finished when a real
  founder message on the phone produces a real voice reply / a real transcript in the forwarded
  cluster log. This ADR changes the defaults and the image; it does not by itself produce that log
  line.

## Proof boundary (read before executing)

This override is a config value and an image dependency set. It is provable as green only where
the fork is present and `uv sync` runs — the Docker image build in CI
(`.github/workflows/build-agent-image.yml`), not a bare git worktree (the fork is gitignored and
materialises only at build). It is provable as *true* only on the live cluster: voice ON-default
and local STT each need one founder phone message answered and quoted from the pod log. A local
synthetic load of config.yaml is not done; an HTTP 200 is not done.

Release road (unchanged from the spec): merge to `hermes-v2` main → image
`ghcr.io/chidionyema/hermes-agent:main-N-<sha>` → the idp `image-update-pr.yml` cron opens the pin
PR → merge → Flux. Reconcile only through `gh workflow run oke-check -f mode=apply`. Never edit a
Kustomization by hand.

## Guards

- `hermes-v2` config.yaml and Dockerfile carry the change. The fork's own test that locks the
  local-first STT preference lives in `chidionyema/hermes-agent`'s test suite
  (`tests/tools/test_transcription_tools.py`), reached through a `PINNED_VERSION` bump if the
  fork itself changes; a config-only change needs no fork commit.
- No founder menu is served by this ADR: the three decisions above are made, with the rejected
  prior road named and the reason. Open items below the proof boundary are cluster actions that
  name a command, not a choice.

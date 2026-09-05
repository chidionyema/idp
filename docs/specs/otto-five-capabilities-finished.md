# Spec: the five Otto capabilities, finished and proved

- Founder record: `~/.claude/docs/founder/2026-09-05T2023Z-spec-for-deepseek-to-get-everything-done-and-a8f82afe.md`
  ("spec for deepseek to get everything done and fully finished")
- Written for: the executing session (any model). Every step is a command; every finish line is
  a log line quoted from the cluster. Nothing here is a menu: where a choice existed it is made
  below, with the reason, and the rejected road named.
- Repos: `hermes-v2` (the bot's code, image and `config.yaml`; `hermes-agent/` is vendored into
  the image at build and is not tracked), `idp` (the deploy: `platform/hermes-agent/`,
  `platform/otto-gateway/`, `llm/config.yaml`).
- Release road (do not invent another): merge to `hermes-v2` main -> image
  `ghcr.io/chidionyema/hermes-agent:main-N-<sha>` -> `idp` `.github/workflows/image-update-pr.yml`
  (cron, every 10 minutes) opens the pin PR -> merge -> Flux. Reconcile on demand only through
  `gh workflow run oke-check --repo chidionyema/idp -f mode=apply`. Never edit a Kustomization by hand.

## State on 2026-09-05, with receipts

| capability | code | deploy | Telegram path | verdict |
|---|---|---|---|---|
| Edge-TTS voice replies | `hermes-agent/tools/tts_tool.py:1727`; toolset `hermes-agent/toolsets.py:230` | extra in image `hermes-v2/Dockerfile:57`, pinned `deploy/k8s/boot-contract.txt:13`; no `voice:` block in `config.yaml`, so `voice.auto_tts` is False (`gateway/run.py:7581`) and per-chat mode is `off` (`gateway/slash_commands.py:3291`) | `gateway/run.py:22231 _send_voice_reply` -> `plugins/platforms/telegram/adapter.py:7615 send_voice` | built, off by default |
| screenshot handler | template only: `templates/handlers/screenshot_to_issue.py.tmpl`, rendered copy gitignored (`.gitignore:60`); live path is the skill `skills/screenshot-to-story/SKILL.md` | flag `screenshot_handler: off` in `idp/platform/hermes-agent/estate.yaml:114`, and nothing reads it (`bin/install-cron.py`, `cron/*.jobs`: no screenshot job) | a photo reaches the model and the skill (row 5) | flag is decorative |
| bench | the name only: `hermes-v2/bin/features:37`, `estate.yaml:79`, `tests/test_features_switch.py:24` | `bench: off` `idp/platform/hermes-agent/estate.yaml:113` | none | not built |
| speech-to-text | `adapter.py:9854 _transcribe_voice_message` -> `tools/voice_mode.py:1402` -> `tools/transcription_tools.py:3175`; on by default `gateway/config.py:959` | `faster-whisper` is the `voice` extra (`hermes-agent/pyproject.toml:196`) and is not in `Dockerfile:57`; lazy install cannot write a read-only rootfs; no STT key in the deploy, so the provider chain (`transcription_tools.py:1140-1173`) returns `none` | handler `adapter.py:4236` (`filters.VOICE`), transcript becomes `event.text` (`adapter.py:9953-9976`) | built, broken in the cluster |
| vision | `tools/vision_tools.py:1299`; auto-enrich `gateway/run.py:24720`; Telegram declares `IMAGE_IN` (`otto/surface/bindings/telegram.py:25`) | was a root `aux:` key nothing reads; fixed by hermes-v2 #86 (`auxiliary.vision.model: gemini`) | handler `adapter.py:4236` (`filters.PHOTO`) -> `gateway/run.py:18288-18357` | built, mis-pointed, fix merged and not yet proved |

Where the bot's self-report came from: the toolset inventory (`hermes-agent/tools/registry.py:1210`),
the estate flags mounted as `HERMES_ESTATE_YAML` (`idp/platform/hermes-agent/gateway.yaml:269`), and
the hedge rule in `hermes-v2/SOUL.md:19`. The flags gate nothing; flipping them changes the report,
not the behaviour. Do not flip a flag to make a sentence true.

## The decisions

1. **Voice replies stay off by default; `/voice on` is the switch and it must work.** Auto-TTS on
   every reply is a per-chat preference, not a platform default. Rejected: `voice.auto_tts: true`
   in `config.yaml` (every customer would get audio unasked).
2. **The `screenshot_handler` and `bench` flags are deleted.** A flag that gates nothing is a
   claim the file does not support, and a buyer's engineer finds it in one sitting. `bench` is
   not a feature until a founder request names what it does; today no file does. Rejected:
   building "bench" from the name.
3. **Speech-to-text goes through the estate router, not a local model.** `stt.openai.base_url`
   is honoured (`transcription_tools.py:121,3326`), so the bot sends audio to the LiteLLM
   `/v1/audio/transcriptions` endpoint with the key it already holds, and the router owns the
   provider root (LAW 52, one root per provider; 0020, the client chooses the road). Rejected:
   `faster-whisper` in the image (a model download at first use on a read-only rootfs behind a
   default-deny fence, plus ffmpeg), and a vendor key in the pod (a second secret road).
4. **Vision is proved, not re-fixed.** hermes-v2 #86 is merged; the finish line is a photo
   described in the log.

## The work, in order

### 1. STT through the router

idp:
- `llm/config.yaml`: add a `model_name: stt` entry on a transcription-capable provider. The
  first provider with a root already in the router that LiteLLM lists for transcription is the
  one; if none of the estate's roots transcribe, the root is Groq (`groq/whisper-large-v3`),
  minted on the vault road: `gh secret set SEED_GROQ_API_KEY`, then
  `gh workflow run vault-seed.yml -f entry=groq`, and the router's ExternalSecret gains the key
  the way every other provider key reaches it (`platform/litellm/`). One console step, once.
- Prove the alias before touching the bot:
  `curl -sS -F model=stt -F file=@tests/fixtures/otto/hello.ogg https://llm.mumchimp.com/v1/audio/transcriptions -H "Authorization: Bearer $LITELLM_API_KEY"`
  returns `{"text": "hello ..."}`. Commit the fixture (a two-second Opus voice note).

hermes-v2:
- `config.yaml`: 
  ```yaml
  stt:
    enabled: true
    provider: openai
    openai:
      model: stt
      base_url: https://llm.mumchimp.com/v1
      key_env: LITELLM_API_KEY
  ```
  (verify the exact key names against `tools/transcription_tools.py:3300-3350`, `_resolve_openai_audio_client_config`; the
  spec names the intent, the code names the keys.)
- A test under `tests/` that loads `config.yaml` and asserts the STT provider resolves to the
  router base URL, in the style of `tests/test_incident_crew516_cp4_image_carries_the_estate.py`
  (structure, not prose; `prose_pin_scan` refuses a string-membership test). README row for the file.

### 2. Voice replies: prove the switch

- No code change expected. In a chat with the customer bot: `/voice on`, then any question.
- If the reply carries no audio, the defect is in `_send_voice_reply` (`gateway/run.py:22231`) or
  the edge-tts extra; fix at the site, never by adding a second TTS road.

### 3. Delete the decorative flags

hermes-v2: remove `bench` and `screenshot_handler` from `bin/features`, `estate.yaml`,
`estate.example.yaml`, `README.md:102`, `tests/test_features_switch.py`; delete
`templates/handlers/screenshot_to_issue.py.tmpl` and its `.gitignore:60` line.
idp: remove both lines from `platform/hermes-agent/estate.yaml`. `bin/idp-ci` green.

### 4. Vision: prove it

- No code change. Send the bot a photo of a printed page; the answer must name what is on it.

## Definition of done, in commands

Each row is one log line quoted from the cluster, from a message the founder sent from his
phone. A probe, a unit test or a 200 is not done.

| capability | command | expected |
|---|---|---|
| STT | `bin/idp-kube logs -n hermes-agent deploy/hermes-agent --since=10m \| grep -E 'transcrib'` | a line naming the transcript of the founder's voice note, and the reply answers it |
| voice replies | same log, `grep -E 'send_voice\|voice_reply'` | a `send_voice` line for the founder's chat after `/voice on`, and the audio arrives on the phone |
| vision | same log, `grep -E 'vision'` | a line with the photo's description, and the reply names what is in it |
| flags | `grep -rn 'bench\|screenshot_handler' hermes-v2 idp/platform` | nothing |
| silent failures | `bin/idp-kube get events -n hermes-agent --sort-by=.lastTimestamp \| tail -20` | no restart, OOM or refused create after the messages |

Reply with `INVENTORY:` when every row above is quoted; `DONE:` only with the founder's receipt.

## Guards the executing session will meet

- No `git add -A`, no `git push -q`, no `git stash`; explicit paths, plain push.
- The PR body file is written in one call and `gh pr create --body-file` in the next; the body
  carries `Closes #N` or `No-Issue:` and an `Optimised:` line.
- `gh pr merge <number>` with the literal number, from the branch's own worktree, after
  `gh pr checks <number> --watch`; never `--auto`.
- `checkpoints/LATEST.md` must be fresh before a worktree is opened; the guard reads the copy
  at `~/.claude/projects/<project-dir>/checkpoints/LATEST.md`.
- hermes-v2: `bin/check-readme.py` wants a README row for every new tracked file; pre-commit
  reformats Python.
- `FOUNDER ACTION:` is for a step on his phone and goes through `founder-blocker.py --physical --register none`;
  everything else is `STAGED:`.

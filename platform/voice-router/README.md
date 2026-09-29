# voice-router

The estate's voice: speech in, the brain, speech out, in one Go process. The ears (streaming ASR)
and voice (TTS) run in-process on sherpa-onnx; the brain is a chat call to the LLM router's `voice`
lane. /fleet's microphone talks to it over a websocket.

**Is voice working? Run `estate-execute voice-doctor`.** It walks the chain below in order, runs a
real spoken turn, and names the first broken link with the command that fixes it. Start there,
not in the logs.

## The chain a spoken turn walks

```
/fleet mic ──ws──▶ voice-router /voice/ws ──▶ ASR (sherpa, local model files)
                                         ──▶ brain: POST {LLM_BASE_URL}/chat/completions model=voice
                                         ──▶ TTS (sherpa piper, local model files + espeak-ng-data)
                                         ──▶ audio back over the ws
```

Each arrow is a way it breaks. `/readyz` checks that the brain answers, but **not** that speech
synthesis works. Only a real turn (`cmd/talk`, which `voice-doctor` runs) proves the whole chain.

## Where it runs

| | Laptop (the founder's /fleet today) | OKE |
|---|---|---|
| What | launchd `ai.estate.voice-router`, full voice | Deployment `voice-router-director` (namespace `voice-router`): director mode only, no speech yet |
| Binary | `~/.estate/voice-router/voice-router`, built by `bin/estate-runtime-sync` from main | image `ghcr.io/chidionyema/voice-router`, rolled by ImagePolicy `flux-system/voice-router` |
| Started by | `bin/voice-router-launchd`: fetches missing speech models, loads the router key, execs the binary | `deploy/director.yaml` |
| Settings | `launchd/ai.estate.voice-router.plist.tmpl` (`LLM_MODEL=voice`, `VOICE_MODELS`, `VOICE_ADDR=127.0.0.1:8091`) | the Deployment's env |
| Brain | laptop router `com.estate.litellm-local` on :4000, config `llm/config.yaml` | `litellm.llm.svc:4000` |
| Speech models | `~/.cache/estate-tools/sherpa-models`, fetched by the launcher | baked into the image |
| Watched by | `bin/voice-watch` (launchd `ai.estate.voice-watch`): probes `/readyz` every 2 min, log `~/.estate/voice-watch.log` | kubelet `/healthz` |
| Logs | `~/Library/Logs/voice-router.log` (turns: `voice.turn`, `voice.tts`), `.err.log` (sherpa) | `kubectl -n voice-router logs deploy/voice-router-director` |

## How a change reaches it

Nothing is installed by hand. Merge to main, and:

- **Laptop:** `bin/estate-runtime-sync` (launchd, every 5 min, log `~/.estate/runtime-sync.log`)
  rebuilds and restarts voice-router when `platform/voice-router/` or `bin/voice-router-launchd`
  changes, and rolls back if `/readyz` does not come back. It also carries `llm/config.yaml` and
  the router modules to the laptop router. It keeps a router change only if voice is at least as
  ready as before.
- **OKE:** `build-multiarch` builds the image. The ImagePolicy in `platform/image-automation/voice-router.yaml`
  opens the tag bump, and Flux rolls it. That policy only exists in the cluster if a Flux row under
  `clusters/oke` applies `platform/image-automation` (`tests/test_image_automation_is_applied.py`).

## Speech models

Pinned by sha256 in `Dockerfile` (the `fetch` lines): NeMo streaming fast-conformer (ASR) and piper
ljspeech medium (TTS). The image bakes them in. On the laptop, `bin/voice-router-launchd` reads the
same pins and downloads any model directory that is missing, with the system curl, before starting
the binary. Change a model by changing the Dockerfile pin; both places follow.

## Known ways it has broken

| Symptom | Cause | Fix / guard |
|---|---|---|
| `/readyz` 503 `no healthy deployments for model_group=voice` | router config lacked the `voice` lane (main had it; the laptop router never got it) | runtime-sync carries `llm/config.yaml`; `voice-doctor` "router voice lane" |
| brain answers, no audio; `Failed to convert … to token IDs`, `voice.tts … synthesis failed` | speech model directory deleted under a running voice-router (espeak-ng-data is read per sentence) | restart: the launcher refetches the pinned models; `voice-doctor` "speech models" |
| `the brain did not answer`, `context deadline exceeded` | laptop overloaded (load 80–120 on 4 cores): the router itself answers in 5–35 s | `voice-doctor` "machine load"; judge voice in OKE, not on a starved laptop |
| OKE director CrashLoopBackOff `nats: no stream matches subject` | OKE ran an image from before the fix: the Flux row applying image policies had been deleted | row restored; `voice-doctor` "image policy" |
| answers are invented ("saved half a kilowatt") | the brain has no grounding in live estate data | open |

## Develop

```
cd platform/voice-router
go test ./...                                 # needs VOICE_MODELS pointing at the models
go build -o /tmp/voice-talk ./cmd/talk        # the end-to-end probe
/tmp/voice-talk -wav q.wav -out reply.raw     # stream a 16 kHz mono WAV, time the reply
```

Specs and history: `docs/specs/2026-09-18-voice-conversation-pipeline.md`,
`docs/tickets/2026-09-26-voice-router-self-hosted.md`, `docs/how-to/onboarding/voice-loop.md`.

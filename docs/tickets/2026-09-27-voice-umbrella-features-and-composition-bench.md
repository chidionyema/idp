# Voice umbrella: every feature from all 7, and a bench that ranks compositions

**Status:** open, 2026-09-27. Parent: `2026-09-26-voice-router-self-hosted.md` (PR #4392).
**Founder asks:** "ensure we are extracting all features from all 7 — we need to run experiments and
rank combinations or compositions"; "one umbrella, different implementations as tools and research".

## Rules this work is held to

- No paid vendor APIs, no free tiers (so Groq / OpenAI realtime / edge-tts lanes are research-only,
  never a default).
- §6: one voice layer. `platform/voice-router` is the seed; the others fold in as engines or get
  deleted.
- A number counts only if it was measured, and it is valid only for the machine that measured it.

## 1. Feature matrix — what each of the 7 has, and where it ends up

| # | Implementation | Features worth keeping | Umbrella slot | Vendor / rule problem |
|---|---|---|---|---|
| 1 | `platform/voice-router` (Go, sherpa-onnx) | streaming ASR partials; endpointing (0.5s silence); 3s continue-window joins a paused sentence; filler/noise filter before barge; barge-in by turn id; phrase chunker with early first phrase; phrase-streamed TTS; `say` (read aloud, no brain); live `system` context; history cap 12; Origin allow-list; slog turn metrics (`first_phrase_ms`, `first_audio_ms`) | **core** — transport, session, ASR/TTS engines | none |
| 2 | `sovereign/voice` (Python) | faster-whisper ASR (tiny.en int8 / large-v3-turbo, `VOICE_ASR_MODEL`); Kokoro ONNX fp32 (`af_heart`; int8 blocked by ConvInteger); piper; macOS `say`; voice **catalogue** with NOVELTY filter + preview/select; `fleet_summary` context (≤20 sessions); clause streaming (`CLAUSE_END`, 8s router timeout); **turnlog** SQLite `voice_turns` (asr_s, llm_first_s, llm_total_s, tts_s, words, clauses, engine, voice, outcome) with medians | engines: whisper ASR, kokoro TTS; **turnlog → the evidence schema** | WS on :8899 (one laptop only) — delete the socket |
| 3 | `fleetview_backend/voice.py` | **spatial fast path** ("the one on the left", `_SPATIAL_PATTERN`, skips the LLM); zone-aware router host (`ESTATE_ZONE`); `history_block(6)`; SSE `stream_ask`; `split_clauses`; per-answer **cost/"why"** (model, region, usd) | brain pre-router (fast path) + answer provenance | default model `deepseek` via router — fine if self-hosted lane |
| 4 | `fleetview_backend/voice_media.py` | publish to NATS bus + durable outbox; **speculate on partials** (`intent-speculative`, 2s); Schema v2 intent validation; `clarification_needed` below 0.90 confidence; **steer** a target agent; voice choice persisted (`~/.estate/voice-choice.json`); hear/say/log routes | **intent layer**: speculation, confidence gate, steer-to-agent | `_router_transcribe` (Groq whisper) and `_router_synthesise` (Groq Orpheus) — **vendor, remove as defaults** |
| 5 | `packages/voice` (TS SDK) | VoiceClient start/stop/speak/bargeIn/history; whisper-tiny via transformers.js; 16 kHz resample; VAD with sensitivity; **IntentProcessor** (SmolLM2) → intent categories; Kokoro.js `speakStream`; model cache mgmt (load/check/clear/preload) | **edge mode** (in-browser, zero audio on the wire) | none |
| 6 | `modules/home/useEstateVoice.ts` | Silero MicVAD + onnxruntime served same-origin; voice log polling; catalogue/select UI | client; replaced by `useVoiceRouter` with fallback | three round trips (measured 3.0–3.8s to first word) |
| 7 | `packages/chrome-extension/src/lib/voice.ts` | whisper-tiny.en via transformers.js **WebGPU**; model cached in IndexedDB; MediaRecorder | edge mode (shares #5's engine) | none |
| + | `mums-concierge` (separate product) | Twilio g711_ulaw telephony bridge; true barge-in on calls; `PendingIntent`; `UtteranceBuffer` / `is_speakable`; WhatsApp voice notes; **voiceprint gate** (sherpa speaker embedding, ~30MB, ~43ms, cosine 0.6, `bin/derive-voice-threshold`); consent script | telephony transport; **speaker verification engine** | realtime-model bridge and edge-tts `en-NG-EzinneNeural` are vendor/free — replace with core engines |

| 8 | `bin/idp-voice` (Python CLI, 824 lines) | asyncio duplex listen → think → speak; micro-clause chunking; barge-in from stdin / `--watch`; `--ask` text-only testable mode; `--check` engine reachability with exit 2 when blind | CLI client of the core contract (`--ask` = `ask`, `--text` = `say`) | brain is Ollama `deepseek-r1:8b` on localhost, a second local-model path beside resident-brain — point it at litellm |

**ambient-os (examined 2026-09-27): nothing new to fold in.** It is a second clone of the idp repo (same origin), on a 2026-09-23 commit already in idp's history,
plus an unpushed local `land/voice-fleet` branch made from idp's uncommitted voice work. Every speech
file has a newer idp counterpart (`sovereign/voice/*`, `bin/idp-voice`, `bin/voice-loop`, the
fleetview `voice.py` at 397 vs 634 lines, `FleetVoice.tsx`). Its `FleetVoice.tsx` has 140 lines idp
lacks: the browser's Web Speech API (Chrome sends that audio to Google, so it's a vendor lane) with a
900 ms silence auto-send and queued (not cancelled) per-clause speech. voice-router's endpointer and
phrase-streamed TTS already do both. `platform/voice-gate` (Rust) is a *prose-register* linter for
written copy, not speech — out of scope.

Not yet examined: hermes-agent desktop voice files.

### Every feature, and its place in the engine (founder: "we can't leave any feature out")

No feature is dropped. A feature that came through a vendor lane keeps its place and is rebuilt on a
self-hosted engine. `have` = in voice-router today; `todo` = its slot, in build order (a–f are the
founder's order).

| Feature | From | Engine slot | Status |
|---|---|---|---|
| streaming partials, endpointing, continue window, filler filter, barge by turn, early first phrase, phrase-streamed TTS, `say`, live `system`, history cap, Origin allow-list, turn metrics | 1 | core | have |
| queued per-clause speech, silence auto-send | ambient-os FleetVoice, 6 | core | have (phrase queue, endpointer) |
| micro-clause chunking, duplex listen/think/speak | 2, 3, 8 | core | have |
| **a.** per-turn log (asr_s, llm_first_s, llm_total_s, tts_s, words, clauses, engine, voice, outcome) + medians, one schema for bench and production, HLC stamp | 2, omni-fleet | evidence | **built** (`internal/turnlog`, `GET /voice/turns`, one `voice.turn` line per turn); run on the laptop router, not operating in the cluster |
| **b.** spatial fast path ("the one on the left") that skips the brain | 3 | intent pre-router | todo |
| **b.** speculate on partials (`intent-speculative`, 2s) | 4 | intent | todo |
| **c.** Schema v2 intent validation + clarify below 0.90 confidence | 4 | intent | todo |
| **c.** steer a target agent via the durable outbox; publish turns to NATS | 4 | intent → bus | todo |
| **c.** hard bounds on what a spoken steer may do (the executor refuses the action) | omni-fleet | intent → executor | todo |
| **d.** voiceprint gate (speaker embedding, cosine 0.6, derived threshold) on steer | mums | speaker engine | todo |
| **e.** voice catalogue with NOVELTY filter, preview, select, choice persisted | 2, 4, 6 | TTS registry | todo |
| **e.** Kokoro voices (af_heart etc.), piper lessac/ljspeech/amy, kitten | 2, 5 | TTS engines | todo (bench first) |
| **e.** "cloud" voice quality (Groq Orpheus troy etc.) | 4 | TTS engine, self-hosted Orpheus/Kokoro | todo |
| whisper ASR (tiny.en → large-v3-turbo) | 2, 5, 7 | ASR engine (offline, via sherpa) | todo (bench) |
| Groq whisper transcription | 4 | replaced by the whisper engine above | todo |
| fleet context (sessions summary, capped) | 2, 3 | `system` provider | todo (/fleet sends it) |
| history block, SSE ask/stream_ask for text clients | 3 | core `ask` over WS; SSE adapter | todo |
| cost/"why" per answer (model, region, usd) | 3 | evidence | todo |
| zone-aware brain host (`ESTATE_ZONE`) | 3 | brain config | todo |
| **f.** in-browser mode: whisper-tiny WebGPU, IndexedDB model cache, Silero VAD, Kokoro.js, SmolLM2 intent, model cache mgmt | 5, 6, 7 | edge engines behind the same contract | todo |
| telephony: Twilio g711 bridge, call barge-in, PendingIntent, consent script, TwiML | mums | telephony transport | todo |
| speakable-text filter, utterance buffer | mums | core phrase chunker | todo (merge rules) |
| WhatsApp voice notes | mums | `say` → file output | todo |
| macOS `say` as a last-resort voice | 2, 4 | TTS engine (laptop only) | todo |
| CLI loop: `--ask`, `--text`, `--file`, `--listen`, `--check` (exit 2 when blind) | 8 | CLI client of the contract | todo |
| engine reachability check (honest degradation) | 8 | `/healthz` reports each engine | todo |

## 2. The composition bench

**Question:** which combination of ASR × TTS × brain × endpoint setting gives the best experience on
our hardware under our rules?

**Axes**
- ASR: nemo-480ms-int8 (current), kroko-zipformer, nemotron-0.6b-160ms-int8, whisper tiny/turbo
  (non-streaming, via sherpa offline).
- TTS: piper ljspeech / lessac / amy, kokoro int8, kitten-nano int8.
- Brain: litellm `fast`; a local small model (the `edge-runtime` / `resident-brain` llama.cpp pods
  already exist — reuse them, don't add a third).
- Endpoint silence: 0.3 / 0.5 / 0.8s.

**Metrics** (each measured, per machine)
- first audio after the words are final (ms): the number the listener feels;
- ASR finalise latency and RTF; TTS first-audio and RTF;
- human-speech ASR WER (LibriSpeech test_wavs from the model releases);
- round-trip intelligibility WER (TTS → ASR), 3 reps, because VITS sampling is stochastic
  (3.5–12.3% single pass measured 2026-09-26);
- resident memory; licence (gate: weights must be commercially usable).

**Ranking.** Hard gates first (licence; human WER ≤ 10%; intelligibility WER ≤ 20%). Then rank
survivors by first-audio p50, with ties broken by intelligibility WER then memory. No weighted score:
a weighted score hides which axis won.

**Where it runs.** The laptop has 728 MiB free, so it can only rank the models already cached (nemo ×
{ljspeech, lessac}). The full grid runs in the image build or a CI job that fetches sha-pinned models
into scratch space, the same way the Dockerfile's `models` stage does.

### First results (laptop, 2026-09-27, 2 threads, 3 reps, load average 60–185)

`bench -compose 0.3,0.5,0.8` over what is cached: one ASR (nemo-480ms-int8) × two voices. Wall
timings are inflated by the load; WER and endpoint (audio time) are not.

| ASR | voice | silence | endpoint ms | finalise ms | tts first ms | human WER | round-trip WER | gate |
|---|---|---|---|---|---|---|---|---|
| nemo-480 | ljspeech | 0.5s | 1416 | 146 | 511 | 0.0% | 11.1% | pass |
| nemo-480 | ljspeech | 0.8s | 1416 | 162 | 631 | 0.0% | 8.2% | pass |
| nemo-480 | lessac | 0.5 / 0.8s | 1416 | 146–162 | 477–611 | 0.0% | 2.3% | **licence** (Blizzard 2013, research only) |
| nemo-480 | either | 0.3s | 856 | 230 | 820–844 | **27.8%** | 17.5–25.7% | human WER: 0.3s cuts the sentence at its pauses |

What it says:
- **0.3s silence is out.** It ends the utterance mid-sentence on a human speaker.
- **0.5s and 0.8s end at the same moment (1416 ms after speech)** on this model, likely because it
  decodes in 480 ms chunks and both settings are met at the same chunk. So 0.8s is free
  robustness to pauses, and the endpoint, not the setting, is the floor. A 160 ms-chunk model
  (nemotron-0.6b-160ms) is the next ASR to bench.
- **The shippable voice (ljspeech) is 4× less intelligible than the research-only one (lessac).**
  A commercially licensed voice at lessac's clarity (kokoro, kitten, piper amy) is the TTS
  question to settle next.
- **The brain dominates.** On the live router, an `ask` spent 2.52 s of its 3.06 s before first
  audio in the brain. The `fast` lane is a reasoning model that streams hidden reasoning, then the
  whole answer in one burst (llm_first_s ≈ llm_total_s). A non-reasoning lane or the local
  resident-brain is the biggest single win on the table; the brain axis runs next.

## 3. The pasted "omni-fleet" design — what we take, what we refuse

| Piece | Verdict | Why |
|---|---|---|
| k8s manifest with `POSTGRES_PASSWORD "oke_secure"` | **refuse** | Hardcoded secret breaks §4; secrets come from estate-secrets by name. |
| Postgres + NATS + llama.cpp stack | **refuse as new stack** | NATS already exists (voice_media publishes to it). The llama.cpp brain already exists (`platform/edge-runtime`, `resident-brain.yaml`). Memory is `platform/unified-memory-server`. A second copy would break §6. |
| `FleetCRDTMemory` (HLC + bi-temporal facts + asyncpg) | **idea only** | Memory has one home (unified-memory-server). Bi-temporal `valid_from/valid_to` is a proposal for that schema, not a new store. |
| HybridLogicalClock | **take (small)** | Voice turns arrive from several surfaces (web, extension, phone). An HLC stamp on each turn orders them without trusting device clocks. It goes in the turn/evidence record. |
| Asymmetric router Tier 0 → 1 → 2 | **take the pattern, refuse the tiers** | Local-first then escalate is right, but Tier 1 Groq and Tier 2 gpt-4o are vendors. Tier 0 = resident-brain via litellm; escalation stays inside litellm lanes we host. |
| Gherkin AST verification before escalating | **take for steer only** | Verifying a structured intent before acting fits voice_media's Schema v2 + 0.90 gate. It does not belong on chat answers. |
| `ControlBarrierFunction` safety bounds | **take as hard bounds** | A voice steer that would exceed a bound (spend, destructive action) is refused by the executor. Per "guarantees, not controls", that means an intent the executor refuses, not a soft check. |
| NATS JetStream gateway, surfaces/* | **refuse** | Duplicates voice-router transport + existing bus. |

## 4. Work, in order

- [x] Feature extraction across the 7 (this ticket, §1).
- [ ] Bench: `cmd/bench -compose` ranks every cached ASR × TTS pair on first audio + intelligibility.
- [ ] Bench: CI job with the full grid, fetching sha-pinned models; results committed as a table here.
- [ ] Turn evidence record in voice-router (turnlog fields + HLC stamp), one schema with #2.
- [ ] Route `/voice/ws` (dev proxy + ingress) and add a manifest; wire /fleet to `useVoiceRouter`
      with fallback to `useEstateVoice`.
- [ ] Fold in: spatial fast path, speculation, confidence gate, steer.
- [ ] Remove Groq ASR/TTS lanes as defaults in voice_media; delete the :8899 socket.
- [ ] Speaker verification engine (from mums) on steer.

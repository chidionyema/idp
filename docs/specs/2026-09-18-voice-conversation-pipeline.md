# Voice conversation: the pipeline, as specified

Founder, 2026-09-18, with the full reference implementation. Kept verbatim in shape so the
architecture survives the context window; the code lands in `bin/idp-voice` + a Backstage surface.

## The requirement

Real voice conversation, not dictation. Today's Fleet mics use `SpeechRecognition` to fill a text
box — speech in, no speech out, no turn-taking, no interruption. That is a keyboard replacement.

## Architecture: asynchronous, streaming, duplex

    [Mic PCM] ─► [Silero VAD v5] ─► (Barge-in trigger / end-of-speech)
                      │
                      ▼
            [Faster-Whisper STT]
                      │
                      ▼
           [vLLM / Ollama Stream] ─► [Clause Buffer / Splitter]
                                              │
                                              ▼
     [Speaker PCM] ◄── [Audio Queue] ◄── [Kokoro TTS]

Three principles carry the latency budget:

1. **Async duplex queues.** Mic capture, VAD, STT, LLM streaming, TTS and playback each run as
   parallel asyncio workers. Nothing blocks on anything downstream of it.
2. **Micro-clause chunking.** LLM tokens buffer until a phonetic boundary (`, . ? ! ;`), then TTS
   synthesises that clause while the LLM is still producing the next. This is what makes
   first-audio arrive long before the full answer exists.
3. **Barge-in.** VAD detects speech while SPEAKING → cancel the LLM stream, flush the TTS playback
   queue, resume capture. Three consecutive speech frames (~100 ms) triggers the halt, so a
   person can talk over the agent and be heard immediately.

## Components and their latency

| stage | technology | budget | strategy |
|---|---|---|---|
| voice detection | Silero VAD v5 | 5–15 ms | CPU, ONNX |
| transcription | Faster-Whisper large-v3-turbo | 80–140 ms | CTranslate2, FP16 |
| first token | vLLM (Llama 3.3 70B) | 120–200 ms | continuous batching, KV cache |
| synthesis | Kokoro-82M | 30–60 ms | per-clause streaming |
| **glass-to-glass** | | **< 400 ms** | parallel async + micro-clause |

## Configuration (LAW 46: no literal in behaviour)

    vad_threshold                    0.65
    vad_min_silence_duration_ms      400     end of turn
    vad_speech_pad_ms                200
    whisper_model                    large-v3-turbo
    llm_endpoint                     http://localhost:8000/v1/chat/completions
    kokoro_endpoint                  http://localhost:8880/v1/audio/speech
    kokoro_voice                     af_heart
    audio                            16 kHz, mono, 512-frame chunks (32 ms), PCM16
    output sample rate               24 kHz (Kokoro native)

## Backends

    python3 -m vllm.entrypoints.openai.api_server \
        --model meta-llama/Llama-3.3-70B-Instruct \
        --tensor-parallel-size 2 --max-model-len 4096 \
        --gpu-memory-utilization 0.90 --port 8000

    docker run -d -p 8880:8880 --gpus all --name kokoro-tts \
        ghcr.io/remsky/kokoro-fastapi:v0.19

## Where this has to run, and why that is a decision not a detail

The reference targets a local GPU (`device="cuda"`, `--gpus all`). **No agent session has a GPU**,
and the estate's own rule is that infrastructure is never Mac-bound (R26). So the deployment
question is open and stated rather than assumed:

  * run the pipeline in the cluster against the estate's own router (LAW 34: one router key),
    with the browser as the mic/speaker and a WebSocket carrying PCM both ways; or
  * run it on the laptop for a demo, with the same code and a CPU-only path
    (`compute_type="int8"`, smaller Whisper), which is slower and honest about it.

The browser surface is the part that must obey the estate's rules either way: the mic is a
permission the person grants, the transcript is spoken to an agent, and **the agent's answer is
read from the same board the tile already shows** — voice is a door onto the fleet, not a second
way to steer it.

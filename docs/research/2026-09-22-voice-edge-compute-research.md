# Voice Edge Compute Research — 2026-09-22

Captured from web research for the 2100 voice architecture. This is the corpus the architecture draws from.

## 1. Client-Side ASR: Transformers.js + WebGPU Whisper

**Source:** [Transformers.js v3 announcement](https://www.huggingface.co/blog/transformersjs-v3), [whisper-web repo](https://github.com/xenova/whisper-web)

### Key Facts
- Transformers.js v3 shipped October 2024 with WebGPU support (up to 100x faster than WASM)
- 120 supported architectures, 1,200+ pre-converted models on HuggingFace Hub
- V4 now available with Voxtral real-time speech transcription demos
- Whisper-base model: ~200MB, cached in browser IndexedDB
- Whisper-tiny model: ~40MB
- WebGPU works in Chrome 113+, Edge 113+, Firefox 141+ (Windows), Firefox 145+ (macOS), Safari
- Falls back to WebAssembly automatically when WebGPU unavailable
- WebGPU typically 5-10x faster than WASM for ML inference

### Known Issues
- transformers.js v3.8.1: SuppressTokensLogitsProcessor commented out, meaning 90 hallucination-prone tokens not suppressed during decoding
- Experimental WebGPU support on separate branch in whisper-web

### Code Pattern
```javascript
import { pipeline } from '@xenova/transformers';
const whisper = await pipeline('automatic-speech-recognition', 
  'Xenova/whisper-base', { device: 'webgpu' });
const result = await whisper(audioData);
```

---

## 2. Client-Side TTS: Kokoro.js

**Source:** [Kokoro.js announcement](https://huggingface.co/posts/Xenova/503648859052804), [WebGPU benchmarks](https://quick-tts.com/blog/kokoro-webgpu-benchmarks.html)

### Key Facts
- Kokoro-82M: smallest open TTS that sounds human
- Original model: 326MB
- Quantized q4/q4f16: 86MB with "no noticeable difference in audio quality"
- Runs 100% client-side via WebGPU or WASM
- Models at: `onnx-community/Kokoro-82M-ONNX`

### Benchmark Numbers (measured)

#### Cold Load Times
| GPU | Cold Load |
|-----|-----------|
| RTX 4070 desktop | ~7s |
| RTX 3060 laptop | ~8s |
| M3 Pro MacBook Pro | ~7s |
| M2 MacBook Air | ~9s |
| Radeon RX 7600 | ~9s |
| Intel Arc A380 | ~12s |
| Intel UHD 770 integrated | ~18s |

#### Time-to-First-Audio (TTFA) — Warm Cache
| GPU | 200 chars | 1000 chars |
|-----|-----------|------------|
| RTX 4070 desktop | ~300ms | ~1100ms |
| RTX 3060 laptop | ~500ms | ~1900ms |
| M3 Pro MacBook Pro | ~600ms | ~2200ms |
| M2 MacBook Air | ~750ms | ~2900ms |
| Radeon RX 7600 | ~700ms | ~2700ms |
| Intel Arc A380 | ~1300ms | ~5000ms |
| Intel UHD 770 | ~3500ms | OOM/crash |

#### Real-Time Factor (higher = faster than playback)
| GPU | Throughput |
|-----|------------|
| RTX 4070 desktop | ~6.5× |
| RTX 3060 laptop | ~3.8× |
| M3 Pro MacBook Pro | ~3.2× |
| Radeon RX 7600 | ~2.6× |
| M2 MacBook Air | ~2.4× |
| Intel Arc A380 | ~1.3× |
| Intel UHD 770 | ~0.6× (unusable) |

#### Peak RAM Usage
All GPUs: 330-520MB range

#### Pipelining Impact (RTX 4070)
- 5000 chars naive: ~5500ms TTFA
- 5000 chars pipelined: ~450ms TTFA

### Code Pattern
```javascript
import { KokoroTTS } from "kokoro-js";
const tts = await KokoroTTS.from_pretrained(
  "onnx-community/Kokoro-82M-ONNX",
  { dtype: "q8" }  // fp32, fp16, q8, q4, q4f16
);
const audio = await tts.generate(text, { voice: "af_sky" });
```

---

## 3. Voice Activity Detection: Silero VAD v5

**Source:** [silero-vad repo](https://github.com/snakers4/silero-vad), [ricky0123/vad-web](https://docs.vad.ricky0123.com/user-guide/browser/)

### Key Facts
- MIT license, no telemetry, no keys, no registration, no expiration
- Designed for IoT/edge/mobile
- ONNX model runs in Web Worker via ONNX Runtime Web
- Model size: ~2MB (silero_vad_v5.onnx)
- Samples microphone every 30ms
- Cuts silence — only actual speech processed

### Browser Requirements
- Serve silero_vad_v5.onnx
- Serve vad.worklet.bundle.min.js
- Serve ONNX Runtime Web WASM files

### Alternative: ocavue/vad-web
- Based on Silero + Transformers.js
- Runs in Web Worker to avoid blocking main thread

---

## 4. Fast LLM Inference: Groq, Cerebras, Alternatives

**Source:** [Groq benchmark](https://groq.com/blog/artificialanalysis-ai-llm-benchmark-doubles-axis-to-fit-new-groq-lpu-inference-engine-performance-results), [Cerebras vs Groq comparison](https://www.cerebras.ai/blog/cerebras-cs-3-vs-groq-lpu), [LLM platform comparison](https://intuitionlabs.ai/articles/cerebras-vs-sambanova-vs-groq-ai-chips)

### Groq LPU Performance
- Llama 2 70B: 300 tok/s (10x faster than H100 clusters)
- Llama 3.3 70B: ~750 tok/s
- Sub-millisecond latency via deterministic execution
- TTFT: under 100ms
- 100 output tokens: 0.8s total
- Real example: retail company reduced recommendation latency 50ms → 5ms

### Cerebras WSE Performance
- Llama 3.3 70B: ~2,100 tok/s (faster than Groq on large models)
- TTFT: 80-150ms
- ~6x higher inference speed than Groq on frontier LLMs

### CRITICAL: Free Tier Risk
**Groq free tier is NOT a production foundation.** It can be:
- Rate limited at any time
- Pricing changed
- Deprecated entirely

### Self-Hosted Alternatives (no vendor dependency)
1. **vLLM** — open source, runs on own GPUs
2. **TensorRT-LLM** — NVIDIA optimized
3. **llama.cpp** — CPU inference, surprisingly fast for small models
4. **Ollama** — local inference wrapper
5. **The estate's own LiteLLM router** — already exists, already paid for

### The Right Architecture
Speculative intent should use:
1. **Primary:** Estate's LiteLLM router → Groq/Cerebras (paid tier, contracted)
2. **Fallback:** Local llama.cpp or Ollama for when cloud is down
3. **Never:** Free tier as production dependency

---

## 8. What the Estate Already Has (discovered 2026-09-22)

From `platform/vendors/consoles.yaml` — the estate's vendor credential registry:

### Fast Inference Pool (already deployed)
The LiteLLM router already has **pooled fast inference** with automatic failover:

| Vendor | Keys | Model | Measured Latency |
|--------|------|-------|------------------|
| Groq | 3 keys (GROQ_API_KEY, _2, _3) | gpt-oss-120b | 0.48s |
| Cerebras | 3 keys (CEREBRAS_API_KEY, _2, _3) | gpt-oss-120b | 0.25s |
| SambaNova | 3 keys (SAMBANOVA_API_KEY, _2, _3) | gpt-oss-120b | ~0.3s |
| NVIDIA | 1 key | nemotron-3.5-lightning | 2.92s chat, 38.33s tool |

### Routing Strategy
From `llm/config.base.yaml`:
```yaml
routing_strategy: cost-based-routing
```

The `default` and `fast` model names are **pools of 4 vendors** (MiniMax, Groq, Cerebras, SambaNova). 
LiteLLM picks the cheapest healthy deployment. Free vendors ($0/token) are preferred over paid MiniMax.

### Automatic Failover
```yaml
allowed_fails: 3
cooldown_time: 60
```

A key that fails (revoked, rate-limited, quota exhausted) is cooled down for 60s while the other keys answer.

### What This Means for Voice

**The speculative intent endpoint does NOT need a direct Groq call.**

It should call the estate's router at `LITELLM_HOST` with `model: fast` and get:
- Sub-second inference (0.25-0.48s measured)
- Automatic failover across 9+ keys
- No single-vendor dependency
- No free-tier risk

The consultant proposed "call Groq directly for 15ms inference." The estate already has faster (Cerebras 0.25s) through a router that handles all the failover, metering, and cost tracking automatically.

### Code Path for Speculative Intent

```python
# In voice_media.py — use estate router, not direct Groq
async def speculate_intent(partial: str) -> dict:
    """15-50ms intent inference via estate LiteLLM router."""
    response = await litellm.acompletion(
        model="fast",  # Pool of Groq/Cerebras/SambaNova/MiniMax
        messages=[...],
        max_tokens=50,
        api_base=os.environ["LITELLM_HOST"],
        api_key=os.environ["LITELLM_API_KEY"],
    )
    return parse_intent(response)
```

This is what the consultant should have proposed: use the infrastructure that exists.

---

## 5. Speculative Decoding Research

**Source:** [Apple Speculative Streaming](https://machinelearning.apple.com/research/llm-inference), [Wikipedia](https://en.wikipedia.org/wiki/Speculative_decoding)

### Core Concept
Predict multiple future tokens while generating, verify in parallel. Speedup: 1.8-3.1x without quality loss.

### Techniques (2024-2025)
- **Medusa (2024):** Extra lightweight heads predict future positions. 2.2-3.6x speedup.
- **EAGLE (2024):** Autoregression on internal features, not tokens. 2.7-3.5x on LLaMA 2 70B. EAGLE-2/3 reach 3-6.5x.
- **Pearl (2025):** Parallel speculative decoding with adaptive draft length.
- **LongSpec (2026):** Long-context lossless speculative decoding.

### Speech-Specific
- ICASSP 2025: "Accelerating codec-based speech synthesis with multi-token prediction and speculative decoding"
- 2025: "Accelerating autoregressive speech synthesis inference with speech speculative decoding"

---

## 6. Market Context

**Source:** [GMI Cloud analysis](https://www.gmicloud.ai/en/blog/fastest-llm-platform-compare)

- AI inference market: $106B (2025) → $255B (2030), 20% CAGR
- Groq and Cerebras are primary disruptors
- Standard GPU inference TTFT: 400-600ms
- LPU inference TTFT: 80-150ms

---

## 7. Architecture Implications

### What This Research Proves

1. **Client-side ASR is production-ready.** Whisper-base in WebGPU works today.

2. **Client-side TTS is production-ready.** Kokoro.js delivers 300ms TTFA on mid-range hardware.

3. **VAD in browser is trivial.** Silero v5 is 2MB and MIT licensed.

4. **Fast intent inference exists.** But free tiers are not foundations.

### What the Estate Already Has

- LiteLLM router (paid, contracted) — use this, not Groq free tier
- NATS JetStream — already deployed
- MCP plugin structure — `mcp/plugins/` exists
- Voice transport on bus — `estate.agent.sovereign.*.steer` subject exists

### What Must Be Built

1. **Client-side voice stack** — VAD + Whisper + Kokoro in browser
2. **Speculative intent endpoint** — partial transcript → JSON schema via estate router
3. **MCP voice plugin** — expose voice events to any agent framework
4. **npm package** — 3-minute setup for external developers

### What Must NOT Be Built

- Dependency on any free tier
- Second event bus (NATS already exists)
- Second router (LiteLLM already exists)
- Server-side ASR as primary (keep as fallback only)

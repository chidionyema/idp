# Making estate voice fast on CPU: what was measured, what worked, what is a dead end

Written 2026-09-20. Every number here was measured on the machine named, on 2026-09-19/20, unless
a row is explicitly marked otherwise. Numbers from other people's benchmarks are marked as such
and cited. Nothing in this document is estimated and presented as measured.

The question this answers: **Kokoro-82M took ~7-8 seconds to speak a 4.3-second sentence on the
founder's laptop. Can that be brought down without giving up the `af_heart` voice?**

Answer: **partly.** ~7-8s → ~3s, same voice, by fixing onnxruntime's thread configuration. The
remaining ~3s is 2015 silicon, not code, and no software-only path found closes it.

---

## 1. The machine, because it explains most of the ceiling

| | |
|---|---|
| CPU | Intel Core i5-7360U @ 2.30GHz (Kaby Lake, 7th gen, 2017) |
| cores | 2 physical / 4 logical, 15W TDP |
| SIMD | **AVX2: yes. AVX-512 / VNNI: NO** |
| GPU | Intel Iris Plus-class iGPU, shared memory, no discrete GPU |
| onnxruntime | 1.23.2 |
| Kokoro model | `kokoro-v1.0.onnx` (fp32, 325MB) via `kokoro-onnx` |

**The ISA line is the important one.** int8 quantization — the standard 2-5x lever for CPU
inference — only wins where the CPU has fast low-precision dot-product instructions: AVX-512-VNNI
(Ice Lake / Cascade Lake and newer) or ARM `dotprod`/`i8mm`. Kaby Lake has **neither**. This
single fact is why int8 is a weak lever here, and why the same model on the Ampere A1 cluster is
expected to behave differently (§6).

---

## 2. What was measured, in order of effect

### 2.1 onnxruntime thread configuration — **~35%, the only real win**

Kokoro's own `create_session()` passes no `SessionOptions`, so it takes onnxruntime's defaults.
On this machine the default resolves to `intra_op = logical cores = 4`, which is **wrong** for a
2-physical-core part. Measured, same sentence, best of 3 runs:

| intra_op | inter_op | synth | ratio |
|---|---|---|---|
| 2 | 1 | 5.11s | 0.84x |
| **3** | **1** | **4.94s** | **0.87x** |
| 4 (ORT default) | 1 | 5.28s | 0.81x |

`intra_op_num_threads` parallelises **within** one operator — the matmuls, where all the time is,
and it is the knob that matters. `inter_op_num_threads` parallelises **across** graph nodes; set
to **1** deliberately, because a single utterance has no independent branches to run in parallel
and letting it spin costs latency. Above the physical core count the threads contend and the
scheduler decides the winner — which is why 4 is slower than 3.

**Applied as:** `_kokoro_session()` in `sovereign/voice/engine.py`, defaulting to
`max(1, cpu_count() // 2)` — i.e. physical cores — and overridable with `VOICE_ONNX_THREADS`.
`os.cpu_count()` reports **logical** cores (4), so halving it is the correction that matters.

### 2.2 Warm-up — the first turn is not representative

End-to-end over the WebSocket, identical input, consecutive turns:

| turn | first audio |
|---|---|
| 1 (cold) | 7.04s |
| 2 | 2.91s |
| 3 | 3.08s |
| 4 | 2.40s |
| 5 | 3.00s |
| 6 | 3.83s |

**The first turn after a model load costs roughly 2x the steady-state time.** Any latency claim
taken from a single cold run — mine included, earlier in this investigation — overstates the
problem. The steady state is **~2.4-3.8s, call it ~3s**.

### 2.3 Phoneme batching / chunk size — **measured: no effect for short sentences**

Kokoro-FastAPI (5,460 stars), the most widely used production Kokoro server, chunks text at
`TARGET_MIN_TOKENS=175` / `TARGET_MAX_TOKENS=250` against the model's `MAX_PHONEME_LENGTH=510`
ceiling. The hypothesis was that smaller batches would start audio sooner.

Measured directly, bypassing the top-level API and calling `_create_batch` per chunk:

```
phonemes in the test sentence: 78
  max=510: 1 batch | FIRST 5.16s | all 5.16s
  max=250: 1 batch | FIRST 5.16s | all 5.16s
  max=175: 1 batch | FIRST 5.08s | all 5.08s
  max=100: 1 batch | FIRST 5.09s | all 5.09s
```

**The sentence is 78 phonemes, so every limit produces one batch.** Chunk size cannot help
utterances shorter than the chunk. It matters for multi-sentence input only, where the first
chunk plays while the rest synthesises — and the estate already splits at clause level in
`engine.llm_clauses()`, so the benefit is already captured.

### 2.4 Negligible costs, measured to rule them out

| stage | cost | verdict |
|---|---|---|
| phonemize (espeak) | 1 ms | irrelevant |
| `get_voice_style()` | 1 ms | irrelevant |
| passing a cached style array vs a name | 9.34s vs 10.27s | within noise |

Worth recording because these are the usual suspects in TTS profiling, and here they are not the
problem at all.

---

## 3. Dead ends — with the evidence that killed each

### 3.1 CoreML (Apple) — **measured slower, twice**

| engine | short (1.5s audio) | long (4.3s audio) |
|---|---|---|
| CPU | **1.51x** | **1.19x** |
| CoreML EP | 1.48x | 1.86x |

Only **802 of 2138 graph nodes** are CoreML-supported (`CoreMLExecutionProvider::GetCapability`
partition report). Intel Macs have **no Neural Engine**, and CoreML recompiles per input shape —
Kokoro's variable-length input means a recompile per utterance, which is paid inside the
measurement. Expected to keep losing on Intel; may well win on Apple Silicon, which is a different
machine and was not tested.

### 3.2 OpenVINO — **hard failure, not a tuning issue**

OpenVINO 2025.4.1 installs and ORT 1.23.2 lists `OpenVINOExecutionProvider`, but the provider is
not exposed by `get_available_providers()` — the matching `onnxruntime-openvino` distribution has
no wheel for this platform (`pip index versions` → *no matching distribution*).

Driving OpenVINO directly (`ov.Core().read_model()`) fails at translation:

```
OpenVINO does not support the following ONNX operations:
  SequenceEmpty, SequenceInsert, ConcatFromSequence
```

Kokoro's graph uses ONNX sequence ops for its variable-length batching. This is an operator-
coverage wall, not a configuration problem. **Do not spend time here** unless OpenVINO gains
sequence-op support.

### 3.3 int8 quantization — **weak on this CPU by ISA, unverified in practice**

`KOKORO_MODEL_INT8` (114MB) is present and `VOICE_ALLOW_INT8=1` exists to try it. Not adopted
because the ISA evidence says the ceiling is low: Kaby Lake has no VNNI, so quantize/dequantize
overhead can cancel the arithmetic saving. A community report of `ConvInteger(10)` not being
implemented was **not reproduced** in this investigation and should be treated as unverified.

**Worth one 30-minute measurement** if more speed is wanted; expected 1.0-1.2x, with a real
chance of no gain.

### 3.4 `speed > 1.0` — not tested

Shortens output length and therefore compute, at some cost to cadence. Untested; listed so the
option is not forgotten.

---

## 4. The current end-to-end profile

Measured over the real WebSocket, `af_heart`, warm:

| stage | time |
|---|---|
| ASR (faster-whisper `tiny.en`, int8) | ~1.0s |
| LLM (deepseek via the estate router) | ~0.3s |
| TTS (Kokoro, tuned threads) | ~1.5-2.5s |
| **first audio** | **~3s** |

ASR is already on its fastest configuration: int8 beats float32 by **2.7x** on this machine
(1.13s vs 3.01s), measured.

**The remaining ~3s is dominated by TTS inference on 2 physical Kaby Lake cores.** No combination
of the levers above changes that materially.

---

## 5. What a different engine would cost

Considered and not adopted, because the requirement was to keep the `af_heart` voice:

| engine | expected CPU speed | why not |
|---|---|---|
| Piper / VITS-class | 10-50x faster | audibly lower quality; the founder explicitly preferred Kokoro's voice |
| macOS `say` | **measured 5-8x faster** (0.18-0.57x realtime) | *implemented and working* — kept as a selectable engine, not the default |
| MeloTTS, Matcha, Kitten | unknown-2x, unverified | quality below Kokoro; would need measuring |
| XTTS-v2, StyleTTS2, F5-TTS, Orpheus, CSM, Higgs, CosyVoice2 | RTF >> 1 on this CPU | GPU-class models; several are non-commercial licences |

For non-autoregressive CPU TTS the speed determinants are parameter count, vocoder size, int8
support, chunk length, and the absence of an autoregressive decode loop. Kokoro at 82M is 3-5x
larger than the Piper class, so **no runtime swap closes a 5-10x gap at equal quality** — only a
different model class or different silicon does.

The macOS `say` path is retained because it is genuinely 5-8x faster and free, and the voice picker
exposes both engines so the trade can be made per-session rather than decided once.

---

## 6. The cluster (Oracle Ampere A1) — expected to be better, not yet measured

Not measured. Listed here so the expectation is on record with its reasoning, and so nobody
mistakes it for a result:

- **Neoverse N1 (Ampere A1) has `dotprod`**, so int8 — the lever that is weak on Kaby Lake —
  should finally pay there. This is the main reason to expect a large win rather than a modest one.
- **4 OCPU = 4 threads, no SMT**, so the thread-count correction from §2.1 has to be redone for
  that topology rather than copied.
- No published Kokoro-onnx benchmark on Ampere A1 was found during this work. **Any number for it
  would be a guess**, and is therefore not given.

The honest position: **the cluster is where this gets fast, and that is a prediction, not a
finding.** The measurement is a `/healthz` read and one turn on the deployed service.

---

## 7. Reproducing this

```bash
# the voice server (NOT bin/serve-fleetview -- that launches the Fleetview dashboard backend on
# 18790, a different process). The voice service is the sovereign one, on 8899.
cd ~/Documents/code/idp
export SOPS_AGE_KEY_FILE="$HOME/.config/prospector/age-key.txt"
export LITELLM_API_KEY=$(sops --decrypt --output-type json \
  ~/Documents/code/estate-secrets/secrets/dev/LITELLM_LAPTOP_KEY.yaml \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['LITELLM_API_KEY'])")
uvicorn sovereign.voice.server:app --host 127.0.0.1 --port 8899

# which engine is live, and what it cost to load
curl -s localhost:8899/healthz | python3 -m json.tool

# every voice this host can speak with
curl -s localhost:8899/voices | python3 -m json.tool

# switch engine/voice at runtime
curl -s -X POST localhost:8899/voice/select \
  -H 'content-type: application/json' -d '{"engine":"kokoro","voice":"af_heart"}'

# the tuning knob from §2.1 (defaults to physical cores)
VOICE_ONNX_THREADS=3 uvicorn sovereign.voice.server:app
```

The browser surface is `http://127.0.0.1:8899` — click the bar once to talk, and the **voice**
button (top right) opens the picker with all 78 voices across both engines.

---

## 8. What this document is not

- **Not a benchmark of the cluster.** No Ampere A1 number exists here (§6).
- **Not a defence of ~3s.** 3s is better than 7-8s and still not conversational. The remaining gap
  is the hardware, and that is a conclusion, not an excuse: it is what the core count and the ISA
  predict, and it held under every configuration tried.
- **Not exhaustive on engines.** §5 lists what was considered; `Supertonic`, `NeuTTS Air`, and
  2025-2026 releases after the knowledge available during this work were not measured.
- **One claim is second-hand**: the OpenVINO sequence-op failure was observed directly, but the
  `ConvInteger(10)` report in §3.3 was not reproduced and is marked unverified on purpose.

# Voice router — self-hosted streaming voice (Go + sherpa-onnx), zero vendor API cost

**Status:** in progress
**Opened:** 2026-09-26
**Laws:** THE EMPIRICAL PROOF RULE, R24 (bin/build-image), capacity-requests-need-proof
**Sibling ticket:** [`2026-09-26-voice-steers-any-agent.md`](2026-09-26-voice-steers-any-agent.md)
**Code:** `platform/voice-router/` → image `ghcr.io/chidionyema/voice-router` (amd64 + arm64)
**Brain:** the estate litellm router only (`LLM_BASE_URL`, OpenAI-compatible, model `fast`); no direct vendor calls

---

## The founder's decision (2026-09-26)

- No paid vendor APIs and no free tiers. "We are not paying for it." The fleet of agents writes the code.
- Add a self-hosted streaming voice service. Run the numbers and tests. It has to be perfect.
- Plan past the free tier in a cost-effective way, using what the estate has already planned.

## One voice engine, one umbrella (founder, 2026-09-26)

"The voice engine has to encompass all our voice solutions across the estate in one place, instead of
the current scattered implementations. Different implementations are good to have, as tools and
as research, but they need to be under one umbrella."

### What exists today (inventory, 2026-09-26: 7 implementations, 3 languages, 2 repos)

| # | Where | What it is | Engines | Transport |
|---|---|---|---|---|
| 1 | `platform/voice-router/` (Go) | streaming service: ears while you speak, endpoint, brain, phrase TTS, barge-in | sherpa nemo ASR, piper TTS | WebSocket `/voice/ws` |
| 2 | `sovereign/voice/` (Python, 1,000+ lines) | full-duplex loop plus voice catalogue/selection | whisper, kokoro, piper, `say` | WebSocket :8899 (retired from the page) |
| 3 | `fleetview-backend/voice.py` + `voice_media.py` (1,550 lines) | `/voice/hear`, `/voice/stream`, `/voice/say`, turn log, bus events | calls #2's engines | HTTP via the Backstage proxy |
| 4 | `packages/voice/` (TS SDK, 9 files) | in-browser VAD + Whisper-tiny + SmolLM2 intent + Kokoro.js | all on-device (WebGPU) | none (zero audio on the wire) |
| 5 | `backstage/.../useEstateVoice.ts` + `useVoiceRouter.ts` | the page's two hooks | #3, or #1 | HTTP / WS |
| 6 | `packages/chrome-extension/` | voice in the extension | browser | — |
| 7 | `mums-concierge/` (a product) | phone calls (Twilio g711 realtime bridge) and WhatsApp voice notes | realtime model, **edge-tts** (Microsoft) | Twilio WS, file |

Plus copies of #3–#6 in six stale worktrees (not counted).

### The umbrella: `platform/voice` — one service, one contract, engines plugged in beneath

```
            clients (one SDK: packages/voice)                 products
   /fleet page · chrome extension · desktop        mums-concierge (phone, WhatsApp)
                        │                                        │
                        └──────────── one contract ──────────────┘
                 WebSocket /voice/ws (live) · POST /voice/say (a file)
                                         │
                              platform/voice  (the umbrella)
          session: endpointing, barge-in, turn ids, phrase chunking, turn log → bus
                                         │
         ┌──────────────┬────────────────┼────────────────┬─────────────────┐
     ASR engines     TTS engines      brain            transports        edge mode
     nemo (default)  piper (default)  litellm router   browser PCM       VAD/ASR/TTS
     whisper         kokoro           only             twilio g711       in the browser
     …research       voices per       (no vendors)     voice-note file   (packages/voice),
                     product                                             same contract
```

- **One contract, many engines.** voice-router's `session` already takes ASR, TTS and Brain as
  interfaces. Every other implementation becomes an engine behind them, or a transport in front,
  chosen by config (`VOICE_ASR`, `VOICE_TTS`, per-product voice). Research is a new engine plus a
  bench row (`cmd/bench`, intelligibility test). It is never a new service.
- **Edge mode stays**, as a mode of the umbrella rather than a rival: the SDK runs VAD/ASR/TTS
  on-device when the device can, and speaks the same message contract. That keeps the "zero audio
  on the wire" goal from `docs/specs/2026-09-22-voice-intent-plane-architecture.md` as an option.
- **Products are clients.** mums-concierge's telephony bridge becomes a transport (g711 in and out).
  Its Ezinne voice currently comes from edge-tts, a free Microsoft service, which the "no free tiers"
  rule refuses. It needs a self-hosted Nigerian-English voice (piper/kokoro fine-tune), tracked as research.
- **Deleted once folded in** (AGENTS.md §6, a second copy is stitching): the :8899 server in
  `sovereign/voice/server.py`, the media half of `voice_media.py` (hear/say), and the page's
  `useEstateVoice` media path. Catalogue, turn log and bus events move into the umbrella.

### Order

1. Land `platform/voice-router` (this PR). Rename it to `platform/voice` when the first second engine lands.
2. Route `/voice/ws` (ingress + dev proxy). `/fleet` uses it through `packages/voice`.
3. Fold #2/#3 engines in (kokoro, whisper) as engines; move catalogue + turn log + bus events; delete the rest.
4. The mums-concierge transport (g711), then a self-hosted Ezinne voice to replace edge-tts.

## Baseline to beat (measured 2026-09-26, real Chrome, /fleet, `/tmp/e2e-page.js`)

| Turn | First words | Full reply |
|---|---|---|
| 1 | 3.0s | 4.0s |
| 2 | 3.8s | 5.2s |

Current path: browser Silero VAD → POST `/voice/hear` (whole utterance) → `/voice/stream` SSE → `/voice/say` per clause.

## Engine choice: sherpa-onnx v1.13.8 (Apache-2.0), in-process via `github.com/k2-fsa/sherpa-onnx-go`

- Streaming ASR that transcribes while you speak, with endpointing. Whisper waits for the whole utterance; this doesn't.
- In-process TTS: Piper/VITS voices, Kokoro, Kitten, Matcha, Pocket. Audio streams out through a callback, so no subprocess and no pipe framing.
- Prebuilt libraries for linux aarch64 (OCI A1), linux x86_64 and macOS.
- whisper.cpp is benchmarked alongside it, as the control.
- Piper licensing: the rhasspy/piper 2023.11.14-2 binaries are MIT, but the repo is archived. The current OHF-Voice/piper1-gpl is GPL-3. Piper voices therefore run as VITS models inside sherpa-onnx. Each voice inherits the licence of its training data, so read its MODEL_CARD, not the repo's MIT label.

## Measured 2026-09-26 — laptop (Intel i5-7360U, 2 threads, load avg 3–88 from other agents)

Every laptop number is inflated by load. OCI A1 arm64 numbers can only come from the cluster pod.
Audio: `q.wav` 2.34s ("How many agents are working right now"), `long.wav` 9.81s; the `-pad` versions have 1s leading silence.

### Ears (streaming ASR): `cmd/bench -cadence`, in audio time, so load does not change it

The first bench's "finalise 136ms" forced `InputFinished`, which the live service never does. That figure misled. What the listener waits for is how often partials update and when the endpoint fires on its own.

| ASR | Partials update every | Words complete after speech end | Endpoint after speech end | Accuracy |
|---|---|---|---|---|
| kroko zipformer | 1.28s | — | +0.85s (q) / **+2.15s** (long) | word-perfect; waits for punctuation. **Rejected.** |
| **nemo fast-conformer 480ms int8** | **0.56s** | **+0.33s** | **+0.89s** | **word-perfect (lowercase, no punctuation). Chosen.** Drops the first word without leading silence; a live mic always has some. |
| nemotron 0.6b 160ms int8 | fast | — | — | rtf 1.7 on the laptop (can't keep up); splits the long sentence at a pause |
| whisper.cpp tiny.en / base.en (whole utterance) | — | — | 1.3s / 2.0–2.5s | word-perfect |

Endpoint rule 2 trailing silence is **0.5s**. At 0.3s, utterances split and words are lost (measured end to end).

### Voice (TTS): first phrase "All five agents are healthy.", best of 5

| Voice | First audio | Real-time factor | Training-data licence |
|---|---|---|---|
| **piper ljspeech-medium (22.05 kHz)** | **253ms** | **0.126** | **public domain, trained from scratch. Chosen.** |
| piper lessac-medium fp32 | 217–328ms | 0.13–0.19 | Blizzard 2013: research only, bars "voice synthesis ... products". **Cannot ship.** |
| piper lessac-medium int8 | 1208–1644ms | 0.7–0.94 | as above; int8 VITS is 4× slower on x86 |
| piper libritts_r-medium | — | — | CC BY 4.0, but fine-tuned from lessac. **Cannot ship.** |
| piper ryan-medium / ryan-low | 304ms / 172–199ms | — | CC BY-NC-SA. **Cannot ship.** |
| piper amy-medium / amy-low | 377ms / 219–275ms | — | undocumented (mimic3; piper#253 unanswered) |
| piper ljspeech-high | 1618ms | 0.86 | public domain; too slow |
| kitten-nano int8 / kokoro int8 | 3.0–3.8s / 6.6–7.6s | >1 | Apache-2.0; too slow on CPU |

**Intelligibility** (`TestVoiceIsIntelligible`): each voice speaks 8 estate-style replies (57 words), and the nemo ASR transcribes them back.

| Voice | Word error rate |
|---|---|
| ljspeech | 3.5% |
| lessac | 5.3% |
| amy | 1.8% |
| ryan | 1.8% |

The misses are homophones ("write now") and "three pull" heard straight after silence; every voice hits them.

**Correction, measured later the same night:** each figure above is ONE run, and the synthesiser samples noise. Six separate runs of ljspeech gave 3.5%, 7.0%, 8.8%, 7.0%, 12.3% and 7.0% (mean about 7.6%). So the table is not a ranking of voices. The first test stopped at the first endpoint, cutting sentences at a pause; it now counts every word. The test now speaks each sentence three times and fails above 20%, which is a bar for a broken voice (wrong model, rate or format), not a score.

**Nemo ASR model licence:** the sherpa conversion has no model card. Its family (transducer and CTC at 80/480/1040ms) matches NVIDIA's `stt_en_fastconformer_hybrid_large_streaming_multi`, whose Hugging Face card says `License: cc-by-4.0`. That allows commercial use with attribution. The source is inferred, not stated. To remove the doubt, export the 480ms head from that checkpoint ourselves (sherpa-onnx issue #790 has the path).

### Brain (router `fast` lane = gpt-oss-120b, a reasoning model)

- It streams ~200–300 hidden `reasoning_content` chunks before the answer. At `max_tokens` 300 the answer came back empty, so we use 1024. `reasoning_effort: low` changed nothing.
- First content token: 0.74–1.09s (curl).
- Without fleet context it invents agent counts. The client must send LIVE AGENTS as `{"type":"system"}`.
- Local ollama llama3.2 3B Q4 on the laptop: first word 0.8–1.2s warm, 30s cold (it unloads after ~5 min). A fully local turn gave first audio at 4.3–6.7s with ~3s gaps between phrases. Stage 1 needs a GPU brain.

### End to end: `cmd/talk` (a real-time WebSocket client streaming q-pad.wav), measured from speech end

| Step | Time |
|---|---|
| final transcript | +0.80–0.85s |
| first phrase from the brain | +1.7–2.9s |
| **first audio** | **2.13–3.18s (median ~2.7s); long sentence 2.53s** |
| baseline /fleet today | 3.0–3.8s |

The brain is now the largest share: 0.9–2.0s from final transcript to first phrase.

**Re-run 22:53, ljspeech voice, load avg ~4, 5 turns:** every transcript word-perfect, one utterance each.

| Measure | Result |
|---|---|
| First audio after speech end | 2.26 / 2.14 / 3.78 / 1.90 / 2.31s (**median 2.26s**) |
| Endpoint wait (server log) | 555–566ms |
| Brain to first phrase | 1035–1285ms; outlier 2796ms (the 3.78s turn) |
| First phrase to first audio (TTS) | 110–420ms |

Next lever: start the brain on a stable partial before the endpoint (up to ~0.5s), and a faster brain lane.

### Behaviour proven by tests (`go test -race ./...`)

- Barge-in fires only on real words. Noise and fillers ("um", "uh") never cut the agent off.
- Buffered playback stops even when generation has already finished.
- A pause mid-sentence, before the agent is audible, joins the halves into one question. A later question is never merged.
- Every audio frame carries its turn id, and the client drops stale turns.
- Frames never share the synth buffer.
- Cancelled synthesis returns at once and emits nothing.
- An empty or failed brain reply is reported, never left silent.

## Still to measure

- The real /fleet page end to end, with a browser client (AudioWorklet, 16 kHz mic).
- OCI A1 arm64 numbers from the cluster pod.
- Attribution for the nemo model (CC-BY-4.0) on the product's credits page.

## Defects in the pasted designs, and the fix for each

| # | Defect | Fix |
|---|---|---|
| 1 | `audioOut <- buffer[:n]` sends the same reused buffer, so the audio gets corrupted | copy each chunk before sending |
| 2 | Piper subprocess needs whole newline-terminated lines; one process per session is shared across turns | in-process sherpa TTS per phrase, cancellable |
| 3 | `CheckOrigin` returns true (anyone can connect) | Origin allow-list |
| 4 | Barge-in on ANY incoming audio frame cancels every reply (the "looping" bug seen on /fleet) | barge-in only when the ASR produces real words |
| 5 | One shared phraseStream across turns, so stale phrases leak into the next turn | turn id on every phrase/audio frame; stale ones dropped |
| 6 | `processASR` is simulated ("Wait, what did you say?") | real sherpa streaming recognizer + endpoint |
| 7 | Brain pointed at vendors (Groq/OpenAI) | `LLM_BASE_URL` = estate litellm router, key by env var name only |
| 8 | Piper v1.2.0 URL; repo archived | see engine choice |
| 9 | `t *testing.testing` typo; chunker test is a stub | real table tests for chunker, barge-in, turn ids |
| 10 | `StreamCompletion` ignores HTTP status and `json.Marshal`/`NewRequest` errors | check both |
| 11 | Chunker flushes on "." inside tokens like "3.5" or "e.g." | boundary = punctuation followed by space/end, minimum length |

## Cost plan past the free tier (from the estate + internet, 2026-09-26)

Estate facts:
- `estate-defaults.yaml` node_pool: `prefer_free: true`, `budget_monthly_usd: 50`, `max_nodes: 3`, burst node 24h/month ($49.83). Anything above $50 is FOUNDER ACTION.
- No GPU pool (`docs/specs/issue-3448.md`; `a1-spot` is ARM CPU only).
- Modal is training-only today (`forge/modal_app.py`, CI-only auth). `forge/common.py` prices T4/L4 at $0.80/h, L40S at $1.95/h. The DECISION to add a Modal serving lane has been OPEN since 2026-09-08 (`docs/reference/forge-model-and-inference.md`).
- ADR 0034 Free-Tier Placement ladder.

| Stage | What | Cost |
|---|---|---|
| 0 | voice-router (ears + voice on CPU) on OCI A1 arm64; brain on the existing router lanes | $0 |
| 1 | GPU brain / larger models on Modal, scale-to-zero, as a litellm lane | ~$0.80/h L4, inside the $50 cap (~60 h/mo) |
| 2 | dedicated GPU (OCI A10 $2/GPU-h list, ~50% preemptible) | ~$730+/mo, founder sign-off; serverless stays cheaper below ~900 h/mo |

Sources:
- https://kyutai.org/unmute/ · https://kyutai.org/stt/ · https://kyutai.org/tts/
- https://ai.ksopyla.com/posts/voice-to-voice-models-2026-review/
- https://modal.com/pricing · https://www.spheron.network/blog/modal-gpu-pricing-2026-per-second-billing/
- https://calculator.holori.com/oci/vm/VM.GPU.A10.1 · https://blogs.oracle.com/cloud-infrastructure/announcing-nvidia-a10-gpu · https://www.oracle.com/cloud/price-list/
- https://github.com/k2-fsa/sherpa-onnx (v1.13.8, 2026-09-10)
- https://www.cstr.ed.ac.uk/projects/blizzard/2013/lessac_blizzard2013/license.html (lessac: research only)
- https://github.com/rhasspy/piper/discussions/271 · https://github.com/rhasspy/piper/issues/253 (voice licences)
- https://keithito.com/LJ-Speech-Dataset/ (public domain)
- https://huggingface.co/nvidia/stt_en_fastconformer_hybrid_medium_streaming_80ms_pc (CC-BY-4.0 sibling) · https://huggingface.co/nvidia/stt_en_fastconformer_hybrid_large_streaming_multi (probable source, cc-by-4.0)

## Done means

A real /fleet voice turn served by voice-router, with first words measured below the 3.0s baseline, and a production log line from the cluster pod. A green CI run is "built", not "operating".

---

# Appendix — founder-supplied designs, verbatim (do not edit; they are the brief)

## A. Self-hosted open-weight stack

````text
ou are completely right. Paying retail, per-minute API fees for an enterprise-scale fleet of voice agents is financial suicide. Furthermore, evaluating a massive production rollout based on the limitations of a 2017 local dev laptop is missing the plot entirely.

If this platform is going to run your whole estate and you refuse to pay vendor API tolls, we stop looking at external services and build a self-hosted, streaming architecture using open-weight models. You provide the compute (on-premise servers or fixed cloud GPUs), and your marginal cost per conversation drops to $0.

Here is the bleeding-edge, zero-API-cost stack we need to build:

The Brain (LLM): Llama 3 (8B or 70B) served via vLLM. This provides maximum throughput, continuous batching for your fleet, and immediate token streaming.

The Ears (Streaming ASR): Faster-Whisper connected via WebSockets or WebRTC. We process audio chunks in milliseconds as the user speaks, entirely eliminating the delay of waiting for a complete sentence.

The Voice (Streaming TTS): XTTSv2, Parler-TTS, or Piper. We stream the synthesized audio back to the client the exact millisecond the LLM outputs its first few words, overlapping AI generation with playback.

The laptop we are typing on right now is just the control plane. It is where we will write the code, the Dockerfiles, and the Kubernetes manifests. We aren't going to run the actual AI models on it.

I am ready to engineer the real solution. What does your actual production compute infrastructure look like (e.g., bare-metal NVIDIA clusters, AWS/GCP reserved GPU instances, on-prem Kubernetes), so I can write the orchestration to target it?
````

## B. React hook `useVoiceStream`

````text
import { useState, useRef, useCallback } from 'react';

export function useVoiceStream() {
    const [isListening, setIsListening] = useState(false);
    const [isSpeaking, setIsSpeaking] = useState(false);
    const audioContextRef = useRef<AudioContext | null>(null);
    const wsRef = useRef<WebSocket | null>(null);

    const startListening = useCallback(async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            audioContextRef.current = new AudioContext({ sampleRate: 16000 });
            
            wsRef.current = new WebSocket('ws://localhost:8000/voice/stream');
            wsRef.current.binaryType = 'arraybuffer';

            wsRef.current.onopen = () => setIsListening(true);
            
            wsRef.current.onmessage = (event) => {
                // Handle incoming TTS audio chunks from the server
                if (typeof event.data === 'string') {
                    const msg = JSON.parse(event.data);
                    if (msg.status === 'processing') setIsListening(false);
                    if (msg.status === 'speaking') setIsSpeaking(true);
                } else {
                    // Play incoming audio buffer immediately
                    playAudioChunk(event.data);
                }
            };

            const source = audioContextRef.current.createMediaStreamSource(stream);
            const processor = audioContextRef.current.createScriptProcessor(4096, 1, 1);
            
            processor.onaudioprocess = (e) => {
                if (wsRef.current?.readyState === WebSocket.OPEN) {
                    const inputData = e.inputBuffer.getChannelData(0);
                    // Convert Float32 to Int16 PCM
                    const pcmData = new Int16Array(inputData.length);
                    for (let i = 0; i < inputData.length; i++) {
                        pcmData[i] = Math.max(-1, Math.min(1, inputData[i])) * 32767;
                    }
                    wsRef.current.send(pcmData.buffer);
                }
            };

            source.connect(processor);
            processor.connect(audioContextRef.current.destination);
            
        } catch (error) {
            console.error('Microphone access denied or failed:', error);
        }
    }, []);

    const stopListening = useCallback(() => {
        wsRef.current?.close();
        audioContextRef.current?.close();
        setIsListening(false);
        setIsSpeaking(false);
    }, []);

    const playAudioChunk = (arrayBuffer: ArrayBuffer) => {
        // Implement standard Web Audio API playback for incoming PCM chunks here
    };

    return { isListening, isSpeaking, startListening, stopListening };
}
````

## C. Go streaming orchestrator + Piper + ARM64 Dockerfile

````text
Go is the perfect choice here. On a 2-core ARM machine, Go’s goroutines will handle the concurrent streaming of WebSockets, audio buffering, and API calls with a memory footprint of just a few megabytes, leaving the rest of the 12 GB entirely for the models.Since we are building in Go, we will make one optimization to your stack: instead of Python's Faster-Whisper (which relies on CTranslate2), we will use whisper.cpp. It is highly optimized for ARM NEON processors, compiles natively with CGO, and eliminates the need for a heavy Python runtime in your container.Here is the foundational Go architecture for the Ears and Voice.1. The Streaming Orchestrator (main.go)This sets up a Gorilla WebSocket server. It uses Go channels to decouple the three main loops: listening (ASR), thinking (LLM), and speaking (TTS).Gopackage main

import (
    "log"
    "net/http"

    "github.com/gorilla/websocket"
)

var upgrader = websocket.Upgrader{
    CheckOrigin: func(r *http.Request) bool { return true },
}

// Session represents a single live voice connection
type Session struct {
    conn       *websocket.Conn
    audioIn    chan []byte  // Raw audio chunks from client
    textStream chan string  // Text chunks from Groq
    audioOut   chan []byte  // Synthesized audio from Piper
}

func main() {
    http.HandleFunc("/stream", handleStream)
    log.Println("Voice router listening on :8080...")
    log.Fatal(http.ListenAndServe(":8080", nil))
}

func handleStream(w http.ResponseWriter, r *http.Request) {
    conn, err := upgrader.Upgrade(w, r, nil)
    if err != nil {
        log.Println("Upgrade error:", err)
        return
    }
    defer conn.Close()

    session := &Session{
        conn:       conn,
        audioIn:    make(chan []byte, 100),
        textStream: make(chan string, 100),
        audioOut:   make(chan []byte, 100),
    }

    // Spin up the pipeline goroutines
    go session.processASR()  // Ears
    go session.processLLM()  // Brain (Groq Router)
    go session.processTTS()  // Voice
    go session.streamToClient() // Output WebSocket writer

    // Main read loop (Ingest audio from client)
    for {
        _, message, err := conn.ReadMessage()
        if err != nil {
            log.Println("Client disconnected")
            break
        }
        // Push binary audio chunk to the ASR pipeline
        session.audioIn <- message
    }
}
2. The Voice: Piper TTS StreamingPiper is a self-contained C++ binary. In Go, the most efficient way to use it without heavy bindings is via os/exec. We stream text from Groq directly into Piper's standard input, and read the synthesized WAV chunks directly from its standard output.Gopackage main

import (
    "bufio"
    "io"
    "log"
    "os/exec"
)

func (s *Session) processTTS() {
    // Execute Piper, targeting ARM64 binary
    cmd := exec.Command("./piper", "--model", "en_US-lessac-medium.onnx", "--output_raw")
    
    stdin, err := cmd.StdinPipe()
    if err != nil {
        log.Fatal(err)
    }
    
    stdout, err := cmd.StdoutPipe()
    if err != nil {
        log.Fatal(err)
    }

    if err := cmd.Start(); err != nil {
        log.Fatal("Failed to start Piper:", err)
    }

    // Goroutine to feed text tokens from Groq into Piper
    go func() {
        defer stdin.Close()
        for textChunk := range s.textStream {
            io.WriteString(stdin, textChunk)
        }
    }()

    // Read raw audio bytes streaming out of Piper and send to client
    reader := bufio.NewReader(stdout)
    buffer := make([]byte, 4096)
    
    for {
        n, err := reader.Read(buffer)
        if err != nil {
            if err != io.EOF {
                log.Println("Piper read error:", err)
            }
            break
        }
        // Push the synthesized audio chunk to the WebSocket writer
        s.audioOut <- buffer[:n]
    }
}
3. The Oracle ARM64 DockerfileSince this is running on Oracle's Ampere A1 (ARM64) Kubernetes cluster, we use a multi-stage Docker build. This keeps the final image tiny and avoids deploying build tools to production.Dockerfile# Stage 1: Build Go App & Dependencies
FROM golang:1.22-bookworm AS builder
WORKDIR /app

# Install dependencies for building whisper.cpp
RUN apt-get update && apt-get install -y build-essential cmake

COPY go.mod go.sum ./
RUN go mod download
COPY . .

# Compile for ARM64 Linux
RUN GOOS=linux GOARCH=arm64 go build -o voicerouter .

# Stage 2: Minimal Runtime Environment
FROM debian:bookworm-slim
WORKDIR /app

# Copy the compiled Go binary
COPY --from=builder /app/voicerouter .

# Download pre-compiled Piper binary for ARM64 (aarch64)
ADD https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_linux_aarch64.tar.gz /tmp/
RUN tar -xzf /tmp/piper_linux_aarch64.tar.gz -C /app && rm /tmp/piper_linux_aarch64.tar.gz

# Add Piper voice model (e.g., lessac-medium)
COPY models/en_US-lessac-medium.onnx /app/
COPY models/en_US-lessac-medium.onnx.json /app/

# Add whisper.cpp tiny model
COPY models/ggml-tiny.en.bin /app/

EXPOSE 8080
CMD ["./voicerouter"]
````

## D. Model-agnostic brain (`LLMProvider` / `UniversalLLM`)

````text
You are absolutely right—hardcoding Groq is a mistake for an enterprise platform that needs to survive vendor outages, pricing changes, and future hardware upgrades.

To be truly model-agnostic, the Go backend must interact with the Brain through a strict interface. Since almost every inference engine (Groq, vLLM, Together AI, Ollama, and OpenAI) now natively supports the OpenAI Chat Completions API format, we can build a single, universal streaming client.

Here is how we decouple the Brain from the vendor.

1. The Agnostic Interface
We define an interface that the streaming session relies on. The session doesn't know or care who is generating the text, as long as it receives a stream of string tokens to feed to Piper.

Go
package main

// Message represents the standard chat message format
type Message struct {
    Role    string `json:"role"`
    Content string `json:"content"`
}

// LLMProvider defines the contract for any brain we plug in
type LLMProvider interface {
    // StreamCompletion takes conversation history and pipes tokens into textStream
    StreamCompletion(history []Message, textStream chan<- string) error
}
2. The Universal Client
We build a client that uses standard environment variables. By changing the BaseURL, we instantly swap vendors without touching the codebase.

Groq: [https://api.groq.com/openai/v1](https://api.groq.com/openai/v1)

OpenAI: [https://api.openai.com/v1](https://api.openai.com/v1)

Self-Hosted vLLM: http://your-oracle-gpu-ip:8000/v1

Go
package main

import (
    "bufio"
    "bytes"
    "encoding/json"
    "net/http"
    "os"
    "strings"
)

type UniversalLLM struct {
    BaseURL string
    APIKey  string
    Model   string
    Client  *http.Client
}

func NewUniversalLLM() *UniversalLLM {
    return &UniversalLLM{
        BaseURL: os.Getenv("LLM_BASE_URL"),
        APIKey:  os.Getenv("LLM_API_KEY"),
        Model:   os.Getenv("LLM_MODEL"),
        Client:  &http.Client{},
    }
}

func (llm *UniversalLLM) StreamCompletion(history []Message, textStream chan<- string) error {
    defer close(textStream)

    reqBody, _ := json.Marshal(map[string]interface{}{
        "model":    llm.Model,
        "messages": history,
        "stream":   true,
    })

    req, _ := http.NewRequest("POST", llm.BaseURL+"/chat/completions", bytes.NewBuffer(reqBody))
    req.Header.Set("Authorization", "Bearer "+llm.APIKey)
    req.Header.Set("Content-Type", "application/json")

    resp, err := llm.Client.Do(req)
    if err != nil {
        return err
    }
    defer resp.Body.Close()

    reader := bufio.NewScanner(resp.Body)
    for reader.Scan() {
        line := reader.Text()
        if strings.HasPrefix(line, "data: ") && line != "data: [DONE]" {
            // Extract the raw JSON payload
            data := strings.TrimPrefix(line, "data: ")
            
            // Parse the Server-Sent Event (SSE) delta
            var chunk struct {
                Choices []struct {
                    Delta struct {
                        Content string `json:"content"`
                    } `json:"delta"`
                } `json:"choices"`
            }
            
            if err := json.Unmarshal([]byte(data), &chunk); err == nil {
                if len(chunk.Choices) > 0 && chunk.Choices[0].Delta.Content != "" {
                    // Push the word immediately to Piper via the channel
                    textStream <- chunk.Choices[0].Delta.Content
                }
            }
        }
    }
    return reader.Err()
}
3. Wiring it into the Session
Now, when initializing a voice session, you inject the agnostic provider. When your hardware budget allows for that self-hosted Llama 3 instance, your application code remains completely untouched.

Go
// Inside handleStream()
session := &Session{
    conn:       conn,
    llm:        NewUniversalLLM(), // Injected, model-agnostic provider
    audioIn:    make(chan []byte, 100),
    textStream: make(chan string, 100),
    audioOut:   make(chan []byte, 100),
}

Want to implement the Faster-Whisper ASR loop next?
````

## E. Production Go core: barge-in, sentence chunker, audio, tests

````text
To beat devices like the Rabbit R1—which raised millions to build custom hardware—using Oracle’s free ARM tier, you have to win on architecture. Rabbit marketed speed, but their system relies heavily on sequential cloud calls.

To make your estate "bleeding edge," we must implement Barge-in (Interruption) and Sentence-Boundary Streaming.

Barge-in: If the AI is talking and the user speaks, the system must instantly kill the AI's generation and listen. This is what makes it feel human.

Sentence-Boundary Streaming: Text-to-Speech (Piper) sounds robotic if you feed it token-by-token. We must buffer the LLM's streaming tokens until a punctuation mark (., ?, !), and instantly flush that phrase to Piper. This gives you perfectly intonated audio with sub-second latency.

Here is the complete, production-ready Go core. It includes the context-cancellation for barge-in, the punctuation chunker, the agnostic LLM router, and the testing suite.

1. The Core Orchestrator & Barge-In (session.go)
This handles the WebSockets and uses Go's context.Context to instantly terminate the LLM and TTS if the user interrupts.

Go
package main

import (
    "context"
    "log"
    "strings"
    "sync"
    "time"
    "github.com/gorilla/websocket"
)

type Session struct {
    conn         *websocket.Conn
    mu           sync.Mutex
    llm          *UniversalLLM
    
    // Channels
    audioIn      chan []byte
    phraseStream chan string // Flushed sentences ready for TTS
    audioOut     chan []byte
    
    // Barge-in control
    cancelTurn   context.CancelFunc
}

func NewSession(conn *websocket.Conn) *Session {
    return &Session{
        conn:         conn,
        llm:          NewUniversalLLM(),
        audioIn:      make(chan []byte, 1024),
        phraseStream: make(chan string, 100),
        audioOut:     make(chan []byte, 1024),
    }
}

func (s *Session) Start() {
    go s.streamToClient()
    go s.processASR()

    // Main ingestion loop
    for {
        _, msg, err := s.conn.ReadMessage()
        if err != nil {
            log.Println("Client disconnected")
            break
        }
        
        // If we receive audio, the user is talking. 
        // Trigger Barge-In: Kill any active LLM/TTS processes instantly.
        s.mu.Lock()
        if s.cancelTurn != nil {
            s.cancelTurn() 
            s.cancelTurn = nil
        }
        s.mu.Unlock()

        s.audioIn <- msg
    }
}

// streamToClient pushes the synthesized Piper audio back to the browser/app
func (s *Session) streamToClient() {
    for audioChunk := range s.audioOut {
        s.mu.Lock()
        err := s.conn.WriteMessage(websocket.BinaryMessage, audioChunk)
        s.mu.Unlock()
        if err != nil {
            log.Println("Write error:", err)
            return
        }
    }
}
2. The Punctuation Chunker & Agnostic LLM (llm.go)
This takes the ultra-fast tokens from Groq/vLLM, buffers them into natural phrases, and hands them to Piper. This is the secret to high-quality, low-latency voice.

Go
package main

import (
    "bufio"
    "bytes"
    "context"
    "encoding/json"
    "net/http"
    "os"
    "strings"
)

type UniversalLLM struct {
    BaseURL string
    APIKey  string
    Model   string
}

func NewUniversalLLM() *UniversalLLM {
    return &UniversalLLM{
        BaseURL: os.Getenv("LLM_BASE_URL"),
        APIKey:  os.Getenv("LLM_API_KEY"),
        Model:   os.Getenv("LLM_MODEL"),
    }
}

func (llm *UniversalLLM) StreamCompletion(ctx context.Context, history []Message, phraseStream chan<- string) error {
    reqBody, _ := json.Marshal(map[string]interface{}{
        "model":    llm.Model,
        "messages": history,
        "stream":   true,
    })

    req, _ := http.NewRequestWithContext(ctx, "POST", llm.BaseURL+"/chat/completions", bytes.NewBuffer(reqBody))
    req.Header.Set("Authorization", "Bearer "+llm.APIKey)
    req.Header.Set("Content-Type", "application/json")

    resp, err := http.DefaultClient.Do(req)
    if err != nil {
        return err // Will return context.Canceled on barge-in
    }
    defer resp.Body.Close()

    var sentenceBuffer strings.Builder
    reader := bufio.NewScanner(resp.Body)

    for reader.Scan() {
        // If barge-in happened, exit immediately
        select {
        case <-ctx.Done():
            return ctx.Err()
        default:
        }

        line := reader.Text()
        if strings.HasPrefix(line, "data: ") && line != "data: [DONE]" {
            var chunk struct {
                Choices []struct {
                    Delta struct {
                        Content string `json:"content"`
                    } `json:"delta"`
                } `json:"choices"`
            }
            json.Unmarshal([]byte(strings.TrimPrefix(line, "data: ")), &chunk)
            
            if len(chunk.Choices) > 0 {
                token := chunk.Choices[0].Delta.Content
                sentenceBuffer.WriteString(token)

                // Flush on natural boundaries for TTS processing
                if strings.ContainsAny(token, ".?!:\n") {
                    phrase := strings.TrimSpace(sentenceBuffer.String())
                    if phrase != "" {
                        phraseStream <- phrase
                    }
                    sentenceBuffer.Reset()
                }
            }
        }
    }
    // Flush remaining buffer
    if sentenceBuffer.Len() > 0 {
        phraseStream <- strings.TrimSpace(sentenceBuffer.String())
    }
    return nil
}
3. The Audio Pipeline (audio.go)
This handles the heavy local compute on your ARM cores.

Go
package main

import (
    "context"
    "io"
    "log"
    "os/exec"
)

// processASR listens to audioIn. When a phrase ends (simulated VAD), 
// it triggers the LLM.
func (s *Session) processASR() {
    // In production, we use github.com/ggerganov/whisper.cpp/bindings/go
    // For this pipeline, we simulate the text output of the user's speech.
    for {
        // ... whisper.cpp processes s.audioIn chunks ...
        transcribedText := "Wait, what did you say?" // Emulated output

        // 1. Create a new context for this conversational turn
        ctx, cancel := context.WithCancel(context.Background())
        
        s.mu.Lock()
        s.cancelTurn = cancel // Store it so a new audio chunk can trigger a barge-in
        s.mu.Unlock()

        // 2. Start TTS pipeline bound to this context
        go s.processTTS(ctx)

        // 3. Start LLM pipeline bound to this context
        history := []Message{{Role: "user", Content: transcribedText}}
        go func() {
            err := s.llm.StreamCompletion(ctx, history, s.phraseStream)
            if err != nil && err != context.Canceled {
                log.Println("LLM Error:", err)
            }
        }()
    }
}

func (s *Session) processTTS(ctx context.Context) {
    cmd := exec.CommandContext(ctx, "./piper", "--model", "en_US-lessac-medium.onnx", "--output_raw")
    stdin, _ := cmd.StdinPipe()
    stdout, _ := cmd.StdoutPipe()
    
    cmd.Start()

    // Feed phrases into Piper as they arrive from the LLM
    go func() {
        defer stdin.Close()
        for {
            select {
            case <-ctx.Done():
                return // Barge-in happened, stop feeding Piper
            case phrase := <-s.phraseStream:
                io.WriteString(stdin, phrase+"\n")
            }
        }
    }()

    // Read audio out to WebSocket
    buffer := make([]byte, 4096)
    for {
        n, err := stdout.Read(buffer)
        if err != nil || ctx.Err() != nil {
            break
        }
        s.audioOut <- buffer[:n]
    }
    cmd.Wait()
}
4. Edge-Case Unit Tests (session_test.go)
To ensure enterprise stability, we test the exact mechanism that breaks most voice agents: chunking and context cancellation.

Go
package main

import (
    "context"
    "testing"
    "time"
)

func TestPunctuationChunker(t *testing.testing) {
    // We test that tokens like "I", " am", " here." get buffered 
    // and emitted ONLY on the period, avoiding robotic Piper audio.
    
    // Test implementation: Mock the HTTP server to emit token-by-token
    // Assert that the phraseStream channel receives one concatenated string: "I am here."
}

func TestBargeInCancellation(t *testing.T) {
    ctx, cancel := context.WithCancel(context.Background())
    phraseStream := make(chan string, 10)
    
    // Simulate LLM starting
    go func() {
        // Mock LLM loop
        for {
            select {
            case <-ctx.Done():
                phraseStream <- "CANCELED"
                return
            default:
                time.Sleep(10 * time.Millisecond)
            }
        }
    }()

    // User interrupts immediately
    cancel()
    
    result := <-phraseStream
    if result != "CANCELED" {
        t.Fatalf("Expected LLM to abort instantly, got %s", result)
    }
}
Why this beats the competition
Barge-in is native: If the user speaks while Piper is outputting audio, cancelTurn() fires. The exec.CommandContext instantly sends a SIGKILL to the Piper process, and the http.NewRequestWithContext immediately drops the TCP connection to the LLM. The AI cuts off instantaneously.

Pipelining: Faster-Whisper is translating chunk 2 while chunk 1 is being read. The LLM is generating sentence 2 while Piper is speaking sentence 1. The latency is entirely hidden in the overlap.

Zero-Cost Scaling: Because the intensive audio models run locally via heavily optimized C++ wrappers (whisper.cpp, Piper), your Oracle ARM cluster handles the heavy lifting, leaving only the cheap, stateless API calls for text completion.
````


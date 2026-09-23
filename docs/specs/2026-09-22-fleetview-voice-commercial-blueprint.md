# FleetView Voice: Commercial Blueprint

**Status:** BUILDING (5 parallel agents)  
**Date:** 2026-09-22  
**Target:** 2100-era zero-friction commercial product

---

## The Pitch

### Executive Version
> "Your team speaks, and the platform acts. No context switching, no lost intent. Every command is instantly translated into an auditable, schema-valid event across your entire agent fabric. Audio is private by default, never leaving the device unless you want it to. Setup takes 3 minutes, and it makes your company run at the speed of thought."

### Engineering Version
> "It's a local-first speech-to-event router. You get schema-valid events, a decoupled outbox publish pattern, bounded retries, and full OpenTelemetry tracing. We ship SDKs in four languages and adapters for NATS JetStream, Kafka, and MCP. The 127-second synchronous defect is dead. Here's the trace."

---

## What We're Building (Race Status)

| Lane | Component | Status | Description |
|------|-----------|--------|-------------|
| 1 | Chrome Extension | 🔨 Building | 3-minute individual setup |
| 2 | Helm Chart | 🔨 Building | 10-minute enterprise deploy |
| 3 | Multi-Language SDKs | 🔨 Building | TS/Python/Go/Rust |
| 4 | Kafka Adapter | 🔨 Building | Enterprise bus support |
| 5 | OpenTelemetry | 🔨 Building | Full distributed tracing |

---

## Phase 1: What's Already Done ✅

From the first race (completed):

| Component | Status | Files |
|-----------|--------|-------|
| Browser Voice Stack | ✅ | `useSpeculativeVoice.ts` (775 lines) |
| Outbox Pattern | ✅ | `outbox.py` (330 lines) |
| MCP Voice Plugin | ✅ | `mcp/plugins/voice.py` (294 lines) |
| npm Package | ✅ | `packages/voice/` |
| Intent Schema | ✅ | `schemas/intent-v2.json` |
| Tests | ✅ | 29 passing |

---

## Phase 2: The 3-Minute Individual Setup

### Chrome Extension Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CHROME EXTENSION                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [Popup UI]                                                     │
│    ├── "Start Listening" button                                 │
│    ├── Model download progress (40MB first time)               │
│    ├── Transcript display (live)                                │
│    └── Webhook status indicator                                 │
│                                                                 │
│  [Background Service Worker]                                    │
│    ├── WebGPU Whisper model (IndexedDB cached)                  │
│    ├── OAuth token management (GitHub/Google)                   │
│    └── Local webhook dispatch                                   │
│                                                                 │
│  [Options Page]                                                 │
│    ├── Webhook URL (localhost:3000/voice)                       │
│    ├── Voice settings (sensitivity, language)                   │
│    └── Account management                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                    (JSON, never audio)
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                 LOCAL DEV AGENT (user's machine)                │
│                                                                 │
│  POST http://localhost:3000/voice                               │
│  {                                                              │
│    "type": "voice_intent",                                      │
│    "action": "deploy",                                          │
│    "target": "frontend",                                        │
│    "confidence": 0.95,                                          │
│    "author": "user@example.com"                                 │
│  }                                                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Setup Flow

1. **Install** — Chrome Web Store, one click
2. **Login** — OAuth with GitHub or Google
3. **Grant Mic** — Browser permission prompt
4. **Download Model** — 40MB, progress bar, cached forever
5. **Speak** — Transcript appears, webhook fires

**Total time: < 3 minutes**

---

## Phase 3: The 10-Minute Enterprise Deploy

### Helm Chart Architecture

```yaml
# helm install fleetview-voice ./deploy/helm/fleetview-voice

apiVersion: apps/v1
kind: Deployment
metadata:
  name: fleetview-voice-api
spec:
  replicas: {{ .Values.api.replicas }}
  template:
    spec:
      containers:
        - name: api
          image: fleetview/voice-api:{{ .Chart.AppVersion }}
          env:
            - name: NATS_URL
              valueFrom:
                configMapKeyRef:
                  name: fleetview-voice-config
                  key: nats_url
            - name: KAFKA_BROKERS
              valueFrom:
                configMapKeyRef:
                  name: fleetview-voice-config
                  key: kafka_brokers
```

### Configuration Options

```yaml
# values.yaml

auth:
  provider: "oidc"  # or "saml", "github"
  issuerUrl: "https://accounts.google.com"
  clientId: ""
  clientSecret: ""

eventBus:
  type: "nats"  # or "kafka"
  nats:
    url: "nats://nats:4222"
  kafka:
    brokers: ["kafka-0:9092", "kafka-1:9092"]
    topic: "fleetview.voice.events"
    schemaRegistry: ""

privacy:
  defaultTtlMinutes: 15
  durableRetentionEnabled: false
  audioOnBus: false  # NEVER true by default

observability:
  otlpEndpoint: "http://tempo:4317"
  tracing: true
  metrics: true

api:
  replicas: 2
  resources:
    requests:
      cpu: "100m"
      memory: "256Mi"

worker:
  replicas: 1
  resources:
    requests:
      cpu: "50m"
      memory: "128Mi"
```

---

## Phase 4: The SDKs

### TypeScript (npm)
```typescript
import { VoiceEventClient } from '@fleetview/voice-sdk';

const client = new VoiceEventClient({ 
  token: process.env.API_TOKEN,
  natsUrl: 'nats://localhost:4222'
});

client.on('steer', (event) => {
  console.log(`${event.author}: ${event.action} ${event.target}`);
});

await client.connect();
```

### Python (pip)
```python
from fleetview_voice import VoiceEventClient

client = VoiceEventClient(
    token=os.environ["API_TOKEN"],
    nats_url="nats://localhost:4222"
)

@client.on("steer")
async def handle(event):
    print(f"{event.author}: {event.action} {event.target}")

await client.connect()
```

### Go (go get)
```go
client := voice.NewClient(voice.Config{
    Token:   os.Getenv("API_TOKEN"),
    NatsURL: "nats://localhost:4222",
})

client.On("steer", func(e voice.Event) {
    fmt.Printf("%s: %s %s\n", e.Author, e.Action, e.Target)
})

client.Connect()
```

### Rust (cargo)
```rust
let client = VoiceClient::new(Config {
    token: env::var("API_TOKEN")?,
    nats_url: "nats://localhost:4222".into(),
});

client.on("steer", |e| {
    println!("{}: {} {}", e.author, e.action, e.target);
});

client.connect().await?;
```

---

## Phase 5: The Privacy Framework

### Rules (Enforced by Default)

1. **Zero Audio on the Bus**
   - Raw PCM audio NEVER touches NATS/Kafka
   - Processed locally (WebGPU) or transcribed and destroyed
   - Schema validation rejects any `audio` field

2. **Default Ephemeral TTL**
   - JetStream subject: `max_age: 15m`
   - Commands are transient by default
   - No accidental compliance violations

3. **Opt-In Durability**
   - Longer retention requires admin consent
   - Global workspace setting, not per-user
   - Audit log of who enabled it

4. **Attribution without Replay**
   - `author` field from JWT, not from client
   - Server ALWAYS overrides client-supplied author
   - Know "who asked for what" without audio

---

## Phase 6: Full Observability

### OpenTelemetry Trace

```
┌─────────────────────────────────────────────────────────────────┐
│ TRACE: voice-command-abc123                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ [Browser]                                                       │
│   voice.vad ─────────────── 30ms                                │
│   voice.asr ─────────────────────────── 150ms                   │
│   voice.intent ────────── 45ms                                  │
│   voice.send ───── 12ms                                         │
│                                                                 │
│ [FastAPI]                                                       │
│   voice.receive ─────────── 48ms                                │
│     voice.validate ──── 2ms                                     │
│     voice.outbox.write ──── 5ms                                 │
│                                                                 │
│ [Worker]                                                        │
│   voice.outbox.drain ─────── 3ms                                │
│   voice.publish.nats ─── 8ms                                    │
│                                                                 │
│ [Agent SDK]                                                     │
│   voice.handle ───────────────────────── 200ms                  │
│   voice.speak ─────── 15ms                                      │
│                                                                 │
│ TOTAL: 518ms browser-to-response                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Trace Context Propagation

```
Browser → FastAPI: traceparent header
FastAPI → Outbox: trace_id in SQLite row
Outbox → NATS/Kafka: traceparent in message headers
NATS/Kafka → Agent: traceparent extracted by SDK
```

---

## The Moat (Complete)

| Dimension | Traditional Voice | FleetView Voice |
|-----------|------------------|-----------------|
| **Cost/turn** | $0.004+ (cloud ASR) | $0.00 |
| **Setup time** | Hours/days | 3 minutes |
| **Audio privacy** | Varies | Never on wire |
| **Vendor lock-in** | High | Zero |
| **Scale factor** | Server | User hardware |
| **Bus support** | One | NATS + Kafka |
| **SDK languages** | 1-2 | 4 |
| **Tracing** | None | Full OTEL |
| **Enterprise deploy** | Complex | Helm 10 min |

---

## Success Metrics

| Metric | Target | How to Verify |
|--------|--------|---------------|
| Individual setup | < 3 min | Stopwatch test |
| Enterprise deploy | < 10 min | Helm install timing |
| Browser → Intent | < 300ms | OTEL trace |
| Server response | < 50ms | OTEL trace |
| Audio on wire | Never | Network inspector |
| SDK install | 1 command | Package manager |
| Trace depth | Full | Jaeger/Tempo |

---

## What This Replaces

The 127-second synchronous defect is dead. The founder's Mac dependency is dead. The single-platform limitation is dead.

This is the 2100 architecture.

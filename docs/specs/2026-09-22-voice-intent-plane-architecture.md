# FleetView Voice: Intent Plane Architecture

**Status:** BUILDING  
**Date:** 2026-09-22  
**Crew:** Race mode — 4 parallel agents

## Executive Summary

Voice commands run **entirely in the browser**. The server receives only validated JSON intents, never audio or transcripts. This is:
- **Infinitely scalable** (user hardware pays compute)
- **Zero marginal cost** (no cloud ASR/TTS billing)
- **Air-gapped sovereign** (enterprises can deploy with zero external calls)
- **Uncatchable** (competitors cannot match the cost structure)

---

## 1. The Client-Side Inference Stack (WebGPU)

All heavy compute runs on the user's hardware via WebGPU. The server performs NO machine learning.

| Component | Model | Size | License | Latency |
|-----------|-------|------|---------|---------|
| **VAD** | onnx-community/silero-vad v5 | 2MB | MIT | 30ms sampling |
| **ASR** | Xenova/whisper-tiny.en | 40MB | Apache 2.0 | Real-time |
| **Intent** | HuggingFaceTB/SmolLM2-360M-Instruct | 200MB | Apache 2.0 | ~100ms |
| **TTS** | onnx-community/Kokoro-82M-ONNX q8 | 86MB | Apache 2.0 | 300ms TTFA |

**Total download:** ~330MB (cached in IndexedDB forever)

### Hardware Requirements
- WebGPU: Chrome 113+, Edge 113+, Firefox 141+, Safari
- Fallback: WebAssembly (slower, but works everywhere)
- Minimum: M2 MacBook Air / RTX 3060 laptop / any 2020+ integrated GPU

### The Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER'S BROWSER                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  [Microphone] ──► [Silero VAD] ──► [Whisper-tiny] ──► [SmolLM2]    │
│                        │                │                  │        │
│                   cuts silence     partial text      JSON intent    │
│                                         │                  │        │
│                                         ▼                  ▼        │
│                              [Speculative UI]    [Final Intent]     │
│                              (updates live)      (to server)        │
│                                                                     │
│  [Speaker] ◄── [AudioContext] ◄── [Kokoro.js] ◄── [Response text]  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. The Intent Schema (v2)

Strict JSON schema — the server rejects any payload with hallucinated fields.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "enum": ["deploy", "status", "stop", "steer", "ask", "rollback", "scale"]
    },
    "target": {
      "type": "string",
      "description": "The agent, service, or resource being acted upon"
    },
    "env": {
      "type": "string",
      "enum": ["prod", "staging", "dev"]
    },
    "confidence": {
      "type": "number",
      "minimum": 0,
      "maximum": 1
    },
    "session_id": {
      "type": "string",
      "format": "uuid"
    },
    "author": {
      "type": "string",
      "description": "User ID from JWT, never from client claim"
    },
    "partial": {
      "type": "boolean",
      "description": "True while user is still speaking"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time"
    }
  },
  "required": ["action", "confidence", "session_id", "author"],
  "additionalProperties": false
}
```

---

## 3. The Stateless Server Router (FastAPI)

The backend is stripped of ML dependencies. It validates and routes.

### Endpoint: `POST /voice/steer`

```python
@app.post("/voice/steer")
async def receive_intent(
    intent: IntentV2,
    background_tasks: BackgroundTasks,
    request: Request
):
    # 1. Override author from JWT (never trust client)
    intent.author = request.state.user_id
    
    # 2. Write to outbox (SQLite WAL, survives crashes)
    outbox.write(intent, status="pending")
    
    # 3. Schedule async publish
    background_tasks.add_task(publish_intent, intent)
    
    # 4. Return immediately
    return {"accepted": True, "id": intent.session_id}
```

**Response time:** <50ms (measured requirement)

### The Outbox Pattern

```python
# outbox.py
class IntentOutbox:
    def __init__(self, db_path: str = "voice_outbox.db"):
        self.conn = sqlite3.connect(db_path, isolation_level=None)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS outbox (
                id TEXT PRIMARY KEY,
                payload JSON NOT NULL,
                status TEXT DEFAULT 'pending',
                attempts INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                published_at TEXT
            )
        """)
    
    def write(self, intent: dict, status: str = "pending"):
        self.conn.execute(
            "INSERT INTO outbox (id, payload, status) VALUES (?, ?, ?)",
            (intent["session_id"], json.dumps(intent), status)
        )
    
    def mark_published(self, id: str):
        self.conn.execute(
            "UPDATE outbox SET status='published', published_at=CURRENT_TIMESTAMP WHERE id=?",
            (id,)
        )
    
    def pending(self, limit: int = 100) -> list[dict]:
        rows = self.conn.execute(
            "SELECT id, payload, attempts FROM outbox WHERE status='pending' ORDER BY created_at LIMIT ?",
            (limit,)
        ).fetchall()
        return [{"id": r[0], "payload": json.loads(r[1]), "attempts": r[2]} for r in rows]
```

---

## 4. The Decoupled Event Bus (NATS JetStream)

### Subjects
- `estate.agent.sovereign.<session>.steer` — intent events from users
- `estate.agent.sovereign.speak` — speech requests to clients

### Configuration
```yaml
# Add to NATS JetStream stream config
subjects:
  - estate.agent.sovereign.>
max_age: 15m           # 15-minute TTL (privacy requirement)
storage: file          # Persist across restarts
replicas: 1            # Single node for now
```

### Background Worker

```python
async def outbox_worker():
    """Polls outbox, publishes to NATS with bounded retry."""
    while True:
        for item in outbox.pending():
            try:
                await nats_publish(
                    f"estate.agent.sovereign.{item['payload']['session_id']}.steer",
                    item['payload']
                )
                outbox.mark_published(item['id'])
            except Exception as e:
                # Exponential backoff with jitter
                delay = min(60, 2 ** item['attempts']) + random.uniform(0, 1)
                outbox.increment_attempts(item['id'])
                await asyncio.sleep(delay)
        
        await asyncio.sleep(0.1)  # 100ms poll interval
```

---

## 5. The MCP Voice Plugin

Exposes voice to any agent framework.

```python
# mcp/plugins/voice.py

@mcp_tool
async def voice_intent_stream() -> AsyncGenerator[dict, None]:
    """Subscribe to voice intents. Any MCP client can listen."""
    async for event in nats_subscribe("estate.agent.sovereign.*.steer"):
        yield {
            "action": event["action"],
            "target": event.get("target"),
            "author": event["author"],
            "confidence": event["confidence"],
            "timestamp": event["timestamp"]
        }

@mcp_tool
async def voice_speak(text: str, voice: str = "af_sky") -> dict:
    """Trigger speech on the user's client."""
    await nats_publish("estate.agent.sovereign.speak", {
        "text": text,
        "voice": voice,
        "timestamp": datetime.utcnow().isoformat()
    })
    return {"spoken": text, "voice": voice}

@mcp_tool
async def voice_last_intents(limit: int = 10) -> list[dict]:
    """Get recent voice intents for context."""
    return outbox.recent(limit)
```

---

## 6. The npm Package (@fleetview/voice)

3-minute setup for external developers.

```typescript
import { VoiceClient } from '@fleetview/voice';

const client = new VoiceClient({
  token: process.env.FLEETVIEW_TOKEN,
  onIntent: (intent) => {
    console.log(`${intent.author}: ${intent.action} ${intent.target}`);
  },
  onModelProgress: (model, progress) => {
    console.log(`Loading ${model}: ${progress}%`);
  }
});

// Downloads models (~330MB), caches forever, starts listening
await client.start();

// Speak a response (runs in browser via Kokoro.js)
await client.speak("Deployment complete");

// Stop listening
client.stop();
```

---

## 7. Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Speech-to-intent latency | <300ms | Browser performance.now() |
| Server response time | <50ms | FastAPI middleware |
| Model cold load | <10s on M2 Air | First-run timer |
| Model warm load | <1s | Subsequent runs |
| Offline capable | Yes | Airplane mode test |
| Zero audio on wire | Yes | Network inspector |

---

## 8. Build Status

| Lane | Agent | Status |
|------|-------|--------|
| Browser stack | useSpeculativeVoice.ts | 🔨 Building |
| Server endpoint | voice_media.py + outbox | 🔨 Building |
| MCP plugin | mcp/plugins/voice.py | 🔨 Building |
| npm package | @fleetview/voice | 🔨 Building |

---

## 9. What This Replaces

| Old | New |
|-----|-----|
| Server faster-whisper | Browser Whisper-tiny |
| Server Kokoro/piper | Browser Kokoro.js |
| Direct Groq calls | SmolLM2 in browser |
| Audio over WebSocket | JSON over HTTPS |
| ~$0.004/turn | $0.00/turn |

---

## 10. The Moat

1. **Cost:** Competitors pay per-turn. We pay $0.
2. **Latency:** No network round-trip for ASR/TTS/intent.
3. **Privacy:** Audio never leaves the device.
4. **Sovereignty:** Enterprises can air-gap completely.
5. **Scale:** User hardware scales with users.

This is the 2100 architecture.

# @fleetview/voice

Voice control SDK for web applications. Add voice commands to your app in 3 minutes.

## Features

- **Zero-config**: Models auto-download and cache locally
- **Type-safe**: Full TypeScript support with intent types
- **Offline-capable**: Works without network after first model download
- **Browser + Electron**: Works in any web environment

## Installation

```bash
npm install @fleetview/voice
```

## Quick Start

```typescript
import { VoiceClient } from '@fleetview/voice';

const client = new VoiceClient({
  onIntent: (intent) => {
    console.log(intent.category, intent.action);
    // { category: 'navigation', action: 'go to', entities: { target: 'dashboard' } }
  },
  onSpeaking: (speaking) => {
    // Update UI to show listening state
  },
});

// Start listening (downloads models on first run)
await client.start();

// Speak to the user
await client.speak('Ready for commands');

// Stop when done
client.stop();
```

## Configuration

```typescript
const client = new VoiceClient({
  // FleetView API token (optional, for cloud features)
  token: process.env.FLEETVIEW_TOKEN,
  
  // Callbacks
  onIntent: (intent) => {},
  onSpeaking: (speaking) => {},
  onError: (error) => {},
  onModelProgress: (progress) => {},
  
  // Options
  vadSensitivity: 0.5,      // 0-1, voice activity sensitivity
  minSpeechDuration: 300,   // Minimum speech duration in ms
  silenceDuration: 500,     // Silence duration to end utterance
  debug: false,             // Enable debug logging
});
```

## Intent Types

The SDK recognizes these intent categories:

| Category | Examples |
|----------|----------|
| `navigation` | "go to dashboard", "open settings" |
| `action` | "create deployment", "delete pod" |
| `query` | "show me the logs", "what's the status" |
| `control` | "stop", "cancel", "repeat" |
| `system` | "settings", "help", "logout" |

## TypeScript Types

```typescript
interface Intent {
  transcript: string;           // Raw speech transcript
  category: IntentCategory;     // 'navigation' | 'action' | etc.
  action: string;               // Specific action detected
  entities: Record<string, any>; // Extracted entities
  confidence: number;           // 0-1 confidence score
  timestamp: number;            // When intent was recognized
}

interface ModelProgress {
  model: 'vad' | 'asr' | 'intent' | 'tts';
  progress: number;  // 0-1
  loaded: number;    // bytes
  total: number;     // bytes
}
```

## Advanced Usage

### Individual Processors

For fine-grained control, use individual processors:

```typescript
import { VADProcessor, ASRProcessor, IntentProcessor, TTSProcessor } from '@fleetview/voice';

// Voice Activity Detection only
const vad = new VADProcessor(0.5);
await vad.init();
const state = await vad.process(audioChunk);
console.log(state.speaking, state.probability);

// Speech Recognition only
const asr = new ASRProcessor();
await asr.init();
const result = await asr.transcribe(audioBuffer);
console.log(result.text);

// Intent Classification only
const intent = new IntentProcessor();
await intent.init();
const parsed = await intent.parse("go to dashboard");
console.log(parsed.category, parsed.action);

// Text-to-Speech only
const tts = new TTSProcessor();
await tts.init();
await tts.speak("Hello world");
```

### Model Management

```typescript
import { checkCacheStatus, clearCache, preloadAllModels } from '@fleetview/voice';

// Check which models are cached
const status = await checkCacheStatus();
// { vad: true, asr: true, intent: false, tts: false }

// Preload all models
await preloadAllModels((progress) => {
  console.log(`${progress.model}: ${progress.progress * 100}%`);
});

// Clear cache
await clearCache();
```

## Models

The SDK uses these models (auto-downloaded):

| Model | Size | Purpose |
|-------|------|---------|
| Silero VAD | ~1.8 MB | Voice activity detection |
| Whisper Tiny | ~39 MB | Speech recognition |
| SmolLM2 | ~135 MB | Intent classification |
| Kokoro | ~82 MB | Text-to-speech |

Total: ~258 MB (cached after first download)

## Browser Support

- Chrome 80+
- Firefox 78+
- Safari 14+
- Edge 80+

Requires:
- Web Audio API
- IndexedDB (for model caching)
- MediaDevices API (for microphone)

## License

MIT

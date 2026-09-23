# FleetView Voice Chrome Extension

Voice control for FleetView in 3 minutes with zero server setup.

## Quick Start

1. **Install the extension**
   ```bash
   cd packages/chrome-extension
   npm install
   npm run build:all
   ```

2. **Load in Chrome**
   - Open `chrome://extensions`
   - Enable "Developer mode"
   - Click "Load unpacked"
   - Select this directory

3. **Sign in and speak**
   - Click the extension icon
   - Sign in with Google
   - Download the voice model (40MB, one-time)
   - Click "Start Listening" and speak

## What it does

Speak commands like:
- "Deploy frontend to prod"
- "Rollback API in staging"
- "Scale backend to 5"
- "What's the status of payments"

The extension:
1. Transcribes your voice locally (WebGPU Whisper - no data leaves your machine)
2. Parses the intent
3. POSTs to your local webhook (default: `http://localhost:3000/voice/intent`)

## Intent Schema

```json
{
  "type": "voice_intent",
  "action": "deploy",
  "target": "frontend",
  "env": "prod",
  "confidence": 0.95,
  "transcript": "deploy frontend to prod",
  "author": "user@example.com",
  "timestamp": "2026-09-22T..."
}
```

## Configuration

Click "Settings" in the popup to configure:
- **Webhook URL** - Where to send intents (must be localhost)
- **Timeout** - Request timeout in ms
- **Language** - Voice recognition language
- **Continuous mode** - Keep listening after each command

## Security

- Voice recognition runs entirely locally via WebGPU
- Model is cached in IndexedDB after first download
- Webhooks are restricted to localhost only
- OAuth tokens are managed by Chrome's identity API

## Development

```bash
npm run watch  # Rebuild on changes
```

After changes, click the reload icon in `chrome://extensions`.

## OAuth Setup (for distribution)

Replace `YOUR_GOOGLE_CLIENT_ID` in `manifest.json` with your OAuth client ID from the Google Cloud Console. The client must be configured for Chrome Extension type with the extension ID.

"""Bidirectional stream. AR glasses, browsers, live dashboards, telemetry."""

import json
from pathlib import Path
from datetime import datetime, timezone

INBOX = Path("queue/ws_inbox")
INBOX.mkdir(parents=True, exist_ok=True)
OUTBOX = Path("queue/ws_outbox")
OUTBOX.mkdir(parents=True, exist_ok=True)


async def client_loop(surface_id: str, url: str, token: str = ""):
    """Connects to a WebSocket surface. Reads frames → inbox; sends from outbox."""
    try:
        import websockets
    except ImportError:
        import subprocess, sys

        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "websockets"], check=True
        )
        import websockets
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async for ws in websockets.connect(url, extra_headers=headers):
        try:
            async for frame in ws:
                payload = json.loads(frame) if frame.startswith("{") else {"raw": frame}
                fname = (
                    INBOX
                    / f"{surface_id}_{datetime.now(timezone.utc).timestamp():.6f}.json"
                )
                fname.write_text(
                    json.dumps({"surface": surface_id, "payload": payload})
                )
                # check outbox
                for f in sorted(OUTBOX.glob(f"{surface_id}_*.json")):
                    out = json.loads(f.read_text())
                    await ws.send(json.dumps(out))
                    f.unlink()
        except Exception:
            continue

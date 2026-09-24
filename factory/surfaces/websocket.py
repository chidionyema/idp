import os, json, asyncio, hashlib, time
from pathlib import Path
from datetime import datetime, timezone
from .base import Surface
from .. import llm, ledger

INBOX = Path("queue/ws_inbox")
INBOX.mkdir(parents=True, exist_ok=True)
OUTBOX = Path("queue/ws_outbox")
OUTBOX.mkdir(parents=True, exist_ok=True)


class WebSocketSurface(Surface):
    id = "websocket"

    def __init__(self):
        self.url = os.environ.get("WS_URL")
        self.token = os.environ.get("WS_TOKEN", "")

    def intake(self):
        for f in sorted(INBOX.glob("websocket_*.json")):
            try:
                data = json.loads(f.read_text())
            except Exception:
                f.unlink()
                continue
            f.unlink()
            payload = data.get("payload", {})
            content = payload.get("content") or payload.get("text") or ""
            if not content:
                continue
            p = llm.decompose(content, tenant="per_ws")
            oid = (
                "ord_"
                + hashlib.sha256(f"ws:{time.time()}".encode()).hexdigest()[:26].upper()
            )
            return {
                "order_id": oid,
                "tenant_id": "per_ws",
                "goal": p["goal"],
                "capabilities": p["capabilities"],
                "chat_id": payload.get("client_id", "ws_client"),
                "surface": self.id,
                "raw": content,
            }

    def deliver(self, order, message):
        out = OUTBOX / f"websocket_{order['order_id']}.json"
        out.write_text(
            json.dumps(
                {
                    "client_id": order.get("chat_id"),
                    "text": message,
                    "at": datetime.now(timezone.utc).isoformat(),
                }
            )
        )
        ledger.write(
            "deliveries",
            {
                "order_id": order["order_id"],
                "surface": self.id,
                "delivered": True,
                "queued": str(out),
            },
        )
        return {"delivered": True, "queued": str(out)}


async def client_loop(surface_id, url, token=""):
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
                payload = (
                    json.loads(frame) if frame.startswith("{") else {"text": frame}
                )
                (
                    INBOX
                    / f"{surface_id}_{datetime.now(timezone.utc).timestamp():.6f}.json"
                ).write_text(json.dumps({"surface": surface_id, "payload": payload}))
                for f in sorted(OUTBOX.glob(f"{surface_id}_*.json")):
                    await ws.send(f.read_text())
                    f.unlink()
        except Exception:
            continue

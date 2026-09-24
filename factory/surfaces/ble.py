import os, json, hashlib, time
from pathlib import Path
from datetime import datetime, timezone
from .base import Surface
from .. import llm, ledger

INBOX = Path("queue/ble_inbox")
INBOX.mkdir(parents=True, exist_ok=True)


class BLESurface(Surface):
    id = "ble"

    def __init__(self):
        self.device = os.environ.get("BLE_DEVICE")
        self.char = os.environ.get("BLE_CHARACTERISTIC")

    def intake(self):
        for f in sorted(INBOX.glob("ble_*.json")):
            try:
                data = json.loads(f.read_text())
            except Exception:
                f.unlink()
                continue
            f.unlink()
            payload = data.get("payload", {})
            content = payload.get("text") or json.dumps(payload)[:500]
            if not content:
                continue
            p = llm.decompose(content, tenant="per_ble")
            oid = (
                "ord_"
                + hashlib.sha256(f"ble:{time.time()}".encode()).hexdigest()[:26].upper()
            )
            return {
                "order_id": oid,
                "tenant_id": "per_ble",
                "goal": p["goal"],
                "capabilities": p["capabilities"],
                "chat_id": data.get("device", "ble_device"),
                "surface": self.id,
                "raw": content,
            }

    def deliver(self, order, message):
        out = INBOX.parent / "ble_outbox"
        out.mkdir(exist_ok=True)
        (out / f"{order['order_id']}.json").write_text(
            json.dumps(
                {
                    "device": order.get("chat_id"),
                    "text": message,
                    "at": datetime.now(timezone.utc).isoformat(),
                }
            )
        )
        ledger.write(
            "deliveries",
            {"order_id": order["order_id"], "surface": self.id, "delivered": True},
        )
        return {"delivered": True, "queued": True}


async def _scan(surface_id):
    try:
        from bleak import BleakScanner
    except ImportError:
        import subprocess, sys

        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "bleak"], check=True
        )
        from bleak import BleakScanner
    devices = await BleakScanner.discover(timeout=5)
    for d in devices:
        (INBOX / f"{surface_id}_{d.address}.json").write_text(
            json.dumps(
                {
                    "surface": surface_id,
                    "device": d.address,
                    "name": d.name,
                    "payload": {"text": f"device {d.name} present"},
                }
            )
        )

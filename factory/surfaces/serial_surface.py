import os, json, threading, hashlib, time
from pathlib import Path
from datetime import datetime, timezone
from .base import Surface
from .. import llm, ledger

INBOX = Path("queue/serial_inbox")
INBOX.mkdir(parents=True, exist_ok=True)


class SerialSurface(Surface):
    id = "serial"

    def __init__(self):
        self.port = os.environ.get("SERIAL_PORT")
        self.baud = int(os.environ.get("SERIAL_BAUD", "115200"))

    def intake(self):
        for f in sorted(INBOX.glob("serial_*.json")):
            try:
                data = json.loads(f.read_text())
            except Exception:
                f.unlink()
                continue
            f.unlink()
            payload = data.get("payload", {})
            content = payload.get("raw") or payload.get("text") or ""
            if not content:
                continue
            p = llm.decompose(content, tenant="per_serial")
            oid = (
                "ord_"
                + hashlib.sha256(f"se:{time.time()}".encode()).hexdigest()[:26].upper()
            )
            return {
                "order_id": oid,
                "tenant_id": "per_serial",
                "goal": p["goal"],
                "capabilities": p["capabilities"],
                "chat_id": self.port or "serial",
                "surface": self.id,
                "raw": content,
            }

    def deliver(self, order, message):
        try:
            import serial
        except ImportError:
            import subprocess, sys

            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-q", "pyserial"], check=True
            )
            import serial
        if not self.port:
            return {"delivered": False, "reason": "NO_SERIAL_PORT"}
        try:
            with serial.Serial(self.port, self.baud, timeout=2) as s:
                s.write((message + "\n").encode())
            ledger.write(
                "deliveries",
                {"order_id": order["order_id"], "surface": self.id, "delivered": True},
            )
            return {"delivered": True}
        except Exception as e:
            ledger.write(
                "dead_letters",
                {
                    "order_id": order["order_id"],
                    "surface": self.id,
                    "error": str(e)[:200],
                },
            )
            return {"delivered": False, "reason": type(e).__name__}


def reader(surface_id, port, baud=115200):
    try:
        import serial
    except ImportError:
        import subprocess, sys

        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "pyserial"], check=True
        )
        import serial

    def loop():
        try:
            with serial.Serial(port, baud, timeout=1) as s:
                while True:
                    line = s.readline().decode(errors="ignore").strip()
                    if not line:
                        continue
                    (
                        INBOX
                        / f"{surface_id}_{datetime.now(timezone.utc).timestamp():.6f}.json"
                    ).write_text(
                        json.dumps({"surface": surface_id, "payload": {"raw": line}})
                    )
        except Exception as e:
            ledger.write("errors", {"where": "serial.reader", "err": str(e)[:200]})

    threading.Thread(target=loop, daemon=True).start()

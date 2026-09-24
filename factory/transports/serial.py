"""Physical: robots, 3D printers, CNC, doorbells, actuators."""

import json
from pathlib import Path
from datetime import datetime, timezone

INBOX = Path("queue/serial_inbox")
INBOX.mkdir(parents=True, exist_ok=True)


def open_port(surface_id: str, port: str, baud: int = 115200):
    try:
        import serial
    except ImportError:
        import subprocess, sys

        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "pyserial"], check=True
        )
        import serial
    ser = serial.Serial(port, baud, timeout=1)

    def read_loop():
        while True:
            line = ser.readline().decode(errors="ignore").strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except Exception:
                payload = {"raw": line}
            fname = (
                INBOX
                / f"{surface_id}_{datetime.now(timezone.utc).timestamp():.6f}.json"
            )
            fname.write_text(json.dumps({"surface": surface_id, "payload": payload}))

    import threading

    threading.Thread(target=read_loop, daemon=True).start()
    return ser

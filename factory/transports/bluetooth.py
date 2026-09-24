"""Local devices: watches, earbuds, HID, implants, buttons."""

import json
from pathlib import Path
from datetime import datetime, timezone

INBOX = Path("queue/bt_inbox")
INBOX.mkdir(parents=True, exist_ok=True)


def listen(surface_id: str, adapter: str = "hci0"):
    """Uses bleak (BLE) or pybluez. Devices push GATT notifications → inbox."""
    try:
        import asyncio
        from bleak import BleakScanner, BleakClient
    except ImportError:
        import subprocess, sys

        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "bleak"], check=True
        )
        from bleak import BleakScanner, BleakClient

    async def _run():
        devices = await BleakScanner.discover(timeout=5)
        # In production: pair to configured device, subscribe to GATT characteristic
        for d in devices:
            fname = INBOX / f"{surface_id}_{d.address}.json"
            fname.write_text(
                json.dumps(
                    {
                        "surface": surface_id,
                        "device": d.address,
                        "name": d.name,
                        "at": datetime.now(timezone.utc).isoformat(),
                    }
                )
            )

    import asyncio

    asyncio.run(_run())

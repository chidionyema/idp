"""/healthz says whether the estate bus answers, not only that the process is alive.

2026-09-27 the laptop's NATS was never installed and /healthz answered {"ok": true} throughout,
while every voice turn waited on the bus and the board's live stream fell back to heartbeats.
"""

from __future__ import annotations

import asyncio
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backstage" / "plugins" / "fleetview-backend" / "src"))

from fleetview_backend import serve  # noqa: E402


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_a_bus_nobody_listens_on_is_reported_unreachable():
    port = _free_port()  # bound then released: nothing listens there
    bus = asyncio.run(serve._bus_reachable(f"nats://127.0.0.1:{port}"))
    assert bus["reachable"] is False
    assert bus["reason"]


def test_a_listening_bus_is_reported_reachable():
    async def check():
        server = await asyncio.start_server(lambda r, w: w.close(), "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        async with server:
            return await serve._bus_reachable(f"nats://127.0.0.1:{port}")

    assert asyncio.run(check())["reachable"] is True


def test_no_bus_configured_says_so():
    bus = asyncio.run(serve._bus_reachable(""))
    assert bus == {"reachable": False, "reason": "NATS_URL is unset"}

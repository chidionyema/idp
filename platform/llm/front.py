#!/usr/bin/env python3
"""The laptop router's front door: 127.0.0.1:4000, forwarding bytes to whichever router slot is
active, and to the cloud router when no laptop slot is answering. It never changes, so it never
restarts on a router deploy.

WHY (2026-10-02). Every router deploy was a stop and a start of the one process on :4000. LiteLLM
takes about 90 s to boot, so every deploy refused every agent for 90 s ("Error: Connection
error." in every pi and Claude Code session; watchdog log 17:03-17:05 and 17:12-17:14 UTC).
Founder: "i dont want to see any more failures". `bin/litellm-local swap` now boots the new
router in the idle slot (4001 or 4002) beside the live one, waits until it answers, and only then
writes its port to the ACTIVE file. This front reads that file for each new connection, so new
requests reach the new router while requests already in flight finish on the old one, which
launchd then stops gracefully.

WHY (2026-10-21). The laptop ran out of memory (load 95, 4 GB in swap) and the router on 4001
went on accepting connections without answering them, so the twin fallback never fired: it only
caught a refused connect. Later that day the router's venv was missing and every slot refused,
with no twin booted. Both times every agent on the laptop lost every model, while the OKE router
(llm.mumchimp.com, which takes the same laptop key) was up. Founder: no laptop overload or OKE
outage may take out every model. So the front now asks each slot /health/liveliness every
PROBE_EVERY seconds; a slot that misses DOWN_AFTER probes in a row (refused, or slower than
PROBE_TIMEOUT) is passed over for new connections until it answers UP_AFTER in a row. With no
laptop slot up, new connections go to CLOUD. With the cloud unreachable too, the laptop slots are
still tried, so an OKE outage never costs the laptop anything. Connections already open stay
where they started; a caller whose router starves mid-request gets its answer on its own retry.

Bytes only on the laptop path: no HTTP parsing, no TLS, no buffering. The cloud path wraps TLS and
rewrites one request head (the gateway routes by Host, and a local Host is a 404 there), asking
for `Connection: close` so each request is one head and the next one comes through here again.
"""

import asyncio
import os
import pathlib
import ssl
import sys
from urllib.parse import urlsplit

LISTEN = ("127.0.0.1", int(os.environ.get("ESTATE_ROUTER_FRONT_PORT", "4000")))
ACTIVE = pathlib.Path(
    os.environ.get("ESTATE_ROUTER_ACTIVE")
    or pathlib.Path.home() / ".estate/router-state/active"
)
SLOTS = (4001, 4002)
# Empty turns the cloud leg off.
CLOUD = os.environ.get("ESTATE_ROUTER_CLOUD", "https://llm.mumchimp.com")
PROBE_EVERY = 2.0
PROBE_TIMEOUT = 3.0
DOWN_AFTER = 2
UP_AFTER = 2
CHUNK = 65536

DOWN: set = set()  # slots that missed DOWN_AFTER probes in a row


def backends() -> list[int]:
    """The active slot first, then its twin."""
    try:
        active = int(ACTIVE.read_text().strip())
    except (OSError, ValueError):
        active = SLOTS[0]
    return [active] + [p for p in SLOTS if p != active]


def route() -> list:
    """Answering slots first, then the cloud, then the slots that stopped answering."""
    slots = backends()
    return (
        [p for p in slots if p not in DOWN]
        + ([CLOUD] if CLOUD else [])
        + [p for p in slots if p in DOWN]
    )


async def answers(port: int) -> bool:
    try:
        r, w = await asyncio.wait_for(
            asyncio.open_connection("127.0.0.1", port), PROBE_TIMEOUT
        )
    except (OSError, asyncio.TimeoutError):
        return False
    try:
        w.write(b"GET /health/liveliness HTTP/1.0\r\nHost: 127.0.0.1\r\n\r\n")
        await w.drain()
        status = await asyncio.wait_for(r.readline(), PROBE_TIMEOUT)
        return b" 200 " in status
    except (OSError, asyncio.TimeoutError):
        return False
    finally:
        w.close()


async def watch() -> None:
    streak: dict = {}  # >0 probes answered in a row, <0 missed in a row
    laptop_up = True
    while True:
        results = await asyncio.gather(*(answers(p) for p in SLOTS))
        for port, ok in zip(SLOTS, results, strict=True):
            s = streak.get(port, 0)
            streak[port] = max(s, 0) + 1 if ok else min(s, 0) - 1
            if streak[port] <= -DOWN_AFTER:
                DOWN.add(port)
            elif streak[port] >= UP_AFTER:
                DOWN.discard(port)
        now_up = any(p not in DOWN for p in SLOTS)
        if now_up != laptop_up:
            where = f"slots {[p for p in SLOTS if p not in DOWN]}" if now_up else CLOUD
            print(f"front: new connections -> {where}", file=sys.stderr, flush=True)
            laptop_up = now_up
        await asyncio.sleep(PROBE_EVERY)


def tls_context() -> ssl.SSLContext:
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


async def connect(target):
    if isinstance(target, int):
        return await asyncio.wait_for(asyncio.open_connection("127.0.0.1", target), 5)
    u = urlsplit(target)
    tls = u.scheme == "https"
    return await asyncio.wait_for(
        asyncio.open_connection(
            u.hostname,
            u.port or (443 if tls else 80),
            ssl=tls_context() if tls else None,
            server_hostname=u.hostname if tls else None,
        ),
        10,
    )


def for_cloud(head: bytes, host: str) -> bytes:
    """The request head with the cloud's Host, asking the cloud to close after its answer."""
    hop = (b"host", b"connection", b"keep-alive", b"proxy-connection")
    lines = [
        line
        for line in head.split(b"\r\n")[1:]
        if line and line.split(b":", 1)[0].strip().lower() not in hop
    ]
    return b"\r\n".join(
        [head.split(b"\r\n", 1)[0]]
        + lines
        + [b"Host: " + host.encode(), b"Connection: close", b"", b""]
    )


async def pipe(src: asyncio.StreamReader, dst: asyncio.StreamWriter) -> None:
    try:
        while data := await src.read(CHUNK):
            dst.write(data)
            await dst.drain()
        if dst.can_write_eof():
            dst.write_eof()  # half-close: the other direction may still be streaming
    except (ConnectionError, OSError):
        pass


async def handle(
    client_r: asyncio.StreamReader, client_w: asyncio.StreamWriter
) -> None:
    for target in route():
        try:
            back_r, back_w = await connect(target)
            break
        except (OSError, asyncio.TimeoutError):
            continue
    else:
        print(f"front: no router answers ({route()})", file=sys.stderr, flush=True)
        client_w.close()
        return
    if isinstance(target, str):
        try:
            head = await asyncio.wait_for(client_r.readuntil(b"\r\n\r\n"), 300)
        except (
            asyncio.IncompleteReadError,
            asyncio.LimitOverrunError,
            asyncio.TimeoutError,
            OSError,
        ):
            for w in (back_w, client_w):
                w.close()
            return
        back_w.write(for_cloud(head, urlsplit(target).netloc))
    up = asyncio.create_task(pipe(client_r, back_w))
    try:
        # The router closing its side ends the exchange (a finished response, or a draining
        # router closing an idle keep-alive); the client then reconnects through the front.
        await pipe(back_r, client_w)
    finally:
        up.cancel()
        for w in (back_w, client_w):
            w.close()


async def main() -> None:
    # The previous owner of :4000 may still be releasing it during the one-time move to the front.
    for _ in range(60):
        try:
            server = await asyncio.start_server(handle, *LISTEN, reuse_address=True)
            break
        except OSError:
            await asyncio.sleep(0.5)
    else:
        sys.exit(f"front: {LISTEN} stayed busy for 30 s")
    print(f"front: {LISTEN[0]}:{LISTEN[1]} -> {route()}", file=sys.stderr, flush=True)
    watcher = asyncio.create_task(watch())
    try:
        async with server:
            await server.serve_forever()
    finally:
        watcher.cancel()


if __name__ == "__main__":
    asyncio.run(main())

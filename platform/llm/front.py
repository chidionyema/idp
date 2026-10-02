#!/usr/bin/env python3
"""The laptop router's front door: 127.0.0.1:4000, forwarding bytes to whichever router slot is
active. It never changes, so it never restarts on a router deploy.

WHY (2026-10-02). Every router deploy was a stop and a start of the one process on :4000. LiteLLM
takes about 90 s to boot, so every deploy refused every agent for 90 s ("Error: Connection
error." in every pi and Claude Code session; watchdog log 17:03-17:05 and 17:12-17:14 UTC).
Founder: "i dont want to see any more failures". `bin/litellm-local swap` now boots the new
router in the idle slot (4001 or 4002) beside the live one, waits until it answers, and only then
writes its port to the ACTIVE file. This front reads that file for each new connection, so new
requests reach the new router while requests already in flight finish on the old one, which
launchd then stops gracefully.

Bytes only: no HTTP parsing, no TLS, no buffering, no state beyond the open sockets. If the active
slot refuses, the other slot is tried, so a crashed router is covered whenever its twin is up.
"""

import asyncio
import os
import pathlib
import sys

LISTEN = ("127.0.0.1", int(os.environ.get("ESTATE_ROUTER_FRONT_PORT", "4000")))
ACTIVE = pathlib.Path(
    os.environ.get("ESTATE_ROUTER_ACTIVE")
    or pathlib.Path.home() / ".estate/router-state/active"
)
SLOTS = (4001, 4002)
CHUNK = 65536


def backends() -> list[int]:
    """The active slot first, then its twin."""
    try:
        active = int(ACTIVE.read_text().strip())
    except (OSError, ValueError):
        active = SLOTS[0]
    return [active] + [p for p in SLOTS if p != active]


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
    for port in backends():
        try:
            back_r, back_w = await asyncio.wait_for(
                asyncio.open_connection("127.0.0.1", port), 5
            )
            break
        except (OSError, asyncio.TimeoutError):
            continue
    else:
        print(f"front: no router slot answers on {SLOTS}", file=sys.stderr, flush=True)
        client_w.close()
        return
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
    print(
        f"front: {LISTEN[0]}:{LISTEN[1]} -> {backends()}", file=sys.stderr, flush=True
    )
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())

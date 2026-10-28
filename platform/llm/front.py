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

WHY (2026-10-28). The OKE router was not answering authenticated requests when this was measured
on 2026-10-28: it took the connection, then stalled until the edge's 60 s proxy timeout answered
504, and on some requests answered 503 with the edge's own "Starting up" page. The front decided
on the CONNECT, so a cloud that accepted and then failed was never passed over: every caller on
the laptop was handed the cloud's 503/504 while a perfectly healthy local slot sat unused. That
is the outage the 2026-10-21 law forbids ("no OKE outage may take out every model"). So the front
now decides on the ANSWER: it holds the request, asks the cloud, and if the answer is a
server-side failure (5xx) or there is no answer at all (a stall past ANSWER_TIMEOUT), it asks
the NEXT target the same question and the caller gets that answer instead of the cloud's
failure. A caller-side failure (4xx) is the caller's own business and is relayed untouched; the
cloud stays the first target (the founder's 2026-10-26 ruling: the cloud is the default route,
the laptop is the fallback), and a cloud that just failed is passed over for CLOUD_DOWN_S seconds
so one outage costs one request the wait and not every request.

The cloud leg parses the request (head, then body) because a replay needs the request again.
The laptop leg stays bytes only: no parsing, no buffering, exactly as before.
"""

from __future__ import annotations

import asyncio
import os
import pathlib
import ssl
import sys
import time
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
# The most the front holds of a request, so the same request can be asked of another target.
MAX_BODY = 8 * 1024 * 1024
# The most of an error answer the front reads to judge it.
MAX_ERROR = 65536
# A target that has not answered in this long is treated as failed.
ANSWER_TIMEOUT = 120.0
# How long a target that just failed is passed over. Consecutive failures double it, so a
# cloud that fails slowly (its 503 arrives after 30 s) is not paid for on every request.
CLOUD_DOWN_S = 60.0
CLOUD_DOWN_MAX_S = 600.0
# How long the front waits for the rest of a caller's body before it gives up on a replay.
DRAIN_TIMEOUT = 30.0

DOWN: set = set()  # slots that missed DOWN_AFTER probes in a row
CLOUD_DOWN_UNTIL = 0.0  # monotonic time until which the cloud is passed over
CLOUD_FAILURES = 0  # how many times the cloud has failed in a row


def backends() -> list:
    """The active slot first, then its twin."""
    try:
        active = int(ACTIVE.read_text().strip())
    except (OSError, ValueError):
        active = SLOTS[0]
    return [active] + [p for p in SLOTS if p != active]


def route() -> list:
    """Cloud first (the founder's 2026-10-26 ruling: the cloud is the default route, the
    laptop is the fallback), then the answering laptop slots, then the slots that stopped
    answering. A cloud that just failed moves behind the answering slots for CLOUD_DOWN_S
    seconds: the laptop answers while the cloud is down, and the cloud is still in the route
    so a laptop with no slot at all still reaches it."""
    slots = backends()
    healthy = [p for p in slots if p not in DOWN]
    sick = [p for p in slots if p in DOWN]
    if not CLOUD:
        return healthy + sick
    if time.monotonic() < CLOUD_DOWN_UNTIL:
        return healthy + [CLOUD] + sick
    return [CLOUD] + healthy + sick


def mark_cloud_down() -> None:
    """The cloud failed to answer. Pass over it for a while so the laptop answers instead.

    Each failure in a row doubles the pass-over, up to CLOUD_DOWN_MAX_S: a cloud that fails
    slowly (the edge's 503 arrives after half a minute) would otherwise be paid for again on
    every request, and one outage would cost every caller half a minute.
    """
    global CLOUD_DOWN_UNTIL, CLOUD_FAILURES
    CLOUD_FAILURES += 1
    cooldown = min(CLOUD_DOWN_S * 2 ** (CLOUD_FAILURES - 1), CLOUD_DOWN_MAX_S)
    CLOUD_DOWN_UNTIL = time.monotonic() + cooldown
    print(
        f"front: the cloud failed to answer ({CLOUD_FAILURES} in a row); "
        f"the laptop answers for {cooldown:.0f}s",
        file=sys.stderr,
        flush=True,
    )


def mark_cloud_up() -> None:
    """The cloud answered. It is the default route again, and the backoff is forgotten."""
    global CLOUD_DOWN_UNTIL, CLOUD_FAILURES
    CLOUD_DOWN_UNTIL = 0.0
    CLOUD_FAILURES = 0


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
        # Indexed, not zip(): the router's venv is 3.12, but the estate's test python is 3.9,
        # and zip(..., strict=) is a TypeError there -- which killed this watcher (and every
        # slot's cover) silently, on the first loop, in every test run.
        for i, port in enumerate(SLOTS):
            ok = results[i]
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


def _rewrite(head: bytes, host_line: bytes, connection) -> bytes:
    """The request head with one Host, one Connection policy and no Expect."""
    hop = (b"host", b"connection", b"keep-alive", b"proxy-connection", b"expect")
    lines = [
        line
        for line in head.split(b"\r\n")[1:]
        if line and line.split(b":", 1)[0].strip().lower() not in hop
    ]
    out = [head.split(b"\r\n", 1)[0]] + lines + [host_line]
    if connection:
        out.append(connection)
    return b"\r\n".join(out + [b"", b""])


def for_cloud(head: bytes, host: str) -> bytes:
    """The request head with the cloud's Host, asking the cloud to close after its answer."""
    return _rewrite(head, b"Host: " + host.encode(), b"Connection: close")


def for_slot(head: bytes, port: int) -> bytes:
    """The request head as the caller wrote it, with the Host the slot expects."""
    return _rewrite(head, b"Host: 127.0.0.1:" + str(port).encode(), None)


def framing_of(head: bytes) -> tuple:
    """How the caller's body is framed: ('length', n), ('chunked', 0) or ('none', 0)."""
    for line in head.split(b"\r\n"):
        low = line.lower()
        if low.startswith(b"transfer-encoding:") and b"chunked" in low:
            return ("chunked", 0)
    for line in head.split(b"\r\n"):
        low = line.lower()
        if low.startswith(b"content-length:"):
            try:
                n = int(line.split(b":", 1)[1].strip())
            except ValueError:
                return ("none", 0)
            return ("length", n) if n > 0 else ("none", 0)
    return ("none", 0)


def expects_continue(head: bytes) -> bool:
    """The caller asked for a 100-continue. The front answers it, so the target never does."""
    return any(
        line.lower().startswith(b"expect:") and b"100-continue" in line.lower()
        for line in head.split(b"\r\n")
    )


def status_code(line: bytes) -> int:
    parts = line.split()
    if len(parts) >= 2 and parts[1].isdigit():
        return int(parts[1])
    return 0


class Held:
    """The request the front is holding while it asks a target: its head, and a copy of the
    body made while the body is forwarded. The copy is what lets the front ask the next
    target the same question."""

    def __init__(self, head: bytes) -> None:
        self.head = head
        self.framing, self.length = framing_of(head)
        self.buf = bytearray()
        self.overflow = False
        self.complete = False
        self.forward = None  # the target the body is being forwarded to

    def replayable(self) -> bool:
        """The whole request is in hand, so another target can be asked the same question."""
        return self.complete and not self.overflow


class Refusal:
    """A target's answer, kept so it can still be relayed if no other target can answer."""

    def __init__(self, status: bytes, body: bytes, rest, sock) -> None:
        self.status = status
        self.body = body
        self.rest = rest  # the reader for whatever is left of the answer
        self.sock = sock  # the writer for that connection (a reader has no close())


async def emit(held: Held, data: bytes) -> None:
    """Keep a copy of the body, and forward it to the target while it arrives."""
    if len(held.buf) + len(data) <= MAX_BODY:
        held.buf.extend(data)
    else:
        held.overflow = True
    if held.forward is not None:
        try:
            held.forward.write(data)
            await held.forward.drain()
        except (ConnectionError, OSError):
            held.forward = (
                None  # the target is gone; keep holding the body for the replay
            )


async def read_body(held: Held, client_r) -> None:
    """Read the caller's body, forward it to the target and hold a copy for a replay."""
    try:
        if held.framing == "length":
            remaining = held.length
            while remaining > 0:
                data = await client_r.read(min(CHUNK, remaining))
                if not data:
                    return
                remaining -= len(data)
                await emit(held, data)
        elif held.framing == "chunked":
            while True:
                line = await client_r.readline()
                if not line:
                    return
                await emit(held, line)
                try:
                    size = int(line.split(b";", 1)[0].strip() or b"0", 16)
                except ValueError:
                    return
                if size == 0:
                    while True:
                        trailer = await client_r.readline()
                        if not trailer:
                            return
                        await emit(held, trailer)
                        if trailer in (b"\r\n", b"\n"):
                            break
                    break
                remaining = size
                while remaining > 0:
                    data = await client_r.read(min(CHUNK, remaining))
                    if not data:
                        return
                    remaining -= len(data)
                    await emit(held, data)
                await emit(held, await client_r.readexactly(2))
    except (OSError, asyncio.IncompleteReadError, asyncio.LimitOverrunError):
        return
    held.complete = True


async def read_some(reader, limit: int) -> bytes:
    """Read up to limit bytes of an answer, without waiting for the rest of it."""
    out = bytearray()
    while len(out) < limit:
        try:
            data = await asyncio.wait_for(reader.read(min(CHUNK, limit - len(out))), 5)
        except (asyncio.TimeoutError, OSError):
            break
        if not data:
            break
        out.extend(data)
    return bytes(out)


async def drain(held: Held, body) -> None:
    """Let the caller's body finish, so the request can be asked of another target."""
    try:
        await asyncio.wait_for(asyncio.shield(body), DRAIN_TIMEOUT)
    except asyncio.TimeoutError:
        body.cancel()
        held.complete = False


async def read_head(reader):
    try:
        return await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 300)
    except (
        asyncio.IncompleteReadError,
        asyncio.LimitOverrunError,
        asyncio.TimeoutError,
        OSError,
    ):
        return None


async def pipe(src, dst) -> None:
    try:
        while data := await src.read(CHUNK):
            dst.write(data)
            await dst.drain()
        if dst.can_write_eof():
            dst.write_eof()  # half-close: the other direction may still be streaming
    except (ConnectionError, OSError):
        pass


async def ask_cloud(client_r, client_w, target: str, held: Held):
    """Ask the cloud for the request.

    Returns ('ok', None) when the answer is on its way to the caller, and ('retry', refusal)
    when the cloud failed: its answer is a server-side failure, or there was no answer at all.
    """
    try:
        back_r, back_w = await connect(target)
    except (OSError, asyncio.TimeoutError):
        mark_cloud_down()
        await read_body(held, client_r)  # nothing was forwarded; hold it for the replay
        return ("retry", Refusal(b"", b"", None, None))
    held.forward = back_w
    try:
        back_w.write(for_cloud(held.head, urlsplit(target).netloc))
        await back_w.drain()
    except (ConnectionError, OSError):
        held.forward = None
        await read_body(held, client_r)
        back_w.close()
        mark_cloud_down()
        return ("retry", Refusal(b"", b"", None, back_w))
    body = asyncio.create_task(read_body(held, client_r))
    try:
        status = await asyncio.wait_for(back_r.readline(), ANSWER_TIMEOUT)
    except (asyncio.TimeoutError, OSError):
        held.forward = None
        await drain(held, body)
        back_w.close()
        mark_cloud_down()
        return ("retry", Refusal(b"", b"", None, back_w))
    # A 1xx is not the answer; read on to the one that is.
    while status_code(status) // 100 == 1:
        try:
            status = await asyncio.wait_for(back_r.readline(), ANSWER_TIMEOUT)
        except (asyncio.TimeoutError, OSError):
            held.forward = None
            await drain(held, body)
            back_w.close()
            mark_cloud_down()
            return ("retry", Refusal(b"", b"", None, back_w))
    code = status_code(status)
    if code >= 500:
        # The cloud is broken, not the request. Hold its complaint, and ask the next target.
        complaint = await read_some(back_r, MAX_ERROR)
        held.forward = None
        await drain(held, body)
        back_w.close()
        mark_cloud_down()
        return ("retry", Refusal(status, complaint, back_r, back_w))
    if code == 403:
        # The cloud's key may not carry this model. Read the refusal and look.
        complaint = await read_some(back_r, MAX_ERROR)
        mark_cloud_up()  # the cloud is answering; it is the refusal that is wrong, not the cloud
        if b"key_model_access_denied" in complaint:
            held.forward = None
            await drain(held, body)
            back_w.close()
            return ("retry", Refusal(status, complaint, back_r, back_w))
        client_w.write(status + complaint)
        await client_w.drain()
        await pipe(back_r, client_w)
        body.cancel()
        back_w.close()
        return ("ok", None)
    mark_cloud_up()  # the cloud answered: it is the default route again
    client_w.write(status)
    await client_w.drain()
    await pipe(back_r, client_w)
    body.cancel()
    back_w.close()
    return ("ok", None)


async def ask_again(client_r, client_w, target, held: Held) -> bool:
    """Ask another target the same question, from the copy of the request in hand."""
    if not held.replayable():
        return False
    try:
        back_r, back_w = await connect(target)
    except (OSError, asyncio.TimeoutError):
        return False
    head = (
        for_slot(held.head, target)
        if isinstance(target, int)
        else for_cloud(held.head, urlsplit(target).netloc)
    )
    try:
        back_w.write(head + bytes(held.buf))
        await back_w.drain()
    except (ConnectionError, OSError):
        back_w.close()
        return False
    up = asyncio.create_task(pipe(client_r, back_w))
    try:
        await pipe(back_r, client_w)
    finally:
        up.cancel()
        for w in (back_w, client_w):
            w.close()
    return True


async def handle(client_r, client_w) -> None:
    targets = route()
    for index, target in enumerate(targets):
        if isinstance(target, str):
            head = await read_head(client_r)
            if head is None:
                client_w.close()
                return
            held = Held(head)
            if expects_continue(head):
                client_w.write(b"HTTP/1.1 100 Continue\r\n\r\n")
                await client_w.drain()
            verdict, refusal = await ask_cloud(client_r, client_w, target, held)
            if verdict == "ok":
                return
            for nxt in targets[index + 1 :]:
                if await ask_again(client_r, client_w, nxt, held):
                    if refusal is not None and refusal.sock is not None:
                        refusal.sock.close()  # the cloud's half-answer is not needed now
                    return
            # Nothing else could answer: the caller gets the cloud's own complaint.
            if refusal is not None and refusal.status:
                client_w.write(refusal.status + refusal.body)
                await client_w.drain()
                if refusal.rest is not None:
                    await pipe(refusal.rest, client_w)
            else:
                client_w.write(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\n\r\n")
                await client_w.drain()
            client_w.close()
            return
        # A laptop slot: bytes only, exactly as before.
        try:
            back_r, back_w = await connect(target)
        except (OSError, asyncio.TimeoutError):
            continue
        up = asyncio.create_task(pipe(client_r, back_w))
        try:
            # The router closing its side ends the exchange (a finished response, or a draining
            # router closing an idle keep-alive); the client then reconnects through the front.
            await pipe(back_r, client_w)
        finally:
            up.cancel()
            for w in (back_w, client_w):
                w.close()
        return
    print(f"front: no router answers ({route()})", file=sys.stderr, flush=True)
    client_w.close()


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

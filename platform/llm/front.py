#!/usr/bin/env python3
"""The laptop router's front door: 127.0.0.1:4000. It asks the cloud router first (migration
P2.T4, 2026-10-25: spend lives on the cluster) and falls back to the laptop router slots. It
never changes, so it never restarts on a router deploy.

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

WHY (2026-10-25, the zai lane). The cloud moved to the cluster and the front tried it first, but
it only ever failed over on a refused CONNECT. A cloud that answers -- with a refusal -- was
taken as the answer: llm.mumchimp.com carries no zai lane, so it answered 403 "key not allowed
to access model" and the front relayed that refusal to the caller instead of asking the laptop
router, which does carry the lane. The same shape took Claude Code down on 2026-10-22 (403, "Please
run /login"). So the front reads the cloud's status line before it streams the answer: under 400
means the cloud took the request and its answer is the caller's answer; 403 and friends mean the
cloud does not carry that lane, so the request goes on to the laptop router, which does (see
docs/diagnoses/2026-10-22-claude-code-403-cloud-has-no-claude-lane.yaml).

A refusal is the only answer the front may fall back on: the cloud has then said it will not
serve the request, so the laptop router serving it costs nothing twice. A cloud that takes a
request and answers slowly is NOT timed out here -- the caller waits for it, as it did before,
because falling back on a slow answer would have the cloud and the laptop both bill the request.

The laptop path is bytes-only: no HTTP parsing, no TLS, no buffering. The cloud path wraps TLS
and rewrites one request head (the gateway routes by Host, and a local Host is a 404 there), asking
for `Connection: close` so each request is one head and the next one comes through here again.
"""

from __future__ import annotations

import asyncio
import os
import pathlib
import re
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
# How long the caller may take to send its request head, and how long the front waits for the
# body that head announces. Both are the caller's clock, not the router's.
HEAD_TIMEOUT = 300.0
BODY_TIMEOUT = 300.0
# The largest request body the front buffers so it can hand the same request to the laptop
# router when the cloud refuses it. A chat request is kilobytes; a body over this is streamed
# to the cloud and cannot be replayed.
MAX_BODY = 8 * 1024 * 1024
# The largest refusal the front keeps for a caller that has nowhere else to go.
REFUSAL_LIMIT = 65536
# An HTTP request line, e.g. "GET /v1/chat/completions HTTP/1.1". Anything else is not an HTTP
# request, and the cloud (which routes by Host) cannot serve it: the laptop path relays it
# unchanged.
REQUEST_LINE = re.compile(rb"^[A-Za-z]{3,10} \S+ HTTP/1\.[01]$")
# The methods that carry no body when the head does not announce one.
NO_BODY_METHODS = (b"GET", b"HEAD", b"DELETE", b"OPTIONS")

DOWN: set = set()  # slots that missed DOWN_AFTER probes in a row


def backends() -> list[int]:
    """The active slot first, then its twin."""
    try:
        active = int(ACTIVE.read_text().strip())
    except (OSError, ValueError):
        active = SLOTS[0]
    return [active] + [p for p in SLOTS if p != active]


def route() -> list:
    """Cloud first (migration P2.T4, 2026-10-25: spend lives on the cluster), then the
    answering laptop slots as fallback -- the founder's 2026-09-26 ruling keeps the local
    slot alive, so a cloud outage degrades to the laptop instead of to nothing -- then the
    slots that stopped answering."""
    slots = backends()
    return (
        ([CLOUD] if CLOUD else [])
        + [p for p in slots if p not in DOWN]
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
        # The estate's own python is 3.9 on this laptop: zip(strict=True) is 3.10+, and the
        # watcher died on its first pass, so no slot was ever marked down.
        if len(results) != len(SLOTS):
            raise RuntimeError("the probe count and the slot count disagree")
        for port, ok in zip(SLOTS, results):  # noqa: B905 -- strict= is 3.10+, this python is 3.9
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


def status_code(status: bytes) -> int | None:
    """The number in a status line, e.g. 403 in "HTTP/1.1 403 Forbidden"."""
    parts = status.split(b" ", 2)
    if len(parts) < 2:
        return None
    try:
        return int(parts[1])
    except ValueError:
        return None


def content_length(head: bytes) -> int | None:
    """The body length the request head announces, or None when it announces none."""
    for line in head.split(b"\r\n")[1:]:
        name, sep, value = line.partition(b":")
        if sep and name.strip().lower() == b"content-length":
            try:
                return int(value.strip())
            except ValueError:
                return None
    return None


def body_plan(head: bytes) -> tuple[int | None, bool]:
    """(length, known) -- the body the request carries, and whether the head says so."""
    length = content_length(head)
    if length is not None:
        return (length if length >= 0 else None), True
    if head.split(b" ", 1)[0].upper() in NO_BODY_METHODS:
        return 0, True
    return None, False


async def pipe(src: asyncio.StreamReader, dst: asyncio.StreamWriter) -> None:
    try:
        while data := await src.read(CHUNK):
            dst.write(data)
            await dst.drain()
        if dst.can_write_eof():
            dst.write_eof()  # half-close: the other direction may still be streaming
    except (ConnectionError, OSError):
        pass


async def read_head(reader: asyncio.StreamReader) -> tuple[bytes | None, bytes]:
    """The caller's request head, when the caller sent an HTTP request.

    Returns (head, raw). head is the complete request head when the traffic is HTTP. raw is
    the bytes read so far when it is not: the laptop path relays bytes it does not parse, so
    those bytes travel on unchanged.
    """
    buf = b""
    while True:
        try:
            chunk = await asyncio.wait_for(reader.readuntil(b"\n"), HEAD_TIMEOUT)
        except asyncio.IncompleteReadError as exc:
            return None, buf + exc.partial
        except (asyncio.LimitOverrunError, asyncio.TimeoutError, OSError):
            return None, buf
        buf += chunk
        if not REQUEST_LINE.match(buf.split(b"\n", 1)[0].rstrip(b"\r")):
            return None, buf
        if buf.endswith(b"\r\n\r\n") or buf.endswith(b"\n\n"):
            # A head the cloud can be asked with: normalise the line endings to CRLF.
            return buf.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"), b""


async def prepare(
    reader: asyncio.StreamReader,
) -> tuple[bytes | None, bytes | None, bytes]:
    """The request the cloud will be asked, when the caller sent an HTTP request.

    Returns (head, body, raw). head is the request head, or None when the traffic is not an
    HTTP request (raw then holds the bytes read so far). body is the request body when it was
    buffered, or None when it has to be streamed to the cloud and cannot be replayed.
    """
    head, raw = await read_head(reader)
    if head is None:
        return None, None, raw
    length, known = body_plan(head)
    if not known or length is None or length > MAX_BODY:
        return head, None, b""
    body = b""
    if length:
        try:
            body = await asyncio.wait_for(reader.readexactly(length), BODY_TIMEOUT)
        except (asyncio.IncompleteReadError, asyncio.TimeoutError, OSError):
            return None, None, head + raw
    return head, body, b""


async def refusal_bytes(reader: asyncio.StreamReader, status: bytes) -> bytes:
    """The cloud's refusal, as a response the caller can read."""
    chunks: list[bytes] = []
    total = 0
    try:
        while total < REFUSAL_LIMIT:
            chunk = await asyncio.wait_for(reader.read(CHUNK), PROBE_TIMEOUT)
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
    except (OSError, asyncio.TimeoutError):
        pass
    rest = b"".join(chunks)
    body = rest.split(b"\r\n\r\n", 1)[1] if b"\r\n\r\n" in rest else b""
    return (
        status.strip()
        + b"\r\nContent-Length: "
        + str(len(body)).encode()
        + b"\r\nConnection: close\r\n\r\n"
        + body
    )


async def cloud_turn(
    client_r: asyncio.StreamReader,
    client_w: asyncio.StreamWriter,
    target: str,
    back_r: asyncio.StreamReader,
    back_w: asyncio.StreamWriter,
    head: bytes,
    body: bytes | None,
) -> tuple[bool, bytes | None, bool]:
    """Give the request to the cloud and look at its answer.

    Returns (answered, refusal, replayable). answered is True when the cloud took the request:
    its status line is under 400 and its answer is on its way to the caller. refusal is the
    cloud's answer when it refused (403 and friends: the cloud carries no such lane). replayable
    is False when the request body was streamed to the cloud, so the laptop router cannot be
    given the same request afterwards.
    """
    streamed = body is None
    up = None
    try:
        back_w.write(for_cloud(head, urlsplit(target).netloc))
        if body is not None:
            back_w.write(body)
        await back_w.drain()
        if streamed:
            up = asyncio.create_task(pipe(client_r, back_w))
        status = await back_r.readline()
        code = status_code(status)
        if code is not None and code < 400:
            # The cloud took the request: its answer is the caller's answer.
            client_w.write(status)
            await client_w.drain()
            try:
                await pipe(back_r, client_w)
            finally:
                for w in (back_w, client_w):
                    w.close()
            return True, None, not streamed
        # The cloud refused (or closed without answering): the laptop router carries this lane.
        refusal = await refusal_bytes(back_r, status) if status else None
        back_w.close()
        return False, refusal, not streamed
    except (OSError, asyncio.TimeoutError):
        back_w.close()
        return False, None, not streamed
    finally:
        if up is not None:
            up.cancel()


async def slot_turn(
    client_r: asyncio.StreamReader,
    client_w: asyncio.StreamWriter,
    port: int,
    head: bytes | None,
    body: bytes | None,
    raw: bytes,
    replayable: bool,
) -> bool:
    """Give the request to a laptop router slot. True when the slot took it.

    A slot that cannot be reached is passed over (the next one is tried). A slot that took the
    request and then broke is not: the caller has already been given part of an answer, and a
    second attempt would be a second answer on the same connection.
    """
    try:
        back_r, back_w = await asyncio.wait_for(
            asyncio.open_connection("127.0.0.1", port), 5
        )
    except (OSError, asyncio.TimeoutError):
        return False
    took = False
    try:
        if head is not None:
            if not replayable:
                # The cloud already took the request body; the slot cannot be given it.
                back_w.close()
                return False
            back_w.write(head)
            if body:
                back_w.write(body)
        else:
            back_w.write(raw)
        await back_w.drain()
        took = True
        up = asyncio.create_task(pipe(client_r, back_w))
        try:
            # The router closing its side ends the exchange (a finished response, or a draining
            # router closing an idle keep-alive); the client then reconnects through the front.
            await pipe(back_r, client_w)
        finally:
            up.cancel()
            for w in (back_w, client_w):
                w.close()
    except (OSError, asyncio.TimeoutError):
        pass
    return took


async def handle(
    client_r: asyncio.StreamReader, client_w: asyncio.StreamWriter
) -> None:
    targets = route()
    head: bytes | None = None
    body: bytes | None = None
    raw = b""
    prepared = False
    replayable = True
    refusal: bytes | None = None
    for target in targets:
        if isinstance(target, str):
            try:
                back_r, back_w = await connect(target)
            except (OSError, asyncio.TimeoutError):
                continue  # the cloud is unreachable: the laptop slots answer
            if not prepared:
                prepared = True
                head, body, raw = await prepare(client_r)
                if head is None and not raw:
                    back_w.close()
                    client_w.close()
                    return
            if head is None:
                # Not an HTTP request: the cloud routes by Host, so it cannot serve this.
                back_w.close()
                continue
            answered, refusal, replayable = await cloud_turn(
                client_r, client_w, target, back_r, back_w, head, body
            )
            if answered:
                return
            continue
        if await slot_turn(client_r, client_w, target, head, body, raw, replayable):
            return
    print(f"front: no router answers ({targets})", file=sys.stderr, flush=True)
    if refusal:
        # Nothing else can answer: the caller still gets the cloud's reason.
        client_w.write(refusal)
        await client_w.drain()
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

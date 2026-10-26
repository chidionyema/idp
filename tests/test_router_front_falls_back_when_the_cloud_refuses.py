"""A cloud router that refuses a lane hands the request to the laptop router.

WHAT THIS GRADES. `platform/llm/front.py` claims: the cloud router is asked first, and when it
answers with a refusal (403 and friends -- the cloud carries no such lane) the request goes on to
the laptop router, which does carry it; a request the cloud took (status under 400) is never
replayed to the laptop; a refusal with nowhere else to go still reaches the caller; a cloud that
cannot be reached at all falls back to the laptop.

WHY. The cloud moved to the cluster on 2026-10-25 (migration P2.T4) and the front tried it
first, but it only ever failed over on a refused CONNECT. A cloud that ANSWERS -- with a
refusal -- was taken as the answer: llm.mumchimp.com carries no zai lane, so it answered 403
"key not allowed to access model" and the front relayed that to the caller instead of asking the
laptop router, which does carry the lane. The same shape took Claude Code down on 2026-10-22
(403, "Please run /login"). A refusal is the only answer the front may fall back on: the cloud
has then said it will not serve the request, so the laptop serving it costs nothing twice.
"""

import asyncio
import importlib.util
import pathlib
import socket

import pytest

MODULE = pathlib.Path(__file__).resolve().parents[1] / "platform" / "llm" / "front.py"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def front(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("router_front_refusal", MODULE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    a, b, f, c = free_port(), free_port(), free_port(), free_port()
    monkeypatch.setattr(mod, "SLOTS", (a, b))
    monkeypatch.setattr(mod, "ACTIVE", tmp_path / "active")
    monkeypatch.setattr(mod, "LISTEN", ("127.0.0.1", f))
    monkeypatch.setattr(mod, "CLOUD", f"http://127.0.0.1:{c}")
    monkeypatch.setattr(mod, "PROBE_EVERY", 0.05)
    monkeypatch.setattr(mod, "PROBE_TIMEOUT", 0.2)
    (tmp_path / "active").write_text(f"{a}\n")
    return mod


def reply(body: bytes, code: int = 200) -> bytes:
    head = f"HTTP/1.1 {code} Error\r\nContent-Length: {len(body)}\r\n"
    return (head + "Connection: close\r\n\r\n").encode() + body


async def read_request(r):
    """The head and body of one request on a socket."""
    head = await r.readuntil(b"\r\n\r\n")
    length = 0
    for line in head.split(b"\r\n"):
        if line.lower().startswith(b"content-length:"):
            length = int(line.split(b":", 1)[1])
    body = await r.readexactly(length) if length else b""
    return head, body


async def laptop(port: int, seen: list):
    """A laptop router stand-in: records what it was asked, and answers 200."""

    async def handle(r, w):
        try:
            head, body = await read_request(r)
            if head.split(b" ", 2)[1] == b"/health/liveliness":
                w.write(b"HTTP/1.0 200 OK\r\n\r\n")  # the front's health probe
                await w.drain()
                w.close()
                return
            seen.append((head, body))
            w.write(reply(b"laptop:" + head.split(b"\r\n")[0] + b" body=" + body))
            await w.drain()
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        w.close()

    return await asyncio.start_server(handle, "127.0.0.1", port)


async def echoing_laptop(port: int, seen: list):
    """A laptop stand-in that echoes the bytes it is given, for traffic that is not HTTP."""

    async def handle(r, w):
        try:
            data = await r.read(1024)
            if data.startswith(b"GET /health/liveliness"):
                w.write(b"HTTP/1.0 200 OK\r\n\r\n")  # the front's health probe
                await w.drain()
                w.close()
                return
            seen.append(data)
            w.write(data)
            await w.drain()
        except ConnectionError:
            pass
        w.close()

    return await asyncio.start_server(handle, "127.0.0.1", port)


async def refusing_cloud(port: int, code: int = 403):
    """A cloud that carries no such lane: it answers 403 and closes."""

    async def handle(r, w):
        try:
            await read_request(r)
            w.write(
                reply(
                    b'{"error":{"message":"key not allowed to access model"}}',
                    code=code,
                )
            )
            await w.drain()
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        w.close()

    return await asyncio.start_server(handle, "127.0.0.1", port)


async def answering_cloud(port: int, seen: list):
    """A cloud that carries the lane: it answers 200."""

    async def handle(r, w):
        try:
            head, body = await read_request(r)
            seen.append((head, body))
            w.write(reply(b"cloud:" + head.split(b"\r\n")[0] + b" body=" + body))
            await w.drain()
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        w.close()

    return await asyncio.start_server(handle, "127.0.0.1", port)


async def get(front, path: str) -> tuple[int, bytes]:
    r, w = await asyncio.open_connection(*front.LISTEN)
    try:
        w.write(f"GET {path} HTTP/1.1\r\nHost: 127.0.0.1:4000\r\n\r\n".encode())
        await w.drain()
        head = await asyncio.wait_for(r.readuntil(b"\r\n\r\n"), 5)
        code = int(head.split(b" ", 2)[1])
        length = next(
            int(line.split(b":", 1)[1])
            for line in head.split(b"\r\n")
            if line.lower().startswith(b"content-length:")
        )
        body = await asyncio.wait_for(r.readexactly(length), 5)
        return code, body
    finally:
        w.close()


async def post(front, path: str, payload: bytes) -> tuple[int, bytes]:
    r, w = await asyncio.open_connection(*front.LISTEN)
    try:
        w.write(
            f"POST {path} HTTP/1.1\r\nHost: 127.0.0.1:4000\r\n"
            f"Content-Length: {len(payload)}\r\n\r\n".encode()
            + payload
        )
        await w.drain()
        head = await asyncio.wait_for(r.readuntil(b"\r\n\r\n"), 5)
        code = int(head.split(b" ", 2)[1])
        length = next(
            int(line.split(b":", 1)[1])
            for line in head.split(b"\r\n")
            if line.lower().startswith(b"content-length:")
        )
        body = await asyncio.wait_for(r.readexactly(length), 5)
        return code, body
    finally:
        w.close()


def test_a_cloud_that_refuses_a_lane_hands_the_request_to_the_laptop(front):
    async def run():
        seen: list = []
        a, b = front.SLOTS
        servers = [
            await laptop(a, seen),
            await laptop(b, seen),
            await refusing_cloud(int(front.CLOUD.rsplit(":", 1)[1])),
        ]
        task = asyncio.create_task(front.main())
        await asyncio.sleep(0.2)
        code, body = await get(front, "/v1/chat/completions")
        assert code == 200
        assert body.startswith(b"laptop:GET /v1/chat/completions")
        assert len(seen) == 1  # the laptop answered it, once
        task.cancel()
        for s in servers:
            s.close()

    asyncio.run(run())


def test_a_request_body_is_carried_to_the_laptop_when_the_cloud_refuses(front):
    async def run():
        seen: list = []
        a, b = front.SLOTS
        servers = [
            await laptop(a, seen),
            await laptop(b, seen),
            await refusing_cloud(int(front.CLOUD.rsplit(":", 1)[1])),
        ]
        task = asyncio.create_task(front.main())
        await asyncio.sleep(0.2)
        payload = b'{"model":"zai/glm-4.6","messages":[{"role":"user","content":"hi"}]}'
        code, body = await post(front, "/v1/chat/completions", payload)
        assert code == 200
        assert body.endswith(b"body=" + payload)
        assert seen[0][1] == payload  # the laptop was given the same request
        task.cancel()
        for s in servers:
            s.close()

    asyncio.run(run())


def test_a_cloud_that_answers_is_not_replayed(front):
    async def run():
        cloud_seen: list = []
        laptop_seen: list = []
        a, b = front.SLOTS
        servers = [
            await laptop(a, laptop_seen),
            await laptop(b, laptop_seen),
            await answering_cloud(int(front.CLOUD.rsplit(":", 1)[1]), cloud_seen),
        ]
        task = asyncio.create_task(front.main())
        await asyncio.sleep(0.2)
        code, body = await get(front, "/v1/chat/completions")
        assert code == 200
        assert body.startswith(b"cloud:GET /v1/chat/completions")
        assert laptop_seen == []  # the cloud took it: the laptop is not asked
        task.cancel()
        for s in servers:
            s.close()

    asyncio.run(run())


def test_a_refusal_reaches_the_caller_when_there_is_no_laptop(front):
    async def run():
        a, b = front.SLOTS
        servers = [await refusing_cloud(int(front.CLOUD.rsplit(":", 1)[1]))]
        task = asyncio.create_task(front.main())
        await asyncio.sleep(0.2)
        code, body = await get(front, "/v1/chat/completions")
        assert code == 403
        assert b"key not allowed to access model" in body
        task.cancel()
        for s in servers:
            s.close()

    asyncio.run(run())


def test_a_cloud_that_cannot_be_reached_falls_back_to_the_laptop(front):
    async def run():
        seen: list = []
        a, b = front.SLOTS
        # nothing listens on the cloud's port: the connect fails
        servers = [await laptop(a, seen), await laptop(b, seen)]
        task = asyncio.create_task(front.main())
        await asyncio.sleep(0.2)
        code, body = await get(front, "/v1/chat/completions")
        assert code == 200
        assert body.startswith(b"laptop:GET /v1/chat/completions")
        task.cancel()
        for s in servers:
            s.close()

    asyncio.run(run())


def test_traffic_that_is_not_an_http_request_reaches_the_laptop_unchanged(front):
    """The cloud routes by Host, so it cannot serve bytes it cannot read a head from: the
    laptop path relays them, and the front does not parse them."""

    async def run():
        seen: list = []
        a, b = front.SLOTS
        servers = [
            await echoing_laptop(a, seen),
            await echoing_laptop(b, seen),
            await answering_cloud(int(front.CLOUD.rsplit(":", 1)[1]), []),
        ]
        task = asyncio.create_task(front.main())
        await asyncio.sleep(0.2)
        r, w = await asyncio.open_connection(*front.LISTEN)
        w.write(b"\x00\x01not an http request\n")
        await w.drain()
        got = await asyncio.wait_for(r.read(1024), 5)
        assert got == b"\x00\x01not an http request\n"
        assert seen and seen[0] == b"\x00\x01not an http request\n"
        w.close()
        task.cancel()
        for s in servers:
            s.close()

    asyncio.run(run())

"""The front presents its own User-Agent to the cloud, and an edge block does not mask a
healthy laptop slot.

WHAT THIS GRADES. Two facts measured on 2026-10-30 through the live front on 127.0.0.1:4000,
one credential and one body:

    curl/8.7.1               -> HTTP 200
    Python-urllib/3.12       -> HTTP 403, body {"error code": 1010}
    estate-router-front/1.0  -> HTTP 200

The cloud route sits behind Cloudflare, whose browser-signature rules answer some client
signatures with "403 error code: 1010" BEFORE the request reaches the router behind it. The
front forwarded the caller's User-Agent, so a caller whose signature the edge dislikes was
handed the edge's refusal while a healthy laptop slot sat unused. The front now presents its
own User-Agent on the cloud leg, and an edge refusal is treated as the cloud failing to
answer: the same request is asked of the next target.

The second fact these tests pin: an ORDINARY authenticated 403 is still the caller's own
business and is relayed untouched. The edge is recognised by its BODY, not by its status, so
the front never swallows a caller's real answer to hide a router's refusal.
"""

import asyncio
import importlib.util
import pathlib
import socket

import pytest

MODULE = pathlib.Path(__file__).resolve().parents[1] / "platform" / "llm" / "front.py"

# The body the edge measured on 2026-10-30, and the same refusal in the browser's spelling.
EDGE_1010 = b'{"error code": 1010}'
EDGE_1020 = b'{"error code": 1020}'
EDGE_HTML = b"<html><body><p>error code: 1010</p></body></html>"
# An ordinary authenticated refusal from the router: the caller's own business.
ORDINARY_403 = b'{"error":{"code":"invalid_api_key","message":"bad key"}}'


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def front(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "router_front_cloudflare_edge_block", MODULE
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    slot_port, other_port, listen_port, cloud_port = (free_port() for _ in range(4))
    monkeypatch.setattr(mod, "SLOTS", (slot_port, other_port))
    monkeypatch.setattr(mod, "ACTIVE", tmp_path / "active")
    monkeypatch.setattr(mod, "LISTEN", ("127.0.0.1", listen_port))
    monkeypatch.setattr(mod, "CLOUD", f"http://127.0.0.1:{cloud_port}")
    monkeypatch.setattr(mod, "PROBE_EVERY", 0.05)
    monkeypatch.setattr(mod, "PROBE_TIMEOUT", 0.2)
    monkeypatch.setattr(mod, "ANSWER_TIMEOUT", 1.0)
    monkeypatch.setattr(mod, "MAX_BODY", 4096)
    monkeypatch.setattr(mod, "CLOUD_DOWN_UNTIL", 0.0)
    (tmp_path / "active").write_text(f"{slot_port}\n")
    mod.slot_port = slot_port
    mod.cloud_port = cloud_port
    return mod


async def read_raw_body(r, head: bytes) -> bytes:
    """The body bytes as they arrived on the wire, framing included."""
    low = head.lower()
    if b"transfer-encoding:" in low and b"chunked" in low:
        out = bytearray()
        while True:
            line = await r.readline()
            out += line
            size = int(line.split(b";")[0].strip() or b"0", 16)
            if size == 0:
                while True:
                    trailer = await r.readline()
                    out += trailer
                    if trailer in (b"\r\n", b"\n"):
                        break
                break
            remaining = size
            while remaining:
                data = await r.read(remaining)
                out += data
                remaining -= len(data)
            out += await r.readexactly(2)
        return bytes(out)
    length = 0
    for line in head.split(b"\r\n"):
        if line.lower().startswith(b"content-length:"):
            length = int(line.split(b":", 1)[1].strip())
    return await r.readexactly(length) if length else b""


async def cloud_on(port: int, answer: tuple, seen: list):
    """The cloud stand-in. answer is (status bytes, body bytes), or None for a healthy 200."""

    async def handle(r, w):
        try:
            head = await r.readuntil(b"\r\n\r\n")
            body = await read_raw_body(r, head)
            seen.append((head, body))
            if answer is None:
                status = b"HTTP/1.1 200 OK\r\n"
                payload = b"cloud:" + head.split(b" ", 2)[1]
            else:
                status, payload = answer
            w.write(
                status
                + b"Content-Length: "
                + str(len(payload)).encode()
                + b"\r\nConnection: close\r\n\r\n"
                + payload
            )
            await w.drain()
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        w.close()

    return await asyncio.start_server(handle, "127.0.0.1", port)


async def slot_on(port: int, seen: list):
    """The laptop's router stand-in: it answers, and it records what it was asked."""

    async def handle(r, w):
        try:
            head = await r.readuntil(b"\r\n\r\n")
            body = await read_raw_body(r, head)
            if head.split(b" ")[1] != b"/health/liveliness":
                seen.append((head, body))
            answer = b"slot:" + head.split(b" ", 2)[1]
            w.write(
                b"HTTP/1.1 200 OK\r\nContent-Length: "
                + str(len(answer)).encode()
                + b"\r\n\r\n"
                + answer
            )
            await w.drain()
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        w.close()

    return await asyncio.start_server(handle, "127.0.0.1", port)


async def ask(front, raw: bytes, timeout: float = 15.0):
    """Send the caller's own bytes, and read the answer the front gives back."""
    r, w = await asyncio.open_connection(*front.LISTEN)
    try:
        w.write(raw)
        await w.drain()
        head = await asyncio.wait_for(r.readuntil(b"\r\n\r\n"), timeout)
        body = await read_raw_body(r, head)
        return head, body
    finally:
        w.close()


def post(
    path: str = "/v1/chat/completions",
    body: bytes = b'{"model":"fast"}',
    user_agent: bytes = b"curl/8.7.1",
) -> bytes:
    return (
        b"POST "
        + path.encode()
        + b" HTTP/1.1\r\nHost: 127.0.0.1:4000\r\nUser-Agent: "
        + user_agent
        + b"\r\nContent-Length: "
        + str(len(body)).encode()
        + b"\r\n\r\n"
        + body
    )


async def serve(front, cloud_answer):
    """Start the cloud and the laptop slot, and the front in front of them."""
    cloud_seen: list = []
    slot_seen: list = []
    crashes: list = []
    asyncio.get_running_loop().set_exception_handler(
        lambda loop, ctx: crashes.append(ctx.get("message", ""))
    )
    servers = [
        await cloud_on(front.cloud_port, cloud_answer, cloud_seen),
        await slot_on(front.slot_port, slot_seen),
    ]
    task = asyncio.create_task(front.main())
    await asyncio.sleep(0.2)
    return task, servers, cloud_seen, slot_seen, crashes


def user_agents(head: bytes) -> list:
    """Every User-Agent header in the head, as written."""
    out = []
    for line in head.split(b"\r\n"):
        if line.lower().startswith(b"user-agent:"):
            out.append(line.split(b":", 1)[1].strip())
    return out


def test_the_cloud_leg_presents_the_fronts_own_user_agent(front):
    """The caller's signature never reaches the cloud: one header, the front's own."""

    async def run():
        task, servers, cloud_seen, slot_seen, crashes = await serve(front, None)
        head, body = await ask(front, post(user_agent=b"Python-urllib/3.12"))
        assert b"200 OK" in head, head
        assert len(cloud_seen) == 1
        cloud_head = cloud_seen[0][0]
        agents = user_agents(cloud_head)
        assert agents == [front.CLOUD_USER_AGENT.encode()], agents
        assert b"Python-urllib" not in cloud_head, cloud_head
        await asyncio.sleep(0.2)
        assert crashes == [], crashes
        task.cancel()
        for s in servers:
            s.close()

    asyncio.run(run())


def test_an_edge_block_is_answered_by_the_laptop_slot(front):
    """The edge refused the request itself: the next target carries the caller's answer."""

    async def run():
        task, servers, cloud_seen, slot_seen, crashes = await serve(
            front, (b"HTTP/1.1 403 Forbidden\r\n", EDGE_1010)
        )
        head, body = await ask(front, post())
        assert b"200 OK" in head, head
        assert body.startswith(b"slot:"), body
        assert len(cloud_seen) == 1
        assert len(slot_seen) == 1
        await asyncio.sleep(0.2)
        assert crashes == [], crashes
        assert not task.done(), "the front died"
        task.cancel()
        for s in servers:
            s.close()

    asyncio.run(run())


def test_an_ordinary_403_is_the_callers_own_business_and_is_relayed(front):
    """The edge is recognised by its body, not by its status: a router's 403 is relayed."""

    async def run():
        task, servers, cloud_seen, slot_seen, crashes = await serve(
            front, (b"HTTP/1.1 403 Forbidden\r\n", ORDINARY_403)
        )
        head, body = await ask(front, post())
        assert b"403" in head, head
        assert ORDINARY_403 in body, body
        assert slot_seen == [], (
            "the caller's own refusal must not be answered by the laptop"
        )
        task.cancel()
        for s in servers:
            s.close()

    asyncio.run(run())


def test_an_edge_block_marks_the_cloud_down_for_the_next_callers(front):
    """One edge refusal must not cost every caller the edge's refusal."""

    async def run():
        task, servers, cloud_seen, slot_seen, crashes = await serve(
            front, (b"HTTP/1.1 403 Forbidden\r\n", EDGE_1010)
        )
        head, body = await ask(front, post())
        assert body.startswith(b"slot:"), body
        assert front.CLOUD_DOWN_UNTIL > 0, front.CLOUD_DOWN_UNTIL
        assert front.CLOUD_FAILURES == 1

        # the next caller is answered by the laptop, and the cloud is not asked again
        head, body = await ask(front, post())
        assert body.startswith(b"slot:"), body
        assert len(cloud_seen) == 1, cloud_seen
        assert len(slot_seen) == 2
        task.cancel()
        for s in servers:
            s.close()

    asyncio.run(run())


def test_the_edge_is_recognised_by_its_body_and_not_by_its_status(front):
    """Both spellings of the edge's refusal are the edge; a router's refusal is not."""

    assert front.edge_blocked(EDGE_1010)
    assert front.edge_blocked(EDGE_1020)
    assert front.edge_blocked(EDGE_HTML)
    assert not front.edge_blocked(ORDINARY_403)
    assert not front.edge_blocked(b'{"error":{"code":"key_model_access_denied"}}')
    assert not front.edge_blocked(b'{"error":{"code":"invalid_api_key"}}')
    assert not front.edge_blocked(b"the cloud refused this request")


def test_the_second_edge_code_passes_over_to_the_laptop_slot(front):
    """1020 is the edge's own access rule and is passed over the same way."""

    async def run():
        task, servers, cloud_seen, slot_seen, crashes = await serve(
            front, (b"HTTP/1.1 403 Forbidden\r\n", EDGE_1020)
        )
        head, body = await ask(front, post())
        assert b"200 OK" in head, head
        assert body.startswith(b"slot:"), body
        assert len(slot_seen) == 1
        task.cancel()
        for s in servers:
            s.close()

    asyncio.run(run())

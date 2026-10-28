"""The laptop router's front falls back to the laptop when the CLOUD fails to answer.

WHAT THIS GRADES. `platform/llm/front.py` claims: the front decides on the ANSWER, not on the
connect. A cloud that answers 5xx, or that takes the connection and then stalls, does not get to
cost the caller its model: the same request is asked of the next target (the laptop's slot) and
the caller gets that answer. A 4xx is the caller's own business and is relayed untouched. A
cloud that has just failed is passed over for the next callers, so one outage costs one request
the wait and not every request. The laptop leg stays bytes only: the caller's own bytes reach
the slot as they were written.

WHY. On 2026-10-27 the OKE router stopped answering authenticated requests: it took the
connection, then stalled until the edge's 60 s proxy timeout answered 504, and on some requests
answered 503 with the edge's own "Starting up" page. The front decided on the CONNECT, so the
cloud that accepted and then failed was never passed over, and every caller on the laptop was
handed the cloud's failure while a healthy local slot sat unused. The 2026-10-21 law says no OKE
outage may take out every model. These tests are that outage, with real sockets.
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
    spec = importlib.util.spec_from_file_location(
        "router_front_laptop_fallback", MODULE
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


async def cloud_on(port: int, mode: str, seen: list):
    """The OKE router stand-in. mode: 'ok' | 'status:503' | '403' | 'stall'."""

    async def handle(r, w):
        try:
            head = await r.readuntil(b"\r\n\r\n")
            body = await read_raw_body(r, head)
            seen.append((head, body))
            if mode == "stall":
                # takes the connection and never answers: the edge would answer 504
                await asyncio.sleep(30)
                return
            if mode.startswith("status:"):
                code = mode.split(":", 1)[1]
                complaint = b"the cloud refused this request\n"
                if code == "503":
                    complaint = b"502 Bad Gateway\nnginx/1.27.5 Starting up\n"
                w.write(
                    b"HTTP/1.1 "
                    + code.encode()
                    + b" Refused\r\nContent-Length: "
                    + str(len(complaint)).encode()
                    + b"\r\nConnection: close\r\n\r\n"
                    + complaint
                )
            elif mode == "403":
                complaint = (
                    b'{"error":{"code":"key_model_access_denied","message":"no"}}'
                )
                w.write(
                    b"HTTP/1.1 403 Forbidden\r\nContent-Length: "
                    + str(len(complaint)).encode()
                    + b"\r\nConnection: close\r\n\r\n"
                    + complaint
                )
            else:
                answer = b"cloud:" + head.split(b" ", 2)[1]
                w.write(
                    b"HTTP/1.1 200 OK\r\nContent-Length: "
                    + str(len(answer)).encode()
                    + b"\r\nConnection: close\r\n\r\n"
                    + answer
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
    path: str = "/v1/chat/completions", body: bytes = b'{"model":"fast"}'
) -> bytes:
    return (
        b"POST "
        + path.encode()
        + b" HTTP/1.1\r\nHost: 127.0.0.1:4000\r\nContent-Length: "
        + str(len(body)).encode()
        + b"\r\n\r\n"
        + body
    )


async def serve(front, cloud_mode: str):
    """Start the cloud and the laptop slot, and the front in front of them.

    It also installs an exception handler on the running loop: an exception inside the front's
    own request handling does not reach the caller (the caller may already have its answer),
    it kills the process, and launchd restarts it. That is a crash the tests must see.
    """
    cloud_seen: list = []
    slot_seen: list = []
    crashes: list = []
    asyncio.get_running_loop().set_exception_handler(
        lambda loop, ctx: crashes.append(ctx.get("message", ""))
    )
    servers = [
        await cloud_on(front.cloud_port, cloud_mode, cloud_seen),
        await slot_on(front.slot_port, slot_seen),
    ]
    task = asyncio.create_task(front.main())
    await asyncio.sleep(0.2)
    return task, servers, cloud_seen, slot_seen, crashes


def test_a_cloud_503_is_answered_by_the_laptop(front):
    async def run():
        task, servers, cloud_seen, slot_seen, crashes = await serve(front, "status:503")
        head, body = await ask(front, post())
        assert b"200 OK" in head, head
        assert body.startswith(b"slot:"), body
        assert len(cloud_seen) == 1 and len(slot_seen) == 1
        # the failover must not take the front down with it
        await asyncio.sleep(0.2)
        assert crashes == [], crashes
        assert not task.done(), "the front died"
        task.cancel()
        for s in servers:
            s.close()

    asyncio.run(run())


def test_a_healthy_cloud_answers_and_the_laptop_is_left_alone(front):
    async def run():
        task, servers, cloud_seen, slot_seen, crashes = await serve(front, "ok")
        head, body = await ask(front, post())
        assert b"200 OK" in head, head
        assert body.startswith(b"cloud:"), body
        assert slot_seen == []
        task.cancel()
        for s in servers:
            s.close()

    asyncio.run(run())


def test_a_400_is_the_callers_own_business_and_is_relayed(front):
    async def run():
        task, servers, cloud_seen, slot_seen, crashes = await serve(front, "status:400")
        head, body = await ask(front, post())
        assert b"400" in head, head
        assert slot_seen == []
        task.cancel()
        for s in servers:
            s.close()

    asyncio.run(run())


def test_a_cloud_that_stalls_is_answered_by_the_laptop(front):
    async def run():
        task, servers, cloud_seen, slot_seen, crashes = await serve(front, "stall")
        head, body = await ask(front, post())
        assert b"200 OK" in head, head
        assert body.startswith(b"slot:"), body
        assert len(slot_seen) == 1
        task.cancel()
        for s in servers:
            s.close()

    asyncio.run(run())


def test_a_403_on_the_lanes_scope_is_answered_by_the_laptop(front):
    async def run():
        task, servers, cloud_seen, slot_seen, crashes = await serve(front, "403")
        head, body = await ask(front, post())
        assert b"200 OK" in head, head
        assert body.startswith(b"slot:"), body
        assert len(slot_seen) == 1
        task.cancel()
        for s in servers:
            s.close()

    asyncio.run(run())


def test_a_cloud_that_failed_is_passed_over_for_the_next_callers(front):
    async def run():
        task, servers, cloud_seen, slot_seen, crashes = await serve(front, "status:503")
        head, body = await ask(front, post())
        assert body.startswith(b"slot:"), body
        assert len(cloud_seen) == 1

        # the cloud is down for a while: the next caller is answered by the laptop, and the
        # cloud is not asked again
        head, body = await ask(front, post())
        assert body.startswith(b"slot:"), body
        assert len(cloud_seen) == 1, cloud_seen
        assert len(slot_seen) == 2
        task.cancel()
        for s in servers:
            s.close()

    asyncio.run(run())


def test_the_replayed_request_is_the_request_the_caller_wrote(front):
    async def run():
        task, servers, cloud_seen, slot_seen, crashes = await serve(front, "status:503")
        body = b'{"model":"fast","messages":[{"role":"user","content":"hello"}]}'
        await ask(front, post(body=body))
        assert len(slot_seen) == 1
        head, got = slot_seen[0]
        assert head.split(b" ")[0] == b"POST"
        assert head.split(b" ")[1] == b"/v1/chat/completions"
        assert got == body, (got, body)
        task.cancel()
        for s in servers:
            s.close()

    asyncio.run(run())


def test_a_chunked_request_is_replayed_byte_for_byte(front):
    async def run():
        task, servers, cloud_seen, slot_seen, crashes = await serve(front, "status:503")
        raw = (
            b"POST /v1/chat/completions HTTP/1.1\r\nHost: 127.0.0.1:4000\r\n"
            b"Transfer-Encoding: chunked\r\n\r\n5\r\nhello\r\n6\r\n world\r\n0\r\n\r\n"
        )
        head, body = await ask(front, raw)
        assert b"200 OK" in head, head
        assert len(slot_seen) == 1
        got = slot_seen[0][1]
        assert got == b"5\r\nhello\r\n6\r\n world\r\n0\r\n\r\n", got
        task.cancel()
        for s in servers:
            s.close()

    asyncio.run(run())


def test_a_request_too_big_to_replay_is_not_replayed(front):
    async def run():
        task, servers, cloud_seen, slot_seen, crashes = await serve(front, "status:503")
        body = (
            b"x" * 8192
        )  # over the front's MAX_BODY: it cannot be asked of another target
        head, answer = await ask(front, post(body=body))
        assert b"503" in head, head
        assert slot_seen == []
        task.cancel()
        for s in servers:
            s.close()

    asyncio.run(run())


def test_a_cloud_that_fails_repeatedly_is_passed_over_for_longer_each_time(front):
    """One outage must not cost every caller the cloud's failure latency: each failure in a
    row doubles the pass-over, and a cloud that answers again is the default route at once."""

    front.mark_cloud_down()
    first = front.CLOUD_DOWN_UNTIL
    assert front.CLOUD_FAILURES == 1
    assert first > 0

    front.mark_cloud_down()
    assert front.CLOUD_FAILURES == 2
    assert front.CLOUD_DOWN_UNTIL > first, (front.CLOUD_DOWN_UNTIL, first)

    # the ceiling: the pass-over never grows past CLOUD_DOWN_MAX_S
    for _ in range(20):
        front.mark_cloud_down()
    assert front.CLOUD_DOWN_UNTIL - front.time.monotonic() <= front.CLOUD_DOWN_MAX_S + 1

    front.mark_cloud_up()
    assert front.CLOUD_FAILURES == 0
    assert front.CLOUD_DOWN_UNTIL == 0.0


def test_the_laptop_leg_is_bytes_only(front):
    async def run():
        task, servers, cloud_seen, slot_seen, crashes = await serve(front, "status:503")
        await ask(front, post())
        # the cloud failed, so the laptop is first: the slot sees the caller's own head, with
        # the caller's own Host and no rewriting by the front
        await ask(front, post())
        head, _ = slot_seen[-1]
        assert b"Host: 127.0.0.1:4000" in head, head
        task.cancel()
        for s in servers:
            s.close()

    asyncio.run(run())

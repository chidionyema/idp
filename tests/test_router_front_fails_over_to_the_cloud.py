"""The laptop router's front fails over to the cloud router and back, and an OKE outage costs the
laptop nothing.

WHAT THIS GRADES. `platform/llm/front.py` claims: a slot that stops answering /health/liveliness
(it accepts and never replies, or it refuses) is passed over for new connections after
DOWN_AFTER missed probes; with no laptop slot up, new connections go to CLOUD with the cloud's
Host and `Connection: close`; once a slot answers UP_AFTER probes again, new connections return
to it while the one already on the cloud finishes; with the cloud unreachable, the laptop slots
are still tried.

WHY. On 2026-10-21 the laptop ran out of memory and the router on 4001 accepted connections and
never answered them, so the front's refused-connect fallback never fired and every agent lost
every model while llm.mumchimp.com was up. Founder: no laptop overload or OKE outage may take out
every model. These tests are that starvation and that outage, with real sockets.
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
    spec = importlib.util.spec_from_file_location("router_front_failover", MODULE)
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


def reply(body: bytes, close: bool) -> bytes:
    head = f"HTTP/1.1 200 OK\r\nContent-Length: {len(body)}\r\n"
    return (head + ("Connection: close\r\n" if close else "") + "\r\n").encode() + body


async def slot(port: int, name: bytes, state: dict):
    """A router stand-in. state['mode']: 'up' answers; 'starved' accepts and never replies (the
    laptop out of memory); 'sick' fails its health check but still serves requests."""

    async def handle(r, w):
        try:
            while True:
                head = await r.readuntil(b"\r\n\r\n")
                if state["mode"] == "starved":
                    await r.read()  # hold the socket open, answer nothing
                    break
                path = head.split(b" ", 2)[1]
                if path == b"/health/liveliness":
                    ok = state["mode"] == "up"
                    w.write(
                        b"HTTP/1.0 200 OK\r\n\r\n" if ok else b"HTTP/1.0 503 No\r\n\r\n"
                    )
                    await w.drain()
                    break
                w.write(reply(name + b":" + path, close=False))
                await w.drain()
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        w.close()

    return await asyncio.start_server(handle, "127.0.0.1", port)


async def cloud(url: str):
    """The OKE router stand-in: answers with the request head it received, then closes."""

    async def handle(r, w):
        try:
            head = await r.readuntil(b"\r\n\r\n")
            w.write(reply(b"cloud:" + head, close=True))
            await w.drain()
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        w.close()

    return await asyncio.start_server(handle, "127.0.0.1", int(url.rsplit(":", 1)[1]))


async def ask(r, w, path: str) -> bytes:
    w.write(f"GET {path} HTTP/1.1\r\nHost: 127.0.0.1:4000\r\n\r\n".encode())
    await w.drain()
    head = await asyncio.wait_for(r.readuntil(b"\r\n\r\n"), 5)
    length = next(
        int(line.split(b":", 1)[1])
        for line in head.split(b"\r\n")
        if line.lower().startswith(b"content-length:")
    )
    return await asyncio.wait_for(r.readexactly(length), 5)


async def fresh(front, path: str) -> bytes:
    r, w = await asyncio.open_connection(*front.LISTEN)
    try:
        return await ask(r, w, path)
    finally:
        w.close()


async def until(cond, seconds: float = 5.0) -> None:
    for _ in range(int(seconds / 0.05)):
        if cond():
            return
        await asyncio.sleep(0.05)
    raise AssertionError("condition never held")


def test_a_starved_laptop_sends_new_callers_to_the_cloud_and_back(front):
    async def run():
        a, b = front.SLOTS
        sa, sb = {"mode": "up"}, {"mode": "up"}
        servers = [
            await slot(a, b"a", sa),
            await slot(b, b"b", sb),
            await cloud(front.CLOUD),
        ]
        task = asyncio.create_task(front.main())
        await asyncio.sleep(0.2)
        assert await fresh(front, "/one") == b"a:/one"

        # the laptop runs out of memory: both slots accept and never answer
        sa["mode"] = sb["mode"] = "starved"
        await until(lambda: front.DOWN == {a, b})
        got = await fresh(front, "/two")
        assert got.startswith(b"cloud:GET /two HTTP/1.1\r\n")
        assert f"Host: {front.CLOUD.split('//')[1]}".encode() in got
        assert b"Host: 127.0.0.1:4000" not in got
        assert b"Connection: close" in got

        # the laptop recovers: a caller opened on the cloud finishes there, new ones come home
        on_cloud = await asyncio.open_connection(*front.LISTEN)
        sa["mode"] = sb["mode"] = "up"
        await until(lambda: not front.DOWN)
        assert await fresh(front, "/three") == b"a:/three"
        assert (await ask(*on_cloud, "/four")).startswith(b"cloud:GET /four ")
        on_cloud[1].close()

        task.cancel()
        for s in servers:
            s.close()

    asyncio.run(run())


def test_one_starved_slot_is_covered_by_its_twin_before_the_cloud(front):
    async def run():
        a, b = front.SLOTS
        sa, sb = {"mode": "starved"}, {"mode": "up"}
        servers = [
            await slot(a, b"a", sa),
            await slot(b, b"b", sb),
            await cloud(front.CLOUD),
        ]
        task = asyncio.create_task(front.main())
        await until(lambda: front.DOWN == {a})
        assert await fresh(front, "/hi") == b"b:/hi"
        task.cancel()
        for s in servers:
            s.close()

    asyncio.run(run())


def test_an_oke_outage_still_reaches_the_laptop(front):
    async def run():
        a, b = front.SLOTS
        # the cloud refuses (nothing listens on its port), slot b is gone, and slot a fails its
        # health check while it can still serve: the laptop is the only way left, and is used
        sa = {"mode": "sick"}
        server = await slot(a, b"a", sa)
        task = asyncio.create_task(front.main())
        await until(lambda: front.DOWN == {a, b})
        assert front.route()[0] == front.CLOUD
        assert await fresh(front, "/hi") == b"a:/hi"
        task.cancel()
        server.close()

    asyncio.run(run())


def test_the_cloud_leg_can_be_turned_off(front, monkeypatch):
    monkeypatch.setattr(front, "CLOUD", "")
    front.DOWN.update(front.SLOTS)
    assert front.route() == list(front.SLOTS)

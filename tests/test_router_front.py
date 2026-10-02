"""The laptop router's front forwards to the active slot, and a switch never cuts a caller.

WHAT THIS GRADES. `platform/llm/front.py` claims: each new connection goes to the slot named in
the active file; a connection already open stays on the slot it started on until that slot
closes it; a refused active slot falls through to its twin.

WHY. On 2026-10-02 every router deploy stopped the only router on :4000 and every agent saw
"Connection error" for ~90 s. `bin/litellm-local swap` now boots the new router beside the old
one and flips the active file; these tests are that flip, with real sockets.
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
    spec = importlib.util.spec_from_file_location("router_front", MODULE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    a, b, f = free_port(), free_port(), free_port()
    monkeypatch.setattr(mod, "SLOTS", (a, b))
    monkeypatch.setattr(mod, "ACTIVE", tmp_path / "active")
    monkeypatch.setattr(mod, "LISTEN", ("127.0.0.1", f))
    return mod


async def slot(port: int, name: bytes):
    """A router stand-in: answers every line with its name, until the caller closes."""

    async def handle(r, w):
        while line := await r.readline():
            w.write(name + b":" + line)
            await w.drain()
        w.close()

    return await asyncio.start_server(handle, "127.0.0.1", port)


async def ask(r, w, msg: bytes) -> bytes:
    w.write(msg + b"\n")
    await w.drain()
    return (await asyncio.wait_for(r.readline(), 5)).strip()


def test_a_switch_sends_new_callers_to_the_new_slot_and_keeps_open_ones(front):
    async def run():
        a, b = front.SLOTS
        front.ACTIVE.write_text(f"{a}\n")
        old, new = await slot(a, b"old"), await slot(b, b"new")
        task = asyncio.create_task(front.main())
        await asyncio.sleep(0.2)

        r1, w1 = await asyncio.open_connection(*front.LISTEN)
        assert await ask(r1, w1, b"one") == b"old:one"

        front.ACTIVE.write_text(
            f"{b}\n"
        )  # what `litellm-local swap` does once b answers
        r2, w2 = await asyncio.open_connection(*front.LISTEN)
        assert await ask(r2, w2, b"two") == b"new:two"
        # the caller that was mid-conversation is still on the old slot, uncut
        assert await ask(r1, w1, b"three") == b"old:three"

        for w in (w1, w2):
            w.close()
        task.cancel()
        old.close()
        new.close()

    asyncio.run(run())


def test_a_refused_active_slot_falls_through_to_its_twin(front):
    async def run():
        a, b = front.SLOTS
        front.ACTIVE.write_text(f"{a}\n")  # nothing listens on a
        twin = await slot(b, b"twin")
        task = asyncio.create_task(front.main())
        await asyncio.sleep(0.2)
        r, w = await asyncio.open_connection(*front.LISTEN)
        assert await ask(r, w, b"hi") == b"twin:hi"
        w.close()
        task.cancel()
        twin.close()

    asyncio.run(run())


def test_a_large_streamed_response_arrives_whole(front):
    async def run():
        a, _ = front.SLOTS
        front.ACTIVE.write_text(f"{a}\n")
        body = bytes(range(256)) * 8192  # 2 MiB, many chunks

        async def handle(r, w):
            await r.readline()
            w.write(body)
            await w.drain()
            w.close()

        srv = await asyncio.start_server(handle, "127.0.0.1", a)
        task = asyncio.create_task(front.main())
        await asyncio.sleep(0.2)
        r, w = await asyncio.open_connection(*front.LISTEN)
        w.write(b"go\n")
        await w.drain()
        got = await asyncio.wait_for(r.read(), 10)  # until the slot closes
        assert got == body
        w.close()
        task.cancel()
        srv.close()

    asyncio.run(run())

"""A loaded box with a live slot is SERVED, not refused (idp#7660).

WHAT THIS GRADES. `platform/llm/front.py` refuses every caller with a 503 when the machine's
load average is above LOAD_MAX -- before it has asked the router anything. On 2026-10-31 that
was measured on the laptop: load 115.93 on 4 CPUs, the router at 0.1-0.5% CPU answering
/health/liveliness in milliseconds, and the front refusing every caller in about 1 ms. The
load average was the false negative; the router's own answer is the truth.

So the load guard now PROBES the slot that is serving instead of refusing blind:

  * a loaded box whose slot answers  -> the caller is served (this file);
  * a loaded box whose slot is dead   -> the caller is refused at once, with the same 503
    and the same Retry-After the old blind refusal sent (this file).

Both halves matter. The first is the outage; the second is the promise that a loaded box
still refuses fast instead of joining a queue it cannot serve.
"""

import asyncio
import importlib.util
import pathlib
import socket
import time

MODULE = pathlib.Path(__file__).resolve().parents[1] / "platform" / "llm" / "front.py"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def load_front(tmp_path, monkeypatch, load):
    spec = importlib.util.spec_from_file_location("router_front_failopen", MODULE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    a, b, f = free_port(), free_port(), free_port()
    monkeypatch.setattr(mod, "SLOTS", (a, b))
    monkeypatch.setattr(mod, "ACTIVE", tmp_path / "active")
    monkeypatch.setattr(mod, "LISTEN", ("127.0.0.1", f))
    monkeypatch.setattr(mod, "CLOUD", "")
    # The load is stated, not inherited: this file grades what the front DOES with a loaded
    # box, and a verdict that depends on the machine running the test is not a verdict.
    monkeypatch.setattr(mod.os, "getloadavg", lambda: (load, load, load))
    return mod


async def slot(port: int, name: bytes):
    """A router stand-in: answers every line, including the liveliness probe."""

    async def handle(r, w):
        while line := await r.readline():
            w.write(name + b":" + line)
            await w.drain()
        w.close()

    return await asyncio.start_server(handle, "127.0.0.1", port)


def test_a_loaded_box_with_a_live_slot_is_served(tmp_path, monkeypatch):
    mod = load_front(tmp_path, monkeypatch, 999.0)

    async def run():
        a, _ = mod.SLOTS
        mod.ACTIVE.write_text(f"{a}\n")
        server = await slot(a, b"live")
        task = asyncio.create_task(mod.main())
        await asyncio.sleep(0.2)
        r, w = await asyncio.open_connection(*mod.LISTEN)
        w.write(b"hello\n")
        await w.drain()
        got = (await asyncio.wait_for(r.readline(), 5)).strip()
        w.close()
        task.cancel()
        server.close()
        return got

    got = asyncio.run(run())
    assert got == b"live:hello", got


def test_a_loaded_box_with_a_dead_slot_is_refused_at_once(tmp_path, monkeypatch):
    mod = load_front(tmp_path, monkeypatch, 999.0)

    async def run():
        a, _ = mod.SLOTS
        mod.ACTIVE.write_text(f"{a}\n")  # nothing listens on a
        task = asyncio.create_task(mod.main())
        await asyncio.sleep(0.2)
        started = time.monotonic()
        r, w = await asyncio.open_connection(*mod.LISTEN)
        w.write(b"hello\n")
        await w.drain()
        head = await asyncio.wait_for(r.read(), 5)
        elapsed = time.monotonic() - started
        w.close()
        task.cancel()
        return head, elapsed

    head, elapsed = asyncio.run(run())
    assert head.startswith(b"HTTP/1.1 503"), head[:80]
    assert b"Retry-After: 30" in head, head[:120]
    assert elapsed < 1.0, (
        "the refusal took %.2fs; a caller waiting for it gives up first" % elapsed
    )


def test_the_probe_is_bounded_even_when_the_slot_hangs(tmp_path, monkeypatch):
    """A slot that accepts the connection and never answers must not hold the caller.

    The probe is what stands between the caller and an open socket, so it has a bound of its
    own -- and it is short: the refusal a caller waits for is a refusal, not a queue.
    """
    mod = load_front(tmp_path, monkeypatch, 999.0)
    monkeypatch.setattr(mod, "SAT_PROBE_TIMEOUT", 0.2)

    async def run():
        a, _ = mod.SLOTS

        async def handle(r, w):
            await r.readline()
            await asyncio.sleep(30)  # accepts, never answers

        server = await asyncio.start_server(handle, "127.0.0.1", a)
        mod.ACTIVE.write_text(f"{a}\n")
        task = asyncio.create_task(mod.main())
        await asyncio.sleep(0.2)
        started = time.monotonic()
        r, w = await asyncio.open_connection(*mod.LISTEN)
        w.write(b"hello\n")
        await w.drain()
        head = await asyncio.wait_for(r.read(), 5)
        elapsed = time.monotonic() - started
        w.close()
        task.cancel()
        server.close()
        return head, elapsed

    head, elapsed = asyncio.run(run())
    assert head.startswith(b"HTTP/1.1 503"), head[:80]
    assert elapsed < 2.0, "the bounded probe took %.2fs" % elapsed

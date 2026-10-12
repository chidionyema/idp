"""The stream plane must not cost the process a bus connection per client.

WHY THIS FILE EXISTS. `bin/idp-fleet` ran with `[Errno 24] Too many open files` 12,114 times in a
231 MB error log, and `lsof` showed 191 sockets to nats:4222 behind 49 inbound ones (issue #5829).
/stream called nats.connect four times per client -- one per source -- and each connection lived
in that client's own generator, so a client that went away while a dial was in flight cancelled
the dial, the connection was never recorded, and the next client dialled again. On the local bus
that is measurable: eight connect/disconnect cycles left sockets behind and the dial count climbed
one per client. The fix gives the plane one connection per process, established by a task that
outlives the client that triggered it.

These tests drive the ASGI app and the adapter directly. The load-bearing assertion is a dial
count: an earlier version of this file asserted only that the four sources were *closed* when a
client left, and it passed on the unfixed code -- the cancellation unwinds those generators either
way, so that assertion could not fail, and a test that cannot fail is not a test.
"""

from __future__ import annotations

import asyncio
import contextlib
import sys
import types

import pytest

BUS = "nats://bus.test:4222"


def _scope(path: str = "/stream") -> dict:
    """The scope uvicorn actually hands a request: it speaks ASGI spec 2.3, not 2.4."""
    return {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [(b"host", b"test")],
        "client": ("127.0.0.1", 4444),
        "server": ("test", 80),
    }


class _NC:
    """Enough of a NATS client for the plane's bookkeeping."""

    is_closed = False


class _Client:
    """A minimal ASGI client: it disconnects on demand and records what it was sent."""

    def __init__(self) -> None:
        self.sent: list[dict] = []
        self._disconnected = asyncio.Event()

    def disconnect(self) -> None:
        self._disconnected.set()

    async def receive(self) -> dict:
        await self._disconnected.wait()
        return {"type": "http.disconnect"}

    async def send(self, message: dict) -> None:
        self.sent.append(message)


@pytest.fixture()
def serve_app(monkeypatch):
    # uvicorn is a server, not a dependency of the app; importing serve must not need it.
    sys.modules.setdefault("uvicorn", types.ModuleType("uvicorn"))
    from fleetview_backend import routes, serve

    monkeypatch.setenv("NATS_URL", BUS)
    monkeypatch.setattr(routes, "sessions_envelope", lambda: ({"sessions": []}, 200))
    return serve.build_app()


def _reset_plane(monkeypatch):
    from fleetview_backend import nats_adapter

    monkeypatch.setattr(nats_adapter, "_STREAM_CONNS", {})
    monkeypatch.setattr(nats_adapter, "_STREAM_DIALS", {})
    monkeypatch.setattr(nats_adapter, "_STREAM_LOCKS", {})
    return nats_adapter


def _count_dials(monkeypatch, *, never_returns: bool = False):
    """Replace nats.connect with a counter. Returns the dial list (appended to as each dial starts)."""
    nats = pytest.importorskip("nats")

    dials: list = []

    async def fake_connect(url, **kwargs):
        dials.append(url)  # recorded as the dial starts, not as it finishes
        if never_returns:
            await asyncio.Event().wait()  # a dial still in flight
        return _NC()

    monkeypatch.setattr(nats, "connect", fake_connect)
    return dials


def _install_sources(monkeypatch, seen: list):
    """Four sources that take the plane's connection, exactly as the real ones do."""
    from fleetview_backend import nats_adapter

    def _source(name: str):
        async def _gen(url):
            await nats_adapter._stream_conn(url)  # the real source does this
            seen.append(name)
            try:
                await asyncio.Event().wait()  # a bus with nothing on it
                yield {}
            finally:
                seen.append(name + ":closed")

        return _gen

    for name in ("stream", "cues", "stories", "approvals"):
        monkeypatch.setattr(nats_adapter, f"subscribe_{name}", _source(name))


def test_one_client_opens_one_bus_connection_not_four(serve_app, monkeypatch):
    """Four sources, one dial -- driven through the app, which is where the four came from."""
    _reset_plane(monkeypatch)
    dials = _count_dials(monkeypatch)
    seen: list = []
    _install_sources(monkeypatch, seen)

    async def scenario():
        client = _Client()
        task = asyncio.create_task(serve_app(_scope(), client.receive, client.send))
        for _ in range(200):  # let all four sources subscribe
            if len(seen) == 4:
                break
            await asyncio.sleep(0.01)
        assert len(seen) == 4, f"only {seen!r} subscribed"
        assert dials == [BUS], (
            f"one client dialled the bus {len(dials)} times; it used to be four, one per source, "
            "and every one of them was a socket held by that client's own generator (#5829)"
        )
        client.disconnect()
        await asyncio.wait_for(task, timeout=5)
        return list(seen)

    seen_after = asyncio.run(scenario())
    assert sorted(seen_after) == [
        "approvals",
        "approvals:closed",
        "cues",
        "cues:closed",
        "stories",
        "stories:closed",
        "stream",
        "stream:closed",
    ], f"the response left a source open: {seen_after!r}"


def test_a_client_that_leaves_mid_dial_does_not_cost_a_second_dial(monkeypatch):
    """The measured leak: cancelling the caller must not abort the dial or strand its socket."""
    _reset_plane(monkeypatch)
    dials = _count_dials(monkeypatch, never_returns=True)
    from fleetview_backend import nats_adapter

    async def scenario():
        first = asyncio.create_task(nats_adapter._stream_conn(BUS))
        for _ in range(200):  # wait for the dial to be in flight
            if dials:
                break
            await asyncio.sleep(0.01)
        assert dials == [BUS], "the first client never dialled"
        first.cancel()  # the client that triggered the dial goes away
        with contextlib.suppress(asyncio.CancelledError):
            await first
        second = asyncio.create_task(nats_adapter._stream_conn(BUS))
        await asyncio.sleep(0.05)
        second.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await second

    asyncio.run(scenario())
    assert dials == [BUS], (
        f"{len(dials)} dials were made for one connection: the first client's cancellation killed "
        "its dial, nothing was recorded, and the next client dialled again -- one stranded bus "
        "socket per client, which is the EMFILE this ticket is about (issue #5829)"
    )


def test_the_response_closes_the_iterator_it_was_given():
    from fleetview_backend import serve

    closed: list = []

    async def body():
        try:
            yield b"one"
            await asyncio.Event().wait()
        finally:
            closed.append("body")

    async def scenario():
        client = _Client()
        task = asyncio.create_task(
            serve._ClosingStream(body())(_scope(), client.receive, client.send)
        )
        for _ in range(200):  # wait for the first chunk, then vanish
            if client.sent and client.sent[-1].get("type") == "http.response.body":
                break
            await asyncio.sleep(0.01)
        client.disconnect()
        with contextlib.suppress(
            asyncio.CancelledError
        ):  # a cancelled response is still closed
            await asyncio.wait_for(task, timeout=5)

    asyncio.run(scenario())
    assert closed == ["body"], (
        "the response was abandoned with its body iterator left suspended at `yield`; Starlette "
        "does not aclose it, so nobody runs the `finally` that closes the bus (issue #5829)"
    )

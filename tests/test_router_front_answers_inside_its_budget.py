"""The front answers inside a budget that is smaller than the caller's patience.

WHAT THIS GRADES. `platform/llm/front.py` claims: one caller's request is answered, or refused,
inside ANSWER_BUDGET seconds; a box too loaded to answer is refused at once instead of being
joined to a queue it cannot serve; and a front that can answer still answers.

WHY. On 2026-10-30 three Claude Code sessions gave up at once with "Request timed out" while the
front held their requests for 22 minutes: the cloud's 120 s plus two laptop slots at 600 s each.
Claude Code's patience is 364 s. Measured over the transcripts of 2026-10-28..30 by
bin/estate-session-audit (the audit: docs/audits/2026-10-30-claude-code-session-stalls/): 21
"Request timed out" events in the founder's own seven sessions, the gap from the request that
went out to the timeout that came back landing in a 361.3-374.4 s band on all 21, so the answer
always arrived after the caller had gone. The answers that can be paired with the request that
produced them (n=1,284): p50 7.9 s, p90 31.5 s, p95 69.6 s, p99 260.1 s. The front now spends
ONE budget per request, below the patience, and refuses a caller it cannot serve inside it.

THE FALSIFIER IS HERE. A target that takes the request and never answers it is the known-bad
fixture: against the old front (no budget) the caller waits until this test's own deadline and
the test fails; against the front as it stands, the caller is refused inside the budget. The
known-good fixture is a target that answers: it must still be answered, or the gate proves
nothing.
"""

import asyncio
import importlib.util
import pathlib
import socket
import time

import pytest

MODULE = pathlib.Path(__file__).resolve().parents[1] / "platform" / "llm" / "front.py"

REQUEST = (
    b"POST /v1/messages HTTP/1.1\r\nHost: 127.0.0.1:4000\r\nContent-Length: 0\r\n\r\n"
)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def load(name: str):
    """The front, loaded fresh."""
    spec = importlib.util.spec_from_file_location(name, MODULE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def front(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "ESTATE_FRONT_ANSWER_BUDGET", "2"
    )  # the shape, in seconds, not in minutes
    mod = load("router_front_budget")
    a, b, f, c = free_port(), free_port(), free_port(), free_port()
    monkeypatch.setattr(mod, "SLOTS", (a, b))
    monkeypatch.setattr(mod, "ACTIVE", tmp_path / "active")
    monkeypatch.setattr(mod, "LISTEN", ("127.0.0.1", f))
    monkeypatch.setattr(mod, "CLOUD", f"http://127.0.0.1:{c}")
    monkeypatch.setattr(mod, "PROBE_EVERY", 0.05)
    monkeypatch.setattr(mod, "PROBE_TIMEOUT", 0.2)
    monkeypatch.setattr(mod, "CLOUD_DOWN_UNTIL", 0.0)
    (tmp_path / "active").write_text(f"{a}\n")
    return mod


async def starved(port: int, state: dict):
    """A router that takes the request and never answers it: the laptop out of memory."""

    async def handle(r, w):
        try:
            head = await r.readuntil(b"\r\n\r\n")
            if b"/health/liveliness" not in head:
                state["asked"] = state.get("asked", 0) + 1
            await r.read()  # hold the socket open, answer nothing
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        w.close()

    return await asyncio.start_server(handle, "127.0.0.1", port)


async def answering(port: int, body: bytes):
    """A router that answers."""

    async def handle(r, w):
        try:
            await r.readuntil(b"\r\n\r\n")
            head = f"HTTP/1.1 200 OK\r\nContent-Length: {len(body)}\r\n\r\n".encode()
            w.write(head + body)
            await w.drain()
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        w.close()

    return await asyncio.start_server(handle, "127.0.0.1", port)


async def ask(front, request: bytes = REQUEST):
    """Send one request through the front; return the first status line and how long it took."""
    r, w = await asyncio.open_connection(*front.LISTEN)
    w.write(request)
    await w.drain()
    started = time.monotonic()
    line = await asyncio.wait_for(r.readline(), 20)
    elapsed = time.monotonic() - started
    w.close()
    return line, elapsed


def test_the_default_budget_is_smaller_than_the_callers_patience(monkeypatch):
    monkeypatch.delenv("ESTATE_FRONT_ANSWER_BUDGET", raising=False)
    mod = load("router_front_default")
    assert (
        mod.CLIENT_PATIENCE == 364.0
    )  # measured: the 361.3-374.4 s band to the timeout
    assert mod.ANSWER_BUDGET < mod.CLIENT_PATIENCE
    # The measured work is p50 7.9 s and p95 69.6 s (n=1,284 answers paired with their request),
    # so the budget is above the work and below the patience: the caller either gets its answer
    # or a refusal it can retry. 240 s is 3.4x the p95 of the work and 124 s below the patience.
    assert mod.ANSWER_BUDGET > 69.6
    assert mod.ANSWER_BUDGET <= 300


def test_a_router_that_never_answers_is_refused_inside_the_budget(front):
    async def run():
        a, _ = front.SLOTS
        front.CLOUD = ""  # the laptop is the only target
        state = {}
        srv = await starved(a, state)
        task = asyncio.create_task(front.main())
        await asyncio.sleep(0.2)
        line, elapsed = await ask(front)
        assert line.startswith(b"HTTP/1.1 504"), line
        assert elapsed < front.ANSWER_BUDGET + 2, elapsed
        assert state.get("asked", 0) == 1  # the router was asked once, and gave nothing
        task.cancel()
        srv.close()

    asyncio.run(run())


def test_a_stalled_cloud_and_a_stalled_router_are_refused_inside_the_budget(front):
    """The shape of the 2026-10-30 outage: nothing answers, and the caller waits anyway."""

    async def run():
        a, b = front.SLOTS
        cloud_port = int(front.CLOUD.rsplit(":", 1)[1])
        slot = await starved(a, {})
        twin = await starved(b, {})
        cloud = await starved(cloud_port, {})
        task = asyncio.create_task(front.main())
        await asyncio.sleep(0.2)
        line, elapsed = await ask(front)
        assert line.startswith(b"HTTP/1.1 504"), line
        assert elapsed < front.ANSWER_BUDGET + 2, elapsed
        task.cancel()
        for srv in (slot, twin, cloud):
            srv.close()

    asyncio.run(run())


def test_a_router_that_answers_is_still_answered(front):
    async def run():
        a, _ = front.SLOTS
        front.CLOUD = ""
        srv = await answering(a, b"answer")
        task = asyncio.create_task(front.main())
        await asyncio.sleep(0.2)
        r, w = await asyncio.open_connection(*front.LISTEN)
        w.write(REQUEST)
        await w.drain()
        head = await asyncio.wait_for(r.readuntil(b"\r\n\r\n"), 10)
        assert b"200" in head, head
        assert await asyncio.wait_for(r.read(6), 10) == b"answer"
        w.close()
        task.cancel()
        srv.close()

    asyncio.run(run())


async def refusing(port: int, status: bytes, body: bytes):
    """A router that refuses, the way the recovery router refuses a model it does not carry."""

    async def handle(r, w):
        try:
            await r.readuntil(b"\r\n\r\n")
            head = (
                b"HTTP/1.1 "
                + status
                + b"\r\nContent-Length: "
                + str(len(body)).encode()
                + b"\r\n\r\n"
            )
            w.write(head + body)
            await w.drain()
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        w.close()

    return await asyncio.start_server(handle, "127.0.0.1", port)


def test_a_cloud_that_does_not_carry_the_model_is_passed_over(front):
    """The cloud is healthy and answers, but it does not carry the caller's model.

    Measured on the recovery router (2026-10-30): HTTP 400 "Invalid model name passed in
    model=claude-sonnet-4-5. Call `/v1/models` to view available models for your key." The
    front used to relay that refusal as the answer, so Claude Code failed at once on a healthy
    cloud although the laptop carries the model. The falsifier is the front as it stood before
    this change: the caller gets the 400 and this test fails.
    """

    async def run():
        a, _ = front.SLOTS
        cloud_port = int(front.CLOUD.rsplit(":", 1)[1])
        cloud = await refusing(
            cloud_port,
            b"400 Bad Request",
            b'{"error":{"message":"Invalid model name passed in model=claude-sonnet-4-5."}}',
        )
        slot = await answering(a, b"answer")
        task = asyncio.create_task(front.main())
        await asyncio.sleep(0.2)
        r, w = await asyncio.open_connection(*front.LISTEN)
        w.write(REQUEST)
        await w.drain()
        head = await asyncio.wait_for(r.readuntil(b"\r\n\r\n"), 10)
        assert b"200" in head, head  # the laptop's answer, not the cloud's refusal
        assert await asyncio.wait_for(r.read(6), 10) == b"answer"
        w.close()
        task.cancel()
        for srv in (cloud, slot):
            srv.close()

    asyncio.run(run())


def test_a_refusal_about_the_request_is_still_relayed(front):
    """Only a refusal that names the model is passed over. The caller's own error is theirs."""

    async def run():
        a, _ = front.SLOTS
        cloud_port = int(front.CLOUD.rsplit(":", 1)[1])
        cloud = await refusing(
            cloud_port,
            b"400 Bad Request",
            b'{"error":{"message":"max_tokens is too large"}}',
        )
        state = {}
        slot = await starved(a, state)
        task = asyncio.create_task(front.main())
        await asyncio.sleep(0.2)
        r, w = await asyncio.open_connection(*front.LISTEN)
        w.write(REQUEST)
        await w.drain()
        head = await asyncio.wait_for(r.readuntil(b"\r\n\r\n"), 10)
        assert b"400" in head, head  # the caller's own refusal, relayed untouched
        w.close()
        task.cancel()
        for srv in (cloud, slot):
            srv.close()

    asyncio.run(run())


def test_a_saturated_box_is_refused_at_once(front, monkeypatch):
    async def run():
        a, _ = front.SLOTS
        front.CLOUD = ""
        state = {}
        srv = await starved(a, state)
        monkeypatch.setattr(front.os, "getloadavg", lambda: (999.0, 999.0, 999.0))
        task = asyncio.create_task(front.main())
        await asyncio.sleep(0.2)
        line, elapsed = await ask(front)
        assert line.startswith(b"HTTP/1.1 503"), line
        assert elapsed < 1.0, elapsed
        assert (
            state.get("asked", 0) == 0
        )  # the router was never asked: the box could not answer
        task.cancel()
        srv.close()

    asyncio.run(run())

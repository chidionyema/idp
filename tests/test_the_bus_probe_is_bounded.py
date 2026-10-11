"""The bus probe cannot run past its budget, on either end of the sweep.

Incident (issue #5788): the acceptance suite's estate-twin-runtime sweep was SIGKILLed at
pytest's 180s timeout in 4 of the last 12 ci.yml runs -- 2 of the last 3 candidates -- with
the CI log ending in `socket.gaierror: [Errno 8] nodename nor servname provided, or not known`.

Measured 2026-10-11, nats-py on this machine, with the twin's own options
(`connect_timeout=5, allow_reconnect=False`) against a name that cannot resolve:

    attempt 1 at 0.05s, attempt 2 at 2.05s, attempt 3 at 4.05s, attempt 4 at 6.06s, ...

i.e. allow_reconnect=False does NOT bound a first connect -- nats-py still walks its own
reconnect ladder, one attempt every reconnect_time_wait (2s), up to max_reconnect_attempts
(60): ~122s against one candidate, and the same again against the loopback candidate that
refuses, ~244s for a probe whose suite has 180s. That is the SIGKILL. The resolver is not the
hang; it is merely the slowest call inside it.

Measured too, against a live nats-server listening on 127.0.0.1:4222: the twin connects and
then blocks in the JetStream read for over four minutes -- main thread in select(), ~3s CPU,
no child processes, no open sockets. The read is the other unbounded half.

So the probe is bounded in three places, and each is asserted here: a hostname that does not
resolve is not dialled (and the resolve itself runs in a child this process can kill), one
candidate is one attempt, and one JetStream read has a deadline. A bus that is genuinely
absent must cost the sweep seconds and say so -- not eat the suite's whole timeout.
"""

from __future__ import annotations

import asyncio
import importlib.machinery
import importlib.util
import sqlite3
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
TWIN = REPO / "bin" / "estate-twin-runtime"
URL = "nats://127.0.0.1:4222"


def load_twin():
    loader = importlib.machinery.SourceFileLoader("twin_bus_probe", str(TWIN))
    spec = importlib.util.spec_from_loader("twin_bus_probe", loader)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def twin():
    return load_twin()


def test_a_literal_address_needs_no_resolver(twin):
    """A literal is dialled directly: no resolver cost, no resolver to hang."""
    started = time.monotonic()
    assert twin._resolves("127.0.0.1", 4222, 0.01) is True
    assert time.monotonic() - started < 0.5


def test_a_resolver_that_never_answers_is_killed_by_its_budget(twin, monkeypatch):
    """The resolve runs in a child, so the budget is real: a hung getaddrinfo is killable."""
    monkeypatch.setattr(twin, "_RESOLVE_SNIPPET", "import time;time.sleep(60)")
    started = time.monotonic()
    assert twin._resolves("name.invalid", 4222, 1) is False
    assert time.monotonic() - started < 5


def test_a_name_that_does_not_resolve_is_not_dialled(twin, monkeypatch):
    """`.invalid` never resolves (RFC 2606), so the candidate must cost nothing at all."""
    nats = pytest.importorskip("nats")
    dialled: list[str] = []

    async def connect(url, **kwargs):
        dialled.append(url)
        raise AssertionError("an unresolvable host must not reach nats.connect")

    monkeypatch.setattr(nats, "connect", connect)
    monkeypatch.setenv("NATS_URL", "nats://nats.event-bus.invalid:4222")

    with pytest.raises(RuntimeError):
        twin._bus_streams(sqlite3.connect(":memory:"))
    assert dialled == []


def test_one_candidate_is_one_attempt_not_sixty_one(twin, monkeypatch):
    """What nats-py does 61 times over, ~122s, must become one attempt with a deadline."""
    nats = pytest.importorskip("nats")
    attempts: list[str] = []

    async def connect(url, **kwargs):
        attempts.append(url)
        await asyncio.sleep(12)  # nats-py's own ladder, compressed into one call
        raise OSError("unreachable")

    monkeypatch.setattr(nats, "connect", connect)
    monkeypatch.setenv("NATS_URL", URL)
    monkeypatch.setenv("ESTATE_TWIN_BUS_PROBE_S", "2")

    started = time.monotonic()
    with pytest.raises(RuntimeError):
        twin._bus_streams(sqlite3.connect(":memory:"))
    elapsed = time.monotonic() - started
    assert attempts == [URL], "one candidate is one attempt"
    assert elapsed < 5, f"the probe held the sweep for {elapsed:.1f}s"


def test_a_bus_that_never_answers_the_jetstream_api_is_dropped(twin, monkeypatch):
    """A connected bus that never answers the read is the other unbounded half."""
    nats = pytest.importorskip("nats")

    class NeverAnswers:
        def jetstream(self):
            return self

        async def streams_info(self):
            await asyncio.sleep(12)  # measured: four minutes in select(), unbounded

        async def close(self):
            return None

    async def connect(url, **kwargs):
        return NeverAnswers()

    monkeypatch.setattr(nats, "connect", connect)
    monkeypatch.setenv("NATS_URL", URL)
    monkeypatch.setenv("ESTATE_TWIN_BUS_PROBE_S", "2")

    started = time.monotonic()
    with pytest.raises((RuntimeError, asyncio.TimeoutError)):
        twin._bus_streams(sqlite3.connect(":memory:"))
    assert time.monotonic() - started < 5

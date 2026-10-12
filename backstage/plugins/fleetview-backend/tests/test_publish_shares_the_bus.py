"""Publishing an event must not cost the bus a connection.

WHY THIS FILE EXISTS. 2026-10-12: the laptop's nats-server stopped answering connects. Its client
ids had passed 180,000 in 2.4 days of uptime -- publish() dialled, ran add_stream and drained once
per event -- and its last log lines were consumer creates taking 37s to 1m14s. Meanwhile
fleetview-backend's error log was 277 MB, almost all of it nats-py's default error callback
printing a 30-line traceback for every reconnect attempt. And approvals_adapter called
asyncio.run() from a coroutine already on the server's loop, which raises before publishing; past
that, its payload's "kind" collided with publish()'s own, and the subject it built was not one the
board reads. No approval event had ever reached /fleet.
"""

from __future__ import annotations

import asyncio

import pytest

nats = pytest.importorskip("nats")
from nats.js.errors import NoStreamResponseError  # noqa: E402

from fleetview_backend import approvals_adapter, nats_adapter  # noqa: E402

BUS = "nats://bus.test:4222"


class _JS:
    def __init__(self, missing_stream: bool = False) -> None:
        self.streams: list[str] = []
        self.published: list[str] = []
        self._missing = missing_stream

    async def add_stream(self, name, subjects, max_age):
        self.streams.append(name)
        self._missing = False

    async def publish(self, subject, payload):
        if self._missing:
            raise NoStreamResponseError()
        self.published.append(subject)


class _NC:
    is_closed = False

    def __init__(self, js: _JS) -> None:
        self._js = js

    def jetstream(self):
        return self._js


@pytest.fixture()
def bus(monkeypatch):
    monkeypatch.setattr(nats_adapter, "_STREAM_CONNS", {})
    monkeypatch.setattr(nats_adapter, "_STREAM_DIALS", {})
    monkeypatch.setattr(nats_adapter, "_STREAM_LOCKS", {})
    js = _JS()
    dials: list[dict] = []

    async def connect(url, **kwargs):
        dials.append(kwargs)
        return _NC(js)

    monkeypatch.setattr(nats, "connect", connect)
    return js, dials


def test_many_events_dial_once_and_create_the_stream_once(bus):
    js, dials = bus

    async def scenario():
        for i in range(20):
            await nats_adapter.publish(BUS, f"s{i}", "test", "phase", "executing")

    asyncio.run(scenario())
    assert len(js.published) == 20
    assert len(dials) == 1, (
        f"{len(dials)} dials for 20 events: a dial per publish is what ran nats-server's client "
        "ids past 180,000 and wedged it"
    )
    assert js.streams == ["ESTATE_AGENT"], (
        "add_stream ran per event, not per connection"
    )


def test_a_bus_that_lost_the_stream_gets_it_back(bus):
    js, _ = bus
    js._missing = True

    async def scenario():
        nc = await nats_adapter._stream_conn(BUS)
        setattr(
            nc, nats_adapter._STREAM_READY_ATTR, True
        )  # known-ready before the bus restarted
        await nats_adapter.publish(BUS, "s", "test", "phase", "executing")

    asyncio.run(scenario())
    assert js.streams == ["ESTATE_AGENT"]
    assert js.published == ["estate.agent.test.s.phase"]


def test_the_shared_dial_logs_bus_errors_in_one_line(bus):
    _, dials = bus

    asyncio.run(nats_adapter._stream_conn(BUS))
    assert dials[0].get("error_cb") is nats_adapter._log_bus_error, (
        "the default error_cb prints a traceback per reconnect attempt: 277 MB of error log"
    )


def test_an_approval_is_published_from_the_running_loop(bus):
    js, _ = bus

    async def scenario():
        # the adapter's own context: a coroutine already running on the server's loop
        await approvals_adapter._emit_event(
            BUS, nats_adapter, "L1", "approved", {"claim": "c"}, "2026-10-12T00:00:00Z"
        )

    asyncio.run(scenario())
    assert js.published == ["estate.approvals.L1.approved"], (
        "no approval reached estate.approvals.>, the only subject the board's approvals "
        "subscription reads"
    )
    assert js.streams == ["ESTATE_APPROVALS"]

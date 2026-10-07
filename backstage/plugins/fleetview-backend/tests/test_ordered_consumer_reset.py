"""An ordered consumer's reset must send a request the server accepts.

2026-10-07 19:41Z: the bus came back after nats-0's outage and fleetview-backend logged hundreds of
400 err_code=10094 a minute -- "consumer delivery policy is deliver by start sequence, but optional
start time is also set". nats-py 2.16.0 re-creates an ordered consumer from the caller's own
ConsumerConfig, setting BY_START_SEQUENCE + opt_start_seq and leaving opt_start_time. These tests
replay that reset on the config subscribe_stories / subscribe_approvals hand to nats-py and read
the request the server would get.
"""

from __future__ import annotations

import asyncio

import pytest

nats = pytest.importorskip("nats")
from nats.js import api as js_api  # noqa: E402

from fleetview_backend import nats_adapter  # noqa: E402


class _Sub:
    def __init__(self) -> None:
        async def _none():
            return
            yield

        self.messages = _none()


class _JS:
    def __init__(self) -> None:
        self.at_create: dict = {}
        self.config: js_api.ConsumerConfig | None = None

    async def subscribe(self, subject, ordered_consumer=False, config=None, **_):
        assert ordered_consumer
        self.config = config
        self.at_create = config.as_dict()
        return _Sub()


class _NC:
    def __init__(self, js: _JS) -> None:
        self._js = js

    def jetstream(self):
        return self._js

    async def drain(self):
        return None


def _reset_like_nats_py(config: js_api.ConsumerConfig) -> dict:
    # nats/js/client.py 2.16.0, _JSI reset: the same object, mutated, becomes the new request
    config.deliver_subject = "_INBOX.reset"
    config.deliver_policy = js_api.DeliverPolicy.BY_START_SEQUENCE
    config.opt_start_seq = 42
    return config.as_dict()


@pytest.mark.parametrize(
    "subscribe", [nats_adapter.subscribe_stories, nats_adapter.subscribe_approvals]
)
def test_the_consumer_starts_by_time_and_its_reset_sends_no_start_time(
    monkeypatch, subscribe
):
    js = _JS()

    async def connect(*_a, **_k):
        return _NC(js)

    monkeypatch.setattr(nats, "connect", connect)

    async def drive():
        async for _ in subscribe("nats://x:4222"):
            pass

    asyncio.run(drive())

    # created with the "while you were away" replay
    assert js.at_create["deliver_policy"] == "by_start_time"
    assert js.at_create.get("opt_start_time")
    # and a reset is a request the server takes: start sequence without a start time
    req = _reset_like_nats_py(js.config)
    assert req["deliver_policy"] == "by_start_sequence"
    assert "opt_start_time" not in req, (
        "reset request carries opt_start_time with BY_START_SEQUENCE: the server answers "
        "400 err_code=10094 and the ordered consumer never comes back"
    )

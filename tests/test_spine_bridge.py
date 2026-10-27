"""The bridge: the decisions, with no broker in the room.

The fakes are small on purpose: a message that records what was done to it, a JetStream
that holds a key/value bucket, and a signaller that counts. The bridge's logic is the
thing under test; NATS and Temporal are the things that would make it slow.
"""

from __future__ import annotations

import asyncio
import json


from spine.bridge import (
    DUPLICATE,
    RETRIED,
    SIGNALLED,
    TERMINATED,
    Bridge,
    derive_message_id,
)
from spine.contracts import FluxEvent


def event_body(**overrides):
    body = {
        "involvedObject": {
            "kind": "Kustomization",
            "name": "efda",
            "namespace": "flux-system",
            "uid": "uid-1",
            "resourceVersion": "42",
        },
        "severity": "info",
        "timestamp": "2026-10-26T12:00:00Z",
        "message": "Applied revision",
        "reason": "ReconciliationSucceeded",
    }
    body.update(overrides)
    return body


class FakeMsg:
    def __init__(
        self, data, subject="flux.event.kustomization.reconciled.v1", headers=None
    ):
        self.data = (
            data if isinstance(data, bytes) else json.dumps(data).encode("utf-8")
        )
        self.subject = subject
        self.headers = headers or {}
        self.acked = False
        self.nacked = False
        self.termed = False

    async def ack(self):
        self.acked = True

    async def nak(self):
        self.nacked = True

    async def term(self):
        self.termed = True


class FakeKV:
    def __init__(self):
        self.store = {}

    async def get(self, key):
        if key not in self.store:
            raise KeyError(key)
        return self.store[key]

    async def put(self, key, value):
        self.store[key] = value


class FakeJS:
    def __init__(self):
        self.kv = FakeKV()
        self.streams = []
        self.buckets = []

    async def add_stream(self, **kwargs):
        self.streams.append(kwargs)

    async def key_value(self, bucket):
        if bucket not in [b for b, _ttl in self.buckets]:
            raise KeyError(bucket)
        return self.kv

    async def create_key_value(self, bucket, ttl=None):
        self.buckets.append((bucket, ttl))
        return self.kv


class FakeSignaller:
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    async def signal(self, workflow_id, signal_name, payload):
        if self.fail:
            raise RuntimeError("temporal is unreachable")
        self.calls.append((workflow_id, signal_name, payload))


def make_bridge(signaller=None, js=None):
    js = js or FakeJS()
    signaller = signaller or FakeSignaller()
    bridge = Bridge(js, signaller, log=lambda _msg: None)
    # The stream and the dedup store exist before the first message, exactly as the running
    # bridge does before it serves.
    run(bridge.ensure())
    return bridge, js, signaller


def run(coro):
    return asyncio.run(coro)


def test_an_event_with_an_id_is_signalled_and_acked():
    bridge, _js, signaller = make_bridge()
    msg = FakeMsg(event_body(), headers={"Nats-Msg-Id": "msg-1"})
    assert run(bridge.handle(msg)) == SIGNALLED
    assert msg.acked is True
    assert signaller.calls[0][0] == "spine-verify-kustomization-flux-system-efda"
    assert signaller.calls[0][1] == "flux.reconciled"


def test_the_same_event_twice_signals_once():
    bridge, _js, signaller = make_bridge()
    first = FakeMsg(event_body(), headers={"Nats-Msg-Id": "msg-1"})
    second = FakeMsg(event_body(), headers={"Nats-Msg-Id": "msg-1"})
    assert run(bridge.handle(first)) == SIGNALLED
    assert run(bridge.handle(second)) == DUPLICATE
    assert len(signaller.calls) == 1
    assert second.acked is True


def test_an_event_without_an_id_gets_one_derived_from_itself():
    bridge, _js, signaller = make_bridge()
    msg = FakeMsg(event_body())
    assert run(bridge.handle(msg)) == SIGNALLED
    # The derived id is stable: the same body derives the same id, so a redelivery is a
    # duplicate rather than a second signal.
    event = FluxEvent.from_payload(event_body())
    assert derive_message_id(event) == derive_message_id(event)
    again = FakeMsg(event_body())
    assert run(bridge.handle(again)) == DUPLICATE
    assert len(signaller.calls) == 1


def test_a_body_that_cannot_be_parsed_is_terminated_not_dropped():
    bridge, _js, signaller = make_bridge()
    msg = FakeMsg(b"not json at all", headers={"Nats-Msg-Id": "msg-2"})
    assert run(bridge.handle(msg)) == TERMINATED
    assert msg.termed is True
    assert signaller.calls == []


def test_an_event_on_the_wrong_subject_is_terminated():
    bridge, _js, signaller = make_bridge()
    msg = FakeMsg(
        event_body(),
        subject="flux.event.helmrelease.reconciled.v1",
        headers={"Nats-Msg-Id": "msg-3"},
    )
    assert run(bridge.handle(msg)) == TERMINATED
    assert msg.termed is True
    assert signaller.calls == []


def test_a_failed_signal_is_naked_and_not_remembered():
    bridge, _js, _signaller = make_bridge(FakeSignaller(fail=True))
    msg = FakeMsg(event_body(), headers={"Nats-Msg-Id": "msg-4"})
    assert run(bridge.handle(msg)) == RETRIED
    assert msg.nacked is True
    assert msg.acked is False
    # Not remembered: the redelivery has to try again.
    assert run(bridge.seen("msg-4")) is False


def test_the_dedup_record_is_written_after_the_signal():
    order = []

    class OrderedSignaller(FakeSignaller):
        async def signal(self, workflow_id, signal_name, payload):
            order.append("signal")
            await super().signal(workflow_id, signal_name, payload)

    class OrderedKV(FakeKV):
        async def put(self, key, value):
            order.append("dedup")
            await super().put(key, value)

    js = FakeJS()
    js.kv = OrderedKV()
    bridge = Bridge(js, OrderedSignaller(), log=lambda _m: None)
    run(bridge.ensure())
    msg = FakeMsg(event_body(), headers={"Nats-Msg-Id": "msg-5"})
    assert run(bridge.handle(msg)) == SIGNALLED
    assert order == ["signal", "dedup"]


def test_the_bridge_creates_its_stream_and_its_dedup_store():
    js = FakeJS()
    bridge = Bridge(js, FakeSignaller(), log=lambda _m: None)
    run(bridge.ensure())
    assert js.streams and js.streams[0]["subjects"] == ["flux.event.>"]
    assert js.buckets and js.buckets[0][0] == "BRIDGE_DEDUP"

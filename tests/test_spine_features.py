"""The spine's feature, bound to the code that has to satisfy it.

A feature that cannot run is prose. Every sentence here is a step against the real
bridge, the real decisions and the real subject rules -- with the broker and the workflow
engine faked, because the thing under test is the decision, not the wire.
"""

from __future__ import annotations

import json

import pytest
from pytest_bdd import given as _given
from pytest_bdd import parsers
from pytest_bdd import scenarios
from pytest_bdd import then as _then
from pytest_bdd import when as _when

from spine.bridge import Bridge
from spine.contracts import SubjectError, subject_for, validate_subject
from spine.kube import verdict_from_object
from spine.observer import build_receipt, decide, timeout_receipt

scenarios("../features/spine")


def given(text):
    return _given(parsers.parse(text))


def when(text):
    return _when(parsers.parse(text))


def then(text):
    return _then(parsers.parse(text))


class FakeMsg:
    def __init__(self, data, subject, headers=None):
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
    def __init__(self, reachable=True):
        self.calls = []
        self.reachable = reachable

    async def signal(self, workflow_id, signal_name, payload):
        if not self.reachable:
            raise RuntimeError("temporal is unreachable")
        self.calls.append((workflow_id, signal_name, payload))


@pytest.fixture()
def world():
    return {}


def flux_event(name="efda", namespace="flux-system", event_id=None):
    body = {
        "involvedObject": {
            "kind": "Kustomization",
            "name": name,
            "namespace": namespace,
            "uid": "uid-1",
            "resourceVersion": "42",
        },
        "severity": "info",
        "timestamp": "2026-10-26T12:00:00Z",
        "message": "Applied revision",
        "reason": "ReconciliationSucceeded",
    }
    if event_id:
        body["id"] = event_id
    return body


@given('a Provider with type "{provider_type}" and channel "{channel}"')
def _provider(world, provider_type, channel):
    world["provider"] = {"type": provider_type, "channel": channel}


@given('a bridge with a durable consumer on "{subject}"')
def _bridge(world, subject):
    import asyncio

    world["subject"] = subject
    world["signaller"] = FakeSignaller()
    world["bridge"] = Bridge(FakeJS(), world["signaller"], log=lambda _m: None)
    # The stream and the dedup store exist before the first message, as in the running pod.
    asyncio.run(world["bridge"].ensure())


@given('the event "{event_id}" has already been signalled')
def _already(world, event_id):
    import asyncio

    asyncio.run(world["bridge"]._dedup.put(event_id, b"signalled"))


@given("Temporal cannot be reached")
def _unreachable(world):
    world["signaller"].reachable = False


@given('an object "{name}" in "{namespace}" whose reconcile succeeded')
def _succeeded(world, name, namespace):
    world["object"] = {
        "status": {
            "conditions": [
                {"type": "Ready", "status": "True", "reason": "ReconciliationSucceeded"}
            ],
            "lastAppliedRevision": "main@sha1:abc",
            "lastAttemptedRevision": "main@sha1:abc",
        }
    }


@given('an object "{name}" in "{namespace}" whose reconcile failed')
def _failed(world, name, namespace):
    world["object"] = {
        "status": {
            "conditions": [
                {
                    "type": "Ready",
                    "status": "False",
                    "reason": "HealthCheckFailed",
                    "message": "no",
                }
            ]
        }
    }


@given('an object "{name}" in "{namespace}" that no longer exists')
def _missing(world, name, namespace):
    world["object"] = None


@when(
    'Flux publishes a Kustomization reconciliation event for "{name}" in "{namespace}"'
)
def _publish(world, name, namespace):
    # The Provider publishes to the concrete subject; the consumer filters on the wildcard.
    world["msg"] = FakeMsg(flux_event(name, namespace), subject_for("Kustomization"))


@when('Flux publishes a Kustomization reconciliation event with the id "{event_id}"')
def _publish_with_id(world, event_id):
    headers = {"Nats-Msg-Id": event_id}
    world["msg"] = FakeMsg(flux_event(), subject_for("Kustomization"), headers=headers)


@when("a message arrives that carries no parsable event body")
def _garbage(world):
    world["msg"] = FakeMsg(
        b"not an event", subject_for("Kustomization"), headers={"Nats-Msg-Id": "msg-x"}
    )


@when("the spine checks the reconciliation")
def _check(world):
    if world.get("object") is None:
        world["verdict"] = {
            "found": False,
            "ready": False,
            "verdict": "missing",
            "reason": "NotFound",
            "revision": "",
        }
    else:
        world["verdict"] = verdict_from_object(world["object"])
    world["outcome"] = decide(world["verdict"])
    world["receipt"] = build_receipt(flux_event(), world["verdict"], world["outcome"])


def handle_once(world):
    """Run the bridge over the message once, and remember what it decided."""
    import asyncio

    if world.get("decision") is None:
        world["decision"] = asyncio.run(world["bridge"].handle(world["msg"]))
    return world["decision"]


@then('the event is signalled to the workflow "{workflow_id}"')
def _signalled_to(world, workflow_id):
    handle_once(world)
    assert world["signaller"].calls, "nothing was signalled"
    assert world["signaller"].calls[0][0] == workflow_id


@then('the signal name is "{signal_name}"')
def _signal_name(world, signal_name):
    assert world["signaller"].calls[0][1] == signal_name


@then('the subject "{subject}" passes the estate\'s subject rules')
def _subject_ok(world, subject):
    assert validate_subject(subject) == subject


@then('the subject "{subject}" fails the estate\'s subject rules')
def _subject_bad(world, subject):
    with pytest.raises(SubjectError):
        validate_subject(subject)


@then("the bridge does not signal again")
def _not_again(world):
    handle_once(world)
    assert world["signaller"].calls == []


@then("the event is acknowledged")
def _acked(world):
    handle_once(world)
    assert world["msg"].acked is True


@then("the message is terminated")
def _termed(world):
    handle_once(world)
    assert world["msg"].termed is True


@then("nothing is signalled")
def _nothing(world):
    handle_once(world)
    assert world["signaller"].calls == []


@then("the message is negatively acknowledged")
def _nacked(world):
    handle_once(world)
    assert world["msg"].nacked is True


@then("the event is not marked as processed")
def _not_processed(world):
    import asyncio

    handle_once(world)
    assert asyncio.run(world["bridge"].seen("msg-2")) is False


@then('the outcome is "{outcome}"')
def _outcome(world, outcome):
    assert world["outcome"] == outcome


@then('the receipt says the verdict was "{verdict}"')
def _receipt_verdict(world, verdict):
    assert world["receipt"]["verdict"] == verdict


@then('the receipt is routed to "{where}"')
def _routed(world, where):
    body = timeout_receipt({}, 60)
    assert body["detail"]["routedTo"] == where


@then("the receipt carries a digest of its own body")
def _digest(world):
    body = dict(world["receipt"])
    digest = body.pop("digest")
    from spine.contracts import digest_of

    assert digest == digest_of(body)


@then("the receipt is written into the evidence layer")
def _written(world):
    from spine.observer import aevum_body

    payload = aevum_body(world["receipt"])
    assert payload["purpose"]
    assert payload["data"]["digest"] == world["receipt"]["digest"]

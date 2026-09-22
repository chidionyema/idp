"""FleetView CP6: NATS adapter — publish agent events and subscribe to the live stream.

Subjects follow the estate contract: `estate.agent.<runtime>.<session_id>.<kind>` where
kind ∈ phase|tool|wait|done|steer (schema: platform/event-bus/contract/estate.agent.event.json).

Both `publish` and `subscribe_stream` fail loudly when nats-py is not importable — the estate
rule is that a missing required service raises, never silently succeeds (see evals.py, signals.py).

CONFIG (LAW 46): NATS_URL env, default nats://nats.event-bus.svc:4222. The stream's TTL is
NATS_STREAM_MAX_AGE_S, default 900 (15 minutes, matching the outbox's drain-side expiry).
"""

from __future__ import annotations

import datetime as dt
import json
import os
from typing import TYPE_CHECKING, AsyncGenerator

if TYPE_CHECKING:
    pass

_DEFAULT_NATS_URL = "nats://nats.event-bus.svc:4222"

# HOW LONG A PUBLISH MAY SPEND FAILING. nats-py's connect() defaults are built for a long-lived
# service connection -- max_reconnect_attempts=60, reconnect_time_wait=2 -- and those two
# multiply into a 120-second budget before it admits the server is unreachable. `publish` opens
# a connection, sends one event and drains, so it never needs a single retry, and on 2026-09-22
# those defaults cost 123 seconds on EVERY /voice/hear request: a spoken turn measured 127.00s
# with an unreachable NATS_URL against 4.10s with it unset -- same audio, same machine,
# transcript identical both times.
#
# EVERY NUMBER HERE WAS MEASURED, because two plausible diagnoses were wrong first:
#   * Not DNS. NATS_URL pointed at an IP literal with nothing listening -- no name to resolve,
#     TCP refused in microseconds -- still took 131.98s. The cost was never resolution.
#   * Not allow_reconnect. Setting it False left the turn at 122.47s: that flag governs
#     reconnection AFTER a connection is established, not the initial server-selection loop.
# max_reconnect_attempts is the knob that bounds the initial loop, and the total is
# attempts x reconnect_time_wait, which is why 60 x 2s came to exactly the 120s observed.
#
# One attempt and a tenth of a second between tries: a refused port now raises NoServersError in
# 0.39s and an unresolvable name in 0.17s (measured). voice_media.publish turns that into
# {"published": false, "reason": "NoServersError: ..."} -- the same honest refusal, 300x sooner.
# When the bus IS reachable the first attempt succeeds and neither value is ever consulted.
_CONNECT_TIMEOUT_S = float(os.environ.get("NATS_CONNECT_TIMEOUT_S", "2"))
_CONNECT_ATTEMPTS = int(os.environ.get("NATS_CONNECT_ATTEMPTS", "1"))
_RETRY_WAIT_S = float(os.environ.get("NATS_RETRY_WAIT_S", "0.1"))

# THE STREAM, PROVISIONED BY THE FIRST CALLER BECAUSE NOTHING ELSE PROVISIONS IT.
#
# platform/event-bus/nats.yaml provisions a JetStream-CAPABLE server, not streams: the chart has
# no place to declare one, and `js.publish` to a subject no stream covers is not a fire-and-
# forget -- it is a 503 the caller pays for. Until 2026-09-22 no code in the estate created the
# stream either, so every steer worked only where someone had created one by hand on the
# cluster -- configuration that lived in nobody's checkout, which is the state LAW 43 exists
# to prevent. The adapter now creates it lazily and idempotently: the ordinary case is
# "already in use", which is swallowed; every OTHER failure re-raises so js.publish below
# remains the loud boundary (a gate that cannot fail is not a gate).
#
# THE TTL IS 15 MINUTES because a voice intent is perishable: a steer for a session is stale
# by the time a person has repeated themselves, and the outbox that feeds this stream already
# refuses to publish a row older than its own TTL_S = 15 * 60 (outbox.py). The two numbers
# must agree, or the stream would faithfully replay intents the outbox deliberately dropped;
# tests/test_voice_on_the_bus.py grades this stream's max_age against that constant.
#
# CONFIG (LAW 46): NATS_STREAM_MAX_AGE_S (default 900) -- one knob, one default, env-overridable.
_STREAM_NAME = "ESTATE_AGENT"
_STREAM_SUBJECTS = ["estate.agent.>"]
_STREAM_MAX_AGE_S = float(os.environ.get("NATS_STREAM_MAX_AGE_S", str(15 * 60)))


async def _ensure_stream(js) -> None:
    """Create the estate stream if it does not exist; succeed quietly if it does.

    Idempotent by design: every publish and subscribe calls this, and the second call's
    "name already in use" is the normal outcome, not an error. An unexpected failure
    re-raises -- this helper must never turn a broken bus into a silent no-op.
    """
    try:
        await js.add_stream(
            name=_STREAM_NAME,
            subjects=list(_STREAM_SUBJECTS),
            max_age=int(
                _STREAM_MAX_AGE_S * 1_000_000_000
            ),  # JetStream wants nanoseconds
        )
    except Exception as exc:  # noqa: BLE001 -- narrowed below, never swallowed wholesale
        if "already in use" not in str(exc).lower():
            raise


def _nats_url(nats_url: str | None = None) -> str:
    return nats_url or os.environ.get("NATS_URL", _DEFAULT_NATS_URL)


def _require_nats():
    try:
        import nats  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("nats-py not installed") from exc


async def publish(
    nats_url: str,
    session_id: str,
    runtime: str,
    kind: str,
    phase: str,
    **kwargs,
) -> None:
    """Build an estate.agent.event and publish it on JetStream.

    Subject: `estate.agent.<runtime>.<session_id>.<kind>`.
    All keyword arguments are merged into the event payload (e.g. tool, trace_id, needs, steer).
    Raises RuntimeError("nats-py not installed") when nats-py is absent.
    """
    _require_nats()
    import nats

    url = _nats_url(nats_url)
    event: dict = {
        "session_id": session_id,
        "runtime": runtime,
        "kind": kind,
        "at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "phase": phase,
    }
    event.update(kwargs)

    subject = f"estate.agent.{runtime}.{session_id}.{kind}"
    payload = json.dumps(event).encode()

    nc = await nats.connect(
        url,
        connect_timeout=_CONNECT_TIMEOUT_S,
        max_reconnect_attempts=_CONNECT_ATTEMPTS,
        reconnect_time_wait=_RETRY_WAIT_S,
    )
    try:
        js = nc.jetstream()
        await _ensure_stream(js)
        await js.publish(subject, payload)
    finally:
        await nc.drain()


async def subscribe_stream(nats_url: str) -> AsyncGenerator[dict, None]:
    """Subscribe to `estate.agent.>` and yield each decoded JSON message as a dict.

    Raises RuntimeError("nats-py not installed") when nats-py is absent.
    Uses a push subscription on JetStream so the consumer gets the full durable
    replay. Yields control back to the event loop between messages so the SSE
    generator can interleave heartbeats.
    """
    _require_nats()
    import nats

    url = _nats_url(nats_url)
    nc = await nats.connect(url)
    try:
        js = nc.jetstream()
        # The subscriber may be the first caller on a fresh bus; a subscribe with no stream
        # fails the same way a publish does, so both paths provision it.
        await _ensure_stream(js)
        sub = await js.subscribe("estate.agent.>")
        async for msg in sub.messages:
            await msg.ack()
            try:
                yield json.loads(msg.data)
            except (ValueError, UnicodeDecodeError):
                # A malformed message is skipped, not fatal — the board must not
                # go dark because one adapter emitted bad JSON.
                continue
    finally:
        await nc.drain()

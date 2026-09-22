"""FleetView CP6: NATS adapter — publish agent events and subscribe to the live stream.

Subjects follow the estate contract: `estate.agent.<runtime>.<session_id>.<kind>` where
kind ∈ phase|tool|wait|done|steer (schema: platform/event-bus/contract/estate.agent.event.json).

Both `publish` and `subscribe_stream` fail loudly when nats-py is not importable — the estate
rule is that a missing required service raises, never silently succeeds (see evals.py, signals.py).

CONFIG (LAW 46): NATS_URL env, default nats://nats.event-bus.svc:4222.
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

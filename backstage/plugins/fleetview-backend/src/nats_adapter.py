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

    nc = await nats.connect(url)
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

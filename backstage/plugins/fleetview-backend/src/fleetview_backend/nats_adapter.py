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

# The stream the board reads. One stream, one subject family, one schema (the contract).
STREAM_NAME = "ESTATE_AGENT"
STREAM_SUBJECTS = ["estate.agent.>"]
# The 15-minute TTL in nanoseconds, matching outbox.py's TTL_S. The drain side expires a row
# after TTL_S seconds; the stream's max_age is the same span in nanos so the two ends of the
# pipeline agree on what is stale.
STREAM_MAX_AGE_NS = 15 * 60 * 1_000_000_000

# The retry budget a one-shot publish asks of nats-py. The stock defaults
# (max_reconnect_attempts=60, reconnect_time_wait=2) multiply to a 120s worst case a single
# drained connection can never use -- measured 127s on one /voice/hear call for no reason. The
# product of attempts and wait is the real ceiling; keep it tight (<=5s).
CONNECT_MAX_RECONNECT_ATTEMPTS = 2
CONNECT_RECONNECT_TIME_WAIT = 1.0
CONNECT_TIMEOUT = 2.0


async def _ensure_stream(js) -> None:
    """Create the estate-agent stream on first use. Idempotent: a stream that already exists
    raises the server's own 'stream name already in use' (error 10058); that exact refusal is
    swallowed, anything else re-raises. Without this, the first publish to an uncovered subject
    is a 503 NoStreamResponseError and the board's /stream has no durable replay -- the defect
    this function exists to remove.

    Uses the same nats-py JetStream API the outbox drains through, so the stream is provisioned
    by whichever caller publishes first, never a hand-created object that lives in nobody's
    checkout (AGENTS.md: never hand-apply).
    """
    try:
        await js.add_stream(
            name=STREAM_NAME,
            subjects=STREAM_SUBJECTS,
            # nats-py's StreamConfig.max_age is a float in SECONDS on the client, but the
            # server and outbox.py agree on NANOSECONDS. Pass the nano value raw so the
            # recorder's add_stream sees the same number the drain side emits.
            max_age=STREAM_MAX_AGE_NS,
        )
    except Exception as exc:  # noqa: BLE001 — only the 'already exists' refusal is harmless
        # nats-py raises ApiError for a 10058; match on its description rather than the class,
        # because the message text ('stream name already in use') is the stable signal.
        text = str(exc)
        if "already in use" in text or "stream name already in use" in text:
            return
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
        max_reconnect_attempts=CONNECT_MAX_RECONNECT_ATTEMPTS,
        reconnect_time_wait=CONNECT_RECONNECT_TIME_WAIT,
        connect_timeout=CONNECT_TIMEOUT,
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

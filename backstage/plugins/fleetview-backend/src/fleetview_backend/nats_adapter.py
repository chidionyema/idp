"""FleetView CP6: NATS adapter — publish agent events and subscribe to the live stream.

Subjects follow the estate contract: `estate.agent.<runtime>.<session_id>.<kind>` where
kind ∈ phase|tool|wait|done|steer (schema: platform/event-bus/contract/estate.agent.event.json).

Both `publish` and `subscribe_stream` fail loudly when nats-py is not importable — the estate
rule is that a missing required service raises, never silently succeeds (see evals.py, signals.py).

CONFIG (LAW 46): NATS_URL env, default nats://nats.event-bus.svc:4222.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import logging
import os
from typing import TYPE_CHECKING, Any, AsyncGenerator, AsyncIterable, AsyncIterator

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_DEFAULT_NATS_URL = "nats://nats.event-bus.svc:4222"

# The stream the board reads. One stream, one subject family, one schema (the contract).
STREAM_NAME = "ESTATE_AGENT"
STREAM_SUBJECTS = ["estate.agent.>"]
# Core NATS, ephemeral; published by voice-router in VOICE_MODE=director.
CUE_SUBJECT = "estate.cinema.cue"

# The director's news stream. Subjects estate.news.story.<channel>; the stream (ESTATE_NEWS,
# 24h max_age) is created by the director, not here -- subscribe_stories only ever reads it.
STORY_SUBJECTS = "estate.news.story.>"

# Estate streams — created on first use so they survive the bus restarting without hand-apply.
# crew#1013: Agents, News and Approvals streams must exist for FleetView's channels to replay.
ESTATE_NEWS_NAME = "ESTATE_NEWS"
ESTATE_NEWS_SUBJECTS = ["estate.news.story.>"]
ESTATE_APPROVALS_NAME = "ESTATE_APPROVALS"
ESTATE_APPROVALS_SUBJECTS = ["estate.approvals.>"]
STORY_REPLAY_S = 3600
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
    """Create the ESTATE_AGENT stream on first use. Idempotent."""
    await _ensure_stream_by_name(js, STREAM_NAME, STREAM_SUBJECTS)


async def _ensure_stream_by_name(js, name: str, subjects: list[str]) -> None:
    """Create a named JetStream stream on first use. Idempotent: a stream that already exists
    raises the server's own 'stream name already in use' (error 10058); that exact refusal is
    swallowed, anything else re-raises.

    crew#1013: every estate stream is created here, never by hand-apply, so it survives the
    bus restarting without anyone touching a kubectl command.
    """
    try:
        await js.add_stream(name=name, subjects=subjects, max_age=STREAM_MAX_AGE_NS)
    except Exception as exc:  # noqa: BLE001 — only the 'already exists' refusal is harmless
        text = str(exc)
        if "already in use" in text or "stream name already in use" in text:
            return
        raise


async def ensure_estate_streams(nats_url: str) -> None:
    """Ensure all three estate streams exist. Idempotent; safe to call on every startup.

    crew#1013: agents (ESTATE_AGENT), news (ESTATE_NEWS) and approvals (ESTATE_APPROVALS)
    streams must exist for FleetView's channels to replay events that arrived while it was closed.
    """
    _require_nats()
    import nats

    nc = await nats.connect(
        _nats_url(nats_url),
        max_reconnect_attempts=CONNECT_MAX_RECONNECT_ATTEMPTS,
        reconnect_time_wait=CONNECT_RECONNECT_TIME_WAIT,
        connect_timeout=CONNECT_TIMEOUT,
    )
    try:
        js = nc.jetstream()
        await _ensure_stream_by_name(js, STREAM_NAME, STREAM_SUBJECTS)
        await _ensure_stream_by_name(js, ESTATE_NEWS_NAME, ESTATE_NEWS_SUBJECTS)
        await _ensure_stream_by_name(
            js, ESTATE_APPROVALS_NAME, ESTATE_APPROVALS_SUBJECTS
        )
    finally:
        await nc.drain()


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


async def decode_cues(messages: AsyncIterable) -> AsyncGenerator[dict, None]:
    """Decode raw cue messages into validated cue dicts, skipping anything malformed."""
    async for msg in messages:
        try:
            obj = json.loads(msg.data)
        except (ValueError, UnicodeDecodeError, TypeError):
            continue
        if (
            isinstance(obj, dict)
            and isinstance(obj.get("target_id"), str)
            and obj["target_id"]
            and isinstance(obj.get("shot_type"), str)
        ):
            yield obj
        else:
            continue


async def subscribe_cues(nats_url: str) -> AsyncGenerator[dict, None]:
    """Subscribe to `estate.cinema.cue` (core NATS, ephemeral) and yield validated cue dicts.

    Raises RuntimeError("nats-py not installed") when nats-py is absent.
    """
    _require_nats()
    import nats

    nc = await nats.connect(_nats_url(nats_url))
    try:
        sub = await nc.subscribe(CUE_SUBJECT)
        async for cue in decode_cues(sub.messages):
            yield cue
    finally:
        await nc.drain()


async def decode_stories(
    messages: AsyncIterable,
) -> AsyncGenerator[tuple[str, dict], None]:
    """Decode raw story messages into (on, story) pairs, skipping anything malformed.

    `on` is the last token of the message subject (`estate.news.story.<channel>` -> `<channel>`),
    the channel the story actually arrived on -- distinct from the `channel` field inside the
    story payload itself (the director also republishes high-score/breaking stories to `news`).
    """
    async for msg in messages:
        try:
            obj = json.loads(msg.data)
        except (ValueError, UnicodeDecodeError, TypeError):
            continue
        if (
            isinstance(obj, dict)
            and isinstance(obj.get("id"), str)
            and obj["id"]
            and isinstance(obj.get("headline"), str)
            and obj["headline"]
            and isinstance(obj.get("channel"), str)
            and obj["channel"]
            and obj.get("severity") in ("info", "warn", "danger")
        ):
            on = msg.subject.rsplit(".", 1)[-1]
            yield (on, obj)
        else:
            continue


def _forget_start_time(config: Any) -> None:
    """Drop opt_start_time once the ordered consumer exists, so its resets are valid.

    nats-py 2.16.0 keeps the caller's ConsumerConfig as the ordered consumer's re-create request,
    and on a reset (a gap, a reconnect) sets deliver_policy=BY_START_SEQUENCE and opt_start_seq
    but leaves opt_start_time. The server refuses that pair -- 400 err_code=10094 "consumer
    delivery policy is deliver by start sequence, but optional start time is also set" -- and the
    reset is retried forever. Measured 2026-10-07 19:41Z, the minute the bus came back after
    nats-0's outage: hundreds a minute from fleetview-backend, and no stories or approvals on
    /fleet. The start time has done its work by now; the consumer was created with it.
    """
    config.opt_start_time = None


async def subscribe_stories(
    nats_url: str, replay_s: int = STORY_REPLAY_S
) -> AsyncGenerator[tuple[str, dict], None]:
    """Subscribe to `estate.news.story.>` and yield decoded (on, story) pairs.

    An ordered push consumer starting from `now - replay_s` -- the "while you were away"
    rundown on connect. Never creates the ESTATE_NEWS stream; raises when it is absent (the
    caller's isolated() wrapper turns that into a logged, isolated end, not a dead /stream).
    Raises RuntimeError("nats-py not installed") when nats-py is absent.
    """
    _require_nats()
    import nats
    from nats.js import api as js_api

    nc = await nats.connect(_nats_url(nats_url))
    try:
        js = nc.jetstream()
        start_time = dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=replay_s)
        config = js_api.ConsumerConfig(
            deliver_policy=js_api.DeliverPolicy.BY_START_TIME,
            opt_start_time=start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        sub = await js.subscribe(STORY_SUBJECTS, ordered_consumer=True, config=config)
        _forget_start_time(config)
        async for on_story in decode_stories(sub.messages):
            yield on_story
    finally:
        await nc.drain()


async def subscribe_approvals(
    nats_url: str, replay_s: int = 3600
) -> AsyncGenerator[dict, None]:
    """Subscribe to `estate.approvals.>` and yield decoded approval/rejection dicts.

    An ordered push consumer starting from `now - replay_s` -- the "while you were away"
    rundown on connect, so an approval that arrived while FleetView was closed appears
    when it opens (crew#1013).
    Raises when the stream is absent (the caller's isolated() wrapper turns that into a
    logged, isolated end, not a dead /stream).
    Raises RuntimeError("nats-py not installed") when nats-py is absent.
    """
    _require_nats()
    import nats
    from nats.js import api as js_api

    nc = await nats.connect(_nats_url(nats_url))
    try:
        js = nc.jetstream()
        start_time = dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=replay_s)
        config = js_api.ConsumerConfig(
            deliver_policy=js_api.DeliverPolicy.BY_START_TIME,
            opt_start_time=start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        sub = await js.subscribe(
            "estate.approvals.>", ordered_consumer=True, config=config
        )
        _forget_start_time(config)
        async for msg in sub.messages:
            await msg.ack()
            try:
                obj = json.loads(msg.data)
            except (ValueError, UnicodeDecodeError):
                continue
            if isinstance(obj, dict) and obj.get("ledger_id"):
                yield obj
    finally:
        await nc.drain()


async def isolated(name: str, gen: AsyncIterator) -> AsyncGenerator[Any, None]:
    """Iterate `gen`, yielding its items; on any Exception, log one line and return.

    Never raises. This is what lets each /stream source (events, cues, stories) fail on its
    own -- one source's stream not existing must not take the others down with it.
    """
    try:
        async for item in gen:
            yield item
    except Exception as exc:  # noqa: BLE001 -- isolate this source, never the merged stream
        logger.info("fleetview.stream_source_down source=%s err=%s", name, exc)
        return


async def merge(*gens: AsyncIterator) -> AsyncGenerator[Any, None]:
    """Merge multiple async generators into one, interleaving items as they arrive.

    An exception raised by any source generator cancels the rest and re-raises.
    """
    queue: asyncio.Queue = asyncio.Queue()

    async def _drain(gen: AsyncIterator) -> None:
        exc: Exception | None = None
        try:
            async for item in gen:
                await queue.put((False, item))
        except Exception as e:  # noqa: BLE001 — forwarded to the consumer, not swallowed
            exc = e
        finally:
            await queue.put((True, exc))

    tasks = [asyncio.create_task(_drain(gen)) for gen in gens]
    finished = 0
    try:
        while finished < len(tasks):
            is_done, payload = await queue.get()
            if is_done:
                finished += 1
                if payload is not None:
                    for t in tasks:
                        t.cancel()
                    raise payload
                continue
            yield payload
    finally:
        for t in tasks:
            if not t.done():
                t.cancel()

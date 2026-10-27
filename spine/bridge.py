"""The bridge: NATS in, Temporal signals out.

This is the only component in the estate that knows both NATS and Temporal. Every Flux
controller speaks NATS; every agent speaks Temporal; neither leaks into the other's domain.
That is what keeps the seam countable -- one place knows both, so the place is the thing
that gets tested, and either side can be replaced without the other noticing.

The rules, and where each one comes from:

  Nats-Msg-Id is required. An event without one is terminated, not silently dropped: a
  duplicate that cannot be recognised is a duplicate nobody can reason about.

  ...with one measured exception. The notification-controller's NATS provider publishes the
  event body as JSON and sets NO headers at all (read from upstream
  internal/notifier/nats.go: nc.Publish(subject, eventPayload), no header call anywhere in
  the file). So a Flux event arrives with no Nats-Msg-Id, and terminating every one of
  them would answer nothing. The bridge therefore DERIVES the id from the event itself --
  the involved object's uid and resourceVersion, the reason and the timestamp -- which is
  stable across redeliveries, so the dedup still works. The derivation is logged, because a
  publisher that ought to set the id and does not is a fact somebody should see.

  Deduplicate BEFORE the signal, write AFTER it. If the signal fails, the event is not
  marked processed, so the redelivery tries again. The reverse order loses the event.

  A failed signal is NAKed, not terminated. JetStream redelivers up to MAX_DELIVER, and when
  the consumer gives up the estate's own DLQ processor (platform/messaging/dlq) copies the
  original into the dlq subject of the same grammar. The bridge does not write a second
  dead-letter path: one writer per stream, and the DLQ writer already exists.

  A subject that does not match the event it carries is terminated, not absorbed. That is a
  misconfigured Provider, and a misconfiguration that is absorbed is a misconfiguration that
  is never found.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from typing import Any, Callable, Dict, Optional

from .contracts import EventError, FluxEvent

# The file the readiness probe looks for. It is written AFTER the stream exists, because
# the notification-controller publishes into core NATS and a message published to a subject
# with no stream behind it is dropped on the floor. The probe therefore answers "is there
# a stream to receive into", which is the question that matters.
READY_FILE = os.environ.get("SPINE_READY_FILE", "/tmp/spine.ready")  # noqa: S108 - pod-local marker


def derive_message_id(event: FluxEvent) -> str:
    """The id of an event that arrived without one.

    Stable across redeliveries: the same event body always derives the same id, which is
    what the dedup store needs. Flux's event carries the involved object's uid and
    resourceVersion, the reason and the timestamp -- the thing that changed, and when.
    """
    involved = (event.raw or {}).get("involvedObject") or {}
    parts = [
        str(involved.get("uid") or ""),
        str(involved.get("resourceVersion") or ""),
        event.kind,
        event.name,
        event.namespace,
        event.reason,
        event.timestamp,
    ]
    return "flux-" + hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:32]


def _write_ready_file(path: str = READY_FILE) -> None:
    try:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("ready\n")
    except OSError as exc:  # pragma: no cover - a read-only /tmp is a broken pod
        LOG.warning("could not write the ready file %s: %s", path, exc)


LOG = logging.getLogger("spine.bridge")

# The stream the flux events live in. The estate's bus owns the broker; this is one stream
# on it, and the bridge creates it if it is not there (the estate's own consumers do the
# same -- platform/messaging/cmd/epistemic-ingest/main.go ensureStream).
STREAM_NAME = "FLUX_EVENTS"
# The durable consumer. Durable, so a bridge restart resumes where it stopped instead of
# replaying the estate's history.
CONSUMER_NAME = "signal-bridge"
# The idempotency store: message ids already signalled.
DEDUP_BUCKET = "BRIDGE_DEDUP"
# The subject filter: every spine event, and nothing else.
SUBJECT_FILTER = "flux.event.>"
# How long the broker waits for an ack before redelivering.
ACK_WAIT_S = 30
# How many times an event is delivered before the consumer gives up and the estate's DLQ
# processor takes it.
MAX_DELIVER = 5
# The idempotency store keeps ids for a day. A day is long enough that a redelivery inside
# any redelivery window is caught, and short enough that the store does not become a ledger
# nobody prunes.
DEDUP_TTL_S = 24 * 60 * 60

# The stream's own limits, from the founder's build kit and the estate's scale: seven days
# of events, a million messages, a gigabyte, file storage, and a ten-minute duplicate
# window so the broker itself drops a republished copy.
STREAM_CONFIG = {
    "name": STREAM_NAME,
    "subjects": [SUBJECT_FILTER],
    "retention": "limits",
    "max_age": 168 * 3600,
    "max_msgs": 1000000,
    "max_bytes": 1024 * 1024 * 1024,
    "storage": "file",
    "duplicate_window": 600,
    "discard": "old",
}

# The decisions the bridge can reach. They are the words the logs and the tests use, so a
# run can be read without a debugger.
SIGNALLED = "signalled"
DUPLICATE = "duplicate"
TERMINATED = "terminated"
RETRIED = "retried"


class Signaller:
    """What the bridge needs from Temporal. The real one is in spine.signaller."""

    async def signal(
        self, workflow_id: str, signal_name: str, payload: Dict[str, Any]
    ) -> None:
        raise NotImplementedError


class Bridge:
    """Turns Flux events into Temporal signals, exactly once each."""

    def __init__(
        self,
        js: Any,
        signaller: Signaller,
        *,
        log: Callable[[str], None] = LOG.info,
        stream: str = STREAM_NAME,
        consumer: str = CONSUMER_NAME,
        dedup_bucket: str = DEDUP_BUCKET,
        subject_filter: str = SUBJECT_FILTER,
        ack_wait_s: int = ACK_WAIT_S,
        max_deliver: int = MAX_DELIVER,
    ) -> None:
        self.js = js
        self.signaller = signaller
        self.log = log
        self.stream = stream
        self.consumer = consumer
        self.dedup_bucket = dedup_bucket
        self.subject_filter = subject_filter
        self.ack_wait_s = ack_wait_s
        self.max_deliver = max_deliver
        self._dedup: Any = None

    async def ensure(self) -> None:
        """Create the stream and the idempotency store if they are not there."""
        await self.js.add_stream(
            name=self.stream, subjects=list(STREAM_CONFIG["subjects"]), storage="file"
        )
        try:
            self._dedup = await self.js.key_value(self.dedup_bucket)
        except Exception:
            self._dedup = await self.js.create_key_value(
                self.dedup_bucket, ttl=DEDUP_TTL_S
            )

    async def _seen(self, message_id: str) -> bool:
        if self._dedup is None:
            return False
        try:
            await self._dedup.get(message_id)
            return True
        except Exception:
            return False

    async def seen(self, message_id: str) -> bool:
        """True when this id has already been signalled. The dedup store, read."""
        return await self._seen(message_id)

    async def _remember(self, message_id: str) -> None:
        if self._dedup is None:
            return
        await self._dedup.put(message_id, b"signalled")

    async def handle(self, msg: Any) -> str:
        """Handle one message. Returns the decision it reached."""
        headers = dict(getattr(msg, "headers", None) or {})
        message_id = headers.get("Nats-Msg-Id") or headers.get("nats-msg-id") or ""

        try:
            event = FluxEvent.from_payload(msg.data, event_id=message_id)
        except EventError as exc:
            # No id and no parsable body: there is nothing to identify, so there is nothing
            # to deduplicate. Terminated, not dropped -- and said out loud.
            self.log(
                "unidentifiable event on subject=%s: %s"
                % (getattr(msg, "subject", "?"), exc)
            )
            await msg.term()
            return TERMINATED

        if not message_id:
            message_id = derive_message_id(event)
            self.log(
                "no Nats-Msg-Id on %s, derived %s from the event itself"
                % (getattr(msg, "subject", "?"), message_id)
            )
        event = FluxEvent.from_payload(msg.data, event_id=message_id)

        if await self._seen(message_id):
            self.log(
                "duplicate event %s, acking subject=%s"
                % (message_id, getattr(msg, "subject", "?"))
            )
            await msg.ack()
            return DUPLICATE

        if event.subject != getattr(msg, "subject", event.subject):
            # The Provider's channel and the event disagree about what this is. Say so and
            # stop: a mismatched event delivered to the wrong workflow is worse than none.
            self.log(
                "subject mismatch: transport=%s derived=%s event=%s"
                % (getattr(msg, "subject", "?"), event.subject, message_id)
            )
            await msg.term()
            return TERMINATED

        try:
            await self.signaller.signal(
                event.workflow_id, event.signal_name, event.as_payload()
            )
        except Exception as exc:
            # NAK: let the broker redeliver. The event is NOT marked processed, so the retry
            # tries again; after MAX_DELIVER the estate's DLQ processor takes it.
            self.log("signal failed for %s: %s" % (event.workflow_id, exc))
            await msg.nak()
            return RETRIED

        # Write after the success: the dedup record is the receipt of the signal, so it may
        # only exist once the signal exists.
        await self._remember(message_id)
        await msg.ack()
        self.log("signalled %s on %s" % (event.workflow_id, event.signal_name))
        return SIGNALLED

    async def run(self, stop: Optional[asyncio.Event] = None) -> None:
        """Pull messages until stopped. The durable consumer is the state; this is the pump."""
        await self.ensure()
        _write_ready_file()
        sub = await self.js.pull_subscribe(
            self.subject_filter,
            durable=self.consumer,
            stream=self.stream,
            config={
                "ack_wait": self.ack_wait_s,
                "max_deliver": self.max_deliver,
                "filter_subject": self.subject_filter,
            },
        )
        self.log(
            "bridge ready: stream=%s consumer=%s subject=%s"
            % (self.stream, self.consumer, self.subject_filter)
        )
        while stop is None or not stop.is_set():
            try:
                messages = await sub.fetch(1, timeout=1)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                raise
            for msg in messages:
                await self.handle(msg)


def describe() -> str:
    """One line about the wiring, for the pod's readiness log."""
    return json.dumps(
        {
            "stream": STREAM_NAME,
            "consumer": CONSUMER_NAME,
            "subject": SUBJECT_FILTER,
            "ackWaitS": ACK_WAIT_S,
            "maxDeliver": MAX_DELIVER,
        },
        sort_keys=True,
    )

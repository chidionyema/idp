"""The live feed: what the founder watches while a round is running.

The founder's ask (2026-10-23) is that the eval surface report *as the round happens*, not as a
report written afterwards: "the founder surface must monitor evals across the estate in real
time." Two rules from the spec decide this file's shape.

  * No second layer. The estate already has one bus (`estate.agent.>` over JetStream) and one
    surface that reads it (/fleet). So an event is an envelope in *that* shape -- `session_id`,
    `runtime`, `kind`, `at`, `phase` -- and the surface needs no new transport to find it.
  * Proof, not assertion. The envelope is written to a JSONL file under the report directory
    before anything is published, so the file is the record whether or not a bus was reachable,
    and a reader can tell the difference between "the round ran and published" and "the round ran
    and could not publish". A feed that goes quiet because publishing failed is worse than one
    that says it could not publish.

Publishing is best effort and never fatal: an eval must not fail because a bus is down, and a
harness that swallowed its own evidence to keep a connection clean would be the defect this
module exists to avoid.

Env:
  ESTATE_FOUNDER_EVAL_NATS   bus URL to publish to; absent means "record only" (the default on
                            a laptop, which has no route to the in-cluster ClusterIP)
  ESTATE_FOUNDER_EVAL_LIVE   where the JSONL lives (default: reports/live.jsonl by the harness)
"""

from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
from typing import Any

#: The subject family the Fleet surface already reads. One bus, one prefix: a second prefix would
#: be a second routing layer for a feed nobody has to subscribe to twice.
RUNTIME = "founder-agent-eval"
SUBJECT = f"estate.agent.{RUNTIME}"

#: Events kept in the file. A round writes one per task plus a handful of round marks -- a few
#: thousand lines for a huge suite -- and a bounded tail means a long-lived checkout cannot grow
#: the feed without limit.
KEEP = 4000

#: Publish failures already written to the feed, per process. See `emit`.
_REPORTED: set[str] = set()


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def envelope(kind: str, round_id: str, **fields: Any) -> dict[str, Any]:
    """One event, in the shape `estate.agent.<runtime>.<session>.<kind>` already carries."""
    event: dict[str, Any] = {
        "session_id": str(round_id),
        "runtime": RUNTIME,
        "kind": kind,
        "at": _now(),
        "phase": "eval",
    }
    event.update({k: v for k, v in fields.items() if v is not None})
    return event


def subject_for(kind: str, round_id: str = "") -> str:
    """`estate.agent.founder-agent-eval.<round>.<kind>` -- dotted, not colon-split.

    The session id is part of the subject so a single round can be followed on its own, which is
    what the founder's surface does: it opens the round that is running now.
    """
    return f"{SUBJECT}.{round_id or 'round'}.{kind}"


def _trim(path: Path) -> None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return
    if len(lines) <= KEEP:
        return
    path.write_text("\n".join(lines[-KEEP:]) + "\n", encoding="utf-8")


def record(event: dict[str, Any], path: Path) -> None:
    """Append the event to the feed file, bounded. The write happens before any publish."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, default=str) + "\n")
    _trim(path)


def publish(event: dict[str, Any], nats_url: str | None = None) -> dict[str, Any]:
    """Publish one envelope to the estate bus, best effort, and say what happened.

    Returns `{"published": bool, "why": str}`. `nats-py` absent or a bus that refuses the
    connection is a *recorded* outcome, not an exception: the round's own evidence is the file.
    """
    url = (
        nats_url
        if nats_url is not None
        else os.environ.get("ESTATE_FOUNDER_EVAL_NATS", "")
    ).strip()
    if not url:
        return {
            "published": False,
            "why": "no bus configured (ESTATE_FOUNDER_EVAL_NATS unset)",
        }
    try:
        import asyncio

        import nats
    except ImportError as exc:  # pragma: no cover - depends on the host's packages
        return {"published": False, "why": f"nats-py not importable: {exc}"}

    subject = subject_for(
        str(event.get("kind", "event")), str(event.get("session_id", ""))
    )
    payload = json.dumps(event, default=str).encode()

    async def _send() -> None:
        nc = await nats.connect(url, connect_timeout=2, max_reconnect_attempts=0)
        try:
            await nc.publish(subject, payload)
            await nc.flush(timeout=2)
        finally:
            await nc.close()

    try:
        asyncio.run(_send())
    except Exception as exc:  # noqa: BLE001 - a feed may never cost a round
        return {"published": False, "why": f"{type(exc).__name__}: {exc}"}
    return {"published": True, "why": subject}


def emit(kind: str, round_id: str, path: Path, **fields: Any) -> dict[str, Any]:
    """Record one event and try to publish it. Returns the publish outcome for the caller's log."""
    event = envelope(kind, round_id, **fields)
    record(event, path)
    outcome = publish(event)
    if not outcome["published"] and outcome["why"] not in _REPORTED:
        # The feed says it could not publish, in the feed, **once per distinct reason**: a reader of
        # live.jsonl can tell an unconfigured laptop from a dead bus without a second tool, and a
        # round of 200 turns does not write 200 copies of the same line over it.
        _REPORTED.add(outcome["why"])
        record(
            envelope(
                "feed.not_published",
                round_id,
                why=outcome["why"],
                for_kind=kind,
            ),
            path,
        )
    return outcome


def tail(path: Path, limit: int = 200) -> list[dict[str, Any]]:
    """The last `limit` events, newest last. A malformed line is skipped, never fatal."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    out: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out

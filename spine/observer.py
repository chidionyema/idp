"""The spine's decisions, with no I/O in them.

Everything the spine decides is decided here, in plain functions, so it can be graded
offline: the workflow and the bridge are the parts that talk to Temporal and NATS, and they
are thin enough to read.

The decisions are small and total: a verdict becomes an outcome, an outcome becomes a
receipt, and a receipt says what happened to what. There is no fourth case, and a case
that is not in the table is a bug rather than a default.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .contracts import digest_of

# The outcomes.
COMPLETE = "complete"
"""The reconciliation is verified. The workflow is done with this object."""

WAIT = "wait"
"""The reconciliation did not succeed, but the object is there. A later event may."""

GAP = "gap"
"""Something the spine cannot answer: the object is gone, or the status cannot be read.
This is routed to a human, because nobody else can resolve it."""

# The verdicts that mean what they say.
VERIFIED = "verified"
FAILED = "failed"
STALE = "stale"
MISSING = "missing"
UNREADABLE = "unreadable"

# The purpose Aevum records the receipt under. A receipt whose purpose is vague is a
# receipt nobody can query.
RECEIPT_PURPOSE = "spine reconciliation receipt"


def decide(verdict: Dict[str, Any]) -> str:
    """The outcome a verdict leads to."""
    if not verdict:
        return GAP
    name = str(verdict.get("verdict") or "")
    if name == VERIFIED and verdict.get("ready"):
        return COMPLETE
    if name in (FAILED, STALE):
        return WAIT
    if name in (MISSING, UNREADABLE):
        return GAP
    # An unknown verdict is not a pass. It is a gap.
    return GAP


def build_receipt(
    event: Dict[str, Any],
    verdict: Dict[str, Any],
    outcome: str,
    *,
    ingested: bool = True,
    detail: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """The receipt: the event, the verdict, the outcome, and a digest of all of it.

    `ingested` says whether the receipt reached the ledger. A receipt that could not be
    written is not a receipt, so the body says so rather than pretending.
    """
    body = {
        "eventId": str(event.get("eventId") or ""),
        "subject": str(event.get("subject") or ""),
        "kind": str(event.get("kind") or ""),
        "namespace": str(event.get("namespace") or ""),
        "name": str(event.get("name") or ""),
        "reason": str(event.get("reason") or ""),
        "severity": str(event.get("severity") or ""),
        "verdict": str(verdict.get("verdict") or ""),
        "ready": bool(verdict.get("ready")),
        "revision": str(verdict.get("revision") or ""),
        "outcome": outcome,
        "ingested": bool(ingested),
        "detail": detail or {},
    }
    body["digest"] = digest_of(body)
    return body


def timeout_receipt(target: Dict[str, Any], wait_seconds: int) -> Dict[str, Any]:
    """The receipt for a wait that ended with no event at all.

    The build kit calls this "deployment_timeout": the workflow waited for an event and
    none came. The gap is routed to a human, because a timeout nobody reads is a timeout
    that changes nothing.
    """
    body = {
        "eventId": "",
        "subject": "",
        "kind": str(target.get("kind") or ""),
        "namespace": str(target.get("namespace") or ""),
        "name": str(target.get("name") or ""),
        "reason": "NoEvent",
        "severity": "error",
        "verdict": MISSING,
        "ready": False,
        "revision": "",
        "outcome": GAP,
        "ingested": False,
        "detail": {"waitedSeconds": wait_seconds, "routedTo": "human_review"},
    }
    body["digest"] = digest_of(body)
    return body


def aevum_body(receipt: Dict[str, Any]) -> Dict[str, Any]:
    """The shape Aevum's /v1/ingest wants (aevum-server 0.9.0, routes/data.py)."""
    return {
        "data": receipt,
        "provenance": {
            "source": "spine",
            "subject": receipt.get("subject", ""),
            "eventId": receipt.get("eventId", ""),
            "digest": receipt.get("digest", ""),
        },
        "purpose": RECEIPT_PURPOSE,
        "subject_id": receipt.get("subject") or receipt.get("digest", ""),
    }

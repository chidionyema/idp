"""The contracts the spine speaks: the Flux event, the subject it travels on, the receipt.

The subject grammar is the estate's, not this module's: D1 of ADR 0012, five lower-case
tokens {domain}.{kind}.{aggregate}.{action}.{version}, implemented in Go at
platform/messaging/subject/subject.go. The spine is a PRODUCER, so it needs the check in
Python to fail a bad subject before it is published -- and to fail it the same way the Go
package would. tests/test_spine_contracts.py reads the Go source and asserts the two still
agree, so the mirror cannot drift away from the thing it mirrors.

The founder's build kit proposed the subject `evt.flux.kustomization.reconciled`. That is
not a D1 subject: it is four tokens, the kind is `evt` (D1 admits event, command, dlq), the
action `reconciled` sits in the aggregate slot, and there is no version. The spine therefore
publishes `flux.event.kustomization.reconciled.v1`, and the review in
docs/specs/2026-10-26-efda-spine.md says why the change was made rather than made silently.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

# D1: the domain every spine subject lives in.
DOMAIN = "flux"
# D1: the version token. A new meaning is a new subject, never a new field.
SUBJECT_VERSION = "v1"
# The kind token, per D1.
KIND = "event"
# The action token: the event happened, so the action is past tense (D1-past-tense).
ACTION = "reconciled"
# The signal every reconcile event raises. One name, not one per kind and reason: the event
# body carries the kind and the reason, and a channel per reason would multiply the channels
# without adding a single bit of information.
SIGNAL_NAME = "flux.reconciled"

# D1-shape: five tokens. D1-case: lower-case token. D1-version: v1, v2, ...
_TOKEN = re.compile(r"^[a-z][a-z0-9_]*$")
_VERSION = re.compile(r"^v[1-9][0-9]*$")
# D1-kind: event, command, dlq.
_KINDS = ("event", "command", "dlq")
# D1-no-environment: an environment or a region is never part of a subject.
_FORBIDDEN = ("prod", "production", "staging", "dev", "test", "eu", "us", "uk")


class EventError(ValueError):
    """The payload is not a Flux event this spine can route."""


class SubjectError(ValueError):
    """The subject breaks the estate's D1 grammar."""


def validate_subject(raw: str) -> str:
    """Grade a subject against D1 and name the rule it broke.

    The rules and their names are the Go package's (platform/messaging/subject/subject.go);
    the test that keeps this mirror honest is tests/test_spine_contracts.py.
    """
    parts = raw.split(".")
    if len(parts) != 5:
        raise SubjectError(
            "rule D1-shape: five tokens {domain}.{kind}.{aggregate}.{action}.{version}, got %d"
            % len(parts)
        )
    for token in parts[:4]:
        if not _TOKEN.match(token):
            raise SubjectError(
                "rule D1-case: token %r must be lower-case [a-z][a-z0-9_]*" % token
            )
    if parts[0] in _FORBIDDEN:
        raise SubjectError(
            "rule D1-no-environment: %r is an environment or region" % parts[0]
        )
    if parts[1] not in _KINDS:
        raise SubjectError(
            "rule D1-kind: kind %r must be event, command or dlq" % parts[1]
        )
    if not parts[3].endswith("ed") and parts[1] == "event":
        raise SubjectError(
            "rule D1-past-tense: an event action is past tense, got %r" % parts[3]
        )
    if not _VERSION.match(parts[4]):
        raise SubjectError("rule D1-version: version %r must be v1, v2, ..." % parts[4])
    return raw


def digest_of(payload: Any) -> str:
    """The content digest of a payload: sha256 over the canonical JSON form.

    Canonical means sorted keys and no spaces, so two writers that agree on the content
    agree on the digest, whatever order they built the dict in.
    """
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class FluxEvent:
    """One reconcile event, as the notification-controller publishes it.

    The notification-controller's v1beta3 event body is
    {involvedObject{kind,name,namespace,apiVersion,uid}, severity, timestamp, message,
    reason, metadata, reportingController, reportingInstance}. The founder's build kit
    described the same shape in its Go struct, and the estate's own flux-events workflow
    already reads these bodies (the SIGNATURE_JQ in .github/workflows/flux-events.yml).
    """

    kind: str
    name: str
    namespace: str
    reason: str
    severity: str
    message: str
    timestamp: str
    event_id: str
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: Any, event_id: str = "") -> "FluxEvent":
        """Parse a Flux event body. Raises EventError when the body cannot be routed."""
        if isinstance(payload, (bytes, bytearray)):
            try:
                payload = payload.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise EventError("event body is not utf-8: %s" % exc) from exc
        if isinstance(payload, str):
            try:
                body = json.loads(payload)
            except ValueError as exc:
                raise EventError("event body is not JSON: %s" % exc) from exc
        elif isinstance(payload, dict):
            body = payload
        else:
            raise EventError("event body is neither JSON text nor a mapping")
        if not isinstance(body, dict):
            raise EventError("event body is not an object")

        involved = body.get("involvedObject") or {}
        if not isinstance(involved, dict):
            raise EventError("involvedObject is not an object")
        kind = str(involved.get("kind") or "").strip()
        name = str(involved.get("name") or "").strip()
        namespace = str(involved.get("namespace") or "").strip()
        reason = str(body.get("reason") or "").strip()
        for label, value in (
            ("kind", kind),
            ("name", name),
            ("namespace", namespace),
            ("reason", reason),
        ):
            if not value:
                raise EventError("event has no %s" % label)
        return cls(
            kind=kind,
            name=name,
            namespace=namespace,
            reason=reason,
            severity=str(body.get("severity") or "info"),
            message=str(body.get("message") or ""),
            timestamp=str(body.get("timestamp") or ""),
            event_id=str(event_id or body.get("id") or ""),
            raw=body,
        )

    @property
    def aggregate(self) -> str:
        """The D1 aggregate token: the kind, lower-cased (kustomization, helmrelease)."""
        return self.kind.lower()

    @property
    def subject(self) -> str:
        """The D1 subject this event travels on."""
        return "%s.%s.%s.%s.%s" % (
            DOMAIN,
            KIND,
            self.aggregate,
            ACTION,
            SUBJECT_VERSION,
        )

    @property
    def workflow_id(self) -> str:
        """The workflow this event wakes.

        One workflow per reconciled object, so a second event for the same object reaches a
        workflow that is already waiting rather than starting a second one.
        """
        return "spine-verify-%s-%s-%s" % (self.aggregate, self.namespace, self.name)

    @property
    def signal_name(self) -> str:
        return SIGNAL_NAME

    @property
    def failed(self) -> bool:
        """True when the event says the reconciliation did not succeed."""
        return self.severity == "error" or "failed" in self.reason.lower()

    def as_payload(self) -> Dict[str, Any]:
        """The body the bridge signals with: the event, not a summary of it."""
        return {
            "eventId": self.event_id,
            "kind": self.kind,
            "name": self.name,
            "namespace": self.namespace,
            "reason": self.reason,
            "severity": self.severity,
            "message": self.message,
            "timestamp": self.timestamp,
            "subject": self.subject,
        }


def subject_for(kind: str) -> str:
    """The subject a Flux kind travels on."""
    return validate_subject(
        "%s.%s.%s.%s.%s" % (DOMAIN, KIND, str(kind).lower(), ACTION, SUBJECT_VERSION)
    )


def receipt(
    event: FluxEvent,
    verdict: str,
    *,
    detail: Optional[Dict[str, Any]] = None,
    outcome: str = "reconciliation_verified",
) -> Dict[str, Any]:
    """The receipt the spine leaves when it has checked a reconciliation.

    A receipt is a claim somebody else can check, so it carries the event it came from, the
    verdict, the observation the verdict was drawn from, and a digest of all of it.
    """
    body = {
        "eventId": event.event_id,
        "subject": event.subject,
        "kind": event.kind,
        "namespace": event.namespace,
        "name": event.name,
        "reason": event.reason,
        "verdict": verdict,
        "outcome": outcome,
        "detail": detail or {},
        "recordedAt": event.timestamp,
    }
    body["digest"] = digest_of(body)
    return body

"""Estate memory + topology context ACK admission, using existing estate-graph.

This is only a verifier for control-plane-signed delivery evidence, not a
source of context, a new graph, a new certifier or an execution authorization.
Expected values MUST be obtained from the independently authenticated broker,
never from model-supplied fields. DoF and existing effect doors remain binding.
"""
from __future__ import annotations
import base64
import hashlib
import json
import re
import time
from dataclasses import dataclass

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

SCHEMA = "genesis.context-delivery.v1"
HEX40 = re.compile(r"^[a-f0-9]{40}$")
HEX64 = re.compile(r"^[a-f0-9]{64}$")
FIELDS = frozenset({
    "schema", "source", "actor", "mission", "session", "lease_epoch",
    "sequence", "memory_sha256", "topology_sha256", "source_commit",
    "source_observed_at", "issued_at", "acknowledged_at", "expires_at", "readiness",
})


@dataclass(frozen=True)
class Decision:
    admitted: bool
    reason: str
    receipt_digest: str = ""


def _deny(reason):
    return Decision(False, reason)


def canonical(payload: dict) -> bytes:
    """ASCII, integer-time, sorted-key canonical JSON; not general-purpose JCS."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def verify(envelope: bytes, *, public_key: bytes, actor: str, mission: str,
           session: str, epoch: int, min_sequence: int,
           memory_sha256: str, topology_sha256: str, source_commit: str,
           now: int | None = None) -> Decision:
    """Require an authenticated, fresh, version-bound receipt before any effect."""
    now = int(time.time()) if now is None else now
    if not isinstance(envelope, bytes) or not 0 < len(envelope) <= 16384:
        return _deny("CONTEXT_RECEIPT_UNAVAILABLE")
    if not isinstance(public_key, bytes) or len(public_key) != 32:
        return _deny("CONTEXT_CERTIFIER_UNAVAILABLE")
    if (type(epoch) is not int or epoch < 1 or
            type(min_sequence) is not int or min_sequence < 1 or
            type(now) is not int or now < 0):
        return _deny("INVALID_BROKER_PARAMETERS")
    if not all(isinstance(x, str) and 0 < len(x) <= 128
               for x in (actor, mission, session)):
        return _deny("BROKER_IDENTITY_MISSING")
    if not all(isinstance(x, str) and HEX64.fullmatch(x)
               for x in (memory_sha256, topology_sha256)):
        return _deny("UNTRUSTED_BROKER_DIGEST")
    if not isinstance(source_commit, str) or not HEX40.fullmatch(source_commit):
        return _deny("UNTRUSTED_BROKER_SOURCE")
    try:
        outer = json.loads(envelope)
        if not isinstance(outer, dict) or set(outer) != {
                "format", "payload_b64", "signature_b64"}:
            return _deny("MALFORMED_CONTEXT_ENVELOPE")
        if outer["format"] != "genesis.context.ed25519.v1":
            return _deny("UNTRUSTED_CONTEXT_FORMAT")
        raw = base64.b64decode(outer["payload_b64"], validate=True)
        sig = base64.b64decode(outer["signature_b64"], validate=True)
        if not 0 < len(raw) <= 16384 or len(sig) != 64:
            return _deny("CONTEXT_PROOF_SHAPE_INVALID")
        Ed25519PublicKey.from_public_bytes(public_key).verify(sig, raw)
        payload = json.loads(raw)
        if (not isinstance(payload, dict) or set(payload) != FIELDS
                or canonical(payload) != raw):
            return _deny("NONCANONICAL_CONTEXT")
    except Exception:
        return _deny("CONTEXT_SIGNATURE_UNVERIFIED")
    if payload["schema"] != SCHEMA or payload["source"] != "estate-graph":
        return _deny("WRONG_CONTEXT_AUTHORITY")
    if (payload["actor"], payload["mission"], payload["session"]) != (
            actor, mission, session):
        return _deny("CONTEXT_ACK_WRONG_AGENT_OR_MISSION")
    if type(payload["lease_epoch"]) is not int or payload["lease_epoch"] != epoch:
        return _deny("CONTEXT_LEASE_STALE")
    if (payload["memory_sha256"] != memory_sha256 or
            payload["topology_sha256"] != topology_sha256 or
            payload["source_commit"] != source_commit):
        return _deny("CONTEXT_CHANGED_SINCE_ACK")
    if payload["readiness"] != "STRICT_READY":
        return _deny("ESTATE_GRAPH_NOT_READY")
    keys = ("sequence", "source_observed_at", "issued_at",
            "acknowledged_at", "expires_at")
    if any(type(payload[k]) is not int or payload[k] < 0 for k in keys):
        return _deny("INVALID_DELIVERY_SEQUENCE_OR_TIME")
    if payload["sequence"] < min_sequence:
        return _deny("CONTEXT_ACK_REPLAY")
    observed, issued, ack, expiry = (payload[k] for k in keys[1:])
    if max(observed, issued, ack) > now + 10:
        return _deny("CONTEXT_RECEIPT_FROM_FUTURE")
    if (not observed <= issued <= ack <= expiry or
            now - observed > 120 or now - issued > 120):
        return _deny("CONTEXT_STALE_OR_OUT_OF_ORDER")
    if expiry <= now or expiry - issued > 120:
        return _deny("CONTEXT_ACK_EXPIRED")
    return Decision(True, "CONTEXT_ACK_VERIFIED", hashlib.sha256(raw).hexdigest())

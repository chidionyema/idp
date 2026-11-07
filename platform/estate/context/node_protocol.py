"""Executable admission rules for disconnected estate surfaces."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping


class ProtocolError(ValueError):
    """The envelope or operation is not admissible under this protocol."""


PROTOCOL = json.loads(Path(__file__).with_name("node_protocol.json").read_text())
RULES_HASH = hashlib.sha256(
    json.dumps(
        PROTOCOL["rules"],
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
).hexdigest()
PROTOCOL_VERSION = PROTOCOL["version"]
CONNECTIVITY = ("online", "offline")
REQUIRED = tuple(PROTOCOL["requiredEnvelopeFields"])
MUTATION_REQUIRED = tuple(PROTOCOL["mutationEnvelopeFields"])
OFFLINE_QUEUE_ALLOWED = frozenset(PROTOCOL["offlineQueueAllowed"])


def _present(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    return value is not None


def _validate_envelope(envelope: Mapping[str, Any]) -> bool:
    for field in REQUIRED:
        if field not in envelope:
            raise ProtocolError(f"envelope is missing {field}")
        value = envelope[field]
        if field == "capabilities":
            if (
                not isinstance(value, list)
                or not value
                or any(not isinstance(item, str) or not item.strip() for item in value)
            ):
                raise ProtocolError(
                    "envelope capabilities must be a non-empty list of names"
                )
        elif field == "cursor":
            if not isinstance(value, dict):
                raise ProtocolError("envelope cursor must be an object")
            offset = value.get("offset")
            if not isinstance(offset, int) or offset < 0:
                raise ProtocolError(
                    "envelope cursor.offset must be a non-negative integer"
                )
            if not value.get("eventId") and offset != 0:
                raise ProtocolError("envelope cursor needs eventId after offset zero")
        elif not _present(value):
            raise ProtocolError(f"envelope is missing {field}")

    return (
        envelope.get("protocolVersion") == PROTOCOL_VERSION
        and envelope.get("rulesHash") == RULES_HASH
    )


def _validate_operation(operation: Mapping[str, Any]) -> tuple[str, bool, bool]:
    name = operation.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ProtocolError("operation name is required")
    mutating = operation.get("mutating")
    offline_safe = operation.get("offlineSafe")
    if not isinstance(mutating, bool) or not isinstance(offline_safe, bool):
        raise ProtocolError("operation mutating and offlineSafe must be booleans")
    return name, mutating, offline_safe


def evaluate_operation(
    envelope: Mapping[str, Any],
    operation: Mapping[str, Any],
    *,
    connectivity: str,
) -> dict[str, Any]:
    """Admit or refuse one operation for one disconnected-surface envelope."""
    if connectivity not in CONNECTIVITY:
        raise ProtocolError(f"connectivity must be one of {CONNECTIVITY}")
    compatible = _validate_envelope(envelope)
    name, mutating, offline_safe = _validate_operation(operation)

    if not compatible:
        if mutating:
            raise ProtocolError(
                "incompatible protocol rules are read-only; mutation refused"
            )
        return {
            "allowed": True,
            "mode": "read_only",
            "receiptRequired": False,
            "reason": "incompatible protocol rules permit reads only",
        }

    if connectivity == "offline":
        if not mutating:
            return {
                "allowed": True,
                "mode": "offline_read",
                "receiptRequired": False,
                "reason": "read served from the node's signed snapshot",
            }
        if not offline_safe or name not in OFFLINE_QUEUE_ALLOWED:
            raise ProtocolError(
                f"offline mutation {name!r} is not approved for queued execution"
            )
        if not _present(envelope.get("idempotencyKey")):
            raise ProtocolError("offline mutation requires idempotencyKey")
        return {
            "allowed": True,
            "mode": "offline_queue",
            "receiptRequired": True,
            "reason": "offline-safe command queued for reconciliation",
        }

    if not mutating:
        return {
            "allowed": True,
            "mode": "online",
            "receiptRequired": False,
            "reason": "online read admitted",
        }

    missing = [field for field in MUTATION_REQUIRED if not _present(envelope.get(field))]
    if missing:
        raise ProtocolError("online mutation requires " + ", ".join(missing))
    return {
        "allowed": True,
        "mode": "online",
        "receiptRequired": True,
        "reason": "leased, context-bound mutation admitted",
    }


def guarded_execute(
    envelope: Mapping[str, Any],
    operation: Mapping[str, Any],
    *,
    connectivity: str,
    execute: Callable[[dict[str, Any]], Any],
) -> dict[str, Any]:
    """Admit an operation before invoking it and enforce the receipt contract."""
    decision = evaluate_operation(
        envelope,
        operation,
        connectivity=connectivity,
    )
    result = execute(decision)
    if decision["receiptRequired"]:
        if not isinstance(result, dict) or not isinstance(result.get("receipt"), dict):
            raise ProtocolError("accepted mutation returned no receipt object")
    return {"decision": decision, "result": result}

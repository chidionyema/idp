"""The disconnected-node admission contract, pinned by refusal."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "platform"))

from estate.context.node_protocol import (  # noqa: E402
    ProtocolError,
    RULES_HASH,
    evaluate_operation,
    guarded_execute,
)


EXPECTED_RULES_HASH = "18e3ccdaee2a0cceff3ad85c777ddfe7b33255694844b6925a4d331b29a9f3dd"
SCHEMA = json.loads(
    (
        __import__("pathlib").Path(__file__).parents[1]
        / "platform/estate/context/node-protocol.schema.json"
    ).read_text()
)
CLI = (
    __import__("pathlib").Path(__file__).parents[1]
    / "platform/estate/context/estate-node-protocol"
)


def envelope():
    return {
        "protocolVersion": "estate.node-protocol.v1",
        "rulesHash": RULES_HASH,
        "nodeId": "node-web-1",
        "sessionId": "session-123",
        "surface": "web",
        "capabilities": ["context.read"],
        "cursor": {"eventId": "evt-100", "offset": 100},
        "leaseId": None,
        "contextPlanHash": None,
        "idempotencyKey": None,
    }


def test_protocol_rules_are_hash_pinned():
    assert RULES_HASH == EXPECTED_RULES_HASH


def test_cross_language_schema_requires_the_runtime_envelope_fields():
    from estate.context.node_protocol import REQUIRED

    assert tuple(SCHEMA["required"]) == REQUIRED


def test_online_mutation_requires_a_lease_context_plan_and_idempotency():
    with pytest.raises(ProtocolError, match="lease"):
        evaluate_operation(
            envelope(),
            {"name": "memory.write", "mutating": True, "offlineSafe": False},
            connectivity="online",
        )

    command = envelope()
    command.update(
        leaseId="lease-1",
        contextPlanHash="plan-1",
        idempotencyKey="command-1",
    )
    result = evaluate_operation(
        command,
        {"name": "memory.write", "mutating": True, "offlineSafe": False},
        connectivity="online",
    )
    assert result["allowed"] is True
    assert result["receiptRequired"] is True
    assert result["mode"] == "online"


def test_disconnected_safe_mobile_command_is_queued_without_a_lease():
    disconnected = envelope()
    disconnected["surface"] = "mobile"
    disconnected["idempotencyKey"] = "mobile-command-1"
    result = evaluate_operation(
        disconnected,
        {"name": "back", "mutating": True, "offlineSafe": True},
        connectivity="offline",
    )
    assert result == {
        "allowed": True,
        "mode": "offline_queue",
        "receiptRequired": True,
        "reason": "offline-safe command queued for reconciliation",
    }


def test_disconnected_unsafe_mutation_is_refused():
    with pytest.raises(ProtocolError, match="offline"):
        evaluate_operation(
            {**envelope(), "idempotencyKey": "command-2"},
            {"name": "secret.rotate", "mutating": True, "offlineSafe": False},
            connectivity="offline",
        )


def test_unknown_rules_version_can_read_but_cannot_mutate():
    stale = envelope()
    stale["rulesHash"] = "0" * 64

    read = evaluate_operation(
        stale,
        {"name": "context.read", "mutating": False, "offlineSafe": True},
        connectivity="online",
    )
    assert read["allowed"] is True
    assert read["mode"] == "read_only"

    with pytest.raises(ProtocolError, match="read-only"):
        evaluate_operation(
            stale,
            {"name": "memory.write", "mutating": True, "offlineSafe": False},
            connectivity="online",
        )


def test_every_envelope_requires_identity_cursor_and_capability_scope():
    for field in ("nodeId", "sessionId", "surface", "cursor", "capabilities"):
        broken = copy.deepcopy(envelope())
        broken.pop(field)
        with pytest.raises(ProtocolError, match=field):
            evaluate_operation(
                broken,
                {"name": "context.read", "mutating": False, "offlineSafe": True},
                connectivity="online",
            )


def test_cli_returns_a_machine_readable_admission():
    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--connectivity",
            "online",
            "--action",
            "context.read",
        ],
        input=json.dumps(envelope()),
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    decision = json.loads(result.stdout)
    assert decision["allowed"] is True
    assert decision["mode"] == "online"


def test_cli_refuses_an_unsafe_offline_mutation():
    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--connectivity",
            "offline",
            "--action",
            "secret.rotate",
            "--mutating",
        ],
        input=json.dumps(envelope()),
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 1
    assert "offline mutation" in result.stderr


def test_guarded_execute_never_calls_a_refused_capability():
    calls = []
    with pytest.raises(ProtocolError, match="lease"):
        guarded_execute(
            envelope(),
            {"name": "memory.write", "mutating": True, "offlineSafe": False},
            connectivity="online",
            execute=lambda _decision: calls.append("called"),
        )
    assert calls == []


def test_guarded_execute_requires_a_receipt_from_a_mutation():
    command = envelope()
    command.update(
        leaseId="lease-1",
        contextPlanHash="plan-1",
        idempotencyKey="command-1",
    )
    with pytest.raises(ProtocolError, match="receipt"):
        guarded_execute(
            command,
            {"name": "memory.write", "mutating": True, "offlineSafe": False},
            connectivity="online",
            execute=lambda _decision: {"ok": True},
        )

    result = guarded_execute(
        command,
        {"name": "memory.write", "mutating": True, "offlineSafe": False},
        connectivity="online",
        execute=lambda _decision: {"ok": True, "receipt": {"id": "receipt-1"}},
    )
    assert result["decision"]["receiptRequired"] is True
    assert result["result"]["receipt"]["id"] == "receipt-1"

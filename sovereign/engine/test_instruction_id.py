"""FLOW admission uses Argon's instruction_id in IDP's EXISTING Temporal durable store.

These tests exercise a real asynchronous caller and a fake unique-ID Temporal
server. They never claim the production Temporal server is reachable.
"""
from __future__ import annotations

import asyncio
import sys
import types
from pathlib import Path

import pytest

from sovereign.engine import client as engine_client


class FakeTemporal:
    def __init__(self) -> None:
        self.accepted: dict[str, tuple] = {}
        self.calls: list[dict] = []

    async def start_workflow(self, workflow, params, **kwargs):
        self.calls.append(dict(kwargs))
        workflow_id = kwargs["id"]
        if workflow_id in self.accepted:
            raise RuntimeError("Temporal WorkflowExecutionAlreadyStarted: duplicate")
        self.accepted[workflow_id] = (workflow, params, kwargs)
        return object()


@pytest.fixture()
def temporal(monkeypatch):
    fake = FakeTemporal()

    async def connect():
        return fake

    monkeypatch.setattr(engine_client, "get_client", connect)
    # The pinned SDK owns the real enum; tests stub only the engine boundary.
    # Real workflow replay and server-side ID uniqueness require remote canary.
    common = types.ModuleType("temporalio.common")

    class Reuse:
        REJECT_DUPLICATE = "reject-duplicate"

    common.WorkflowIDReusePolicy = Reuse
    monkeypatch.setitem(sys.modules, "temporalio.common", common)
    return fake


def test_argon_instruction_id_is_temporal_workflow_id(temporal):
    result = asyncio.run(
        engine_client.start(
            "ship real Genesis canary",
            runner="gemini",
            by="genesis",
            instruction_id="INS-00011",
            critical=True,
        )
    )
    assert result == {
        "session_id": "INS-00011",
        "instruction_id": "INS-00011",
        "state": "TEMPORAL_ACCEPTED_UNVERIFIED",
    }
    assert len(temporal.accepted) == 1
    workflow, params, options = temporal.accepted["INS-00011"]
    assert workflow == engine_client.WORKFLOW
    assert params["session_id"] == "INS-00011"
    assert params["instruction_id"] == "INS-00011"
    assert params["task"] == "ship real Genesis canary"
    assert options["id_reuse_policy"] == "reject-duplicate"
    assert options["memo"]["instruction_id"] == "INS-00011"
    assert len(options["memo"]["instruction_fingerprint"]) == 64


def test_retry_after_completion_still_cannot_start_second_worker(temporal):
    args = dict(
        task="deliver founder surface",
        by="founder",
        instruction_id="I-0045",
    )
    asyncio.run(engine_client.start(**args))
    with pytest.raises(RuntimeError, match="AlreadyStarted"):
        asyncio.run(engine_client.start(**args))
    assert len(temporal.accepted) == 1
    assert len(temporal.calls) == 2
    assert all(
        call["id_reuse_policy"] == "reject-duplicate" for call in temporal.calls
    )


def test_changed_payload_same_id_is_not_a_second_execution(temporal):
    asyncio.run(engine_client.start(
        task="first authorized work", instruction_id="GEN-123", by="telegram"
    ))
    with pytest.raises(RuntimeError, match="AlreadyStarted"):
        asyncio.run(engine_client.start(
            task="different work under the same ID",
            instruction_id="GEN-123",
            by="telegram",
        ))
    assert len(temporal.accepted) == 1
    original = temporal.accepted["GEN-123"][1]
    assert original["task"] == "first authorized work"


@pytest.mark.parametrize("bad", [
    "", "A", "AA", "bad/id", "bad id", "ID:001",
    "x" * 101, "a\nmalicious", None,
])
def test_invalid_instruction_id_never_contacts_temporal(temporal, bad):
    with pytest.raises(ValueError, match="instruction_id"):
        asyncio.run(engine_client.start(
            "task", instruction_id=bad, by="founder"
        ))
    assert temporal.calls == []


def test_founder_and_telegram_cannot_silently_generate_session_id(temporal):
    for by in ("founder", "genesis", "telegram"):
        with pytest.raises(ValueError, match="stable instruction_id"):
            asyncio.run(engine_client.start("task", by=by))
    assert temporal.calls == []


def test_no_empty_instruction_is_accepted(temporal):
    with pytest.raises(ValueError, match="empty task"):
        asyncio.run(engine_client.start(
            "", by="founder", instruction_id="INS-EMPTY-001"
        ))
    assert temporal.calls == []


def test_legacy_adhoc_sessions_remain_compatible(temporal):
    result = asyncio.run(engine_client.start("investigate", by="cli"))
    assert result["session_id"].startswith("sb-")
    assert result.get("instruction_id") is None
    assert temporal.calls[0]["id"] == result["session_id"]
    assert "id_reuse_policy" not in temporal.calls[0]


def test_fingerprint_is_payload_sensitive_without_exposing_prompt():
    fingerprint = engine_client._instruction_fingerprint
    x = fingerprint("INS-42", task="A", by="founder", runner="echo",
                    repo=None, budget=10, critical=False)
    y = fingerprint("INS-42", task="B", by="founder", runner="echo",
                    repo=None, budget=10, critical=False)
    assert x != y
    assert len(x) == 64
    assert "A" not in x


def test_founder_readback_uses_instruction_id_instead_of_session_guess():
    row = {
        "session_id": "INS-00011",
        "instruction_id": "INS-00011",
        "task": "real work",
        "status": "running",
    }
    assert engine_client._to_row(row, "INS-00011")["instruction_id"] == "INS-00011"
    assert engine_client._to_row(None, "INS-00011")["instruction_id"] is None


def test_workflow_receipts_and_cli_retain_canonical_id():
    repo = Path(__file__).resolve().parents[2]
    workflow = (repo / "sovereign/engine/workflow.py").read_text()
    cli = (repo / "sovereign/cli.py").read_text()
    assert 'self.instruction_id = params.get("instruction_id")' in workflow
    assert '"instruction_id": self.instruction_id' in workflow
    assert '"--instruction-id"' in cli
    assert 'instruction_id=getattr(args, "instruction_id", None)' in cli

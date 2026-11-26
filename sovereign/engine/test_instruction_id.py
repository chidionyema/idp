"""FLOW admission uses Argon's instruction_id in IDP's EXISTING Temporal durable store.

These tests exercise a real asynchronous caller and a fake unique-ID Temporal
server. They never claim the production Temporal server is reachable.
"""

# Pytest assertions are test checks, never runtime input validation.
# ruff: noqa: S101
from __future__ import annotations

import asyncio
import sys
import types
from pathlib import Path

import pytest

from sovereign.engine import client as engine_client


class AlreadyStarted(Exception):
    run_id = "existing-run"


class FakeTemporal:
    def __init__(self) -> None:
        self.accepted: dict[str, tuple] = {}
        self.calls: list[dict] = []

    async def start_workflow(self, workflow, params, **kwargs):
        self.calls.append(dict(kwargs))
        workflow_id = kwargs["id"]
        if workflow_id in self.accepted:
            raise AlreadyStarted("duplicate")
        self.accepted[workflow_id] = (workflow, params, kwargs)
        return object()

    def get_workflow_handle(self, workflow_id, *, run_id):
        assert run_id == "existing-run"
        memo = self.accepted[workflow_id][2]["memo"]

        async def memo_value(key, default=None):
            return memo.get(key, default)

        async def describe():
            return types.SimpleNamespace(memo_value=memo_value)

        return types.SimpleNamespace(describe=describe)


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
    errors = types.ModuleType("temporalio.exceptions")
    errors.WorkflowAlreadyStartedError = AlreadyStarted
    monkeypatch.setitem(sys.modules, "temporalio.exceptions", errors)
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
    replay = asyncio.run(engine_client.start(**args))
    assert replay["instruction_id"] == "I-0045"
    assert replay["replayed"] is True
    assert len(temporal.accepted) == 1
    assert len(temporal.calls) == 2
    assert all(call["id_reuse_policy"] == "reject-duplicate" for call in temporal.calls)


def test_changed_payload_same_id_is_not_a_second_execution(temporal):
    asyncio.run(
        engine_client.start(
            task="first authorized work", instruction_id="GEN-123", by="telegram"
        )
    )
    with pytest.raises(
        ValueError, match="bound to a different or unverifiable request"
    ):
        asyncio.run(
            engine_client.start(
                task="different work under the same ID",
                instruction_id="GEN-123",
                by="telegram",
            )
        )
    assert len(temporal.accepted) == 1
    original = temporal.accepted["GEN-123"][1]
    assert original["task"] == "first authorized work"


def test_duplicate_without_matching_durable_memo_is_refused(temporal):
    args = dict(task="real work", by="genesis", instruction_id="INS-00042")
    asyncio.run(engine_client.start(**args))
    temporal.accepted["INS-00042"][2]["memo"].pop("instruction_fingerprint")
    with pytest.raises(ValueError, match="unverifiable request"):
        asyncio.run(engine_client.start(**args))
    assert len(temporal.accepted) == 1


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "A",
        "AA",
        "bad/id",
        "bad id",
        "ID:001",
        "x" * 101,
        "a\nmalicious",
        None,
    ],
)
def test_invalid_instruction_id_never_contacts_temporal(temporal, bad):
    with pytest.raises(ValueError, match="instruction_id"):
        asyncio.run(engine_client.start("task", instruction_id=bad, by="founder"))
    assert temporal.calls == []


def test_founder_and_telegram_cannot_silently_generate_session_id(temporal):
    for by in ("founder", "genesis", "telegram"):
        with pytest.raises(ValueError, match="stable instruction_id"):
            asyncio.run(engine_client.start("task", by=by))
    assert temporal.calls == []


def test_no_empty_instruction_is_accepted(temporal):
    with pytest.raises(ValueError, match="empty task"):
        asyncio.run(
            engine_client.start("", by="founder", instruction_id="INS-EMPTY-001")
        )
    assert temporal.calls == []


def test_legacy_adhoc_sessions_remain_compatible(temporal):
    result = asyncio.run(engine_client.start("investigate", by="cli"))
    assert result["session_id"].startswith("sb-")
    assert result.get("instruction_id") is None
    assert temporal.calls[0]["id"] == result["session_id"]
    assert "id_reuse_policy" not in temporal.calls[0]


def test_fingerprint_is_payload_sensitive_without_exposing_prompt():
    fingerprint = engine_client._instruction_fingerprint
    x = fingerprint(
        "INS-42",
        task="A",
        by="founder",
        runner="echo",
        repo=None,
        budget=10,
        critical=False,
    )
    y = fingerprint(
        "INS-42",
        task="B",
        by="founder",
        runner="echo",
        repo=None,
        budget=10,
        critical=False,
    )
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


def test_independent_yield_rejects_worker_claims_and_stale_receipts(monkeypatch):
    import json

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    from sovereign.engine.activities import verify_instruction_yield

    signer = Ed25519PrivateKey.generate()
    monkeypatch.setenv(
        "ESTATE_YIELD_VERIFIER_PUBKEY_HEX", signer.public_key().public_bytes_raw().hex()
    )
    expected = {
        "instruction_id": "INS-42",
        "run_id": "current-run",
        "epoch": 2,
        "goal_sha256": "a" * 64,
        "commit_sha": "b" * 40,
    }
    receipt = {
        **expected,
        "ok": True,
        "action": "settle",
        "effect_ref": "independently-observed-effect",
        "reconciled": True,
    }

    def verify(data, signing_key=signer):
        subject = (
            b"meridian/instruction-yield-v1:"
            + json.dumps(
                data, sort_keys=True, separators=(",", ":"), allow_nan=False
            ).encode()
        )
        envelope = {"receipt": data, "signature": signing_key.sign(subject).hex()}
        return asyncio.run(
            verify_instruction_yield({"expected": expected, "envelope": envelope})
        )

    assert verify(receipt) == "settle"
    assert verify({**receipt, "action": "retry"}) == "retry"
    assert verify(receipt, Ed25519PrivateKey.generate()) == "reject"
    for mutation in (
        {"instruction_id": "INS-43"},
        {"run_id": "previous-run"},
        {"epoch": 1},
        {"goal_sha256": "c" * 64},
        {"commit_sha": "d" * 40},
        {"ok": False},
        {"reconciled": False},
        {"effect_ref": ""},
    ):
        assert verify({**receipt, **mutation}) == "reject"
    monkeypatch.delenv("ESTATE_YIELD_VERIFIER_PUBKEY_HEX")
    assert verify(receipt) == "reject"


def test_worker_done_and_worker_exit_are_not_instruction_settlement():
    source = (Path(__file__).resolve().parent / "workflow.py").read_text()
    assert "workflow.patched(" in source
    assert 'self._retain_instruction("worker-exit-unverified")' in source
    assert 'self._retain_instruction("worker-claim-unverified")' in source
    assert '"verify_instruction_yield"' in source


def test_controller_poll_uses_same_signature_gate(monkeypatch):
    import json

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    from sovereign.engine import activities

    signer = Ed25519PrivateKey.generate()
    monkeypatch.setenv(
        "ESTATE_YIELD_VERIFIER_PUBKEY_HEX", signer.public_key().public_bytes_raw().hex()
    )
    expected = {
        "instruction_id": "INS-42",
        "run_id": "current-run",
        "epoch": 2,
        "goal_sha256": "a" * 64,
        "commit_sha": None,
    }
    receipt = {
        **expected,
        "action": "retry",
        "ok": True,
        "effect_ref": "observed-reconciliation",
        "reconciled": True,
    }
    subject = (
        b"meridian/instruction-yield-v1:"
        + json.dumps(
            receipt, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    )
    observed = []

    async def fetch(query):
        observed.append(query)
        return {"receipt": receipt, "signature": signer.sign(subject).hex()}

    monkeypatch.setattr(activities, "_fetch_independent_yield", fetch)
    request = {"expected": expected, "envelope": None}
    assert asyncio.run(activities.verify_instruction_yield(request)) == "retry"
    assert observed == [expected]
    receipt["epoch"] = 1
    assert asyncio.run(activities.verify_instruction_yield(request)) == "reject"
    monkeypatch.delenv("ESTATE_YIELD_VERIFIER_PUBKEY_HEX")
    assert asyncio.run(activities.verify_instruction_yield(request)) == "reject"
    assert len(observed) == 2

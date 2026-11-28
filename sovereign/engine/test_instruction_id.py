"""FLOW admission uses Argon's instruction_id in IDP's EXISTING Temporal durable store.

These tests exercise a real asynchronous caller and a fake unique-ID Temporal
server. They never claim the production Temporal server is reachable.
"""

# Pytest assertions are test checks, never runtime input validation.
# ruff: noqa: S101
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
import time
import types
import uuid
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from temporalio import activity
from temporalio.client import WorkflowFailureError  # noqa: F401
from temporalio.exceptions import ApplicationError
from temporalio.service import RPCError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Replayer, Worker

from sovereign.engine import activities as engine_activities
from sovereign.engine import client as engine_client
from sovereign.engine import fsm
from sovereign.engine.workflow import SessionWorkflow


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


# ---------------------------------------------------------------------------
# MERIDIAN-CTRL-001 section 11: real Temporal Test Server (time-skipping), a real
# Worker, the real SessionWorkflow, and the real Ed25519 verify_instruction_yield
# activity. Only the disk/network activities are stubbed. No fixture above is used.
# ---------------------------------------------------------------------------

TASK = "ship the effect"
IID = "INS-S11-001"
DEADLINE_S = 60
ROUNDS = 3


class Lab:
    def __init__(self) -> None:
        self.loop = asyncio.new_event_loop()
        self.env = self.loop.run_until_complete(WorkflowEnvironment.start_time_skipping())

    def run(self, coro):
        return self.loop.run_until_complete(coro)

    def close(self) -> None:
        self.loop.run_until_complete(self.env.shutdown())
        self.loop.close()


@pytest.fixture(scope="module")
def lab():
    lab = Lab()
    try:
        yield lab
    finally:
        lab.close()


class Rec:
    def __init__(self) -> None:
        self.receipts: list[dict] = []
        self.verdicts: list[str] = []
        self.gates: list[str] = []
        self.steps = 0

    def kinds(self) -> list[str]:
        return [r["kind"] for r in self.receipts]


def _activities(rec: Rec, step_result):
    @activity.defn(name="budget_op")
    async def budget_op(inp):
        return {"remaining": 1000}

    @activity.defn(name="append_receipt")
    async def append_receipt(record):
        rec.receipts.append(record)
        return {}

    @activity.defn(name="notify_change")
    async def notify_change(state):
        return {}

    @activity.defn(name="run_step")
    async def run_step(inp):
        rec.steps += 1
        if step_result is None:
            raise ApplicationError("worker exited", non_retryable=True)
        return step_result

    @activity.defn(name="verify_instruction_yield")
    async def verify(inp):
        verdict = await engine_activities.verify_instruction_yield(inp)
        rec.verdicts.append(verdict)
        return verdict

    @activity.defn(name="rust_gate_verify_settlement")
    async def rust_gate(inp):
        verdict = await engine_activities.rust_gate_verify_settlement(inp)
        rec.gates.append(verdict)
        return verdict

    return [budget_op, append_receipt, notify_change, run_step, verify, rust_gate]


def _params(**over):
    params = {
        "session_id": IID,
        "instruction_id": IID,
        "task": TASK,
        "runner": "claude",
        "repo": None,
        "by": "genesis",
        "budget": 1000,
        "critical": False,
        "receipt_activity_timeout_s": 30,
        "receipt_retry_max_attempts": 1,
        "notify_activity_timeout_s": 30,
        "notify_retry_max_attempts": 1,
        "step_start_to_close_min": 1,
        "step_heartbeat_s": 30,
        "step_activity_retry_max_attempts": 1,
        "last_output_max_chars": 500,
        "fsm_states": list(fsm.STATES),
        "fsm_max_cycles": 5,
        "budget_activity_timeout_s": 30,
        "budget_retry_max_attempts": 1,
        "approval_timeout_min": 0,
        "verification_deadline_s": DEADLINE_S,
        "verification_max_rounds": ROUNDS,
    }
    params.update(over)
    return params


GATE: dict = {}


def _settlement(run_id, *, epoch=1, url="https://llm.meridianlabs.cloud/health", signer=None, **over):
    """What the independent certifier signs for the compiled Rust gate (MERIDIAN-SETTLEMENT-V1)."""
    signer = signer or GATE["certifier"]
    now = int(time.time())
    fields = {
        "instruction_id": IID,
        "attempt_id": run_id,
        "execution_epoch": epoch,
        "objective_hash": hashlib.sha256(TASK.encode()).hexdigest(),
        "acceptance_predicate_hash": "ab" * 32,
        "target_identity": "llm.meridianlabs.cloud",
        "artifact_digest": "cd" * 32,
        "observed_at_utc": now,
        "evidence_expires_utc": now + 3600,
        "observation_url": url,
        "verifier_pubkey_hex": signer.public_key().public_bytes_raw().hex(),
        "policy_hash": "ef" * 32,
    }
    fields.update(over)
    order = ("instruction_id", "attempt_id", "execution_epoch", "objective_hash",
             "acceptance_predicate_hash", "target_identity", "artifact_digest",
             "observed_at_utc", "evidence_expires_utc", "observation_url", "policy_hash")
    digest = hashlib.sha256(
        ("MERIDIAN-SETTLEMENT-V1|" + "|".join(str(fields[k]) for k in order)).encode()
    ).digest()
    fields["signature_hex"] = signer.sign(digest).hex()
    return {
        "obligation": {
            "acceptance_predicate_hash": fields["acceptance_predicate_hash"],
            "policy_hash": fields["policy_hash"],
        },
        "receipt": fields,
    }


def _envelope(key, run_id, settlement=True, **over):
    receipt = {
        "instruction_id": IID,
        "run_id": run_id,
        "epoch": 1,
        "goal_sha256": hashlib.sha256(TASK.encode()).hexdigest(),
        "commit_sha": None,
        "action": "settle",
        "ok": True,
        "effect_ref": "effect-1",
        "reconciled": True,
    }
    receipt.update(over)
    subject = b"meridian/instruction-yield-v1:" + json.dumps(
        receipt, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    envelope = {"receipt": receipt, "signature": key.sign(subject).hex()}
    if settlement is True:
        envelope["settlement"] = _settlement(run_id)
    elif settlement:
        envelope["settlement"] = settlement
    return envelope


async def _until(predicate, what, seconds=120.0):
    deadline = asyncio.get_running_loop().time() + seconds
    while asyncio.get_running_loop().time() < deadline:
        if await predicate():
            return
        await asyncio.sleep(0.05)
    raise AssertionError(f"never reached: {what}")


async def _halted(handle) -> bool:
    try:
        state = await handle.query("state")
    except Exception:
        return False
    return state["status"] == "halted"


def _gate_binary() -> str:
    root = Path(__file__).resolve().parents[2]
    for cand in (os.environ.get("MERIDIAN_GATE_BIN"), str(root / "target/release/meridian-gate")):
        if cand and Path(cand).is_file() and os.access(cand, os.X_OK):
            return cand
    raise AssertionError(
        "compiled meridian-gate not found: run `cargo build --release -p meridian-gate` "
        "or set MERIDIAN_GATE_BIN (these tests prove the real binary, they never skip it)"
    )


@pytest.fixture()
def signing(monkeypatch):
    key = Ed25519PrivateKey.generate()
    pub = key.public_key().public_bytes_raw().hex()
    monkeypatch.setenv("ESTATE_YIELD_VERIFIER_PUBKEY_HEX", pub)
    certifier = Ed25519PrivateKey.generate()
    worker = Ed25519PrivateKey.generate()
    monkeypatch.setenv("MERIDIAN_GATE_BIN", _gate_binary())
    monkeypatch.setenv(
        "ESTATE_SETTLEMENT_CERTIFIERS_HEX", certifier.public_key().public_bytes_raw().hex()
    )
    monkeypatch.setenv("ESTATE_WORKER_PUBKEY_HEX", worker.public_key().public_bytes_raw().hex())
    GATE.clear()
    GATE.update(certifier=certifier, worker=worker)
    return key


async def _start(lab, workflow_cls, rec, step_result, params=None, wid=None):
    queue = "s11-" + uuid.uuid4().hex
    worker = Worker(
        lab.env.client,
        task_queue=queue,
        workflows=[workflow_cls],
        activities=_activities(rec, step_result),
    )
    return worker, queue


def test_a_valid_independent_receipt_settles(lab, signing):
    """Positive control: a real signed receipt from the independent verifier settles."""
    rec = Rec()

    async def scenario():
        worker, queue = await _start(lab, SessionWorkflow, rec, None)
        async with worker:
            handle = await lab.env.client.start_workflow(
                "SessionWorkflow", _params(), id=IID + uuid.uuid4().hex, task_queue=queue
            )
            await _until(lambda: _halted(handle), "halted awaiting verifier")
            await handle.signal(
                "submit_independent_yield", _envelope(signing, handle.result_run_id)
            )
            await _until(lambda: asyncio.sleep(0, len(rec.gates) >= 1), f"rust gate verdict (python={rec.verdicts} kinds={rec.kinds()})")
            return await asyncio.wait_for(handle.result(), 60)

    state = lab.run(scenario())
    assert state["status"] == "done"
    assert rec.verdicts == ["settle"]
    assert rec.gates == ["allow"]
    assert rec.kinds().count("done") == 1
    assert "verification_requested" in rec.kinds()
    assert "verification_timeout" not in rec.kinds()


def test_b_missing_verifier_hits_deadline_and_fails_closed(lab, signing):
    """Negative control: no verifier ever answers. The wait is bounded, re-dispatches
    for the configured rounds, then fails closed. It must not hang."""
    rec = Rec()

    async def scenario():
        worker, queue = await _start(lab, SessionWorkflow, rec, None)
        async with worker:
            handle = await lab.env.client.start_workflow(
                "SessionWorkflow", _params(), id=IID + uuid.uuid4().hex, task_queue=queue
            )
            return await asyncio.wait_for(handle.result(), 90)

    state = lab.run(scenario())
    assert state["status"] == "failed"
    assert state["reason"] == "verification-deadline-exceeded"
    kinds = rec.kinds()
    assert kinds.count("verification_requested") == ROUNDS
    assert kinds.count("verification_timeout") == ROUNDS
    assert kinds[-1] == "fail"
    assert "done" not in kinds
    assert rec.verdicts == []


def test_b_delayed_verifier_after_one_timeout_still_settles(lab, signing):
    """Bounded recovery, not an abort: a verifier that is late once (past the first
    deadline) but inside the round budget still settles, in a later round."""
    rec = Rec()

    async def scenario():
        worker, queue = await _start(lab, SessionWorkflow, rec, None)
        async with worker:
            handle = await lab.env.client.start_workflow(
                "SessionWorkflow", _params(), id=IID + uuid.uuid4().hex, task_queue=queue
            )
            await _until(lambda: _halted(handle), "halted awaiting verifier")
            await lab.env.sleep(DEADLINE_S + 5)
            await _until(
                lambda: asyncio.sleep(0, "verification_timeout" in rec.kinds()),
                "first deadline fired",
            )
            await handle.signal(
                "submit_independent_yield", _envelope(signing, handle.result_run_id)
            )
            await _until(lambda: asyncio.sleep(0, len(rec.gates) >= 1), "rust gate verdict")
            return await asyncio.wait_for(handle.result(), 60)

    state = lab.run(scenario())
    assert state["status"] == "done"
    assert rec.kinds().count("verification_timeout") == 1
    assert rec.kinds().count("verification_requested") == 2
    assert rec.verdicts == ["settle"]


def test_c_stale_forged_and_duplicate_receipts_are_rejected(lab, signing):
    rec = Rec()
    attacker = Ed25519PrivateKey.generate()

    async def scenario():
        worker, queue = await _start(lab, SessionWorkflow, rec, None)
        async with worker:
            handle = await lab.env.client.start_workflow(
                "SessionWorkflow", _params(), id=IID + uuid.uuid4().hex, task_queue=queue
            )
            await _until(lambda: _halted(handle), "halted awaiting verifier")
            run_id = handle.result_run_id
            bad = [
                _envelope(signing, "a-previous-run"),  # stale attempt: other run
                _envelope(signing, run_id, epoch=0),  # stale attempt: older epoch
                _envelope(attacker, run_id),  # wrong signer
            ]
            for n, envelope in enumerate(bad, start=1):
                await handle.signal("submit_independent_yield", envelope)
                await _until(
                    lambda n=n: asyncio.sleep(0, len(rec.verdicts) >= n), f"verdict {n}"
                )
                assert await _halted(handle)
            good = _envelope(signing, run_id)
            await handle.signal("submit_independent_yield", good)
            await _until(lambda: asyncio.sleep(0, len(rec.gates) >= 1), "rust gate verdict")
            state = await asyncio.wait_for(handle.result(), 60)
            duplicate_refused = False
            try:
                await handle.signal("submit_independent_yield", good)
            except RPCError:
                duplicate_refused = True
            return state, duplicate_refused

    state, duplicate_refused = lab.run(scenario())
    assert rec.verdicts == ["reject", "reject", "reject", "settle"]
    assert rec.gates == ["allow"]
    assert state["status"] == "done"
    assert rec.kinds().count("done") == 1
    assert duplicate_refused


def test_c_missing_instruction_id_is_refused_by_client_and_by_workflow(lab):
    with pytest.raises(ValueError, match="consequential runners require"):
        asyncio.run(engine_client.start("do a thing", runner="claude", by="cli"))
    rec = Rec()

    async def scenario():
        worker, queue = await _start(lab, SessionWorkflow, rec, {"output": "x", "tokens": 1})
        async with worker:
            handle = await lab.env.client.start_workflow(
                "SessionWorkflow",
                _params(instruction_id=None, session_id="sb-" + uuid.uuid4().hex[:8], by="cli"),
                id="sb-" + uuid.uuid4().hex[:8],
                task_queue=queue,
            )
            return await asyncio.wait_for(handle.result(), 60)

    state = lab.run(scenario())
    assert state["status"] == "failed"
    assert state["reason"].startswith("custody-required")
    assert rec.steps == 0, "the consequential runner must never have been dispatched"


def test_c_non_consequential_runner_without_instruction_id_still_runs(lab):
    rec = Rec()

    async def scenario():
        worker, queue = await _start(
            lab, SessionWorkflow, rec, {"output": "ok", "tokens": 1, "done": True}
        )
        async with worker:
            handle = await lab.env.client.start_workflow(
                "SessionWorkflow",
                _params(instruction_id=None, runner="echo", by="cli"),
                id="sb-" + uuid.uuid4().hex[:8],
                task_queue=queue,
            )
            return await asyncio.wait_for(handle.result(), 60)

    state = lab.run(scenario())
    assert not str(state["reason"]).startswith("custody-required")
    assert rec.steps >= 1


def _prepatch():
    from sovereign.engine.prepatch_workflow_snapshot import SessionWorkflow as Old

    return Old


def test_b_falsifier_prepatch_workflow_hangs_where_patched_one_fails_closed(lab, signing):
    """Same scenario as the bounded test, run on the pre-patch code: it never terminates.
    This is what proves the bounded test can fail."""
    rec = Rec()

    async def scenario():
        worker, queue = await _start(lab, _prepatch(), rec, None)
        async with worker:
            handle = await lab.env.client.start_workflow(
                "SessionWorkflow", _params(), id=IID + uuid.uuid4().hex, task_queue=queue
            )
            await _until(lambda: _halted(handle), "halted awaiting verifier")
            # Real time, not result(): awaiting result() lets the time-skipping server jump
            # the clock, which is exactly what the patched deadline relies on.
            await asyncio.sleep(3)
            state = await handle.query("state")
            hung = state["status"] == "halted"
            await handle.terminate("test cleanup")
            return hung, state

    hung, state = lab.run(scenario())
    assert hung and state["status"] == "halted"


def test_d_prepatch_histories_replay_on_patched_workflow(lab, signing):
    """Replay compatibility: histories recorded by the PRE-patch workflow replay on the
    patched one with no non-determinism (workflow.patched keeps the old path)."""
    histories = []
    rec = Rec()

    async def record():
        worker, queue = await _start(lab, _prepatch(), rec, None)
        async with worker:
            handle = await lab.env.client.start_workflow(
                "SessionWorkflow", _params(), id=IID + uuid.uuid4().hex, task_queue=queue
            )
            await _until(lambda: _halted(handle), "halted awaiting verifier")
            # The pre-patch workflow predates the Rust gate: it takes the 2-key envelope.
            await handle.signal(
                "submit_independent_yield",
                _envelope(signing, handle.result_run_id, settlement=False),
            )
            await asyncio.wait_for(handle.result(), 60)
            histories.append(("guarded-settled", await handle.fetch_history()))
        rec2 = Rec()
        worker, queue = await _start(
            lab, _prepatch(), rec2, {"output": "ok", "tokens": 1, "done": True}
        )
        async with worker:
            handle = await lab.env.client.start_workflow(
                "SessionWorkflow",
                _params(instruction_id=None, runner="claude", by="cli"),
                id="sb-" + uuid.uuid4().hex[:8],
                task_queue=queue,
            )
            await asyncio.wait_for(handle.result(), 60)
            histories.append(("unnamed-consequential", await handle.fetch_history()))

    lab.run(record())
    assert len(histories) == 2
    for name, history in histories:
        assert not any(
            "bounded-verification-deadline-v1" in str(e) or "custody-required-v1" in str(e)
            for e in history.events
        ), name
        lab.run(Replayer(workflows=[SessionWorkflow]).replay_workflow(history))


# ---- MERIDIAN-CTRL-001 B08/B10: the compiled Rust gate must also allow settlement ----


def _gated_run(lab, rec, envelope_for, *, then_wait_s=None):
    """Park a guarded session, submit one envelope, return (state, rec)."""

    async def scenario():
        worker, queue = await _start(lab, SessionWorkflow, rec, None)
        async with worker:
            handle = await lab.env.client.start_workflow(
                "SessionWorkflow", _params(), id=IID + uuid.uuid4().hex, task_queue=queue
            )
            await _until(lambda: _halted(handle), "halted awaiting verifier")
            await handle.signal("submit_independent_yield", envelope_for(handle.result_run_id))
            await _until(lambda: asyncio.sleep(0, len(rec.verdicts) >= 1), "python verdict")
            await _until(lambda: asyncio.sleep(0, len(rec.gates) >= 1), "rust gate verdict")
            return await asyncio.wait_for(handle.result(), 120)

    return lab.run(scenario())


def _refused(lab, signing, envelope_for):
    """The python verifier signs a valid settle; the compiled gate must still refuse, and the
    wait must then run out its deadline and fail closed, never settle."""
    rec = Rec()
    state = _gated_run(lab, rec, envelope_for)
    assert rec.verdicts == ["settle"], "the python-side signature was valid; the gate decides"
    assert rec.gates == ["reject"]
    assert state["status"] == "failed"
    assert state["reason"] == "verification-deadline-exceeded"
    assert "done" not in rec.kinds()
    assert "settlement_refused" in rec.kinds()


def test_e_python_settle_without_a_certifier_receipt_is_refused_by_the_rust_gate(lab, signing):
    _refused(lab, signing, lambda run_id: _envelope(signing, run_id, settlement=None))


def test_e_proxy_green_observation_url_is_refused_by_the_rust_gate(lab, signing):
    for url in (
        "https://raw.githubusercontent.com/chidionyema/idp/main/README.md",
        "http://llm.meridianlabs.cloud/health",
        "https://localhost/health",
    ):
        _refused(
            lab,
            signing,
            lambda run_id, url=url: _envelope(
                signing, run_id, settlement=_settlement(run_id, url=url)
            ),
        )


def test_e_worker_cannot_certify_itself(lab, signing):
    _refused(
        lab,
        signing,
        lambda run_id: _envelope(
            signing, run_id, settlement=_settlement(run_id, signer=GATE["worker"])
        ),
    )


def test_e_untrusted_certifier_and_stale_epoch_are_refused(lab, signing):
    outsider = Ed25519PrivateKey.generate()
    _refused(
        lab,
        signing,
        lambda run_id: _envelope(
            signing, run_id, settlement=_settlement(run_id, signer=outsider)
        ),
    )
    _refused(
        lab,
        signing,
        lambda run_id: _envelope(
            signing, run_id, settlement=_settlement(run_id, epoch=0)
        ),
    )


def test_e_expired_evidence_is_refused(lab, signing):
    _refused(
        lab,
        signing,
        lambda run_id: _envelope(
            signing,
            run_id,
            settlement=_settlement(run_id, evidence_expires_utc=int(time.time()) - 5),
        ),
    )


def test_e_missing_gate_binary_fails_closed(lab, signing, monkeypatch, tmp_path):
    monkeypatch.setenv("MERIDIAN_GATE_BIN", str(tmp_path / "no-such-binary"))
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    _refused(lab, signing, lambda run_id: _envelope(signing, run_id))


def test_e_unconfigured_host_trust_fails_closed(lab, signing, monkeypatch):
    monkeypatch.delenv("ESTATE_SETTLEMENT_CERTIFIERS_HEX")
    _refused(lab, signing, lambda run_id: _envelope(signing, run_id))


def test_e_falsifier_s11_workflow_settles_without_the_rust_gate(lab, signing):
    """The same refused envelope settles on the s11 workflow, which has no gate. This is what
    shows the e-tests can fail."""
    from sovereign.engine.s11_workflow_snapshot import SessionWorkflow as S11

    rec = Rec()

    async def scenario():
        worker, queue = await _start(lab, S11, rec, None)
        async with worker:
            handle = await lab.env.client.start_workflow(
                "SessionWorkflow", _params(), id=IID + uuid.uuid4().hex, task_queue=queue
            )
            await _until(lambda: _halted(handle), "halted awaiting verifier")
            await handle.signal(
                "submit_independent_yield",
                _envelope(signing, handle.result_run_id, settlement=None),
            )
            return await asyncio.wait_for(handle.result(), 60)

    state = lab.run(scenario())
    assert state["status"] == "done" and rec.gates == []


def test_f_s11_histories_replay_on_rust_gated_workflow(lab, signing):
    """Replay safety: a history recorded by the s11 workflow carries no rust-gate-v1 marker
    and replays on the current workflow with no non-determinism, for both a settled
    and a deadline-failed guarded session."""
    from sovereign.engine.s11_workflow_snapshot import SessionWorkflow as S11

    histories = []
    rec = Rec()

    async def record():
        worker, queue = await _start(lab, S11, rec, None)
        async with worker:
            handle = await lab.env.client.start_workflow(
                "SessionWorkflow", _params(), id=IID + uuid.uuid4().hex, task_queue=queue
            )
            await _until(lambda: _halted(handle), "halted awaiting verifier")
            await handle.signal(
                "submit_independent_yield",
                _envelope(signing, handle.result_run_id, settlement=None),
            )
            await asyncio.wait_for(handle.result(), 60)
            histories.append(("s11-settled", await handle.fetch_history()))
        rec2 = Rec()
        worker, queue = await _start(lab, S11, rec2, None)
        async with worker:
            handle = await lab.env.client.start_workflow(
                "SessionWorkflow", _params(), id=IID + uuid.uuid4().hex, task_queue=queue
            )
            await asyncio.wait_for(handle.result(), 120)
            histories.append(("s11-deadline-failed", await handle.fetch_history()))

    lab.run(record())
    assert len(histories) == 2
    for name, history in histories:
        assert any("bounded-verification-deadline-v1" in str(e) for e in history.events), name
        assert not any("rust-gate-v1" in str(e) for e in history.events), name
        lab.run(Replayer(workflows=[SessionWorkflow]).replay_workflow(history))


def test_f_new_histories_carry_the_rust_gate_marker(lab, signing):
    rec = Rec()
    histories = []

    async def scenario():
        worker, queue = await _start(lab, SessionWorkflow, rec, None)
        async with worker:
            handle = await lab.env.client.start_workflow(
                "SessionWorkflow", _params(), id=IID + uuid.uuid4().hex, task_queue=queue
            )
            await _until(lambda: _halted(handle), "halted awaiting verifier")
            await handle.signal("submit_independent_yield", _envelope(signing, handle.result_run_id))
            await _until(lambda: asyncio.sleep(0, len(rec.gates) >= 1), "rust gate verdict")
            await asyncio.wait_for(handle.result(), 60)
            histories.append(await handle.fetch_history())

    lab.run(scenario())
    assert any("rust-gate-v1" in str(e) for e in histories[0].events)
    lab.run(Replayer(workflows=[SessionWorkflow]).replay_workflow(histories[0]))

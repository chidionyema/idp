"""Adversarial, executable baseline against IDP's *actual* router ledger.

Two strict xfails are currently demonstrated security gaps, NOT passing security
claims. The positive control proves the old request signature verifier runs.
When the boundary is repaired, XPASS is treated as a failure until this suite is
upgraded to require the protected behavior and the observed gap is closed.
"""
from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("cryptography")
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "platform" / "llm" / "action_ledger.py"
spec = importlib.util.spec_from_file_location("research_action_ledger", PATH)
al = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = al
spec.loader.exec_module(al)


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    pem = Ed25519PrivateKey.generate().private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    (tmp_path / "signer.pem").write_bytes(pem)
    monkeypatch.setenv("ESTATE_AGENT_KEY", str(tmp_path / "signer.pem"))
    monkeypatch.setenv("ESTATE_ACTION_LEDGER", str(tmp_path / "action-ledger.jsonl"))
    monkeypatch.setenv("OUTBOX_DB_PATH", str(tmp_path / "outbox.db"))
    al._KEY = None
    yield tmp_path
    al._KEY = None


def request():
    return {
        "model": "test-model",
        "litellm_params": {
            "metadata": {},
            "proxy_server_request": {
                "method": "POST", "url": "/v1/messages",
                "headers": {"user-agent": "claude-code/2.1"},
                "body": {"messages": [{"role": "user", "content": "test"}],
                         "metadata": {"user_id": '{"session_id":"research-session"}'}},
            },
        },
    }


def rewrite_last(path, edit):
    rows = path.read_text().splitlines()
    tail = json.loads(rows[-1])
    edit(tail)
    rows[-1] = json.dumps(tail, sort_keys=True, separators=(",", ":"))
    path.write_text("\n".join(rows) + "\n")


def test_positive_control_request_signature_rejects_tamper(isolated):
    al.record(request(), {"answer": "unchanged"})
    path = isolated / "action-ledger.jsonl"
    rewrite_last(path, lambda row: row.update(args_hash="0" * 64))
    verified, reason = al.verify()
    assert verified == 0
    assert "signature invalid" in reason


@pytest.mark.xfail(strict=True, reason="Current router signature excludes result_hash; last-row tampering is undetected")
def test_last_result_tampering_must_be_refused(isolated):
    al.record(request(), {"answer": "unchanged"})
    path = isolated / "action-ledger.jsonl"
    rewrite_last(path, lambda row: row.update(result_hash="0" * 64))
    verified, reason = al.verify()
    assert verified == 0 and "signature" in reason


@pytest.mark.xfail(strict=True, reason="Current router callback allows successful responses when evidence cannot be recorded")
def test_unrecorded_router_action_must_not_report_success(isolated, monkeypatch):
    monkeypatch.setenv("ESTATE_AGENT_KEY", str(isolated / "missing-signer.pem"))
    al._KEY = None
    asyncio.run(al.proxy_handler_instance.async_log_success_event(
        request(), {"answer": "success"}, None, None
    ))
    assert (isolated / "action-ledger.jsonl").is_file(), (
        "A successful router response has no durable signed action receipt"
    )


@pytest.mark.xfail(strict=True, reason="Executor core accepts a command without a signed Candidate Act / AuthorizationDecision")
def test_executor_requires_signed_candidate_and_policy_decision(monkeypatch):
    # This is the real executor door, but with a no-process LocalExecutor.
    # The session's plan is valid; it is *not* a substitute for a signed,
    # exact-operation finality witness. No shell or daemon is started.
    path = ROOT / "mcp" / "plugins" / "estate_executor.py"
    module_spec = importlib.util.spec_from_file_location("research_estate_executor", path)
    executor = importlib.util.module_from_spec(module_spec)
    sys.modules[module_spec.name] = executor
    module_spec.loader.exec_module(executor)
    monkeypatch.setattr(executor, "_free_mb", lambda path="/": 500_000)
    monkeypatch.setattr(executor, "_plan_gate", lambda *_args: {"ok": True})
    monkeypatch.setattr(executor, "_plan_ledger_write", lambda *_args: None)
    monkeypatch.setattr(executor, "_record_unenforced_work", lambda *_args: None)
    result = executor.execute_command(
        "git status --short", executor=executor.LocalExecutor(),
        session_id="research-candidate-absent",
    )
    assert not result["accepted"], (
        "A request with no signed Candidate Act or decision reached the executor"
    )

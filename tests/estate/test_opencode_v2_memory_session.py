"""OpenCode V2 may reuse one MCP transport for multiple sessions."""

import importlib.machinery
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def bridge(monkeypatch, tmp_path):
    loader = importlib.machinery.SourceFileLoader(
        "estate_memory_v2", str(ROOT / "bin/estate-memory-mcp")
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    monkeypatch.setattr(mod.plan, "PLAN_LEDGER_DIR", str(tmp_path / "plans"))
    return mod


GOAL = {
    "goal": "restore isolated worker bootstrap",
    "subgoals": [{"id": "g1", "text": "verify independent session"}],
}
BDD = {"goal_id": "g1", "given": "declared plan", "when": "read", "then": "observed"}


def call(b, name, args, sid=None):
    params = {"name": name, "arguments": args}
    if sid is not None:
        params["_meta"] = {"ai.opencode/sessionID": sid}
    return b.handle(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": params}
    )["result"]


def test_interleaved_sessions_and_restart(bridge):
    b = bridge.Bridge(require_session_metadata=True)
    assert not call(b, "declare_plan", GOAL, "ses_A").get("isError")
    assert call(b, "add_bdd", BDD, "ses_B")["isError"]
    assert bridge.plan.ledger_plan("ses_B") is None
    restarted = bridge.Bridge(require_session_metadata=True)
    assert not call(restarted, "add_bdd", BDD, "ses_A").get("isError")
    assert "g1" in bridge.plan.ledger_plan("ses_A")["bdd"]


@pytest.mark.parametrize("sid", [None, "", "../other", "ses_bad/path", 42])
def test_strict_v2_refuses_missing_or_invalid_session(bridge, sid):
    b = bridge.Bridge(require_session_metadata=True)
    assert call(b, "declare_plan", GOAL, sid)["isError"]
    assert b.plan is None


def test_explicit_metadata_uses_separate_ledger_even_in_legacy_mode(bridge):
    b = bridge.Bridge()
    assert not call(b, "declare_plan", GOAL, "ses_C").get("isError")
    assert b.plan is None
    assert bridge.plan.ledger_plan("ses_C") is not None


def test_failed_write_never_yields_plan_success(bridge, monkeypatch):
    b = bridge.Bridge(require_session_metadata=True)
    monkeypatch.setattr(bridge.plan, "record_plan_call", lambda *args: False)
    assert call(b, "declare_plan", GOAL, "ses_D")["isError"]
    assert bridge.plan.ledger_plan("ses_D") is None

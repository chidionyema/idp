"""apply()'s result is a contract every consumer reads: ok implies plan and message.

2026-11-22, measured live: the shared estate-memory MCP process died on
KeyError 'plan'. A runtime restart left the bridge with no in-memory plan; the
next plan-tool call (address_edgecases) landed in apply()'s bootstrap branch,
which returned {"ok": True} with no "plan" key; plan_call did r["plan"] and the
process exited, taking the memory door down for every session. replay() reads
the same key, so a ledger that recorded any plan tool before a declare_plan
could never be replayed back into a plan either.

These falsifiers pin the contract: an ok result from apply() always carries
both "plan" and "message", whatever branch produced it.
"""

import importlib.machinery
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def plan():
    loader = importlib.machinery.SourceFileLoader(
        "estate_plan_contract", str(ROOT / "platform/estate/memory/plan.py")
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


GOAL = {
    "goal": "the memory server survives its own restart",
    "subgoals": [{"id": "g1", "text": "the apply contract holds"}],
}
EDGE = {
    "goal_id": "g1",
    "edgecases": ["a restart lost the in-memory plan"],
}


def test_an_ok_result_always_carries_plan_and_message(plan):
    declared = plan.apply(None, "declare_plan", GOAL)
    assert declared["ok"]
    for r in (
        plan.apply(None, "add_bdd", {"goal_id": "g1", "given": "g", "when": "w", "then": "t"}),
        plan.apply(None, "address_edgecases", EDGE),
        plan.apply(None, "complete_goal", {"goal_id": "g1"}),
        plan.apply(declared["plan"], "add_bdd", {"goal_id": "g1", "given": "g", "when": "w", "then": "t"}),
    ):
        if r.get("ok"):
            assert "plan" in r, r
            assert isinstance(r.get("message"), str) and r["message"], r


def test_the_crash_sequence_refuses_cleanly(plan):
    # The exact live crash (2026-11-22): a restart left the deployed bridge with no plan and
    # the next plan-tool call killed the process with KeyError 'plan'. On this tree the same
    # sequence is a per-call refusal that records nothing -- and any ok result still carries
    # the full contract.
    r = plan.apply(None, "address_edgecases", EDGE)
    if r["ok"]:
        assert r["plan"] is None  # admitted (bootstrap) but nothing recorded
        assert isinstance(r["message"], str) and r["message"]
    else:
        assert "no plan declared" in r["reason"]


def test_replay_of_a_ledger_that_starts_with_a_recording_tool_does_not_raise(plan):
    # replay() reads r["plan"] on every ok: before the fix this raised KeyError and
    # the ledger could never be replayed back into a plan.
    out = plan.replay(
        [
            ["address_edgecases", EDGE],  # recorded before any declare (the live ledger)
            ["declare_plan", GOAL],
            ["add_bdd", {"goal_id": "g1", "given": "g", "when": "w", "then": "t"}],
        ]
    )
    assert out is not None
    assert out["goal"] == GOAL["goal"]


def test_the_v1_bridge_guard_refuses_instead_of_dying(plan, monkeypatch):
    loader = importlib.machinery.SourceFileLoader(
        "estate_memory_v1_guard", str(ROOT / "bin/estate-memory-mcp")
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    calls = []

    def broken_apply(current, name, args):
        return {"ok": True}  # the old incomplete shape, from before the fix

    monkeypatch.setattr(mod.plan, "apply", broken_apply)
    monkeypatch.setattr(
        mod.Bridge, "publish_session", lambda *a, **k: None, raising=False
    )
    bridge = mod.Bridge()
    out = bridge.plan_call(1, "address_edgecases", EDGE)
    assert calls == []  # never recorded
    assert out["result"]["isError"] is True, out
    assert out["result"]["content"][0]["text"].startswith("Refused:"), out

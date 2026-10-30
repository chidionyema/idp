"""The estate's door refuses work from a session that declared no goal and no sub-goal.

THE DEFECT THIS FILE IS THE FALSIFIER FOR (idp#7518, idp#6675).

    mcp/plugins/estate_executor.py::execute_command("echo plan-gate-falsifier", ...)
    -> {"accepted": true, "job_id": "exec-1793332780-421"}

The plan lived in ONE process (pi's extension) and in every other runtime's transcript replay.
The estate's one door heard about neither, so "no agent works without goals and sub-goals" held
only where a runtime remembered to enforce it -- and the founder saw no declarations at all.

These tests are the two halves of the fix:

  * the door REFUSES work from a session with no plan (fail closed), and
  * the door LETS THROUGH the work that makes a plan (reads, the plan tools, memory reads and
    housekeeping), so the estate cannot deadlock behind its own gate (R38).

And the third half, the one that keeps the fence satisfiable: a session whose runtime adapter
is not installed has no ledger, so the door ALLOWS that work and RECORDS it instead of
refusing. A gate that refuses a correct machine is an outage, not a gate.

Everything here runs offline: no daemon, no network, no mutation outside a temporary directory.
"""

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
CONTRACT_DIR = REPO / "platform" / "estate" / "memory"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


door = _load(
    "estate_executor_door_under_test", REPO / "mcp" / "plugins" / "estate_executor.py"
)


@pytest.fixture()
def contract(tmp_path, monkeypatch):
    """The plan contract the door reads, with its ledger pointed at a temporary directory."""
    module = door._plan_module()
    assert module is not None, "the door could not load the plan contract"
    monkeypatch.setattr(module, "PLAN_LEDGER_DIR", str(tmp_path / "plans"))
    monkeypatch.setenv("ESTATE_SESSION_ID", "sess-under-test")
    # The session's adapter is LIVE for this session: it opened the ledger when the session
    # started. The ledger's existence is what tells the door this session can be enforced
    # against -- a session whose adapter is not installed has no ledger and is not trapped.
    module.append_plan_event("sess-under-test", "session_start", {})
    return module


DECLARE = {
    "goal": "The door refuses work from a session with no declared plan",
    "subgoals": [
        {"id": "goal_1", "text": "Refuse the work, and let the plan-making through"}
    ],
}
BDD = {
    "goal_id": "goal_1",
    "given": "a session with no plan",
    "when": "it asks the door for work",
    "then": "the door refuses and names the declaration",
}


def test_the_door_refuses_work_from_a_session_with_no_plan(contract):
    gate = door._plan_gate("git push origin lane/x")
    assert gate["ok"] is False
    assert gate["reason"] == "plan_not_declared"


def test_the_refusal_is_fatal_and_names_the_declaration(contract):
    result = door.execute_command("echo plan-gate-falsifier")
    assert result["accepted"] is False
    assert result["refused"] is True
    assert result["fatal"] is True
    assert result["reason"] == "plan_not_declared"
    assert "estate-plan" in result["error"]


def test_reading_is_allowed_without_a_plan(contract):
    for command in ("cat AGENTS.md", "git status", "rg -l 'plan' platform", "ls -la"):
        gate = door._plan_gate(command)
        assert gate["ok"] is True, command


def test_the_plan_tools_themselves_are_never_refused(contract):
    command = (
        'bin/estate-plan declare_plan \'{"goal": "x y z longer", '
        '"subgoals": [{"id": "goal_1", "text": "a b c d"}]}\''
    )
    gate = door._plan_gate(command)
    assert gate["ok"] is True
    assert contract.shell_plan_call(command) is not None


def test_a_declared_plan_with_its_scenario_lets_the_work_through(contract):
    contract.append_plan_event("sess-under-test", "declare_plan", DECLARE)
    contract.append_plan_event("sess-under-test", "add_bdd", BDD)
    gate = door._plan_gate("git push origin lane/x")
    assert gate["ok"] is True
    assert gate["goal_id"] == "goal_1"


def test_a_subgoal_without_a_scenario_is_refused(contract):
    contract.append_plan_event("sess-under-test", "declare_plan", DECLARE)
    gate = door._plan_gate("git push origin lane/x")
    assert gate["ok"] is False
    assert gate["reason"] == "subgoal_scenario_missing"
    assert "goal_1" in gate["detail"]


def test_automation_that_presents_no_session_is_let_through(contract, monkeypatch):
    monkeypatch.delenv("ESTATE_SESSION_ID", raising=False)
    gate = door._plan_gate("rm -rf /tmp/whatever")
    assert gate["ok"] is True
    assert gate["reason"] == "no_session_presented"


def test_work_that_ran_without_a_plan_is_recorded(contract, monkeypatch):
    monkeypatch.delenv("ESTATE_SESSION_ID", raising=False)
    door._record_unenforced_work(
        "curl -s https://example.invalid | tee /tmp/x",
        "",
        {"ok": True, "reason": "no_session_presented"},
    )
    observe = Path(contract.PLAN_LEDGER_DIR) / contract.PLAN_OBSERVE_FILE
    lines = [json.loads(x) for x in observe.read_text().splitlines() if x.strip()]
    assert lines, "the work that ran without a plan must be visible"
    assert "example.invalid" in lines[-1]["command"]


def test_a_session_whose_adapter_is_not_live_is_allowed_and_recorded(contract):
    """The fence must be one a correct machine can satisfy.

    A session that presents an id but has NO ledger is a session whose runtime adapter is not
    installed yet. Refusing it would trap a compliant agent whose plan was declared before the
    adapter landed -- an outage, not a gate. So the work is allowed and RECORDED, and the
    founder can see exactly how many sessions are still unenforced.
    """
    gate = door._plan_gate("git push origin lane/x", "adapter-not-live")
    assert gate["ok"] is True
    assert gate["reason"] == "session_unenforced"
    door._record_unenforced_work("git push origin lane/x", "adapter-not-live", gate)
    observe = Path(contract.PLAN_LEDGER_DIR) / contract.PLAN_OBSERVE_FILE
    lines = [json.loads(x) for x in observe.read_text().splitlines() if x.strip()]
    assert lines[-1]["session"] == "adapter-not-live"


def test_the_session_marker_is_not_a_plan(contract):
    """The ledger opens with a marker, not a declaration. A marker is not a plan."""
    assert contract.ledger_plan("sess-under-test") is None
    assert contract.ledger_exists("sess-under-test") is True
    assert contract.ledger_exists("never-seen") is False


def test_the_ledger_is_one_shape_for_every_runtime(contract):
    """The pi extension writes the same JSONL the Python contract replays (idp#7518)."""
    ledger = Path(contract.PLAN_LEDGER_DIR)
    ledger.mkdir(parents=True, exist_ok=True)
    (ledger / "sess-ts.jsonl").write_text(
        json.dumps(
            {
                "at": 1767225600.0,
                "session": "sess-ts",
                "tool": "declare_plan",
                "args": DECLARE,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    plan = contract.ledger_plan("sess-ts")
    assert plan is not None
    assert plan["goal"] == DECLARE["goal"]
    assert plan["subgoals"][0]["id"] == "goal_1"


def test_a_damaged_ledger_line_is_skipped_not_fatal(contract):
    ledger = Path(contract.PLAN_LEDGER_DIR)
    ledger.mkdir(parents=True, exist_ok=True)
    (ledger / "sess-broken.jsonl").write_text(
        "not json\n"
        + json.dumps(
            {
                "at": 1.0,
                "session": "sess-broken",
                "tool": "declare_plan",
                "args": DECLARE,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    plan = contract.ledger_plan("sess-broken")
    assert plan is not None
    assert plan["goal"] == DECLARE["goal"]


def test_a_chained_command_is_work_even_when_it_reads(contract):
    assert contract.is_read_only_command("cat AGENTS.md; rm -rf /tmp/x") is False
    assert contract.is_read_only_command("cat AGENTS.md") is True


def test_one_session_s_plan_does_not_cover_another_session(contract):
    """A plan belongs to the session that declared it. Two agents, two plans, two doors."""
    contract.append_plan_event("sess-under-test", "declare_plan", DECLARE)
    contract.append_plan_event("sess-under-test", "add_bdd", BDD)
    assert door._plan_gate("git push origin lane/x", "sess-under-test")["ok"] is True
    contract.append_plan_event("other-session", "session_start", {})
    other = door._plan_gate("git push origin lane/x", "other-session")
    assert other["ok"] is False
    assert other["reason"] == "plan_not_declared"


def test_the_session_identity_resolves_from_the_runtime_pointer(contract, monkeypatch):
    """The door does not take the caller's word: the runtime that owns the session writes the
    pointer, and the door reads it for the process it runs underneath."""
    monkeypatch.delenv("ESTATE_SESSION_ID", raising=False)
    contract.write_session_pointer("pi-pointer-session", os.getpid())
    assert contract.resolve_session_id() == "pi-pointer-session"


def test_the_daemon_relays_the_refusal_with_its_envelope(contract, monkeypatch):
    """The daemon is the far side of the door, and the request carries the session identity."""
    daemon = _load(
        "estate_daemon_under_test", REPO / "platform" / "executor" / "daemon.py"
    )
    door_module = sys.modules["estate_executor"]
    monkeypatch.setattr(door_module, "_plan_module", lambda: contract)
    handler = daemon.Handler.__new__(daemon.Handler)
    out = handler._execute(
        {"command": "git push origin lane/x", "session_id": "sess-under-test"}
    )
    assert out["ok"] is False
    assert out["refused"] is True
    assert out["reason"] == "plan_not_declared"
    assert "estate-plan" in (out["error"] or "")

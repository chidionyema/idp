"""The plan gate starts a session ONE SHOT and keeps it LIVE.

THE DEFECT THIS FILE IS THE FALSIFIER FOR (measured 2026-11-25, session ses_dedf0a566ffeCXSZDKGmKbZdht).

    execute { code: '... add_bdd({goal_id: "goal_diag_release", given: "... it is ..."})' }
    -> refused: goal_diag_release (...) has no BDD scenario, so execute is refused.

Three defects, one class -- a session could brick itself and the remedy pointed at the one call
the gate could not see:

  1. The gate judged the CONTAINER tool (execute) as ordinary work. It knew about the plan call
     inside the payload only by re-reading the agent's SOURCE TEXT (brace matching plus a
     hand-rolled object-literal-to-JSON rewrite). A payload it could not read -- an apostrophe, a
     nested literal -- was invisible: never recorded, so the plan never advanced, so every tool
     was refused, including the add_bdd that would have repaired it.
  2. The refusal itself demanded a ritual before any work: a scenario for the active sub-goal,
     or nothing runs. That made the gate toll on every step and made the repair unreachable.
  3. The sanctioned fallback door (bin/estate-plan) resolved a DIFFERENT session's ledger, so
     the call the refusal asked for was refused again ("goal_diag_release is not on this plan").

THE FIX:

  * a plan call inside a code payload answers ITSELF -- the gate never judges it as work;
  * a DECLARED PLAN IS LIVE -- the scenario, the edge cases and the effects are required before
    a goal is COMPLETE, not before every tool call;
  * the refusal names the session, so the CLI door lands on THIS session's ledger.

THE EVIDENCE GATE IS NOT DEMOTED: complete_goal still refuses without the scenario, the edge
cases and the effects, and a session with no plan is still refused ordinary work.

Everything here runs offline: no daemon, no network, no mutation outside a temporary directory.
"""

import importlib.machinery
import importlib.util
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "estate" / "plugins" / "estate-plan-lock" / "index.ts"


def _load(name: str, path: Path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


@pytest.fixture
def plan():
    return _load(
        "estate_plan_one_shot", ROOT / "platform" / "estate" / "memory" / "plan.py"
    )


GOAL = {
    "goal": "the gate never traps a session",
    "subgoals": [{"id": "goal_1", "text": "a declared plan starts the session live"}],
}


def _declared(plan):
    r = plan.apply(None, "declare_plan", GOAL)
    assert r["ok"]
    return r["plan"]


def test_a_declared_plan_with_no_scenario_lets_the_work_through(plan):
    """One shot: declare once, then work. No scenario toll on every tool call."""
    declared = _declared(plan)
    assert "goal_1" not in declared["bdd"]
    for tool in ("shell", "write", "edit", "subagent", "execute"):
        verdict = plan.authorize(tool, declared, {"command": "ls -la"})
        assert verdict["ok"] is True, (tool, verdict)


def test_a_plan_call_in_a_code_payload_is_never_judged_as_work(plan):
    """The repair call is always admitted: the plan tools answer themselves."""
    declared = _declared(plan)
    code = 'return await tools["estate-memory"].add_bdd({ goal_id: "goal_1", given: "g", when: "w", then: "t" })'
    verdict = plan.authorize("execute", declared, {"code": code})
    assert verdict["ok"] is True, verdict


def test_the_payload_the_old_text_parser_could_not_read_is_admitted(plan):
    """The measured brick: an apostrophe in the scenario text.

    The old gate rebuilt the arguments from the source text and dropped the call when it could
    not, so the plan never advanced and every tool was refused. The gate now looks for the NAME
    of the plan call and never rebuilds the arguments.
    """
    declared = _declared(plan)
    code = (
        'return await tools["estate-memory"].add_bdd({ goal_id: "goal_1", '
        'given: "it is the agent\'s own scenario", when: "w", then: "t" })'
    )
    verdict = plan.authorize("execute", declared, {"code": code})
    assert verdict["ok"] is True, verdict


def test_a_session_with_no_plan_is_still_refused_ordinary_work(plan):
    """The fence is not demoted: one declaration is still owed."""
    verdict = plan.authorize("shell", None, {"command": "rm -rf /tmp/x"})
    assert verdict["ok"] is False
    assert "declare_plan" in verdict["reason"]


def test_the_plan_tools_themselves_are_never_refused(plan):
    for tool in (
        "declare_plan",
        "revise_plan",
        "add_bdd",
        "address_edgecases",
        "address_2nd_order_effects",
        "complete_goal",
    ):
        assert plan.authorize(tool, None, {})["ok"] is True, tool


def test_the_evidence_gate_still_refuses_a_goal_with_no_scenario(plan):
    """The proof is still required before a goal is CLAIMED DONE."""
    declared = _declared(plan)
    refused = plan.apply(declared, "complete_goal", {"goal_id": "goal_1"})
    assert refused["ok"] is False
    assert "BDD" in refused["reason"] or "bdd" in refused["reason"].lower()


def test_the_refusal_names_the_session_so_the_cli_door_lands_here(plan, monkeypatch):
    """The measured third defect: the fallback door landed on another session's ledger."""
    monkeypatch.setenv("ESTATE_SESSION_ID", "ses_measured_1234")
    verdict = plan.authorize("shell", None, {"command": "ls"})
    assert verdict["ok"] is False
    assert "--session ses_measured_1234" in verdict["reason"], verdict["reason"]


def test_the_door_admits_work_when_a_plan_is_declared(plan, tmp_path, monkeypatch):
    """The executor's door keeps the same rule as the opencode gate."""
    monkeypatch.setenv("ESTATE_PLAN_LEDGER_DIR", str(tmp_path))
    plan.PLAN_LEDGER_DIR = str(tmp_path)
    sid = "ses_door_one_shot"
    assert plan.append_plan_event(sid, "declare_plan", GOAL)
    verdict = plan.door_plan_gate("echo hello", sid)
    assert verdict["ok"] is True, verdict
    assert verdict.get("reason") == "plan_active"


def test_the_door_still_refuses_a_session_with_no_plan(plan, tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_PLAN_LEDGER_DIR", str(tmp_path))
    plan.PLAN_LEDGER_DIR = str(tmp_path)
    verdict = plan.door_plan_gate("echo hello", "ses_door_no_plan")
    assert verdict["ok"] is False
    assert verdict["reason"] == "plan_not_declared"
    assert "--session ses_door_no_plan" in verdict["detail"], verdict["detail"]


def test_the_gate_does_not_reconstruct_plan_calls_from_source_text():
    """The structural falsifier: the gate reads the ledger, it does not parse the agent.

    The bridge is the one writer of the session ledger: it has the structured call it applied.
    A gate that rewrites the agent's source text cannot trust what it rewrote.
    """
    source = PLUGIN.read_text(encoding="utf-8")
    assert "planCallFromCode" not in source
    # the fragile rewrite that dropped a payload: single quotes normalised into double quotes
    assert ".replace(/'/g" not in source
    # the gate writes no plan call of its own: the ledger has one writer
    assert "recordPlanCall" not in source


def test_the_gate_publishes_the_session_the_cli_door_reads():
    """The pointer is how bin/estate-plan finds this session's ledger."""
    source = PLUGIN.read_text(encoding="utf-8")
    assert "publishSessionPointer" in source
    assert '"publish", "--session"' in source

"""Binds features/gates/epistemic-and-trajectory.feature (founder 2026-09-12: "we will eliminate
guessing entirely"; "see it through hand ensure and prove everything is operational").

Every step runs the real gate over a real transcript written to a temp file -- no mocks, and no
import of the library under test. The two firewalls are graded the way the estate grades any gate:
by the exit code of the executable a person would run.

Both halves are on this branch so the scenario set is one file. bin/idp-epistemic and
bin/idp-trajectory are the two commands the spec names.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when

scenarios("features/gates/epistemic-and-trajectory.feature")

IDP = Path(__file__).resolve().parents[3]
EPISTEMIC = IDP / "bin" / "idp-epistemic"
TRAJECTORY = IDP / "bin" / "idp-trajectory"


def _run(gate: Path, args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["python3", str(gate), *args],
        cwd=IDP,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _write(tmp_path: Path, turns: list[dict]) -> Path:
    """A transcript in pi's real nesting: every turn under a `message` key.

    The fixtures are written this way on purpose. A flat fixture is what let the epistemic gate
    report a clean pass on a real session for a day, because it read turn["content"] and pi stores
    it at turn["message"]["content"].
    """
    p = tmp_path / "session.jsonl"
    p.write_text(
        "\n".join(json.dumps({"type": "message", "message": t}) for t in turns) + "\n"
    )
    return p


def _plan(goal: str, subgoals: list[dict]) -> dict:
    return {
        "role": "assistant",
        "content": [
            {
                "type": "tool_use",
                "name": "declare_plan",
                "input": {"goal": goal, "subgoals": subgoals},
            },
        ],
    }


def _bash(command: str) -> dict:
    return {
        "role": "assistant",
        "content": [
            {"type": "tool_use", "name": "bash", "input": {"command": command}}
        ],
    }


def _say(text: str) -> dict:
    return {"role": "assistant", "content": [{"type": "text", "text": text}]}


@pytest.fixture
def state() -> dict:
    return {}


# --- epistemic ------------------------------------------------------------------------------


@given("a session transcript where the assistant says it built a thing it never ran")
def _claim(state, tmp_path):
    state["path"] = _write(
        tmp_path, [_say("I built Mum's Sovereign Concierge. 18 modules.")]
    )


@given("no tool call appears anywhere in that transcript")
def _no_tools(state):
    assert "tool_use" not in state["path"].read_text()


@when("bin/idp-epistemic grades the transcript")
def _grade_epistemic(state):
    state["result"] = _run(EPISTEMIC, [str(state["path"])])


@when("bin/idp-epistemic grades it")
def _grade_epistemic_it(state):
    """The same step, worded for the scenario that reads a missing file."""
    state["result"] = _run(EPISTEMIC, [str(state["path"])])


@then("it exits 1 and quotes the claim it could not support")
def _ep_refuse(state):
    r = state["result"]
    assert r.returncode == 1, r.stdout + r.stderr
    assert "I built Mum" in (r.stdout + r.stderr), "the refusal must quote the claim"


@given("a session transcript where the assistant runs a command")
def _with_tool(state, tmp_path):
    state["turns"] = [_bash("git log --oneline -3")]
    state["dir"] = tmp_path


@given("then says it built the thing that command produced")
def _then_says(state):
    state["turns"].append(_say("I built bin/treewalk.py, and the commit is on main."))
    state["path"] = _write(state["dir"], state["turns"])


@then("it exits 0")
def _ep_pass(state):
    r = state["result"]
    assert r.returncode == 0, r.stdout + r.stderr


@given("a transcript file that does not exist")
def _missing(state, tmp_path):
    state["path"] = tmp_path / "absent.jsonl"


@then("it exits 2, because an unreadable transcript is never a clean bill")
def _ep_blind(state):
    assert state["result"].returncode == 2, (
        state["result"].stdout + state["result"].stderr
    )


# --- trajectory -----------------------------------------------------------------------------


@given("a session that declares one goal")
def _declares(state, tmp_path):
    state["turns"] = [
        _plan("fix the eight red gates", [{"id": "goal_1", "text": "wire treewalk"}])
    ]
    state["dir"] = tmp_path
    state["path"] = _write(tmp_path, state["turns"])


@given("then acts on something that goal does not cover")
def _acts_off(state):
    state["turns"].append(
        _say("I will wire rule-guard into pi's extensions directory.")
    )
    state["path"] = _write(state["dir"], state["turns"])


@when("bin/idp-trajectory grades the transcript")
def _grade_traj(state):
    state["result"] = _run(TRAJECTORY, [str(state["path"])])


@then("it exits 1 and names the action outside the plan")
def _tj_refuse(state):
    r = state["result"]
    assert r.returncode == 1, r.stdout + r.stderr
    assert "rule-guard" in (r.stdout + r.stderr), "the refusal must name the action"


@given("then acts only on things that goal covers")
def _acts_on(state):
    state["turns"].append(
        _say("I wired treewalk into the eight gates and verified them.")
    )
    state["path"] = _write(state["dir"], state["turns"])


@given("a session that never declares a plan")
def _no_plan(state, tmp_path):
    state["turns"] = [_say("I built a thing.")]
    state["dir"] = tmp_path
    state["path"] = _write(tmp_path, state["turns"])


@given("acts anyway")
def _acts_anyway(state):
    state["turns"].append(_bash("ls -la"))
    state["path"] = _write(state["dir"], state["turns"])


@then("it exits 1, because work with no contract is drift by definition")
def _tj_noplan(state):
    assert state["result"].returncode == 1, (
        state["result"].stdout + state["result"].stderr
    )


# --- the four mechanisms, driven through the library the gate ships --------------------------


@given("a plan with one goal and a budget of three calls")
def _budget_plan(state):
    import sys

    sys.path.insert(0, str(IDP / "bin"))
    from trajectory_lock import TrajectoryLock

    state["lock"] = TrajectoryLock(budget_per_goal=3)
    state["lock"].declare_plan(
        "s", "fix the gates", [{"id": "goal_1", "text": "wire treewalk"}]
    )


@when("the agent makes a fourth call against that goal")
def _fourth(state):
    loc = state["lock"]
    for i in range(3):
        loc.authorize(
            "bash", {"command": f"attempt {i}"}, session_id="s", target_goal_id="goal_1"
        )
    state["verdict"] = loc.authorize(
        "bash", {"command": "attempt 4"}, session_id="s", target_goal_id="goal_1"
    )


@then("it is halted and told to revise the plan or escalate")
def _halted(state):
    v = state["verdict"]
    assert v["allowed"] is False and v.get("halt") is True, v
    assert "revise_plan" in v["reason"] and "escalate" in v["reason"], v["reason"]


@given("an agent that has been halted for burning its budget")
def _halted_agent(state):
    _budget_plan(state)
    _fourth(state)
    assert state["verdict"].get("halt") is True


@when("it calls revise_plan, or escalate")
def _escape(state):
    state["revise"] = state["lock"].authorize("revise_plan", {}, session_id="s")
    state["escalate"] = state["lock"].authorize(
        "escalate", {"why": "stuck"}, session_id="s"
    )


@then("both are allowed, because a trapped agent cannot report that it is trapped")
def _escapes_ok(state):
    assert state["revise"]["allowed"] is True, state["revise"]
    assert state["escalate"]["allowed"] is True, state["escalate"]


@given("a session in which the last three attempts each failed")
def _three_failures(state):
    import sys

    sys.path.insert(0, str(IDP / "bin"))
    from trajectory_lock import TrajectoryLock

    state["lock"] = TrajectoryLock()
    state["lock"].declare_plan(
        "s", "add a button", [{"id": "goal_1", "text": "add it"}]
    )
    turns = [_say("the goal is: add a button")]
    for i in range(3):
        turns.append(_bash(f"fail {i}"))
        turns.append(
            {"role": "tool", "content": [{"type": "text", "text": f"error {i}"}]}
        )
    state["turns"] = turns


@when("bin/idp-trajectory prunes the context")
def _prune(state):
    state["out"] = state["lock"].prune("s", state["turns"], goal="add a button")


@then("the failed turns are removed and the objective is re-injected at the bottom")
def _pruned(state):
    out = state["out"]
    assert out["pruned"] is True, out
    assert out["removed"] >= 3, out
    assert "Trajectory Drift Detected" in str(out["messages"][-1])
    assert "add a button" in str(out["messages"][-1])


@then(
    "a successful tool call is never removed, because it is the evidence the other gate grades"
)
def _evidence_survives(state):
    import sys

    sys.path.insert(0, str(IDP / "bin"))
    from trajectory_lock import TrajectoryLock

    lock = TrajectoryLock()
    lock.declare_plan("s", "add a button", [{"id": "goal_1", "text": "add it"}])
    turns = [
        _bash("git log --oneline -3"),
        {"role": "tool", "content": [{"type": "text", "text": "abc123 did the thing"}]},
    ] + state["turns"][1:]
    out = lock.prune("s", turns, goal="add a button")
    assert "git log --oneline -3" in str(out["messages"]), (
        "a successful call is evidence"
    )

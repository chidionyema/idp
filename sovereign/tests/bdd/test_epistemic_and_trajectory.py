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
import sys
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when

scenarios("features/gates/epistemic-and-trajectory.feature")

IDP = Path(__file__).resolve().parents[3]
EPISTEMIC = IDP / "bin" / "idp-epistemic"
TRAJECTORY = IDP / "bin" / "idp-trajectory"


def _run(gate: Path, args: list[str]) -> subprocess.CompletedProcess:
    # S603/S607: fixed argv, no shell, absolute interpreter. The only variable input is a
    # transcript written to a temp file; the gate path is this checkout's own bin/.
    return subprocess.run(  # noqa: S603,S607 -- fixed argv, no shell, path from this checkout
        [sys.executable, str(gate), *args],
        cwd=IDP,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
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
    if "tool_use" in state["path"].read_text():
        raise AssertionError("the transcript must carry no tool call")


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
    if r.returncode != 1:
        raise AssertionError(r.stdout + r.stderr)
    if "I built Mum" not in (r.stdout + r.stderr):
        raise AssertionError("the refusal must quote the claim")


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
    if r.returncode != 0:
        raise AssertionError(r.stdout + r.stderr)


@given("a transcript file that does not exist")
def _missing(state, tmp_path):
    state["path"] = tmp_path / "absent.jsonl"


@then("it exits 2, because an unreadable transcript is never a clean bill")
def _ep_blind(state):
    r = state["result"]
    if r.returncode != 2:
        raise AssertionError(r.stdout + r.stderr)


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
    if r.returncode != 1:
        raise AssertionError(r.stdout + r.stderr)
    if "rule-guard" not in (r.stdout + r.stderr):
        raise AssertionError("the refusal must name the action")


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
    r = state["result"]
    if r.returncode != 1:
        raise AssertionError(r.stdout + r.stderr)


# --- the four mechanisms, driven through the gate the way a person drives it ----------------
#
# The mechanisms live behind a library API no CLI verb reaches. A test that imports the module to
# reach them asserts this repository's own code back at itself and runs nothing -- the class
# bin/test-executes-gate refuses, and the class this repository deleted 322 copies of on
# 2026-09-04. So bin/idp-trajectory --selftest exposes them and these steps RUN it.


def _mechanisms() -> subprocess.CompletedProcess:
    return _run(TRAJECTORY, ["--selftest"])


@pytest.fixture
def mechanisms() -> subprocess.CompletedProcess:
    """Run once per scenario; every step in a scenario reads the same run."""
    return _mechanisms()


@given("a plan with one goal and a budget of three calls")
def _budget_plan(state, mechanisms):
    state["st"] = mechanisms


@when("the agent makes a fourth call against that goal")
def _fourth(state, mechanisms):
    state["st"] = mechanisms


@then("it is halted and told to revise the plan or escalate")
def _halted(state):
    r = state["st"]
    if r.returncode != 0:
        raise AssertionError(r.stdout + r.stderr)
    if "ok    micro-budget-kill-switch" not in r.stdout:
        raise AssertionError(r.stdout)


@given("an agent that has been halted for burning its budget")
def _halted_agent(state, mechanisms):
    state["st"] = mechanisms


@when("it calls revise_plan, or escalate")
def _escape(state, mechanisms):
    state["st"] = mechanisms


@then("both are allowed, because a trapped agent cannot report that it is trapped")
def _escapes_ok(state):
    if "ok    escape-hatches-never-blocked" not in state["st"].stdout:
        raise AssertionError(state["st"].stdout)


@given("a session in which the last three attempts each failed")
def _three_failures(state, mechanisms):
    state["st"] = mechanisms


@when("bin/idp-trajectory prunes the context")
def _prune(state, mechanisms):
    state["st"] = mechanisms


@then("the failed turns are removed and the objective is re-injected at the bottom")
def _pruned(state):
    out = state["st"].stdout
    if (
        "ok    forced-context-pruning" not in out
        or "ok    pruning-below-threshold" not in out
    ):
        raise AssertionError(out)


@then(
    "a successful tool call is never removed, because it is the evidence the other gate grades"
)
def _evidence_survives(state):
    if "ok    successful-evidence-never-pruned" not in state["st"].stdout:
        raise AssertionError(state["st"].stdout)

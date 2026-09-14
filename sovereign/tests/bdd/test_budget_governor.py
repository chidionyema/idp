"""Binds features/gates/budget-governor.feature (founder essay 2026-09-14, the Reasoning
Gateway; docs/tickets/2026-09-14-reasoning-gateway.md, deliverable D2).

Every step runs the real gate over a real transcript written to a temp file -- no mocks, no
import of the library under test. Same convention as test_reasoning_gateway.py, which this
file's fixtures deliberately mirror: bin/idp-budget imports bin/idp-trajectory and
bin/idp-epistemic's own logic, so this suite proves the composition, not new detection rules.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when

scenarios("features/gates/budget-governor.feature")

IDP = Path(__file__).resolve().parents[3]
BUDGET = IDP / "bin" / "idp-budget"


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: S603,S607 -- fixed argv, no shell, path from this checkout
        [sys.executable, str(BUDGET), "--run", *args],
        cwd=IDP,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def _write(tmp_path: Path, turns: list[dict]) -> Path:
    p = tmp_path / "session.jsonl"
    p.write_text(
        "\n".join(json.dumps({"type": "message", "message": t}) for t in turns) + "\n"
    )
    return p


def _plan() -> dict:
    return {
        "role": "assistant",
        "content": [
            {
                "type": "tool_use",
                "name": "declare_plan",
                "input": {
                    "goal": "investigate latency spike",
                    "subgoals": [{"id": "sg1", "text": "find root cause"}],
                },
            }
        ],
    }


def _bash(command: str) -> dict:
    return {
        "role": "assistant",
        "content": [
            {"type": "tool_use", "name": "bash", "input": {"command": command}}
        ],
    }


def _complete(goal_id: str) -> dict:
    return {
        "role": "assistant",
        "content": [
            {"type": "tool_use", "name": "complete_goal", "input": {"goal_id": goal_id}}
        ],
    }


@pytest.fixture
def state() -> dict:
    return {}


@given("a session that declares a plan and runs six distinct real tool calls")
def _exhausted(state, tmp_path):
    state["path"] = _write(
        tmp_path,
        [
            _plan(),
            _bash("git show HEAD"),
            _bash("kubectl get pods -n web"),
            _bash("curl http://web/health"),
            _bash("grep ERROR app.log"),
            _bash("docker ps -a"),
            _bash("aws s3 ls"),
        ],
    )


@given(
    "a session that declares a plan, does three distinct tool calls, then completes the goal"
)
def _complete_run(state, tmp_path):
    state["path"] = _write(
        tmp_path,
        [
            _plan(),
            _bash("kubectl get pods -n web"),
            _bash("grep ERROR worker.log"),
            _bash("docker restart worker-7"),
            _complete("sg1"),
        ],
    )


@given("a transcript file that does not exist")
def _missing(state, tmp_path):
    state["path"] = tmp_path / "does-not-exist.jsonl"


@when("bin/idp-budget runs it with the default budget")
def _grade(state):
    state["result"] = _run([str(state["path"])])


@then("it exits 1 and names the branch budget as the cause")
def _refused(state):
    r = state["result"]
    if r.returncode != 1:
        raise AssertionError(r.stdout + r.stderr)
    out = r.stdout + r.stderr
    if "branch_budget" not in out:
        raise AssertionError(out)


@then("it exits 0, because the plan completed before either ceiling was reached")
def _passed(state):
    r = state["result"]
    if r.returncode != 0:
        raise AssertionError(r.stdout + r.stderr)


@then("it exits 2, because an unreadable transcript is never a clean bill")
def _blind(state):
    r = state["result"]
    if r.returncode != 2:
        raise AssertionError(r.stdout + r.stderr)

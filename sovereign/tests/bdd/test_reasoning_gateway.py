"""Binds features/gates/reasoning-gateway.feature (founder essay 2026-09-14, the Reasoning
Gateway; docs/tickets/2026-09-14-reasoning-gateway.md, deliverable D1).

Every step runs the real gate over a real transcript written to a temp file -- no mocks, no
import of the library under test. Same convention as test_epistemic_and_trajectory.py, which
this file's fixtures deliberately mirror: bin/idp-prm imports bin/idp-epistemic and
bin/idp-trajectory's own logic, so this suite proves the composition, not new detection rules.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when

scenarios("features/gates/reasoning-gateway.feature")

IDP = Path(__file__).resolve().parents[3]
PRM = IDP / "bin" / "idp-prm"


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: S603,S607 -- fixed argv, no shell, path from this checkout
        [sys.executable, str(PRM), "--grade", *args],
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
                    "goal": "diagnose database outage",
                    "subgoals": [{"id": "sg1", "text": "check database connectivity"}],
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


def _say(text: str) -> dict:
    return {"role": "assistant", "content": [{"type": "text", "text": text}]}


@pytest.fixture
def state() -> dict:
    return {}


@given(
    "a session that declares a plan and then claims verified state with no tool call"
)
def _blind_claim(state, tmp_path):
    state["path"] = _write(tmp_path, [_plan(), _say("I verified the database is up.")])


@given(
    "a session that declares a plan, gathers three independent readings, "
    "then claims verified state"
)
def _grounded_claim(state, tmp_path):
    state["path"] = _write(
        tmp_path,
        [
            _plan(),
            _bash("git show HEAD"),
            _bash("kubectl get pods -n db"),
            _bash("curl http://db-check/health"),
            _say("I verified the database is up."),
        ],
    )


@given("a transcript file that does not exist")
def _missing(state, tmp_path):
    state["path"] = tmp_path / "does-not-exist.jsonl"


@when("bin/idp-prm grades the transcript")
def _grade(state):
    state["result"] = _run([str(state["path"])])


@when("bin/idp-prm grades it")
def _grade_it(state):
    state["result"] = _run([str(state["path"])])


@then("it exits 1 and names the step, the factual vector, and the blind claim")
def _refused(state):
    r = state["result"]
    if r.returncode != 1:
        raise AssertionError(r.stdout + r.stderr)
    out = r.stdout + r.stderr
    if (
        "step 2" not in out
        or "factual" not in out
        or "verified the database" not in out
    ):
        raise AssertionError(out)


@then("it exits 0, because every step scored at least 0.8 on all three vectors")
def _passed(state):
    r = state["result"]
    if r.returncode != 0:
        raise AssertionError(r.stdout + r.stderr)


@then("it exits 2, because an unreadable transcript is never a clean bill")
def _blind(state):
    r = state["result"]
    if r.returncode != 2:
        raise AssertionError(r.stdout + r.stderr)

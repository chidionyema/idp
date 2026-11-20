"""Real CLI regression for the empty-session bootstrap incident (#8346)."""

import json
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

PLAN = Path(__file__).resolve().parents[2] / "platform/estate/memory/plan.py"
GOAL = {
    "goal": "restore the agent fleet",
    "subgoals": [{"id": "g1", "text": "restore planning"}],
}
BDD = {
    "goal_id": "g1",
    "given": "empty session",
    "when": "declare and pin",
    "then": "mutation is admitted",
}


def verdict(tool, args=None, history="", plan=PLAN):
    proc = subprocess.run(
        [sys.executable, str(plan), "authorize", tool, json.dumps(args or {})],
        input=history,
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    return json.loads(proc.stdout)


def command(name, args):
    return f"estate-plan {name} {shlex.quote(json.dumps(args))}"


@pytest.mark.parametrize("history", ["", "[]", " \n"])
def test_empty_input_is_bootstrap_not_permission(history):
    assert verdict("declare_plan", GOAL, history)["ok"]
    assert verdict("read", {"filePath": "AGENTS.md"}, history)["ok"]
    assert not verdict("edit", {"filePath": "a"}, history)["ok"]
    assert not verdict("shell", {"command": "touch a"}, history)["ok"]


@pytest.mark.parametrize("tool", ["Bash", "shell"])
def test_shell_wrappers_admit_only_the_exact_plan_command(tool):
    args = {"command": command("declare_plan", GOAL)}
    assert verdict(tool, args, "[]")["ok"]
    assert not verdict(tool, {"command": args["command"] + " && touch a"})["ok"]
    assert not verdict(tool, {"command": "touch a", "tool": "declare_plan"})["ok"]
    assert not verdict(tool, {"command": command("add_bdd", BDD)})["ok"]


@pytest.mark.parametrize("history", ["{", "{}", "null", "[1]", '[["declare_plan", 1]]'])
def test_corrupt_history_never_grants_mutation(history):
    assert not verdict("edit", history=history)["ok"]


def test_plan_and_bdd_required_and_not_shared():
    declared = [["declare_plan", GOAL]]
    history = json.dumps(declared)
    assert not verdict("shell", {"command": "touch a"}, history)["ok"]
    assert verdict("shell", {"command": command("add_bdd", BDD)}, history)["ok"]
    active = json.dumps([*declared, ["add_bdd", BDD]])
    assert verdict("shell", {"command": "touch a"}, active)["ok"]
    assert not verdict("shell", {"command": "touch a"}, "[]")["ok"]


def test_wrapper_cannot_hide_an_extra_invocation():
    assert not verdict(
        "execute",
        {"command": command("declare_plan", GOAL), "tool": "write"},
    )["ok"]


def test_code_mode_is_not_an_empty_state_shell_alias():
    assert not verdict("execute", {"command": command("declare_plan", GOAL)})["ok"]
    assert not verdict("execute", {"code": "await tools.read({})"})["ok"]

"""A dispatched headless agent can do the one thing every estate hook demands first: plan (idp#8611).

Measured 2026-11-27: four incident agents critical-watch woke through agent-invoke.sh
(a9ee9b95, c3185745, 30573f96, eb4b4fa9, 02:25-02:32Z) did zero work. The PreToolUse hook refuses
Bash until declare_plan is called, and `claude -p --permission-mode acceptEdits` under a harness
that allows nothing denied declare_plan ("you haven't granted it yet"), the estate-plan CLI
("This command requires approval") and reads of the evidence file the prompt named. A headless
run has no one to approve, so every prompt is a denial. Replayed with the real CLI: acceptEdits ->
2 denials (declare_plan, Bash); auto + the estate-memory server allowed -> 0 denials.

The launcher runs headless agents in `auto` (the classifier that judges interactive sessions),
with the estate-memory server and the estate-plan door allowed outright, so the path every hook
demands never depends on a judgement call. Enforcement stays where it is: in the hooks.
"""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
LIBEXEC = ROOT / "platform/estate/libexec"
GATE = LIBEXEC / "fleet-task-budget.py"
LAUNCHER = LIBEXEC / "agent-invoke.sh"
HEADLESS_REFUSED_MODES = {"acceptEdits", "default", "manual", "plan", "dontAsk"}


def launched_argv(launcher: Path = LAUNCHER) -> list[str]:
    """The argv the launcher hands to claude, captured by a mock claude."""
    with TemporaryDirectory() as d:
        root = Path(d)
        home = root / "home"
        (home / ".estate/libexec").mkdir(parents=True)
        shutil.copyfile(GATE, home / ".estate/libexec" / GATE.name)
        (home / ".estate/harness/cc").mkdir(parents=True)
        (home / ".estate/harness/cc/settings.json").write_text("{}")
        out = root / "argv.json"
        mock = root / "mock-claude"
        mock.write_text(
            f"#!{sys.executable}\nimport json, sys\n"
            f"open({str(out)!r}, 'w').write(json.dumps(sys.argv[1:]))\n"
        )
        mock.chmod(0o755)
        payload = {"task": "proof", "repo": str(root), "runner": "claude", "budget": 20}
        result = subprocess.run(  # noqa: S603 -- fixed argv
            ["bash", str(launcher), "--json", json.dumps(payload)],  # noqa: S607
            env=dict(
                os.environ,
                HOME=str(home),
                ESTATE_CLAUDE=str(mock),
                CRITICAL_WATCH_TEMPORAL="127.0.0.1:0",
            ),
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        log = Path(json.loads(result.stdout)["log"])
        end = time.monotonic() + 15
        while "exit=" not in log.read_text() and time.monotonic() < end:
            time.sleep(0.02)
        return json.loads(out.read_text())


def _flag(argv: list[str], name: str) -> list[str]:
    """Every value that follows `name`, up to the next flag."""
    if name not in argv:
        return []
    vals = []
    for a in argv[argv.index(name) + 1 :]:
        if a.startswith("--"):
            break
        vals += a.replace(",", " ").split()
    return vals


def refusals(argv: list[str]) -> int:
    """How many of the two measured denials this argv would reproduce headless."""
    mode = (_flag(argv, "--permission-mode") or ["default"])[0]
    allowed = _flag(argv, "--allowedTools")
    return int(mode in HEADLESS_REFUSED_MODES) + int(
        "mcp__estate-memory" not in allowed
    )


def test_headless_agents_run_in_auto_not_a_mode_that_needs_an_approver():
    mode = _flag(launched_argv(), "--permission-mode")
    assert mode == ["auto"], mode


def test_the_plan_tools_every_hook_demands_are_allowed_outright():
    allowed = _flag(launched_argv(), "--allowedTools")
    assert "mcp__estate-memory" in allowed, allowed
    assert any("estate-plan" in a for a in allowed), allowed


def test_the_budget_and_turn_cap_are_kept():
    argv = launched_argv()
    assert "--max-turns" in argv and "--settings" in argv, argv


if __name__ == "__main__":
    if "--optimus" not in sys.argv:
        sys.exit(
            "usage: python3 tests/estate/test_agent_invoke_headless_can_plan.py --optimus"
        )
    print(f"optimus.dispatch.headless_plan_denials={refusals(launched_argv())}")

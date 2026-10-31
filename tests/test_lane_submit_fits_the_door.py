"""Every step `lane-submit` declares must fit the door an agent actually runs it through, and no
step may carry a bound of its own that guesses how long its work takes.

2026-10-12. `lane-submit` ended in a step that blocked up to 1900s for the lane's `greenlane`
commit status, and the two steps before it declared 120s and 300s -- 2320s of steps inside a door
that kills the job at 60s (the harness door) or 55s (the MCP door's default, read from the plugin
below). A step whose own timeout exceeds the door that runs it can never be honoured: the door
kills first, and the caller is told nothing.

Measured, and the reason this file exists rather than a paragraph: `estate_execute` ran
`lane-submit` and returned exit 124 with the push step still in flight, while the lane ref landed
on origin a moment later -- the submission had succeeded and the caller was never told. The push
alone costs ~35-45s because the pre-push guard reports `timing 32s total; slowest rungs: 19s tsc
backstage, 12s ruff`, so the budget is real and has to be spent deliberately.

2026-10-25. The bounds inside the step were the same defect one level down, and were tried twice:
`timeout 50` inside a 60s step, then `timeout 80` inside a 100s step. Both times the push was
slower than the guess (measured this turn: 98s with the guard attached) and the step reported the
lane ABSENT while the push was still landing. A guessed bound can only be wrong in the direction
that invents a failure, so the inner bound is gone: the push runs in the background and the step
bounds its OBSERVATION of the remote ref. These tests refuse the bound coming back.

The point is not the numbers; it is that the door is fixed and the declaration must fit it. If a
step genuinely needs longer than a door, it belongs on the session plane (estate_session_start),
not in an intent an agent invokes through the executor door.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
INTENT = ROOT / "platform/estate/intents/lane-submit.yaml"
MCP = ROOT / "mcp/plugins/estate_mcp.py"
EXECUTOR = ROOT / "mcp/plugins/estate_executor.py"


def _ceiling_seconds() -> int:
    """The door's ceiling, read from the module that defines it -- the one number nothing in this
    estate may exceed, whatever the unit or the caller."""
    text = EXECUTOR.read_text()
    m = re.search(r"^CEILING_SEC\s*=\s*(\d+)", text, re.MULTILINE)
    assert m, "cannot find CEILING_SEC in mcp/plugins/estate_executor.py"
    return int(m.group(1))


def _door_seconds() -> int:
    """The MCP plugin's default job timeout -- the door an agent gets if it passes nothing. It is
    derived from the ceiling rather than a literal of its own; whichever form it takes, the test
    follows the door instead of drifting from it."""
    text = MCP.read_text()
    m = re.search(r'args\.get\("timeout", ([A-Z_]+|\d+)\)', text)
    assert m, "cannot find the MCP door's default timeout in mcp/plugins/estate_mcp.py"
    value = m.group(1)
    if value.isdigit():
        return int(value)
    m2 = re.search(rf"^{value}\s*=\s*([A-Z_]+)\s*\+\s*(\d+)", text, re.MULTILINE)
    if m2:  # CHILD_BACKSTOP_SEC = DOOR_CEILING_SEC + 15
        base = _ceiling_seconds() if "CEILING" in m2.group(1) else 0
        return base + int(m2.group(2))
    m3 = re.search(rf"^{value}\s*=\s*(\d+)", text, re.MULTILINE)
    assert m3, f"cannot resolve {value} in mcp/plugins/estate_mcp.py"
    return int(m3.group(1))


def _declared_door() -> int:
    """The door this intent declares it needs. An intent that needs more than the default does not
    get to stay silent about it: the caller has to pass `timeout=` or use the session plane, or
    the door kills the job mid-step and reports nothing (which is the defect this file is about)."""
    doc = yaml.safe_load(INTENT.read_text())
    return int(doc.get("door_s", _door_seconds()))


def _steps() -> list[dict]:
    return yaml.safe_load(INTENT.read_text())["steps"]


def test_the_declared_door_is_the_executors_ceiling():
    """`door_s: 170` was a declaration of time nothing in this estate grants: the executor kills
    any command at CEILING_SEC, so the intent's steps were spent against 100 whatever the file
    said. A door larger than the ceiling is a lie told to the reader and to the tests below."""
    assert _declared_door() <= _ceiling_seconds(), (
        f"lane-submit declares a {_declared_door()}s door but no command in this estate may run "
        f"longer than {_ceiling_seconds()}s: the declaration must fit the ceiling, not exceed it"
    )


def test_a_door_larger_than_the_default_is_named_for_the_caller():
    declared, default = _declared_door(), _door_seconds()
    if declared <= default:
        return
    text = INTENT.read_text()
    assert f"timeout={declared}" in text or "session plane" in text, (
        f"lane-submit declares a {declared}s door, more than the {default}s an agent gets by "
        f"default, and never tells the caller how to get one: the run then dies mid-step with "
        f"nothing reported"
    )


def test_no_step_declares_more_time_than_the_door_allows():
    door = _declared_door()
    over = [
        (s["name"], s.get("timeout"))
        for s in _steps()
        if int(s.get("timeout", 0)) > door
    ]
    assert not over, (
        f"these steps declare more time than the {door}s door that runs them, so they can "
        f"never be honoured -- the door kills the job first: {over}"
    )


def test_the_steps_together_fit_one_door():
    """One invocation runs every step inside one door, so the caps have to sum to the door, not
    each fit it separately."""
    door = _declared_door()
    total = sum(int(s.get("timeout", 0)) for s in _steps())
    assert total <= door, (
        f"lane-submit's step timeouts total {total}s inside a {door}s door; the door kills the "
        f"job at {door}s however the steps are budgeted between themselves"
    )


def test_the_verdict_is_still_reachable_without_a_wait():
    """The wait was removed, not the answer. Removing it must leave the intent naming where the
    lane writes its verdict -- the `greenlane` commit status -- or an agent has no way to learn
    the outcome it used to block for."""
    text = INTENT.read_text()
    assert "greenlane" in text and "status" in text, (
        "lane-submit no longer says where the lane writes its verdict; the removed wait has to "
        "be replaced by an observation, not by silence"
    )
    assert "ci.status" in text or "/status" in text, (
        "lane-submit does not name how to read the verdict (ci.status, or the gh api line)"
    )


def test_the_push_step_uses_the_governed_handover_helper():
    push = next(s for s in _steps() if "push" in s["name"])
    assert "python3 bin/lane-submit-handover" in push["cmd"]
    assert ">" not in push["cmd"] and "tee" not in push["cmd"]
    helper = (ROOT / "bin/lane-submit-handover").read_text()
    assert '"ls-remote", "--heads", "origin"' in helper
    assert "on == sha" in helper
    assert "start_new_session=True" in helper


def test_the_push_step_carries_no_bound_of_its_own():
    """THE RATCHET (2026-10-25). `timeout N git push` was the same defect as the door's 55s cap, one
    level down: a number that guesses a duration, and can only be wrong in the direction that
    invents a failure. The step bounds its observation window, never the push. Reintroducing a
    wall-clock bound on the command is what this refuses."""
    push = next(s for s in _steps() if "push" in s["name"])
    cmd = push["cmd"]
    bound = re.search(r"\btimeout\s+(\d+)[s]?\s+git\s+push", cmd)
    assert not bound, (
        f"the push is bounded by `timeout {bound.group(1) if bound else ''} git push` inside the "
        f"step again: a guessed bound on the work itself can only produce a false failure. Bound "
        f"the observation (the poll window), or narrow the step's own `timeout:`, which is the "
        f"door's number and cannot contradict it"
    )
    assert "command -v timeout" not in cmd, (
        "the push step still probes for `timeout`: the bound it was probing for is gone"
    )

"""Every step `lane-submit` declares must fit the door an agent actually runs it through.

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

The point is not the numbers; it is that the door is fixed and the declaration must fit it. If a
step genuinely needs longer than a door, it belongs on the session plane (estate_session_start),
not in an intent an agent invokes through a 55s door.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
INTENT = ROOT / "platform/estate/intents/lane-submit.yaml"
MCP = ROOT / "mcp/plugins/estate_mcp.py"


def _door_seconds() -> int:
    """The MCP plugin's default job timeout -- the door an agent gets if it passes nothing. Read
    rather than hardcoded so the test follows the door instead of drifting from it."""
    m = re.search(r'timeout = int\(args\.get\("timeout", (\d+)\)\)', MCP.read_text())
    assert m, "cannot find the MCP door's default timeout in mcp/plugins/estate_mcp.py"
    return int(m.group(1))


def _declared_door() -> int:
    """The door this intent declares it needs. An intent that needs more than the default does not
    get to stay silent about it: the caller has to pass `timeout=` or use the session plane, or
    the door kills the job mid-step and reports nothing (which is the defect this file is about)."""
    doc = yaml.safe_load(INTENT.read_text())
    return int(doc.get("door_s", _door_seconds()))


def _steps() -> list[dict]:
    return yaml.safe_load(INTENT.read_text())["steps"]


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


def test_the_push_step_measures_the_handover_instead_of_inferring_it():
    """#5814: the timeout is ambiguous. The push is not killed with it, so the ref can land while
    the intent reports `exit 124`, and the caller cannot tell a handed-over branch from nothing
    happening at all -- measured twice on 2026-10-12, and the ref moved after the kill both
    times. So the step has to end by reading the remote ref. Two things make that true, and
    neither is decoration: the push needs a deadline of its own inside the step, or the step's
    cap kills it before it measures anything, and the remote ref has to be compared against the
    commit actually being handed over, or a stale ref reads as a landing."""
    push = next(s for s in _steps() if "push" in s["name"])
    cmd = push["cmd"]
    assert "git ls-remote --heads origin" in cmd, (
        "the push step never reads the remote ref, so its exit code is the only account of the "
        "handover -- which is the ambiguity #5814 is about"
    )
    assert '"$on" = "$sha"' in cmd, (
        "the push step reads the remote ref but does not compare it to the commit being handed "
        "over, so a stale ref on the lane reads as a successful landing"
    )
    inner = re.search(r'BOUND="timeout (\d+)"', cmd)
    assert inner, (
        "the push has no deadline of its own inside the step, so the step's own cap can kill it "
        "before it reaches the measurement that replaces guessing"
    )
    assert int(inner.group(1)) < int(push["timeout"]), (
        f"the push may run {inner.group(1)}s inside a step capped at {push['timeout']}s, leaving "
        f"no room for the ls-remote that has to report the outcome"
    )
    assert "command -v timeout" in cmd, (
        "the push bound is a hard dependency on `timeout` being installed: where it is not, the "
        "push itself never runs. Bound it when the tool is there, push unbounded when it is not"
    )

"""The execute door names the door that answers the command, instead of only refusing it.

Measured 2026-10-23 over 24h of live pi transcripts (bin/process-census, job
exec-1792784032-4447): 1,277 tool calls were an agent asking "has my branch landed yet?", spread
over 418 distinct commands, 108 of them hand-written shell wait loops. `bin/idp-greenlane status`
existed the whole time and was called 16 times. So the door's job is not to say no -- a plain no
leaves the agent to invent a variation -- it is to name the one call that already answers the
question, at the moment the agent reads the refusal.

The shape that motivated the loop pattern was observed live in a pi session minutes after the
first version shipped:

    for i in $(seq 1 40); do if git log -1 --format=%s | grep -q "^feat(pi)"; then break; fi; sleep 2; done

The first version of the pattern could not match it (`[^;|&]*` cannot cross the `;` before `do`),
so the test below grades the exact string, not an idealised one. That regression is the reason
this file exists rather than a comment in the module.

Everything here is graded offline: the module is loaded by path and `_steer_for` is a pure
function of the command string. No daemon, no shell, nothing that can block (LAW 45).
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys

import pytest

PLUGIN = (
    pathlib.Path(__file__).resolve().parents[1]
    / "mcp"
    / "plugins"
    / "estate_executor.py"
)

# The literal command observed in a live session. Kept verbatim on purpose.
OBSERVED_LOOP = (
    'for i in $(seq 1 40); do if git log -1 --format=%s | grep -q "^feat(pi)"; '
    "then break; fi; sleep 2; done"
)


def _load():
    spec = importlib.util.spec_from_file_location("estate_executor", PLUGIN)
    module = importlib.util.module_from_spec(spec)
    sys.modules["estate_executor"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def door():
    return _load()


@pytest.mark.parametrize(
    "command, expected_door",
    [
        # The measured shape, exactly as it was composed.
        (OBSERVED_LOOP, "lane-where"),
        # The same loop written with `while`.
        (
            "while ! git merge-base --is-ancestor abc origin/main; do sleep 5; done",
            "lane-where",
        ),
        # The poll the census found 1,277 times.
        ("gh api repos/o/r/commits/abc/status --jq .state", "lane-where"),
        ("curl -s https://api.github.com/repos/o/r/commits/abc/status", "lane-where"),
        ("gh api repos/o/r/commits/abc/check-runs", "ci.status"),
        ("gh run view 12345", "ci.status"),
        ("gh pr checks 42", "lane-where"),
    ],
)
def test_a_poll_is_steered_to_the_door_that_answers_it(door, command, expected_door):
    verdict = door._steer_for(command)
    assert verdict is not None, (
        f"not steered, so the agent is left to poll again: {command}"
    )
    assert verdict["accepted"] is False
    assert expected_door in verdict["detail"], (
        f"the refusal must name {expected_door}; it said: {verdict['detail']}"
    )


@pytest.mark.parametrize(
    "command",
    [
        "git status --short",
        "git merge-base --is-ancestor abc origin/main",  # the door's own inner call
        "git log --format=%s -1",  # contains the word `format`, must not trip the loop rule
        "rg -n 'for' docs/x.md",  # the word inside a needle
        "bin/lane-where lane/x",
        "python3 -m pytest tests/test_executor_mcp.py -q",
    ],
)
def test_ordinary_work_is_not_steered(door, command):
    assert door._steer_for(command) is None, (
        f"a guard that refuses correct work is the defect it exists to prevent (R38): {command}"
    )


def test_the_steer_is_reported_by_the_refusal_preview_first(door):
    """`_refusals_for` is what a caller reads to learn why a payload would be refused.

    If the preview named the ceiling while the door was really going to name the door, the
    preview would be lying about the door it describes.
    """
    reasons = door._refusals_for(
        OBSERVED_LOOP, str(pathlib.Path.cwd()), door.CEILING_SEC
    )
    assert reasons, "the preview found no reason for a payload the door refuses"
    assert "lane-where" in reasons[0].get("detail", "")

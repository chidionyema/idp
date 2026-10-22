"""EPIC-IDP-090 lane D: a runner refusal must not be shaped like success.

Before this suite existed, `runners.run("claude", ...)` answered

    {"output": "unknown runner: claude", "done": True, ...}

and `sovereign/engine/workflow.py` terminates the FSM on `done: True`. So a session that asked
for a runner the estate does not have ended as `done` -- successful, empty, and with no receipt
that said anything was wrong. "Invoke any agent" therefore looked implemented at fleet scale
while being impossible: the refusal read back as a completion.

There was no `claude` runner at all (`REGISTRY` had echo/sleep/ask/burn/llm), and the tool
descriptions in the MCP plugin advertised one. This file grades the two properties that make the
lie impossible to repeat: an unavailable runner returns `done: False` *and* an `error` the FSM
terminates on, and a registered runner is unaffected.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from sovereign.engine import runners


@pytest.fixture(autouse=True)
def no_temporal(monkeypatch: pytest.MonkeyPatch) -> None:
    # activity.heartbeat() needs a Temporal activity context (the worker supplies one in
    # production). This suite grades the refusal contract, not Temporal's plumbing -- the same
    # boundary test_runners_session_tagging.py draws for the llm runner.
    monkeypatch.setattr(runners.activity, "heartbeat", lambda *a, **k: None)


def _run(runner: str, task: str = "do the thing") -> dict[str, Any]:
    return asyncio.run(runners.run(runner, task, None, 1, []))


def test_an_unavailable_runner_is_not_a_success() -> None:
    result = _run("claude")
    assert result["done"] is False, "a runner we cannot execute must never report done"
    assert result["tokens"] == 0


def test_the_refusal_names_itself_and_what_does_exist() -> None:
    result = _run("claude")
    error = result["error"]
    assert error.startswith("UNAVAILABLE_RUNNER: "), error
    assert "'claude'" in error, "the error must name the runner that was asked for"
    for registered in runners.REGISTRY:
        assert registered in error, (
            f"the error must list what IS available ({registered})"
        )


def test_the_refusal_carries_an_error_the_fsm_can_terminate_on() -> None:
    # workflow.py: `done: True` -> status done; neither `ask` nor `done` -> loop again.
    # Only `error` stops the loop, so a refusal without it would burn the session's cycles
    # re-asking the same missing runner.
    result = _run("claude")
    assert result["ask"] is None
    assert result.get("error"), (
        "a refusal with no ask and no error would loop, not fail"
    )


def test_the_shape_is_one_place_not_two() -> None:
    direct = runners.unavailable_runner("claude")
    through_run = _run("claude")
    assert direct == through_run, "run() must not build its own refusal dict"


def test_a_registered_runner_still_runs() -> None:
    result = _run("echo", "hello")
    assert result["done"] is True
    assert result["output"].startswith("hello")
    assert "error" not in result

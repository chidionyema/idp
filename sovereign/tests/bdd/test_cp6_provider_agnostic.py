"""cp6 acceptance: provider agnostic -- the runner and the model are configuration, never code.

LAW 34, LAW 46. Owner: engine (sovereign/engine/runners.py). Steps call the real registry
dispatch function, `runners.run()` -- the same one workflow.py's step activity calls, not a
mock of it. The vendor CLI/model call itself is the one true external boundary each runner
already substitutes at (echo instead of a subprocess), the same substitution cp27's own
docstring makes for the same reason: "'claude' is a vendor CLI and a true external boundary
... the same activity path minus the subprocess."

The last scenario is this feature's actual claim, proved rather than asserted: a brand-new
provider is registered as one `REGISTRY` entry (see `_register_acme` below) and nothing else
in this file, in workflow.py, or in client.py changes to run it -- because none of them
branch on a runner's name, only `runners.run()` does, by dict lookup.

Not covered here: a full `bin/sb start` CLI run against a live Temporal dev server and
worker. That harness does not exist anywhere in this BDD suite yet -- cp1_durable_session.feature
names the identical requirement ("Given the Temporal dev server and the sovereign worker are
running") and has no step file either -- and standing one up is a separate, larger lift than
a vendor-agnostic-gate task, not something this file invents.
"""

from __future__ import annotations

import asyncio
import subprocess
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from .conftest import REPO_ROOT

scenarios("features/sovereign-bus/cp6_provider_agnostic.feature")


@pytest.fixture(autouse=True)
def _no_activity_context(monkeypatch: pytest.MonkeyPatch) -> None:
    # activity.heartbeat() needs a real Temporal activity execution context (the worker
    # supplies one in production); this suite grades runners.run()'s dispatch and output,
    # not Temporal's own plumbing -- the same boundary test_runners_session_tagging.py draws.
    from sovereign.engine import runners

    monkeypatch.setattr(runners.activity, "heartbeat", lambda *a, **k: None)


@when(parsers.parse('the "{name}" runner runs the task "{task}"'))
def _run_runner(name: str, task: str, context: dict[str, Any]) -> None:
    from sovereign.engine import runners

    context["result"] = asyncio.run(runners.run(name, task, None, 1, []))


@then("the step reports done")
def _reports_done(context: dict[str, Any]) -> None:
    assert context["result"]["done"] is True, context["result"]


@then(parsers.parse('the step\'s output is "{expected}"'))
def _output_is(expected: str, context: dict[str, Any]) -> None:
    assert context["result"]["output"] == expected, context["result"]


@when(parsers.parse('I run "{command}"'))
def _run_grep(command: str, context: dict[str, Any]) -> None:
    # Every "I run" in this feature is a bare `grep -rEl|-rn '<pattern>' <targets...>` --
    # the pattern is the one single-quoted token, the targets follow it.
    _, pattern, rest = command.split("'")
    argv = command.split()
    flags = argv[1]  # -rEl or -rn
    targets = rest.split()
    proc = subprocess.run(
        ["grep", flags, pattern, *targets],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    context["grep_output"] = proc.stdout


@then("the output is empty")
def _empty(context: dict[str, Any]) -> None:
    assert context["grep_output"] == "", context["grep_output"]


@given('a new runner "acme" is registered, the only change being that one dict entry')
def _register_acme(monkeypatch: pytest.MonkeyPatch) -> None:
    from sovereign.engine import runners

    async def _acme(task, repo, step, steer, session_id=None):
        return {"output": "pong from acme", "done": True, "ask": None, "tokens": 1}

    monkeypatch.setitem(runners.REGISTRY, "acme", _acme)

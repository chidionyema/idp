"""A greenlane tick polls once and returns; the runner budget never has to cover a wait.

2026-10-04: a proposed hardening raised the workflow's `timeout-minutes` from 15 to 60 on the
reading that "a 3-step bisect takes 18 minutes" and the runner would SIGKILL the engine
mid-bisect. Measured, that is not what the engine does. `Engine.tick()` runs `_observe_lanes()`,
then at most one of `_judge_batch()` / `_start_batch()`:

  * `_judge_batch()` calls `b.checks(tip)` -- a single `GET /commits/{sha}/check-runs` -- and on
    "pending" under the deadline it RETURNS (engine.py:230). It does not sleep, retry or block.
  * `_start_batch()` pushes a candidate and returns without grading it.
  * `bin/idp-greenlane tick` calls `tick()` exactly once and saves state in a `finally:`.

So a tick is seconds of API work. `DEFAULT_TIMEOUT` is therefore NOT the duration of a tick: it
is the wall-clock age at which a *still-unfinished* candidate is called red, and that age accrues
across ticks, because `b.started` is stamped from `Backend.now()` (= `time.time()/60`) and the
candidate sits in `refs/greenlane/state` between ticks. The two numbers measure different things
and must not be conflated -- which is exactly the error the 15 -> 60 change would have baked in.

What this test holds is the fact the confusion rests on: a tick that finds CI still running
returns promptly instead of sitting in the runner waiting for it. That is what makes the runner
budget irrelevant to grading, and it is the property a future "let's just wait for CI here"
edit would break.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location(
    "greenlane_engine", _ROOT / "greenlane" / "engine.py"
)
engine = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = engine  # dataclasses resolve their module through sys.modules
_spec.loader.exec_module(engine)


def _runner_budget_minutes() -> float:
    """`timeout-minutes` on the greenlane `tick` job, read from the workflow itself."""
    text = (_ROOT / ".github" / "workflows" / "greenlane.yml").read_text()
    job = text.split("jobs:", 1)[1]
    m = re.search(r"^\s+timeout-minutes:\s*(\d+)\s*$", job, re.MULTILINE)
    assert m, "greenlane.yml declares no timeout-minutes on the tick job"
    return float(m.group(1))


def test_the_runner_budget_does_not_pretend_to_cover_a_candidate():
    """The 15 -> 60 change was justified as "a 3-step bisect takes 18 minutes" -- i.e. that the
    runner must outlast a bisect tree. A tick never runs a bisect tree: it pushes one candidate
    and returns. So the budget must stay well under DEFAULT_TIMEOUT, which is the only number
    that bounds a candidate's life. A budget approaching it means someone re-derived the budget
    from a bisect duration again.
    """
    budget = _runner_budget_minutes()
    assert budget <= engine.DEFAULT_TIMEOUT / 3, (
        f"runner budget {budget:g}min approaches DEFAULT_TIMEOUT="
        f"{engine.DEFAULT_TIMEOUT:g}min. A tick pushes one candidate and returns; only "
        f"DEFAULT_TIMEOUT bounds how long a candidate may sit. A budget this large suggests it "
        f"was derived from bisect duration, which no tick ever waits out."
    )


def test_the_runner_budget_leaves_the_tick_room_to_finish():
    # The tick is a poll plus (maybe) a push and a state save; the floor is only here to catch a
    # budget cut so small it cannot cover those, e.g. a CI step that hangs on a cold fetch.
    budget = _runner_budget_minutes()
    assert budget >= 10, (
        f"runner budget {budget:g}min is too tight to cover one tick's fetch, poll, push and "
        f"state save."
    )


def test_a_tick_returns_promptly_while_a_candidate_is_still_pending():
    """The fact the whole invariant rests on: a pending candidate does not block the tick."""
    calls: list[str] = []

    class Backend:
        def now(self):
            return 0.0  # far inside the deadline

        def main(self):
            return "m1"

        def lanes(self):
            return {}

        def checks(self, tip):
            calls.append("checks")
            return ("pending", "")  # CI has not finished

        def foreign_prs(self):
            return []

    b = Backend()
    # A candidate already in flight, so the tick takes the `_judge_batch()` path.
    st = engine.State()
    st.batch = type(
        "B", (), {"id": "b1", "tip": "t1", "base": "m1", "started": 0.0, "members": []}
    )()
    e = engine.Engine(b, st)
    e.tick()
    assert calls == ["checks"], (
        "a pending candidate must be polled once, never waited on"
    )

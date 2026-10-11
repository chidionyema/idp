"""A lane push that loses the concurrency race is re-armed (idp#5730 follow-up).

A lane push fires `push` exactly once, and that run competes for the single `greenlane`
concurrency slot against the continuous stream of `workflow_run` ticks every completion on
main produces. Measured 2026-10-11 over the last 100 greenlane runs: 8 of 11 `push` runs were
cancelled, 76 of 100 runs were cancelled overall, and 52 of those 76 killed a run that had
already started. The `schedule` backstop meant to cover a lost lane (`*/5 * * * *`, 288/day
expected) fired twice in the same window, so nothing re-armed it.

The tick is safe to repeat -- the engine persists `state.json` in git and requeues anything
interrupted -- so the defect is purely that a cancelled run leaves nothing behind to move the
lane. `bin/idp-greenlane` now chains one more tick when work is still outstanding.

A chain with no termination condition would be a runaway: these tests pin the guard in both
directions, because a bare test that re-arm fires would pass against an infinite loop.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from greenlane import engine as E  # noqa: E402


def _mod():
    loader = importlib.machinery.SourceFileLoader(
        "idp_greenlane_rearm", str(ROOT / "bin/idp-greenlane")
    )
    mod = importlib.util.module_from_spec(
        importlib.util.spec_from_loader("idp_greenlane_rearm", loader)
    )
    loader.exec_module(mod)
    return mod


@pytest.fixture
def mod(monkeypatch):
    # GH_REPO is set for every test: repo() otherwise shells out to `gh repo view` to find the
    # name, which would show up in the recorded argv and make the call count meaningless.
    monkeypatch.setenv("GH_REPO", "owner/name")
    monkeypatch.setenv("GH_TOKEN", "x")
    return _mod()


def _only_dispatch(d: _Dispatch) -> list[list[str]]:
    """The `gh workflow run` calls, ignoring any `gh` lookup made to resolve the repo name."""
    return [c for c in d.calls if c[:3] == ["gh", "workflow", "run"]]


class _Dispatch:
    """Stands in for `subprocess.run`, recording every `gh workflow run` argv."""

    def __init__(self, returncode: int = 0, stderr: str = ""):
        self.calls: list[list[str]] = []
        self.returncode = returncode
        self.stderr = stderr

    def __call__(self, argv, **kw):
        self.calls.append(list(argv))

        class R:
            pass

        r = R()
        r.returncode = self.returncode
        r.stderr = self.stderr
        r.stdout = ""
        return r


def _state(*lanes: E.Lane, main: str = "aaa", queued=None) -> E.State:
    st = E.State()
    st.main = main
    for lane in lanes:
        st.lanes[lane.name] = lane
    if queued:
        st.queued = [list(g) for g in queued]
    return st


def test_a_lost_lane_push_is_re_armed(mod, monkeypatch):
    """The whole point: work outstanding, the tick chains another tick."""
    d = _Dispatch()
    monkeypatch.setattr(mod.subprocess, "run", d)
    mod.rearm(_state(E.Lane(name="lane/a", head="h1", status=E.PENDING)))
    calls = _only_dispatch(d)
    assert len(calls) == 1, "a pending lane must re-arm exactly one tick"
    assert "greenlane.yml" in calls[0]
    assert "--ref" in calls[0] and "main" in calls[0]


def test_a_chain_ends_when_nothing_is_outstanding(mod, monkeypatch):
    """Termination. Without this the guard is a runaway loop, not a chain."""
    d = _Dispatch()
    monkeypatch.setattr(mod.subprocess, "run", d)
    mod.rearm(_state())
    assert _only_dispatch(d) == [], "no lanes outstanding must dispatch nothing"


def test_a_lane_landed_on_the_current_main_does_not_re_arm(mod, monkeypatch):
    """Landed against the main it was judged on: done, so the chain ends."""
    d = _Dispatch()
    monkeypatch.setattr(mod.subprocess, "run", d)
    mod.rearm(
        _state(E.Lane(name="lane/a", head="h1", status=E.LANDED, judged_on="aaa"))
    )
    assert _only_dispatch(d) == []


def test_a_verdict_expired_by_a_main_move_still_re_arms(mod, monkeypatch):
    """Landed, but main moved off the sha it was judged on: its verdict is void."""
    d = _Dispatch()
    monkeypatch.setattr(mod.subprocess, "run", d)
    mod.rearm(
        _state(E.Lane(name="lane/a", head="h1", status=E.LANDED, judged_on="OLD"))
    )
    assert len(_only_dispatch(d)) == 1


def test_a_lane_under_test_is_outstanding(mod, monkeypatch):
    """TESTING is mid-batch. Missing it would strand the lane the batch is testing."""
    d = _Dispatch()
    monkeypatch.setattr(mod.subprocess, "run", d)
    mod.rearm(_state(E.Lane(name="lane/a", head="h1", status=E.TESTING)))
    assert len(_only_dispatch(d)) == 1


def test_a_lane_out_of_retries_is_terminal_and_does_not_re_arm(mod, monkeypatch):
    """A red lane past its retries is parked with its reason and told to its author.

    A lane still inside its retry budget is flipped back to pending by the engine inside the
    same tick (engine.py `lane.attempts += 1; if lane.attempts <= self.retries`), so reaching
    here as RED means the budget is spent and re-arming would loop forever on a real failure.
    """
    d = _Dispatch()
    monkeypatch.setattr(mod.subprocess, "run", d)
    mod.rearm(_state(E.Lane(name="lane/a", head="h1", status=E.RED, attempts=99)))
    assert _only_dispatch(d) == []


def test_a_queued_group_alone_re_arms(mod, monkeypatch):
    """A queued group with no lane entry is still outstanding work."""
    d = _Dispatch()
    monkeypatch.setattr(mod.subprocess, "run", d)
    mod.rearm(_state(queued=[["lane/a", "lane/b"]]))
    assert len(_only_dispatch(d)) == 1


def test_a_refused_dispatch_is_loud_and_does_not_raise(mod, monkeypatch, capsys):
    """Silence here is a lane that sits unproven with nothing left to move it."""
    d = _Dispatch(returncode=1, stderr="HTTP 403: Resource not accessible")
    monkeypatch.setattr(mod.subprocess, "run", d)
    mod.rearm(_state(E.Lane(name="lane/a", head="h1", status=E.PENDING)))
    out = capsys.readouterr().out
    assert "REFUSED" in out and "403" in out


def test_without_a_token_nothing_is_dispatched(mod, monkeypatch):
    """No credential means no dispatch; the next event-triggered tick has to cover it."""
    monkeypatch.delenv("GH_TOKEN", raising=False)
    d = _Dispatch()
    monkeypatch.setattr(mod.subprocess, "run", d)
    mod.rearm(_state(E.Lane(name="lane/a", head="h1", status=E.PENDING)))
    assert d.calls == []


def test_the_dispatch_is_an_argv_list_not_a_shell_string(mod):
    """The estate's rule: fixed argv, never a shell string."""
    src = (ROOT / "bin/idp-greenlane").read_text()
    assert "shell=True" not in src.split("def rearm")[1].split("\ndef ")[0]

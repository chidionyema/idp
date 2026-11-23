"""An unresolved operational obligation must not dispatch endless Greenlane ticks."""

import runpy
from pathlib import Path
from types import SimpleNamespace

from greenlane.engine import State

ROOT = Path(__file__).resolve().parents[1]


def test_recovery_only_state_does_not_rearm(monkeypatch):
    functions = runpy.run_path(str(ROOT / "bin/idp-greenlane"))
    rearm = functions["rearm"]
    state = State()
    state.verifying["lane/a"] = {"state": "recovery_required"}
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setenv("GH_TOKEN", "test")
    monkeypatch.setitem(rearm.__globals__, "repo", lambda: "o/r")
    monkeypatch.setattr(functions["subprocess"], "run", fake_run)

    rearm(state)
    assert calls == [], "an unresolved external effect cannot schedule its own next run"
    rearm(state, force=True)
    assert len(calls) == 1, "a resolved candidate wakes the next batch exactly once"
    assert calls[0][:3] == ["gh", "workflow", "run"]

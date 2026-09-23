"""jev_affected must never turn an unknown into a skip.

THE CONTRACT. `jev_affected` selects which tasks a diff needs. The ONE property that makes
it safe to use is directional: a task runs unless its condition's probability is STRICTLY
BELOW the threshold. Every way the world can fail to answer -- no config, an unreadable
config, a git that cannot produce a diff, a decision layer that raises, a response with no
probability in it -- must resolve to RUN.

These tests exist because the first version of the function CRASHED when `_call_jev` raised,
instead of failing open. A selector that raises is bad; a selector that silently skips is
worse. Both are covered here.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
JEV = REPO / "mcp" / "plugins" / "jev.py"


def _load():
    spec = importlib.util.spec_from_file_location("jev_under_test", JEV)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["jev_under_test"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def jev():
    return _load()


def _write(tmp_path: Path, body: str) -> Path:
    (tmp_path / "jev-affected.yml").write_text(body, encoding="utf-8")
    return tmp_path


CONFIG = """
tasks:
  always-one:
    command: echo always
    always: true
  conditional:
    command: echo maybe
    when: Could anything at all change?
"""


def test_unreachable_layer_runs_everything(jev, tmp_path, monkeypatch):
    """A decision layer that RAISES must produce runs, not an exception."""
    repo = _write(tmp_path, CONFIG)
    monkeypatch.setattr(
        jev, "_call_jev", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down"))
    )
    plan = jev.jev_affected(str(repo), "origin/main")
    assert plan["skipped"] == []
    assert set(plan["ran"]) == {"always-one", "conditional"}
    assert plan["escalated"] is True


def test_missing_config_runs_nothing_but_does_not_skip(jev, tmp_path):
    """No config file: no tasks are INVENTED, and nothing is silently skipped."""
    plan = jev.jev_affected(str(tmp_path), "origin/main")
    assert plan["config_error"]
    assert plan["tasks"] == []
    assert plan["skipped"] == []


def test_probability_absent_means_run(jev, tmp_path, monkeypatch):
    """A response with no usable probability is not a low probability."""
    repo = _write(tmp_path, CONFIG)
    monkeypatch.setattr(
        jev, "jev_score", lambda **k: {"escalated": False, "probabilities": None}
    )
    plan = jev.jev_affected(str(repo), "origin/main")
    conditional = next(t for t in plan["tasks"] if t["name"] == "conditional")
    assert conditional["run"] is True


def test_exactly_at_threshold_runs(jev, tmp_path, monkeypatch):
    """Equality RUNS. The skip test is strict inequality, and this pins it."""
    repo = _write(tmp_path, CONFIG)
    monkeypatch.setattr(
        jev,
        "jev_score",
        lambda **k: {"escalated": False, "probabilities": {"run": 0.3}},
    )
    plan = jev.jev_affected(str(repo), "origin/main", skip_below=0.3)
    conditional = next(t for t in plan["tasks"] if t["name"] == "conditional")
    assert conditional["run"] is True


def test_strictly_below_threshold_is_the_only_skip(jev, tmp_path, monkeypatch):
    """The one and only path to a skip: strictly below."""
    repo = _write(tmp_path, CONFIG)
    monkeypatch.setattr(
        jev,
        "jev_score",
        lambda **k: {"escalated": False, "probabilities": {"run": 0.1}},
    )
    plan = jev.jev_affected(str(repo), "origin/main", skip_below=0.3)
    assert "conditional" in plan["skipped"]
    assert "always-one" in plan["ran"]


def test_git_failure_does_not_crash(jev, tmp_path, monkeypatch):
    """A repo that is not a git checkout still yields a plan."""
    repo = _write(tmp_path, CONFIG)
    plan = jev.jev_affected(str(repo), "origin/main")
    assert plan["diff_error"] is not None
    assert plan["skipped"] in ([],)

"""The wall refuses an advisory gate nobody declared, and lets a declared one through.

Gate 1 of bin/pre-push-wall.py reads every workflow.
Without a falsifier it could allow everything and nobody would know.
"""

from __future__ import annotations

import importlib.machinery as M
import importlib.util as U
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
WALL = REPO / "bin" / "pre-push-wall.py"


def wall():
    ld = M.SourceFileLoader("wall_under_test", str(WALL))
    mod = U.module_from_spec(U.spec_from_loader("wall_under_test", ld))
    ld.exec_module(mod)
    return mod


def mk(tmp_path, advice, caps=None):
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    line = "        continue-on-error: true\n"
    (wf / "ci.yml").write_text("jobs:\n  a:\n    steps:\n" + line * advice)
    if caps is not None:
        (tmp_path / ".ci").mkdir()
        (tmp_path / ".ci" / "advisory-allowlist.json").write_text(
            json.dumps({"caps": caps, "why": {}})
        )
    return tmp_path


def test_an_undeclared_advisory_is_refused(tmp_path):
    w = wall()
    d = mk(tmp_path, 1)
    with pytest.raises(w.Refused) as e:
        w.gate_zero_advisory(d)
    assert "ADVISORY_GATE_FORBIDDEN" in str(e.value)


def test_a_declared_advisory_is_allowed(tmp_path):
    w = wall()
    d = mk(tmp_path, 1, {".github/workflows/ci.yml": 1})
    assert "1 declared" in w.gate_zero_advisory(d)


def test_growth_past_the_declared_cap_is_refused(tmp_path):
    w = wall()
    d = mk(tmp_path, 2, {".github/workflows/ci.yml": 1})
    with pytest.raises(w.Refused) as e:
        w.gate_zero_advisory(d)
    assert "ADVISORY_GROWTH" in str(e.value)

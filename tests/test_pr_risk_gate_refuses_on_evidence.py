"""The pre-submission risk gate: advice on blindness, refusal on evidence.

WHY THIS TEST EXISTS. A gate that refuses when it cannot see is not enforcement, it is an
outage -- it blocks every push on a machine whose decision layer is down, and everyone
learns to type the override, which turns the gate into theatre (LAW 38). A gate that never
refuses is also theatre. This pins BOTH edges:

  * a reachable layer that scores the change risky  -> tier `high`
  * a reachable layer that scores it clean          -> tier `low`
  * an unreachable layer                            -> the conditions it could not answer
                                                       count as LIKELY (a reason to look)
                                                       in the ADVICE, while the gate wrapper
                                                       refuses only when >=1 condition
                                                       actually returned a probability.

The last one is the property the shell wrapper implements; the first two are the scorer's.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
JEV = REPO / "mcp" / "plugins" / "jev.py"

CONFIG = """
conditions:
  a:
    when: Could A change?
    weight: 3
  b:
    when: Could B change?
    weight: 1
"""


@pytest.fixture
def jev():
    spec = importlib.util.spec_from_file_location("jev_pr_risk_under_test", JEV)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["jev_pr_risk_under_test"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "jev-pr-risk.yml").write_text(CONFIG, encoding="utf-8")
    return tmp_path


def test_reachable_and_risky_is_high(jev, repo, monkeypatch):
    monkeypatch.setattr(
        jev,
        "jev_score",
        lambda **k: {"escalated": False, "probabilities": {"likely": 0.95}},
    )
    result = jev.jev_pr_risk(str(repo), "origin/main")
    assert result["tier"] == "high"
    assert result["score"] == 1.0
    assert all(c["probability"] is not None for c in result["conditions"])


def test_reachable_and_clean_is_low(jev, repo, monkeypatch):
    monkeypatch.setattr(
        jev,
        "jev_score",
        lambda **k: {"escalated": False, "probabilities": {"likely": 0.02}},
    )
    result = jev.jev_pr_risk(str(repo), "origin/main")
    assert result["tier"] == "low"
    assert result["score"] == 0.0


def test_unreachable_layer_counts_as_likely_but_reports_no_probability(
    jev, repo, monkeypatch
):
    """Two distinct facts, and the gate depends on the second:
    the ADVICE leans risky (unknown = a reason to look), and NO condition reported a
    probability -- which is what lets the wrapper allow a blind check."""
    monkeypatch.setattr(
        jev, "_call_jev", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down"))
    )
    result = jev.jev_pr_risk(str(repo), "origin/main")
    assert result["tier"] == "high"  # advice leans risky
    assert all(c["probability"] is None for c in result["conditions"])  # no evidence
    assert result["escalated"] is True


def test_missing_config_advises_low_and_says_so(jev, tmp_path):
    result = jev.jev_pr_risk(str(tmp_path), "origin/main")
    assert result["config_error"]
    assert result["conditions"] == []

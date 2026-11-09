"""Risk-based delivery may accelerate tests but must never authorize a merge."""
import importlib.util
import sys
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[1] / "platform/submitqueue/jev_plan.py"
spec = importlib.util.spec_from_file_location("sq_jev_plan", MODULE)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

REQUIRED = ["bdd", "ci-success", "guarded-paths", "greenlane"]


def test_low_risk_may_skip_redundant_tests_but_not_required_check():
    a = {"tasks": [
        {"name": "fast-gate", "run": True, "probability": 1.0},
        {"name": "voice", "run": False, "probability": 0.05},
    ]}
    result = module.consolidate(a, {"tier": "low"}, REQUIRED)
    assert result["impacted_tasks"] == ["fast-gate"]
    assert result["mandatory_required_checks"] == sorted(REQUIRED)
    assert result["authorizes_merge"] is False


@pytest.mark.parametrize("bad", [
    {"escalated": True}, {"diff_error": "unreadable"},
    {"config_error": "no config"},
])
def test_jev_uncertainty_forces_all_tests(bad):
    a = {"tasks": [{"name": "voice", "run": False, "probability": 0.01},
                   {"name": "fast-gate", "run": True, "probability": 1.0}]}
    result = module.consolidate({**a, **bad}, {"tier": "low"}, REQUIRED)
    assert result["jev_state"] == "ESCALATED"
    assert set(result["impacted_tasks"]) == {"voice", "fast-gate"}
    assert result["advisory_risk"] == "UNKNOWN"


def test_model_unavailable_cannot_give_low_risk_decision():
    a = {"tasks": [{"name": "mcp", "run": False, "probability": None}]}
    result = module.consolidate(a, {"tier": "low", "escalated": True}, REQUIRED)
    assert result["impacted_tasks"] == ["mcp"]
    assert result["advisory_risk"] == "UNKNOWN"


def test_invalid_task_decision_rejected_not_skipped():
    with pytest.raises(ValueError):
        module.consolidate({"tasks": [{"foo": "bar"}]}, {"tier": "low"}, REQUIRED)


def test_canonical_required_contexts_include_greenlane():
    contexts = module.required_checks()
    assert "greenlane" in contexts
    assert "ci-success" in contexts
    assert len(contexts) >= 9


def test_exact_checkout_required_for_jev_cache(monkeypatch):
    with pytest.raises(ValueError):
        module.plan(Path("."), "not-sha", "not-sha")

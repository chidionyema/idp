"""BDD bindings for features/gates/judge-drift.feature.

Tests platform/eval/judge_drift.py and platform/eval/pareval_loop.py
without any database or network. Uses in-memory SQLite where needed.
"""

from __future__ import annotations

import importlib.util
import sqlite3
import sys
import tempfile
from pathlib import Path
from types import ModuleType

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/gates/judge-drift.feature")

REPO = Path(__file__).resolve().parents[3]
JUDGE_DRIFT = REPO / "platform" / "eval" / "judge_drift.py"
JUDGE_DRIFT_LOOP = REPO / "platform" / "eval" / "judge_drift_loop.py"
PAREVAL_LOOP = REPO / "platform" / "eval" / "pareval_loop.py"


def _seed_platform():
    """Seed platform.eval.protocol into sys.modules to avoid stdlib conflict."""
    from dataclasses import dataclass
    from typing import Literal, Protocol

    @dataclass
    class GateDecision:
        action: Literal["allow", "halt", "shadow"]
        evidence: str = ""
        confidence: float = 0.0

    @dataclass
    class LoopHealth:
        name: str
        mode: Literal["off", "shadow", "enforce"]
        last_run_at: str = ""
        last_error: str = ""
        is_healthy: bool = True

    class ControlLoop(Protocol):
        name: str

    pkg = sys.modules.get("platform")
    if not hasattr(pkg, "__path__"):
        m = ModuleType("platform")
        m.__path__ = []
        sys.modules["platform"] = m
    for sub in (
        "platform.eval",
        "platform.eval.protocol",
        "platform.telemetry",
        "platform.telemetry.agent_circuit_breaker",
    ):
        if sub not in sys.modules:
            sys.modules[sub] = ModuleType(sub)
    proto = sys.modules["platform.eval.protocol"]
    proto.GateDecision = GateDecision
    proto.LoopHealth = LoopHealth
    proto.ControlLoop = ControlLoop


def _load_judge_drift():
    _seed_platform()
    loader = importlib.machinery.SourceFileLoader("judge_drift_mod", str(JUDGE_DRIFT))
    spec = importlib.util.spec_from_loader("judge_drift_mod", loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["judge_drift_mod"] = mod
    loader.exec_module(mod)
    return mod


def _load_pareval():
    import importlib.machinery

    _seed_platform()
    # pareval_loop imports pareval_policy — stub it if absent
    for sub in ("platform.eval.pareval_policy",):
        if sub not in sys.modules:
            stub = ModuleType(sub)
            from dataclasses import dataclass

            @dataclass
            class Policy:
                max_tasks: int = 3

            stub.CODING_TASK_POLICY_MODEL_SWAP = Policy(max_tasks=3)
            stub.PolicyValidator = type(
                "PV", (), {"validate": staticmethod(lambda p: {"valid": True})}
            )
            sys.modules[sub] = stub
    loader = importlib.machinery.SourceFileLoader("pareval_loop_mod", str(PAREVAL_LOOP))
    spec = importlib.util.spec_from_loader("pareval_loop_mod", loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["pareval_loop_mod"] = mod
    loader.exec_module(mod)
    return mod


def _make_db_with_scores(scores: list[float]) -> str:
    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    f.close()
    with sqlite3.connect(f.name) as conn:
        conn.execute(
            "CREATE TABLE judge_verdicts (id INTEGER PRIMARY KEY, score REAL, created_at TEXT)"
        )
        for i, s in enumerate(scores):
            conn.execute(
                "INSERT INTO judge_verdicts (score, created_at) VALUES (?, datetime('now', ?))",
                (s, f"+{i} seconds"),
            )
    return f.name


import importlib.machinery


@pytest.fixture
def state():
    return {}


@pytest.fixture
def jd_mod():
    return _load_judge_drift()


# Background -------------------------------------------------------------------


@given("the judge drift module exists at platform/eval/judge_drift.py")
def _drift_exists():
    assert JUDGE_DRIFT.exists()


@given("the JudgeDriftLoop module exists at platform/eval/judge_drift_loop.py")
def _loop_exists():
    assert JUDGE_DRIFT_LOOP.exists()


# Scenario: JS divergence zero for identical distributions ---------------------


@given("a baseline distribution of all 0.8 scores")
def _baseline_high(state):
    state["baseline"] = [0.8] * 500


@given("a current window of all 0.8 scores")
def _current_high(state):
    state["current"] = [0.8] * 100


@given("a current window of all 0.2 scores")
def _current_low(state):
    state["current"] = [0.2] * 100


@when("JS divergence is computed")
def _compute_js(state, jd_mod):
    p = jd_mod.JudgeDriftSentinel._to_distribution(state["baseline"])
    q = jd_mod.JudgeDriftSentinel._to_distribution(state["current"])
    state["divergence"] = jd_mod._jensenshannon_divergence(p, q)


@then("the divergence is approximately 0.0")
def _div_zero(state):
    assert state["divergence"] < 0.01, f"expected ~0 got {state['divergence']}"


@then("the divergence is greater than 0.1")
def _div_nonzero(state):
    assert state["divergence"] > 0.1, f"expected >0.1 got {state['divergence']}"


# Scenario: partial window no alert --------------------------------------------


@given("a JudgeDriftSentinel with a current window of size 100")
def _sentinel_empty(state, jd_mod):
    db = _make_db_with_scores([0.8] * 500)
    sentinel = jd_mod.JudgeDriftSentinel(db_path=db, current_window=100)
    state["sentinel"] = sentinel


@when("fewer than 100 scores are recorded")
def _record_few(state):
    results = []
    for i in range(50):
        r = state["sentinel"].record_verdict(0.2)
        results.append(r)
    state["alerts"] = [r for r in results if r is not None]


@then("no drift alert is returned")
def _no_alert(state):
    assert state["alerts"] == [], f"expected no alerts, got {state['alerts']}"


# Scenario: drift alert fires when divergence exceeds threshold ----------------


@given("a JudgeDriftSentinel with threshold 0.15 and baseline of 500 high scores")
def _sentinel_with_baseline(state, jd_mod):
    db = _make_db_with_scores([0.9] * 500)
    sentinel = jd_mod.JudgeDriftSentinel(
        db_path=db, current_window=100, js_threshold=0.15
    )
    state["sentinel"] = sentinel


@when("100 low scores are recorded filling the window")
def _record_full_low(state):
    results = []
    for i in range(100):
        r = state["sentinel"].record_verdict(0.1)
        results.append(r)
    state["alerts"] = [r for r in results if r is not None]


@then("a drift alert is returned")
def _has_alert(state):
    assert len(state["alerts"]) > 0, "expected at least one drift alert"
    state["alert"] = state["alerts"][-1]


@then('the alert action is "judge_drift_detected"')
def _alert_action(state):
    assert state["alert"].get("alert") == "judge_drift_detected"


@then("the alert names the divergence value")
def _alert_has_divergence(state):
    assert "divergence" in state["alert"] or "js" in str(state["alert"]).lower()


# Scenario: JudgeDriftLoop pre_llm always allows --------------------------------


@given("a JudgeDriftLoop instance")
def _drift_loop(state):
    import importlib.machinery

    _seed_platform()
    # stub judge_drift dependency
    jd_stub = ModuleType("platform.eval.judge_drift")
    jd_stub.JudgeDriftSentinel = type(
        "JDS",
        (),
        {
            "__init__": lambda self, db_path: None,
            "record_verdict": lambda self, s: None,
            "_load_baseline": lambda self: None,
        },
    )
    jd_stub.GoldSetCalibrator = type(
        "GSC",
        (),
        {
            "__init__": lambda self, db_path: None,
        },
    )
    sys.modules["platform.eval.judge_drift"] = jd_stub
    sys.modules.setdefault(
        "platform.eval.judge_drift_loop", ModuleType("platform.eval.judge_drift_loop")
    )

    loader = importlib.machinery.SourceFileLoader(
        "judge_drift_loop_mod", str(JUDGE_DRIFT_LOOP)
    )
    spec = importlib.util.spec_from_loader("judge_drift_loop_mod", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    state["drift_loop"] = mod.JudgeDriftLoop(db_path=":memory:")
    state["GateDecision"] = sys.modules["platform.eval.protocol"].GateDecision


@when("pre_llm is called with any state")
def _call_pre_llm(state):
    state["decision"] = state["drift_loop"].pre_llm({"messages": []})


@then('the GateDecision action is "allow"')
def _decision_allow(state):
    assert state["decision"].action == "allow"


# Scenario: health check -------------------------------------------------------


@when("health is called")
def _call_health(state):
    state["health"] = state["drift_loop"].health()


@then('the mode is "shadow"')
def _mode_shadow(state):
    assert state["health"].mode == "shadow"


@then("is_healthy is true before any errors")
def _is_healthy(state):
    assert state["health"].is_healthy is True


# Scenario: ParEval halts at max_tasks -----------------------------------------


@given(parsers.parse("a ParEvalLoop with max_tasks set to {n:d}"))
def _pareval_loop(state, n):
    _seed_platform()
    mod = _load_pareval()
    policy = mod.CODING_TASK_POLICY_MODEL_SWAP.__class__(max_tasks=n)
    state["pareval"] = mod.ParEvalLoop(policy=policy)
    state["pareval_n"] = n


@given(parsers.parse("an agent state with {n:d} AI messages"))
def _agent_state(state, n):
    msgs = [
        type(
            "AIMessage", (), {"__class__": type("cls", (), {"__name__": "AIMessage"})}
        )()
        for _ in range(n)
    ]
    state["agent_state"] = {"messages": msgs}


@when("pre_llm is called")
def _pareval_pre_llm(state):
    state["decision"] = state["pareval"].pre_llm(state["agent_state"])


@then('the GateDecision action is "halt"')
def _decision_halt(state):
    assert state["decision"].action == "halt"


@then("the evidence names max_tasks")
def _evidence_max_tasks(state):
    assert "max_tasks" in state["decision"].evidence


@then('the GateDecision action is "allow"')
def _pareval_allow(state):
    assert state["decision"].action == "allow"

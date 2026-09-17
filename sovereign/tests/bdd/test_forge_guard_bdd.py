"""BDD bindings for features/gates/forge-guard.feature.

Tests forge/common.py budget + quality gates directly. No network, no GPU.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
import yaml
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/gates/forge-guard.feature")

REPO = Path(__file__).resolve().parents[3]
COMMON = REPO / "forge" / "common.py"
TASK_YAML = REPO / "forge" / "task.yaml"

REQUIRED_KEYS = [
    "task",
    "base",
    "kind",
    "prompt_template",
    "labels",
    "abstain_below",
    "min_agreement",
    "kv_cache_prefix",
    "compute",
]


def _load_common():
    spec = importlib.util.spec_from_file_location("forge_common", COMMON)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["forge_common"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def state():
    return {}


@pytest.fixture
def mod():
    return _load_common()


# Background -------------------------------------------------------------------


@given("the forge common module exists at forge/common.py")
def _common_exists():
    assert COMMON.exists(), f"not found: {COMMON}"


@given("the forge task contract exists at forge/task.yaml")
def _task_yaml_exists():
    assert TASK_YAML.exists(), f"not found: {TASK_YAML}"


# Scenario: task.yaml required fields ------------------------------------------


@when("the task file is loaded")
def _load_task(state):
    state["task"] = yaml.safe_load(TASK_YAML.read_text())


@then(parsers.parse('it contains the key "{key}"'))
def _has_key(state, key):
    assert key in state["task"], f"task.yaml missing key: {key!r}"


@then('the prompt_template contains "{input}"')
def _prompt_has_input(state):
    assert "{input}" in state["task"]["prompt_template"]


@then("the abstain_below is between 0 and 1 exclusive")
def _abstain_range(state):
    v = state["task"]["abstain_below"]
    assert 0 < v < 1


# Scenario: shipped task.yaml fits budget --------------------------------------


@when("the cost gate is applied to the shipped task.yaml")
def _cost_gate_shipped(state, mod):
    task = yaml.safe_load(TASK_YAML.read_text())
    state["result"] = mod.cost_gate(task)


@then("the cost gate returns no refusal reason")
def _no_refusal(state):
    assert state["result"] is None, f"unexpected refusal: {state['result']}"


# Scenario: within-budget run --------------------------------------------------


@given(
    parsers.parse(
        'a compute plan with GPU "{gpu}", timeout {timeout:d} seconds, budget USD {budget:f}'
    )
)
def _compute_plan(state, gpu, timeout, budget):
    state["plan"] = {
        "compute": {"gpu": gpu, "timeout_s": timeout, "budget_usd": budget}
    }


@when("the cost gate is applied")
def _cost_gate_plan(state, mod):
    state["result"] = mod.cost_gate(state["plan"])


# Scenario: over-budget run ----------------------------------------------------


@then("the cost gate returns a refusal reason")
def _has_refusal(state):
    assert state["result"] is not None, "expected a refusal reason but got None"


@then(parsers.parse('the refusal reason contains the expected cost "{cost}"'))
def _refusal_has_cost(state, cost):
    assert cost in state["result"], f"{cost!r} not in {state['result']!r}"


@then(parsers.parse('the refusal reason contains the declared budget "{budget}"'))
def _refusal_has_budget(state, budget):
    assert budget in state["result"], f"{budget!r} not in {state['result']!r}"


# Scenario: unpriced GPU -------------------------------------------------------


@given(parsers.parse('a compute plan with GPU "{gpu}" and budget USD {budget:f}'))
def _unpriced_plan(state, gpu, budget):
    state["plan"] = {"compute": {"gpu": gpu, "budget_usd": budget}}


@then(parsers.parse('the refusal reason contains "{text}"'))
def _refusal_contains(state, text):
    assert text in state["result"], f"{text!r} not in {state['result']!r}"


# Scenario: no GPU block defaults to T4 ----------------------------------------


@given("a compute plan with no GPU block")
def _empty_plan(state):
    state["plan"] = {}


@when("the default compute plan is resolved")
def _resolve_default(state, mod):
    state["resolved"] = mod.compute_plan(state["plan"])
    state["result"] = mod.cost_gate(state["plan"])


@then(parsers.parse('the GPU is "{gpu}"'))
def _gpu_is(state, gpu):
    assert state["resolved"]["gpu"] == gpu


# Scenario: T4 cost ------------------------------------------------------------


@when(parsers.parse("the T4 hourly cost is looked up for {seconds:d} seconds"))
def _t4_cost(state, seconds, mod):
    state["cost"] = mod.usd_for("T4", seconds)


@then(parsers.parse("the cost is {amount:f} USD"))
def _cost_is(state, amount):
    assert abs(state["cost"] - amount) < 0.01, f"expected {amount} got {state['cost']}"


# Scenario: dataset split minimum ----------------------------------------------


@given(parsers.parse("a dataset with {n:d} rows"))
def _dataset(state, n):
    state["rows"] = [{"input": f"text {i}", "output": str(i % 2)} for i in range(n)]


@when("the split function is called")
def _split(state, mod):
    try:
        state["split_result"] = mod.split(state["rows"])
        state["split_error"] = None
    except ValueError as e:
        state["split_error"] = e
        state["split_result"] = None


@then("a ValueError is raised")
def _value_error_raised(state):
    assert state["split_error"] is not None, "expected ValueError but none was raised"


# Scenario: split determinism and 80/20 ----------------------------------------


@when("the split function is called twice")
def _split_twice(state, mod):
    rows = state["rows"]
    state["split_a"] = mod.split(list(rows))
    state["split_b"] = mod.split(list(rows))


@then("both results are identical")
def _results_identical(state):
    assert state["split_a"] == state["split_b"]


@then(parsers.parse('{count:d} rows are labelled "{label}"'))
def _rows_labelled(state, count, label):
    actual = sum(1 for r in state["split_a"] if r.get("split") == label)
    assert actual == count, f"expected {count} {label!r} rows, got {actual}"


# Scenario: label probabilities ------------------------------------------------


@given("logit scores where both labels are equal")
def _equal_logits(state):
    state["logits"] = {"0": 2.0, "1": 2.0}


@when("label_probs is called")
def _label_probs(state, mod):
    state["top"], state["prob"], state["margin"] = mod.label_probs(state["logits"])


@then("the margin is 0.0")
def _margin_zero(state):
    assert abs(state["margin"]) < 1e-9


@then("the probability is 0.5")
def _prob_half(state):
    assert abs(state["prob"] - 0.5) < 1e-9


# Scenario: grade abstain rate -------------------------------------------------


@given("a set of predictions where 1 of 3 rows abstains below margin 0.8")
def _predictions(state):
    # (true_label, predicted_label, margin) — one entry has margin < 0.8 → abstains
    state["predictions"] = [("1", "1", 0.9), ("0", "1", 0.9), ("0", "0", 0.1)]


@when("grade is applied")
def _grade(state, mod):
    state["grade"] = mod.grade(state["predictions"], abstain_below=0.8)


@then(parsers.parse("held_out is {n:d}"))
def _held_out(state, n):
    assert state["grade"]["held_out"] == n


@then(parsers.parse("agreement is {v:f}"))
def _agreement(state, v):
    assert abs(state["grade"]["agreement"] - v) < 1e-6


@then(parsers.parse("abstain_rate is approximately {v:f}"))
def _abstain_rate(state, v):
    assert abs(state["grade"]["abstain_rate"] - v) < 0.01

"""Executable component coverage for the frontier assurance acceptance contract.

The complete end-to-end acceptance feature stays in the spec packet until its
trusted runtime steps are implemented. These steps execute production predicates,
real signatures and subprocess observations; no synthetic PR closure is asserted.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/assurance/frontier-core.feature")

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "frontier_assurance_test_support", ROOT / "tests/test_frontier_assurance_core.py"
)
assert SPEC is not None and SPEC.loader is not None
core = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = core
SPEC.loader.exec_module(core)
case = core.case  # shared real Ed25519 fixture; no duplicate fake signer


@pytest.fixture
def evidence_state():
    return {}


@given(parsers.parse('a signed candidate receipt with "{condition}"'))
def signed_case(case, evidence_state, condition):
    expected, receipt, sign, authenticate = case
    if condition == "forged signature":
        receipt["signature"] = "forged"
    elif condition == "stale base":
        expected["base"] = "0" * 40
    elif condition == "replayed nonce":
        expected["nonce_unused"] = False
    elif condition == "builder signer":
        receipt["signer"] = expected["builder"]
        sign(receipt)
    elif condition == "empty tests":
        receipt["checks"]["bdd"]["executed"] = 0
        sign(receipt)
    elif condition == "skipped check":
        receipt["checks"]["bdd"]["status"] = "SKIPPED"
        sign(receipt)
    elif condition == "malformed scope":
        expected["scope"] = receipt["scope"] = ["nsvee//engine.py"]
        sign(receipt)
    elif condition == "malformed roster":
        expected["verifiers"] = "qa"
    elif condition != "valid":
        raise ValueError(condition)
    evidence_state.update(expected=expected, receipt=receipt, authenticate=authenticate)


@when("the admission receipt is validated")
def validate(evidence_state):
    try:
        core.validate_admission_receipt(
            evidence_state["receipt"], evidence_state["expected"], now=20,
            authenticate=evidence_state["authenticate"],
        )
    except core.ReceiptError:
        evidence_state["decision"] = "refused"
    else:
        evidence_state["decision"] = "accepted"


@then(parsers.parse('the evidence decision is "{decision}"'))
def evidence_decision(evidence_state, decision):
    assert evidence_state["decision"] == decision


@given(parsers.parse('a pure function candidate with "{behavior}"'))
def candidate(evidence_state, behavior):
    artifacts = {
        "correct": "def solve(x): return x * 2",
        "wrong result": "def solve(x): return x + 2",
        "early exit": "raise SystemExit(0)",
        "extra output": "def solve(x): print('noise'); return x * 2",
    }
    evidence_state["artifact"] = artifacts[behavior]


@when("the independent observable oracle executes the case")
def observe(evidence_state):
    from nsvee import verify_json_cases

    runner = core.LocalFixtureRunner()
    evidence_state["report"] = verify_json_cases(
        evidence_state["artifact"], "solve",
        [{"args": [137], "kwargs": {}, "expected": 274}], runner=runner,
    )
    evidence_state["scripts"] = runner.scripts


@then(parsers.parse('the verification report status is "{status}"'))
def oracle_status(evidence_state, status):
    assert evidence_state["report"].status == status


@then("the expected answer is not sent to the candidate")
def hidden_expected(evidence_state):
    assert len(evidence_state["scripts"]) == 1
    assert "274" not in evidence_state["scripts"][0]


@given(parsers.parse('calibration observations with "{population}"'))
def population_data(evidence_state, population):
    populations = {
        "both correct classes": [(1, 1)] * 8 + [(0, 0)] * 8,
        "single class": [(1, 1)] * 50,
        "missing score": [(None, 1)],
        "minority unsupported": [(1, 1)] * 10 + [(0, 0)],
    }
    evidence_state["gold"] = populations[population]


@when("the binary calibration is evaluated")
def calibration(evidence_state):
    evidence_state["calibration"] = core.binary_calibration(evidence_state["gold"])


@then(parsers.parse('the calibration decision is "{status}"'))
def calibration_status(evidence_state, status):
    assert evidence_state["calibration"]["status"] == status


@given("mutant evidence with a timeout and a known survivor")
def mutant_data(evidence_state):
    evidence_state["mutants"] = {
        "timeout": {"status": "TIMEOUT"}, "survivor": {"status": "SURVIVED"}
    }


@when("both inventory orders are graded")
def mutation(evidence_state):
    evidence_state["mutation"] = [
        core.mutation_verdict(expected=order, results=evidence_state["mutants"])
        for order in (["timeout", "survivor"], ["survivor", "timeout"])
    ]


@then(parsers.parse('both mutation decisions are "{status}"'))
def mutation_status(evidence_state, status):
    assert evidence_state["mutation"] == [status, status]


@given("a fixed-horizon comparison with equal scores and insufficient observations")
def comparisons(evidence_state):
    evidence_state["rows"], evidence_state["policy"] = core.comparison_case(10, .5, .5)


@when("the fixed-horizon evaluator runs")
def evaluate_comparison(evidence_state):
    evidence_state["comparison"] = core.fixed_horizon_decision(
        evidence_state["rows"], **evidence_state["policy"]
    )


@then(parsers.parse('the comparison decision is "{status}"'))
def comparison_status(evidence_state, status):
    assert evidence_state["comparison"]["decision"] == status

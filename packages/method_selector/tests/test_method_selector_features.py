"""features/assurance/method-selector.feature, bound to the real selector library.

The founder's operational contract (OPERATIONAL_SPEC.md v0.1) states the BDD acceptance
clause; these are its scenarios. Every step runs against packages/method_selector/src/
method_selector - the same code the decision layer will import - and nothing is mocked,
because there is nothing to mock: the selector is a pure function over typed data.

The package uses the estate's src layout, so the library is put on the path here rather
than installed: the same rule packages/aei/tests/conftest.py follows.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from method_selector import SCHEMA_VERSION, get, select_safe  # noqa: E402

scenarios("../../../features/assurance/method-selector.feature")


def _evidence(kind, freshness="fresh", verified=True):
    return {
        "source_id": "src-" + kind,
        "source_type": "test",
        "kind": kind,
        "revision": "0123456789abcdef0123456789abcdef01234567",
        "observed_at": "2026-10-28T09:00:00Z",
        "freshness": freshness,
        "verified": verified,
    }


def _request(
    kind="regression",
    evidence=None,
    risk_tier="low",
    budget=None,
    contradictions=None,
    unavailable=None,
    authorized=None,
    schema_version=SCHEMA_VERSION,
):
    return {
        "schema_version": schema_version,
        "problem_id": "prob-001",
        "kind": kind,
        "source_revision": "0123456789abcdef0123456789abcdef01234567",
        "evidence_refs": [] if evidence is None else evidence,
        "risk_tier": risk_tier,
        "budget": budget
        or {
            "max_attempts": 12,
            "max_cost_usd": 1.0,
            "max_wall_seconds": 900,
            "exhausted": False,
        },
        "uncertainty": 0.4,
        "authority": "maintainer",
        "deadline": "2026-10-29T00:00:00Z",
        "idempotency_key": "idem-001",
        "provenance": {"source": "bdd"},
        "contradictions": contradictions or [],
        "unavailable_dependencies": unavailable or [],
        "authorized_actions": authorized or [],
    }


@pytest.fixture()
def world():
    return {"request": None, "selection": None, "second": None}


@given("a regression problem with repository history and a reproducible check")
def _given_regression(world):
    world["request"] = _request(
        kind="regression",
        evidence=[_evidence("repo_history"), _evidence("failing_check")],
    )


@given("a formal problem with a property specification and no system model")
def _given_formal_without_model(world):
    world["request"] = _request(
        kind="formal",
        evidence=[_evidence("property_spec")],
    )


@given("a high risk incident with a replayable environment and no authorization")
def _given_high_risk_unauthorised(world):
    world["request"] = _request(
        kind="incident",
        evidence=[_evidence("environment"), _evidence("timeline")],
        risk_tier="high",
    )


@given(
    "a high risk incident with a replayable environment and an explicit authorization"
)
def _given_high_risk_authorised(world):
    world["request"] = _request(
        kind="incident",
        evidence=[_evidence("environment"), _evidence("timeline")],
        risk_tier="high",
        authorized=["counterfactual_experiment"],
    )


@given("a regression problem with repository history and an exhausted budget")
def _given_exhausted_budget(world):
    world["request"] = _request(
        kind="regression",
        evidence=[_evidence("repo_history"), _evidence("failing_check")],
        budget={
            "max_attempts": 0,
            "max_cost_usd": 0.0,
            "max_wall_seconds": 0,
            "exhausted": True,
        },
    )


@given("a regression problem with repository history and contradictory observations")
def _given_contradictions(world):
    world["request"] = _request(
        kind="regression",
        evidence=[_evidence("repo_history"), _evidence("failing_check")],
        contradictions=["the failing test passes on the pinned revision"],
    )


@given("a regression problem with no evidence at all")
def _given_no_evidence(world):
    world["request"] = _request(kind="regression", evidence=[])


@given("a regression problem with only stale evidence")
def _given_stale_evidence(world):
    world["request"] = _request(
        kind="regression",
        evidence=[_evidence("repo_history", freshness="stale")],
    )


@given("a regression problem with repository history and an unavailable dependency")
def _given_unavailable_dependency(world):
    world["request"] = _request(
        kind="regression",
        evidence=[_evidence("repo_history"), _evidence("failing_check")],
        unavailable=["git"],
    )


@given("a request with an unknown schema version")
def _given_unknown_schema(world):
    world["request"] = _request(
        kind="regression",
        evidence=[_evidence("repo_history")],
        schema_version="method_selector.request.v99",
    )


@when("the selector runs")
def _when_select(world):
    world["selection"] = select_safe(world["request"])


@when("the selector runs twice")
def _when_select_twice(world):
    world["selection"] = select_safe(world["request"])
    world["second"] = select_safe(world["request"])


@when("the selector runs safely")
def _when_select_safely(world):
    world["selection"] = select_safe(world["request"])


@then("git bisect is the recommended method")
def _then_bisect(world):
    assert world["selection"].method_id == "git_bisect"


@then("Bayesian inference is not among the ranked candidates")
def _then_not_bayesian(world):
    ranked = [row["method_id"] for row in world["selection"].alternatives]
    assert "bayesian_inference" not in ranked


@then("the recommendation grants no execution authority")
def _then_no_authority(world):
    selection = world["selection"]
    assert selection.policy_decision == "ALLOW"
    assert "AUTHORIZATION_REQUIRED" not in selection.reason_codes
    assert get(selection.method_id).requires_authorization is False


@then("no method is recommended")
def _then_no_method(world):
    assert world["selection"].method_id is None
    assert world["selection"].rank == 0


@then("the decision is an abstention")
def _then_abstain(world):
    assert world["selection"].policy_decision == "ABSTAIN"
    assert world["selection"].abstained is True


@then("the decision is a refusal")
def _then_refuse(world):
    assert world["selection"].policy_decision == "REFUSE"


@then("the decision is reassessment")
def _then_reassess(world):
    assert world["selection"].policy_decision == "REASSESS"


@then("the missing prerequisite is the system model")
def _then_missing_model(world):
    probe = world["selection"].probe_request
    assert probe is not None
    assert "system_model" in probe["missing_prerequisites"]


@then("a bounded probe is requested instead of an invented prerequisite")
def _then_probe(world):
    probe = world["selection"].probe_request
    assert probe is not None
    assert probe["max_attempts"] >= 1
    assert probe["max_cost_usd"] >= 0.0
    assert probe["governed_by"] == "estate.executor"


@then("the counterfactual experiment is not recommended")
def _then_not_counterfactual(world):
    assert world["selection"].method_id != "counterfactual_experiment"


@then("the counterfactual experiment is recommended")
def _then_counterfactual(world):
    assert world["selection"].method_id == "counterfactual_experiment"


@then("the decision names the missing authorization")
def _then_authorization_missing(world):
    assert "AUTHORIZATION_REQUIRED" in world["selection"].reason_codes


@then("the decision requires authorization")
def _then_authorization_required(world):
    assert world["selection"].policy_decision == "REQUIRE_AUTHORIZATION"


@then("the decision is a refusal because the budget is exhausted")
def _then_budget_exhausted(world):
    assert world["selection"].policy_decision == "REFUSE"
    assert "BUDGET_EXHAUSTED" in world["selection"].reason_codes
    assert "NO_METHOD_SCHEDULED" in world["selection"].reason_codes


@then("the contradictions are carried in the selection")
def _then_contradictions_carried(world):
    assert world["selection"].contradictions


@then("the decision names the unavailable dependency")
def _then_dependency(world):
    assert "DEPENDENCY_UNAVAILABLE" in world["selection"].reason_codes


@then("both selections carry the same fingerprint")
def _then_same_fingerprint(world):
    assert world["selection"].fingerprint == world["second"].fingerprint


@then("both selections carry the same trace id")
def _then_same_trace(world):
    assert world["selection"].trace_id == world["second"].trace_id


@then("both selections carry the same method")
def _then_same_method(world):
    assert world["selection"].method_id == world["second"].method_id


@then("the reason code is an unknown schema version")
def _then_unknown_schema(world):
    assert "UNKNOWN_SCHEMA_VERSION" in world["selection"].reason_codes

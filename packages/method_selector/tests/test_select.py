"""Unit and negative tests for the method selector (SF-1).

The negative tests are the point: a selector that guesses is worse than no selector, so
every "I do not know" path is pinned here as a refusal, an abstention or an error.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from method_selector import (  # noqa: E402
    METHODS,
    ContractError,
    PREREQUISITE_SATISFIERS,
    SelectionOutcome,
    assess_outcome,
    get,
    select,
    select_safe,
    validate_request,
)


def _evidence(kind, freshness="fresh"):
    return {
        "source_id": "src-" + kind,
        "source_type": "test",
        "kind": kind,
        "revision": "0" * 40,
        "observed_at": "2026-10-28T09:00:00Z",
        "freshness": freshness,
        "verified": True,
    }


def _request(**overrides):
    payload = {
        "schema_version": "method_selector.request.v1",
        "problem_id": "prob-001",
        "kind": "regression",
        "source_revision": "0" * 40,
        "evidence_refs": [_evidence("repo_history"), _evidence("failing_check")],
        "risk_tier": "low",
        "budget": {
            "max_attempts": 12,
            "max_cost_usd": 1.0,
            "max_wall_seconds": 900,
            "exhausted": False,
        },
        "uncertainty": 0.4,
        "authority": "maintainer",
        "deadline": "2026-10-29T00:00:00Z",
        "idempotency_key": "idem-001",
        "provenance": {"source": "unit"},
        "contradictions": [],
        "unavailable_dependencies": [],
        "authorized_actions": [],
    }
    payload.update(overrides)
    return payload


# -- contract validation -------------------------------------------------------


def test_unknown_schema_version_is_rejected():
    with pytest.raises(ContractError) as error:
        validate_request(_request(schema_version="method_selector.request.v99"))
    assert error.value.reason_code == "UNKNOWN_SCHEMA_VERSION"


def test_unknown_problem_kind_is_rejected():
    with pytest.raises(ContractError) as error:
        validate_request(_request(kind="vibes"))
    assert error.value.reason_code == "UNKNOWN_PROBLEM_KIND"


def test_unknown_risk_tier_is_rejected():
    with pytest.raises(ContractError) as error:
        validate_request(_request(risk_tier="apocalyptic"))
    assert error.value.reason_code == "UNKNOWN_RISK_TIER"


def test_unknown_authority_is_rejected():
    with pytest.raises(ContractError) as error:
        validate_request(_request(authority="the-vibes"))
    assert error.value.reason_code == "UNKNOWN_AUTHORITY"


def test_uncertainty_out_of_range_is_rejected():
    with pytest.raises(ContractError) as error:
        validate_request(_request(uncertainty=1.4))
    assert error.value.reason_code == "OUT_OF_RANGE_UNCERTAINTY"


def test_budget_attempts_must_be_an_integer():
    payload = _request()
    payload["budget"]["max_attempts"] = 2.5
    with pytest.raises(ContractError) as error:
        validate_request(payload)
    assert error.value.reason_code == "OUT_OF_RANGE_BUDGET"


def test_budget_attempts_cannot_be_negative():
    payload = _request()
    payload["budget"]["max_attempts"] = -1
    with pytest.raises(ContractError) as error:
        validate_request(payload)
    assert error.value.reason_code == "OUT_OF_RANGE_BUDGET"


def test_missing_required_field_is_rejected():
    payload = _request()
    del payload["problem_id"]
    with pytest.raises(ContractError) as error:
        validate_request(payload)
    assert error.value.reason_code == "MALFORMED_REQUEST"


def test_malformed_evidence_is_rejected():
    payload = _request(evidence_refs=[{"source_id": "src-1"}])
    with pytest.raises(ContractError) as error:
        validate_request(payload)
    assert error.value.reason_code == "MALFORMED_EVIDENCE"


def test_unknown_freshness_is_rejected():
    payload = _request(
        evidence_refs=[dict(_evidence("repo_history"), freshness="vivid")]
    )
    with pytest.raises(ContractError) as error:
        validate_request(payload)
    assert error.value.reason_code == "MALFORMED_EVIDENCE"


# -- fingerprints ---------------------------------------------------------------


def test_fingerprint_ignores_deadline_and_idempotency_key():
    first = validate_request(_request())
    second = validate_request(
        _request(deadline="2030-01-01T00:00:00Z", idempotency_key="idem-999")
    )
    assert first.fingerprint() == second.fingerprint()


def test_fingerprint_changes_with_the_evidence():
    first = validate_request(_request())
    second = validate_request(
        _request(
            evidence_refs=[
                _evidence("repo_history"),
                _evidence("failing_check"),
                _evidence("timeline"),
            ]
        )
    )
    assert first.fingerprint() != second.fingerprint()


def test_fingerprint_is_stable_across_calls():
    request = validate_request(_request())
    assert request.fingerprint() == request.fingerprint()
    assert request.fingerprint().startswith("sha256:")


# -- selection ------------------------------------------------------------------


def test_regression_with_history_selects_bisect():
    selection = select(_request())
    assert selection.method_id == "git_bisect"
    assert selection.policy_decision == "ALLOW"
    assert selection.rank == 1
    assert selection.authority == "maintainer"


def test_selection_is_deterministic():
    first = select(_request()).to_dict()
    second = select(_request()).to_dict()
    assert first == second


def test_bayesian_is_not_a_candidate_for_a_regression():
    selection = select(_request())
    ranked = [row["method_id"] for row in selection.alternatives]
    assert "bayesian_inference" not in ranked


def test_formal_without_a_model_is_not_guessed():
    payload = _request(kind="formal", evidence_refs=[_evidence("property_spec")])
    selection = select(payload)
    assert selection.method_id is None
    assert selection.policy_decision == "ABSTAIN"
    assert selection.probe_request["missing_prerequisites"] == ["system_model"]


def test_exhausted_budget_schedules_nothing():
    payload = _request()
    payload["budget"]["exhausted"] = True
    selection = select(payload)
    assert selection.method_id is None
    assert selection.policy_decision == "REFUSE"
    assert "BUDGET_EXHAUSTED" in selection.reason_codes


def test_no_evidence_abstains():
    selection = select(_request(evidence_refs=[]))
    assert selection.method_id is None
    assert selection.policy_decision == "ABSTAIN"
    assert selection.probe_request["reason_code"] == "NO_EVIDENCE"


def test_stale_evidence_abstains():
    selection = select(
        _request(evidence_refs=[_evidence("repo_history", freshness="stale")])
    )
    assert selection.method_id is None
    assert selection.policy_decision == "ABSTAIN"
    assert selection.probe_request["reason_code"] == "STALE_EVIDENCE"


def test_high_risk_experimental_method_needs_authorization():
    payload = _request(
        kind="incident",
        risk_tier="high",
        evidence_refs=[_evidence("environment"), _evidence("timeline")],
    )
    selection = select(payload)
    assert selection.method_id != "counterfactual_experiment"
    assert "AUTHORIZATION_REQUIRED" in selection.reason_codes


def test_authorized_experimental_method_is_recommendation_only():
    payload = _request(
        kind="incident",
        risk_tier="high",
        evidence_refs=[_evidence("environment"), _evidence("timeline")],
        authorized_actions=["counterfactual_experiment"],
    )
    selection = select(payload)
    assert selection.method_id == "counterfactual_experiment"
    assert selection.policy_decision == "REQUIRE_AUTHORIZATION"
    assert "RECOMMENDATION_ONLY" in selection.reason_codes


def test_contradictions_force_reassessment():
    selection = select(_request(contradictions=["the pin is not the failing revision"]))
    assert selection.policy_decision == "REASSESS"
    assert "CONTRADICTORY_OBSERVATIONS" in selection.reason_codes
    assert selection.contradictions


def test_unavailable_dependency_is_reported():
    selection = select(_request(unavailable_dependencies=["git"]))
    assert selection.method_id is None
    assert "DEPENDENCY_UNAVAILABLE" in selection.reason_codes


def test_malformed_request_through_select_safe_is_a_refusal():
    selection = select_safe({"schema_version": "nope"})
    assert selection.policy_decision == "REFUSE"
    assert "UNKNOWN_SCHEMA_VERSION" in selection.reason_codes
    assert selection.method_id is None


def test_select_raises_on_a_malformed_request():
    with pytest.raises(ContractError):
        select({"schema_version": "method_selector.request.v1"})


def test_every_recommendation_is_marked_unverified():
    selection = select(_request())
    assert selection.evaluation_status == "UNVERIFIED"


# -- catalogue invariants -------------------------------------------------------


def test_catalogue_entries_are_unique():
    ids = [method.method_id for method in METHODS]
    assert len(ids) == len(set(ids))


def test_every_prerequisite_is_satisfiable_by_some_evidence_kind():
    for method in METHODS:
        for prereq in method.prerequisites:
            assert prereq in PREREQUISITE_SATISFIERS
            assert PREREQUISITE_SATISFIERS[prereq]


def test_every_method_carries_its_documentation():
    for method in METHODS:
        assert method.references
        assert method.anti_patterns
        assert method.expected_evidence
        assert method.stop_conditions
        assert method.switch_conditions
        assert method.verifier
        assert method.tool_scopes
        assert method.problem_kinds
        assert method.version


def test_every_method_is_marked_unverified_in_its_own_record():
    for method in METHODS:
        assert method.to_dict()["evaluation_status"] == "UNVERIFIED"


def test_unknown_method_lookup_raises():
    with pytest.raises(KeyError):
        get("no_such_method")


# -- outcomes -------------------------------------------------------------------


def test_an_outcome_without_a_verifier_stays_unverified():
    outcome = SelectionOutcome(
        attempt_id="attempt-1",
        artifact_refs=("artifact://1",),
        verifier="",
        verdict="VERIFIED",
        counterexamples=(),
        actual_cost=0.01,
        elapsed=1.0,
        switch_reason=None,
    )
    assert assess_outcome(outcome) == "UNVERIFIED"


def test_an_independently_verified_outcome_keeps_its_verdict():
    outcome = SelectionOutcome(
        attempt_id="attempt-1",
        artifact_refs=("artifact://1",),
        verifier="nsvee.verify_artifact",
        verdict="VERIFIED",
        counterexamples=(),
        actual_cost=0.01,
        elapsed=1.0,
        switch_reason=None,
    )
    assert assess_outcome(outcome) == "VERIFIED"

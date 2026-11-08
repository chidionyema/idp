"""BDD acceptance of typed automation contracts; no live infrastructure required."""

from __future__ import annotations

import copy

import pytest

from sovereign.automation.contracts import (
    _validate_dag,
    catalogue,
    compile_request,
    find,
    verify_plan,
)


@pytest.fixture
def automation_request():
    return {
        "id": "router-recovery",
        "version": "1.0.0",
        "request_id": "recover-router-20261108",
        "surface": "cli",
        "actor": "svc:estate-router",
        "inputs": {
            "repository": "chidionyema/idp",
            "candidate_url": "https://llm-recovery.mumchimp.com",
        },
    }


@pytest.fixture
def release():
    return {
        "source_sha": "a" * 40,
        "artifact_digest": "sha256:" + "b" * 64,
        "config_digest": "sha256:" + "c" * 64,
    }


def test_outcome_first_discovery_generated_from_implementation():
    assert [m["id"] for m in find("recover router")] == ["router-recovery"]
    assert catalogue()[0]["input_schema"]["properties"]["cutover"] == {"const": False}


def test_compiled_plan_is_stable_and_provenance_bound(automation_request, release):
    p = compile_request(automation_request, release)
    assert p == compile_request(automation_request, release)
    verify_plan(p)
    assert p["workflow_id"].startswith("estate-auto:router-recovery:")
    assert set(s["id"] for s in p["steps"]) == {
        "dispatch",
        "observe",
        "health",
        "models",
        "completion",
    }
    assert {s["id"] for s in p["steps"] if s["deps"] == ["observe"]} == {
        "health",
        "models",
    }
    assert p["max_concurrency"] == 2
    q = copy.deepcopy(p)
    q["steps"][0]["inputs"]["repository"] = "attacker/other"
    with pytest.raises(ValueError, match="mutated"):
        verify_plan(q)


def test_invalid_request_denies_unsafe_cutover(automation_request, release):
    automation_request["inputs"]["cutover"] = True
    with pytest.raises(ValueError, match="invalid automation inputs"):
        compile_request(automation_request, release)


def test_input_schema_refuses_unknown_fields(automation_request, release):
    automation_request["inputs"]["shell"] = "rm -rf /"
    with pytest.raises(ValueError, match="invalid automation inputs"):
        compile_request(automation_request, release)


def test_unknown_contract_or_identity_fails_closed(automation_request, release):
    automation_request["version"] = "2.0.0"
    with pytest.raises(ValueError, match="unknown/incompatible"):
        compile_request(automation_request, release)
    automation_request["version"] = "1.0.0"
    automation_request["actor"] = "founder"
    with pytest.raises(PermissionError, match="lacks authority"):
        compile_request(automation_request, release)


def test_release_unknown_makes_automation_read_only(automation_request, release):
    release["source_sha"] = "main"
    with pytest.raises(ValueError, match="release identity"):
        compile_request(automation_request, release)
    del release["artifact_digest"]
    with pytest.raises(ValueError, match="provenance"):
        compile_request(automation_request, release)


def test_idempotency_key_and_actor_participate_in_workflow_identity(
    automation_request, release
):
    first = compile_request(automation_request, release)
    automation_request["request_id"] = "recover-router-new-request"
    second = compile_request(automation_request, release)
    assert first["workflow_id"] != second["workflow_id"]
    assert first["plan_hash"] != second["plan_hash"]


def test_cycle_missing_parent_and_duplicate_rejected(automation_request, release):
    steps = compile_request(automation_request, release)["steps"]
    bad = copy.deepcopy(steps)
    bad[0]["deps"] = ["completion"]
    with pytest.raises(ValueError, match="cycle"):
        _validate_dag(bad, 2)
    bad = copy.deepcopy(steps)
    bad[0]["deps"] = ["missing"]
    with pytest.raises(ValueError, match="dependency"):
        _validate_dag(bad, 2)
    bad = copy.deepcopy(steps)
    bad[1]["id"] = "dispatch"
    with pytest.raises(ValueError, match="duplicate"):
        _validate_dag(bad, 2)


def test_all_activities_bounded_and_no_unapproved_retry(automation_request, release):
    steps = compile_request(automation_request, release)["steps"]
    assert all(s["timeout_s"] <= 600 and 1 <= s["max_attempts"] <= 5 for s in steps)
    assert next(s for s in steps if s["id"] == "dispatch")["max_attempts"] == 1

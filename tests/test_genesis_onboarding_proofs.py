"""Executable adversarial fixtures for Genesis onboarding's seven proof claims.

The contract is deliberately not an eighth admission gate: this checks
*shape*, never verifies live sources or grants privileges. Those belong to
the canonical context broker and existing trusted DoF/action door.
"""
from __future__ import annotations

import copy
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "platform"))

from estate.context.onboarding_proofs import (  # noqa: E402
    KINDS,
    VERSION,
    assess_portfolio,
    fresh_portfolio,
)


def packet() -> dict:
    return fresh_portfolio(
        instruction_id="I-1001",
        mission_id="M-1001",
        session_id="S-pi-001",
        surface_kind="pi",
        context_receipt_ref="broker:context:sha256:example",
        requested_at="2026-11-08T10:00:00Z",
    )


def cite(label: str) -> dict:
    return {
        "kind": "estate_receipt",
        "ref": f"receipt:{label}",
        "version_or_observed_at": "2026-11-08T10:00:00Z",
    }


DETAILS = {
    "continuous_self_improvement": {
        "failure_class_ref": "fcr:lane-false-success",
        "correction_ref": "commit:ef12b3c7",
        "regression_ref": "ci:run:123",
        "independent_adoption_refs": ["pi:session:1", "cloud:session:2"],
        "recurrence_observation_ref": "observation:two-sessions",
    },
    "research": {
        "research_question": "Which current executor supports this task?",
        "prior_art_ref": "oracle:current-decisions",
        "method_ref": "eval:source-coverage",
        "finding_ref": "context:answer:1",
        "uncertainty_ref": "context:blind-sources",
        "decision_ref": "plan:choose-existing-tool",
    },
    "optimisation": {
        "objective": "minimise time to first correct action",
        "direction": "MINIMISE",
        "before": 87.4,
        "after": 19.2,
        "unit": "seconds",
        "method_ref": "instrument:mission-clock",
        "constraint_refs": ["guardrail:security", "guardrail:accuracy"],
        "comparison_ref": "eval:cohort:same-provider",
    },
    "automation": {
        "trigger_ref": "workflow:incident",
        "executor_ref": "temporal:run",
        "unattended_run_ref": "runtime:founder-off",
        "independent_effect_ref": "probe:service-restored",
        "failure_drill_ref": "drill:worker-died",
    },
    "friction_reduction": {
        "metric": "calls-to-first-correct-action",
        "before": 12,
        "after": 2,
        "unit": "tool calls/mission",
        "before_n": 20,
        "after_n": 20,
        "measurement_method_ref": "telemetry:session-traces",
        "same_population_ref": "eval:matched-missions",
    },
    "reflection": {
        "expected_ref": "plan:expected-outcome",
        "observed_ref": "runtime:actual-outcome",
        "gap": "retry caused duplicate discovery",
        "cause": "old CLI tool returned success without a remote ref",
        "correction_or_followup_ref": "fcr:delivery-truth",
    },
    "founder_awareness": {
        "source_ref": "founder:prompt:source-hash",
        "decision_ref": "decision:record:1",
        "supersession_check_ref": "oracle:temporal-precedence",
        "relevance": "minimise agent rediscovery and false-green receipts",
        "effect_on_plan_ref": "plan:existing-tool-only",
    },
}


def claim(p: dict, kind: str) -> None:
    p["proofs"][kind] = {
        "state": "CLAIMED",
        "details": copy.deepcopy(DETAILS[kind]),
        "evidence_refs": [cite(kind)],
    }


def test_fresh_session_has_all_seven_unearned_not_an_invisible_global_gate():
    p = packet()
    out = assess_portfolio(p)
    assert p["contract_version"] == VERSION
    assert tuple(p["proofs"]) == KINDS
    assert all(s["state"] == "NOT_YET_EARNED" for s in p["proofs"].values())
    assert out["verdict"] == "STRUCTURALLY_VALID_UNVERIFIED"
    assert out["trusted_evidence_resolve_required"] == []
    assert not out["effect_verified"] and not out["authority_granted"]


def test_all_seven_well_formed_claims_still_cannot_grant_dof_or_operational_state():
    p = packet()
    for kind in KINDS:
        claim(p, kind)
    p["admission_stage"] = "PATCH_READY"
    out = assess_portfolio(p)
    assert out["verdict"] == "STRUCTURALLY_VALID_UNVERIFIED", out["errors"]
    assert set(out["trusted_evidence_resolve_required"]) == set(KINDS)
    assert out["authority_granted"] is False
    assert out["effect_verified"] is False


def test_agent_cannot_self-certify_pass_or_founder_approval():
    p = packet()
    p["proofs"]["founder_awareness"]["state"] = "VERIFIED"
    assert assess_portfolio(p)["verdict"] == "INVALID"
    p = packet()
    p["founder_signature"] = "I approve"
    assert assess_portfolio(p)["verdict"] == "INVALID"
    p = packet()
    claim(p, "founder_awareness")
    p["proofs"]["founder_awareness"]["details"]["founder_approval"] = True
    assert assess_portfolio(p)["verdict"] == "INVALID"


def test_claimed_proof_requires_source_pointers_not_just_prose():
    p = packet()
    claim(p, "research")
    p["proofs"]["research"]["evidence_refs"] = []
    assert "requires source references" in " ".join(assess_portfolio(p)["errors"])


def test_research_must_name_existing_knowledge_and_uncertainty():
    p = packet()
    claim(p, "research")
    del p["proofs"]["research"]["details"]["prior_art_ref"]
    del p["proofs"]["research"]["details"]["uncertainty_ref"]
    err = " ".join(assess_portfolio(p)["errors"])
    assert "prior_art_ref" in err and "uncertainty_ref" in err


def test_optimisation_needs_explicit_objective_metric_guardrails_and_comparator():
    p = packet()
    claim(p, "optimisation")
    d = p["proofs"]["optimisation"]["details"]
    del d["objective"]
    d["before"] = "twelve"
    d["direction"] = "BIGGER"
    d["constraint_refs"] = []
    err = " ".join(assess_portfolio(p)["errors"])
    assert all(s in err for s in ("objective", "before", "direction", "constraint_refs"))


def test_automation_claim_requires_unattended_and_independent_effect():
    p = packet()
    claim(p, "automation")
    del p["proofs"]["automation"]["details"]["unattended_run_ref"]
    del p["proofs"]["automation"]["details"]["independent_effect_ref"]
    assert all(s in " ".join(assess_portfolio(p)["errors"])
               for s in ("unattended_run_ref", "independent_effect_ref"))


def test_friction_metrics_require_numeric_measurements_and_real_sample_sizes():
    p = packet()
    claim(p, "friction_reduction")
    d = p["proofs"]["friction_reduction"]["details"]
    d["before_n"] = 0
    d["after_n"] = 2.5
    d["after"] = float("nan")
    err = " ".join(assess_portfolio(p)["errors"])
    assert all(x in err for x in ("before_n", "after_n", "after"))


def test_reflection_records_both_observed_outcome_and_correction():
    p = packet()
    claim(p, "reflection")
    del p["proofs"]["reflection"]["details"]["observed_ref"]
    del p["proofs"]["reflection"]["details"]["correction_or_followup_ref"]
    err = " ".join(assess_portfolio(p)["errors"])
    assert "observed_ref" in err and "correction_or_followup_ref" in err


def test_founder_memory_requires_provenance_supersession_and_plan_effect():
    p = packet()
    claim(p, "founder_awareness")
    del p["proofs"]["founder_awareness"]["details"]["supersession_check_ref"]
    del p["proofs"]["founder_awareness"]["details"]["effect_on_plan_ref"]
    err = " ".join(assess_portfolio(p)["errors"])
    assert "supersession_check_ref" in err and "effect_on_plan_ref" in err


def test_self_improvement_is_not_one_session_patting_itself_on_back():
    p = packet()
    claim(p, "continuous_self_improvement")
    p["proofs"]["continuous_self_improvement"]["details"][
        "independent_adoption_refs"
    ] = ["same-session", "same-session"]
    assert "two distinct" in " ".join(assess_portfolio(p)["errors"])


def test_blind_source_must_name_the_safe_next_estate_tool():
    p = packet()
    p["proofs"]["founder_awareness"] = {
        "state": "BLIND", "details": {}, "evidence_refs": [],
    }
    assert "BLIND requires" in " ".join(assess_portfolio(p)["errors"])
    p["proofs"]["founder_awareness"]["reason"] = "archive unavailable"
    p["proofs"]["founder_awareness"]["next_estate_action"] = (
        "estate_context_status:inspect-source-coverage"
    )
    assert assess_portfolio(p)["verdict"] == "STRUCTURALLY_VALID_UNVERIFIED"


def test_not_applicable_needs_a_policy_receipt_and_still_requires_verification():
    p = packet()
    p["proofs"]["optimisation"]["state"] = "NOT_APPLICABLE"
    assert "policy receipt" in " ".join(assess_portfolio(p)["errors"])
    p["proofs"]["optimisation"]["policy_receipt_ref"] = "dof:policy:example"
    out = assess_portfolio(p)
    assert out["verdict"] == "STRUCTURALLY_VALID_UNVERIFIED"
    assert out["trusted_evidence_resolve_required"] == ["optimisation"]


def test_unknown_schema_or_added_eighth_self_authorisation_is_refused():
    p = packet()
    p["contract_version"] = "v99"
    p["proofs"]["agent_approved"] = {"state": "CLAIMED"}
    err = " ".join(assess_portfolio(p)["errors"])
    assert "unsupported" in err and "seven canonical" in err


def test_fake_sha_and_unresolved_receipt_are_only_unverified_client_claims():
    p = packet()
    claim(p, "research")
    p["proofs"]["research"]["evidence_refs"] = [
        {"kind": "github", "ref": "fake:unresolvable",
         "version_or_observed_at": "invented"}
    ]
    out = assess_portfolio(p)
    assert out["verdict"] == "STRUCTURALLY_VALID_UNVERIFIED"
    assert not out["authority_granted"] and not out["effect_verified"]


def test_no_secret_values_or_extra_fields_can_enter_the_portfolio():
    p = packet()
    p["proofs"]["automation"]["api_key"] = "never-accept-keys"
    assert assess_portfolio(p)["verdict"] == "INVALID"
    p = packet()
    claim(p, "automation")
    p["proofs"]["automation"]["details"]["access_token"] = "token"
    assert assess_portfolio(p)["verdict"] == "INVALID"


def test_untrusted_or_malformed_packet_is_not_an_authority_grant():
    for bad in (None, [], "yes", {"contract_version": VERSION}):
        out = assess_portfolio(bad)
        assert out["verdict"] == "INVALID"
        assert out["authority_granted"] is False
        assert out["effect_verified"] is False


def test_portfolio_contract_is_discoverable_through_the_existing_broker(monkeypatch):
    from estate.context import server

    monkeypatch.setattr(server, "_index_manifest", lambda: {"commit": "tested-sha"})
    monkeypatch.setattr(server, "_engine_reachable", lambda: False)
    response = server.tool_estate_context_status({})
    body = response["structuredContent"]
    assert body["indexed_commit"] == "tested-sha"
    assert body["engine_reachable"] is False
    proof = body["onboarding_proof_contract"]
    assert proof["version"] == VERSION
    assert tuple(proof["kinds"]) == KINDS
    assert proof["grants_authority"] is False
    assert proof["verdict"] == "STRUCTURE_ONLY"
    # No third service or tool for onboarding: existing MCP broker stays the door.
    assert set(server.TOOL_FUNCS) == {"estate_context", "estate_context_status"}

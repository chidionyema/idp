"""The reasoning layer (Interface 3)."""

from __future__ import annotations

from efda.contract import build_artifact
from efda.packs import baseline_pack
from efda.reasoning import reason


def artifact(
    failure_class="exit_nonzero",
    kinds=("checkpoint", "log_tail", "pod_state"),
    hypotheses=None,
):
    return build_artifact(
        component_id="efda-test-agent",
        component_class="efda-test-agent",
        component_kind="agent",
        runner_id="efda-test-run-020",
        failure_class=failure_class,
        attempted_operation="run_to_completion",
        invariant_broken="exit_zero",
        triggering_step="process_exit",
        capture_method="supervisor_wrapper",
        payloads=[{"kind": kind, "uri": f"efda:{kind}"} for kind in kinds],
        hypotheses=hypotheses if hypotheses is not None else [],
        cluster="oke",
        namespace="default",
    )


def specialist_pack():
    """A pack whose confidence was earned: the specialist tier."""
    pack = baseline_pack("efda-test-agent")
    pack["spec"]["coverageTier"] = "specialist"
    for signature in pack["spec"]["signatures"]:
        signature["confidenceBase"] = 0.6
    return pack


def test_a_matching_signature_produces_a_diagnosis():
    report = reason(artifact(), specialist_pack())
    assert report["status"] == "DIAGNOSED"
    assert report["cause"]
    assert report["confidence"] >= 0.5
    assert report["evidenceRefs"]
    assert report["packRef"].startswith("efda-test-agent-v0@")


def test_a_baseline_pack_does_not_claim_a_cause_it_has_not_earned():
    report = reason(artifact(), baseline_pack("efda-test-agent"))
    assert report["status"] == "NEEDS_HUMAN"
    assert report["confidence"] < 0.5


def test_a_thin_artifact_falls_back_to_a_human():
    pack = baseline_pack("efda-test-agent")
    report = reason(artifact(kinds=("checkpoint",)), pack)
    assert report["status"] == "NEEDS_HUMAN"
    assert "questionsAsked" in report


def test_a_tampered_artifact_is_refused():
    pack = baseline_pack("efda-test-agent")
    broken = artifact()
    broken["raw_evidence"]["payloads"][0]["uri"] = "efda:tampered"
    report = reason(broken, pack)
    assert report["status"] == "TAMPER_DETECTED"


def test_a_pack_with_the_wrong_interface_version_is_refused():
    pack = baseline_pack("efda-test-agent")
    pack["spec"]["interfaceVersion"] = "v0"
    report = reason(artifact(), pack)
    assert report["status"] == "SKILLPACK_INCOMPATIBLE"


def test_an_uncorroborated_hypothesis_is_not_propagated():
    pack = baseline_pack("efda-test-agent")
    claimed = [
        {
            "rank": 1,
            "cause": "the disk filled up",
            "confidence": 0.9,
            "source": "component",
        }
    ]
    report = reason(artifact(hypotheses=claimed), pack)
    assert any("UNCORROBORATED_HYPOTHESIS" in warning for warning in report["warnings"])
    assert report["cause"] != "the disk filled up"


def test_a_budget_breach_is_recorded_and_the_next_signature_is_tried():
    pack = baseline_pack("efda-test-agent")
    pack["spec"]["signatures"] = [
        {
            "id": "runaway",
            "symptom": "never ends",
            "matchLogic": 'failure_boundary.failure_class matches "(a+)+$"',
            "cause": "runaway",
            "confidenceBase": 0.9,
        },
        {
            "id": "honest",
            "symptom": "the honest one",
            "matchLogic": 'failure_boundary.failure_class == "exit_nonzero"',
            "cause": "the process exited non-zero",
            "confidenceBase": 0.35,
        },
    ]
    report = reason(artifact(), pack)
    assert report["budgetBreaches"]
    assert report["signatureId"] == "honest"


def test_the_report_names_the_signature_and_the_evidence():
    pack = baseline_pack("efda-test-agent")
    report = reason(artifact(), pack)
    assert report["signatureId"]
    assert report["evidenceRefs"][0].startswith("raw_evidence.payloads[")

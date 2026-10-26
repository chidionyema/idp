"""The five adversarial checks the pack factory runs."""

from __future__ import annotations

from efda.contract import build_artifact
from efda.validation import (
    PRECISION_FLOOR,
    RECALL_FLOOR,
    validate_pack,
    validate_signature,
)


def artifact(failure_class="exit_nonzero"):
    return build_artifact(
        component_id="efda-test-agent",
        component_class="efda-test-agent",
        component_kind="agent",
        runner_id="efda-test-run-030",
        failure_class=failure_class,
        attempted_operation="run_to_completion",
        invariant_broken="exit_zero",
        triggering_step="process_exit",
        capture_method="supervisor_wrapper",
        payloads=[{"kind": "checkpoint", "uri": "efda:ckpt:x"}],
        cluster="oke",
        namespace="default",
    )


def corpus(positives=3, negatives=3):
    items = []
    for _ in range(positives):
        items.append(
            {
                "artifact": artifact("exit_nonzero"),
                "positive": True,
                "failure_class": "exit_nonzero",
            }
        )
    for _ in range(negatives):
        items.append(
            {
                "artifact": artifact("oomkill"),
                "positive": False,
                "failure_class": "oomkill",
            }
        )
    return items


def signature(**overrides):
    base = {
        "id": "sig-1",
        "symptom": "the process exited non-zero",
        "diagnosticQuestions": ["describe the pod's events"],
        "matchLogic": 'failure_boundary.failure_class == "exit_nonzero"',
        "cause": "the process exited non-zero",
        "confidenceBase": 0.6,
        "remediation": {"tier": "T0"},
        "provenance": {"expectedFailureClass": "exit_nonzero"},
    }
    base.update(overrides)
    return base


def test_a_good_signature_passes_every_check():
    result = validate_signature(signature(), corpus())
    assert result["ok"]
    assert result["precision"] >= PRECISION_FLOOR
    assert result["recall"] >= RECALL_FLOOR


def test_a_signature_that_fires_on_everything_fails_the_precision_floor():
    result = validate_signature(signature(matchLogic="true"), corpus())
    assert not result["ok"]
    assert result["precision"] < PRECISION_FLOOR
    assert any("precision" in failure for failure in result["failures"])


def test_a_signature_that_fires_on_nothing_fails_the_recall_floor():
    result = validate_signature(
        signature(matchLogic='failure_boundary.failure_class == "never"'), corpus()
    )
    assert not result["ok"]
    assert result["recall"] < RECALL_FLOOR


def test_a_mutating_diagnostic_question_is_refused():
    result = validate_signature(
        signature(diagnosticQuestions=["delete the pod"]), corpus()
    )
    assert not result["blast_radius_ok"]
    assert any("read-only" in failure for failure in result["failures"])


def test_a_t1_signature_without_a_safety_proof_is_refused():
    result = validate_signature(signature(remediation={"tier": "T1"}), corpus())
    assert not result["blast_radius_ok"]
    assert any("safetyProof" in failure for failure in result["failures"])


def test_a_signature_that_ignores_its_cause_is_refused():
    result = validate_signature(signature(matchLogic="true"), corpus())
    assert not result["counterfactual_ok"]


def test_an_expression_that_reaches_outside_the_sandbox_is_refused():
    result = validate_signature(
        signature(matchLogic='"http://example.com" == "x"'), corpus()
    )
    assert not result["isolation_ok"]


def test_the_pack_report_is_the_sum_of_its_signatures():
    pack = {
        "metadata": {"name": "efda-test-agent-v1"},
        "spec": {"componentClass": "efda-test-agent", "signatures": [signature()]},
    }
    report = validate_pack(pack, corpus())
    assert report["ok"]
    assert report["pack"] == "efda-test-agent-v1"

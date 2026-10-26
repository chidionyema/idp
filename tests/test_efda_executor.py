"""The remediation gates (Interface 4)."""

from __future__ import annotations

from efda.executor import decide, execute, load_allowlist

from efda_fake_kube import FakeKube


def report(tier="T1", confidence=0.9, safety_proof=True, signature_id="sig-1"):
    return {
        "signatureId": signature_id,
        "componentClass": "efda-test-agent",
        "confidence": confidence,
        "remediation": {
            "tier": tier,
            "safetyProof": "risk=low;capabilities=[annotation:patch];rollback=defined"
            if safety_proof
            else "",
        },
    }


def allowlist_with(action=True):
    actions = []
    if action:
        actions.append(
            {
                "signatureId": "sig-1",
                "componentClass": "efda-test-agent",
                "tier": "T1",
                "action": {
                    "type": "annotate",
                    "target": {
                        "kind": "deployment",
                        "namespace": "default",
                        "name": "probe",
                    },
                    "annotations": {"efda.estate/remediated": "true"},
                },
                "rollback": {
                    "type": "annotate",
                    "target": {
                        "kind": "deployment",
                        "namespace": "default",
                        "name": "probe",
                    },
                    "previousAnnotations": {},
                },
                "rollbackTested": True,
            }
        )
    return {"version": "v1", "actions": actions}


def test_a_t0_signature_only_reports():
    decision = decide(report(tier="T0"), allowlist_with())
    assert decision["outcome"] == "REPORT_ONLY"
    assert decision["reason"] == "tier=T0, action=report_only"


def test_a_t1_without_a_safety_proof_is_refused():
    decision = decide(report(safety_proof=False), allowlist_with())
    assert decision["outcome"] == "REFUSED"
    assert decision["reason"] == "safety_proof_missing"


def test_an_action_the_allowlist_does_not_name_is_refused():
    decision = decide(report(), {"version": "v1", "actions": []})
    assert decision["outcome"] == "REFUSED"
    assert decision["reason"] == "action_not_in_allowlist"


def test_a_confidence_below_the_t1_gate_is_refused():
    decision = decide(report(confidence=0.84), allowlist_with())
    assert decision["outcome"] == "REFUSED"
    assert "0.85" in decision["reason"]


def test_a_t2_without_a_tested_rollback_is_refused():
    entry = allowlist_with()
    entry["actions"][0]["rollbackTested"] = False
    decision = decide(report(tier="T2", confidence=0.99), entry)
    assert decision["outcome"] == "REFUSED"
    assert decision["reason"] == "rollback_not_tested"


def test_an_unknown_action_type_is_refused():
    entry = allowlist_with()
    entry["actions"][0]["action"]["type"] = "rm -rf /"
    decision = decide(report(), entry)
    assert decision["outcome"] == "REFUSED"
    assert "not implemented" in decision["reason"]


def test_an_allowed_action_is_applied_and_recorded():
    kube = FakeKube()
    decision = decide(report(), allowlist_with())
    artifact = execute(decision, kube)
    spec = artifact["spec"]
    assert spec["outcome"] == "REMEDIATION_APPLIED"
    assert spec["action"]["type"] == "annotate"
    assert spec["rollbackPoint"]
    assert spec["preState"]["appliedAnnotations"] == {"efda.estate/remediated": "true"}
    assert kube.get_annotations("deployment", "default", "probe") == {
        "efda.estate/remediated": "true"
    }


def test_a_refusal_is_recorded_as_an_artifact_too():
    kube = FakeKube()
    decision = decide(report(tier="T0"), allowlist_with())
    artifact = execute(decision, kube)
    assert artifact["spec"]["outcome"] == "tier=T0, action=report_only"


def test_a_missing_allowlist_is_an_empty_allowlist(tmp_path):
    assert load_allowlist(str(tmp_path / "nope.json"))["actions"] == []


def test_the_executor_never_runs_a_string_it_did_not_implement():
    import inspect

    import efda.executor as module

    source = inspect.getsource(module)
    assert "subprocess" not in source
    assert "os.system" not in source

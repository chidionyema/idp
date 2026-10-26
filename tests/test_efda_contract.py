"""The Diagnostic Artifact contract (Interface 1)."""

from __future__ import annotations

import json

import pytest

from efda.contract import (
    FailureClassRegistry,
    artifact_address,
    build_artifact,
    digest_of,
    recompute_digest,
    validate_artifact,
)


def an_artifact(**overrides):
    kwargs = {
        "component_id": "efda-test-agent",
        "component_class": "efda-test-agent",
        "component_kind": "agent",
        "runner_id": "efda-test-run-001",
        "failure_class": "exit_nonzero",
        "attempted_operation": "run_to_completion",
        "invariant_broken": "exit_zero",
        "triggering_step": "process_exit",
        "capture_method": "supervisor_wrapper",
        "payloads": [{"kind": "checkpoint", "uri": "efda:ckpt:efda-test-run-001"}],
        "hypotheses": [
            {"rank": 1, "cause": "unknown", "confidence": 0.0, "source": "wrapper"}
        ],
        "cluster": "oke",
        "namespace": "default",
    }
    kwargs.update(overrides)
    return build_artifact(**kwargs)


def test_a_fresh_artifact_is_valid():
    assert validate_artifact(an_artifact()) == []


def test_the_digest_covers_the_contents():
    artifact = an_artifact()
    assert artifact["integrity"]["content_digest"] == recompute_digest(artifact)
    assert artifact["integrity"]["content_digest"].startswith("sha256:")


def test_a_changed_payload_breaks_the_digest():
    artifact = an_artifact()
    artifact["raw_evidence"]["payloads"][0]["uri"] = "efda:ckpt:tampered"
    errors = validate_artifact(artifact)
    assert any("content_digest" in error for error in errors)


def test_a_failure_class_outside_the_registry_is_refused():
    registry = FailureClassRegistry.from_dict(
        {"version": "v1", "classes": [{"id": "exit_nonzero"}]}
    )
    errors = validate_artifact(
        an_artifact(failure_class="provider_quota_exhaustion"), registry
    )
    assert any("FailureClassRegistry" in error for error in errors)


def test_an_empty_assessment_is_still_an_assessment():
    artifact = an_artifact(hypotheses=[])
    assert artifact["self_assessment"]["hypotheses"] == []
    assert validate_artifact(artifact) == []


def test_a_payload_without_content_is_refused():
    artifact = an_artifact(payloads=[{"kind": "log_tail"}])
    errors = validate_artifact(artifact)
    assert any("carries no digest" in error for error in errors)


def test_the_address_is_deterministic():
    artifact = an_artifact()
    assert (
        artifact_address(artifact["identity"])
        == "oke/default/efda-test-agent/efda-test-run-001/artifact.json"
    )


def test_an_unknown_component_kind_is_refused_at_build_time():
    with pytest.raises(ValueError):
        an_artifact(component_kind="mystery")


def test_the_artifact_is_json_serialisable():
    assert (
        json.loads(json.dumps(an_artifact()))["identity"]["runner_id"]
        == "efda-test-run-001"
    )


def test_the_registry_reads_both_shapes():
    registry = FailureClassRegistry.from_dict(
        {"version": "v2", "classes": ["a", {"id": "b"}]}
    )
    assert registry.version == "v2"
    assert registry.contains("a")
    assert registry.contains("b")
    assert not registry.contains("c")


def test_the_digest_is_order_independent():
    assert digest_of({"a": 1, "b": 2}) == digest_of({"b": 2, "a": 1})

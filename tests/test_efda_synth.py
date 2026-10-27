"""The synthesizer and the baseline generator (L3)."""

from __future__ import annotations

from efda.contract import build_artifact
from efda.packs import baseline_pack, pack_spec
from efda.synth import MIN_EVENTS, corpus_from_artifacts, synthesize
from efda.validation import validate_pack


def artifacts(count=4, failure_class="exit_nonzero"):
    built = []
    for index in range(count):
        built.append(
            build_artifact(
                component_id="efda-test-agent",
                component_class="efda-test-agent",
                component_kind="agent",
                runner_id=f"efda-test-run-{index:03d}",
                failure_class=failure_class,
                attempted_operation="run_to_completion",
                invariant_broken="exit_zero",
                triggering_step="process_exit",
                capture_method="supervisor_wrapper",
                payloads=[{"kind": "checkpoint", "uri": "efda:ckpt:x"}],
                cluster="oke",
                namespace="default",
            )
        )
    return built


def test_a_class_seen_once_does_not_get_a_candidate():
    candidate = synthesize(corpus_from_artifacts(artifacts(1)), "efda-test-agent")
    assert candidate["spec"]["signatures"] == []


def test_a_class_seen_enough_times_gets_a_candidate():
    candidate = synthesize(
        corpus_from_artifacts(artifacts(MIN_EVENTS)), "efda-test-agent"
    )
    signatures = candidate["spec"]["signatures"]
    assert len(signatures) == 1
    assert signatures[0]["provenance"]["expectedFailureClass"] == "exit_nonzero"
    assert signatures[0]["provenance"]["corpusDigest"].startswith("sha256:")


def test_a_candidate_is_tagged_with_the_factory_that_generated_it():
    candidate = synthesize(corpus_from_artifacts(artifacts(4)), "efda-test-agent")
    assert candidate["spec"]["generatedBy"] == "factory-synthesis@v1"
    assert candidate["spec"]["provenance"]["corpusDigest"]


def test_a_candidate_may_only_report_until_a_human_promotes_it():
    candidate = synthesize(corpus_from_artifacts(artifacts(4)), "efda-test-agent")
    assert all(
        signature["remediation"]["tier"] == "T0"
        for signature in candidate["spec"]["signatures"]
    )


def test_a_candidate_passes_the_validator():
    candidate = synthesize(corpus_from_artifacts(artifacts(4)), "efda-test-agent")
    corpus = corpus_from_artifacts(artifacts(4) + artifacts(3, failure_class="oomkill"))
    report = validate_pack(candidate, corpus)
    assert report["ok"], report


def test_the_baseline_generator_makes_a_class_compliant():
    pack = baseline_pack("efda-test-workload")
    spec = pack_spec(pack)
    assert spec["coverageTier"] == "baseline"
    assert spec["owner"]["team"] == "platform-fallback"
    assert spec["upgradeDeadline"]

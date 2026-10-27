"""The SkillPack model, the baseline generator and composition."""

from __future__ import annotations

import pytest

from efda.packs import (
    baseline_pack,
    compose,
    effective_pack,
    is_sunset,
    pack_spec,
    resolve_chain,
    select_packs,
    version_matches,
)


def test_the_baseline_pack_covers_every_version():
    pack = baseline_pack("efda-test-workload")
    assert pack_spec(pack)["appliesToVersions"] == "*"
    assert version_matches("*", "1.2.3")


def test_the_baseline_pack_carries_the_twelve_agnostic_signatures():
    pack = baseline_pack("efda-test-workload")
    signatures = pack_spec(pack)["signatures"]
    assert len(signatures) >= 10
    assert {signature["id"] for signature in signatures} >= {
        "baseline-crashloop",
        "baseline-oomkill",
        "baseline-hard_kill",
    }


def test_the_baseline_pack_is_cheap_and_t0_only():
    spec = pack_spec(baseline_pack("efda-test-workload"))
    assert spec["executionBudget"]["maxCpuMillicores"] == 100
    assert spec["executionBudget"]["maxMemoryMib"] == 128
    assert spec["executionBudget"]["maxWallClockMs"] == 2000
    assert spec["executionBudget"]["maxRegexComplexity"] == "low"
    assert spec["isolation"]["network"] == "none"
    assert spec["isolation"]["filesystem"] == "none"
    assert all(
        signature["remediation"]["tier"] == "T0" for signature in spec["signatures"]
    )


def test_the_baseline_confidence_is_deliberately_low():
    spec = pack_spec(baseline_pack("efda-test-workload"))
    assert all(signature["confidenceBase"] <= 0.50 for signature in spec["signatures"])


def test_version_ranges_match_what_they_say():
    assert version_matches(">=1.2.0", "1.3.0")
    assert not version_matches(">=1.2.0", "1.1.9")
    assert version_matches(">=1.2.0,<2.0.0", "1.9.9")
    assert not version_matches(">=1.2.0,<2.0.0", "2.0.1")
    assert version_matches("1.2.3", "1.2.3")
    assert not version_matches("1.2.3", "1.2.4")


def test_a_pack_that_cannot_say_which_versions_it_covers_covers_none():
    assert not version_matches("not-a-range", "1.2.3")


def test_a_specialist_pack_is_selected_before_a_baseline():
    baseline = baseline_pack("efda-test-agent")
    specialist = baseline_pack("efda-test-agent", version="1.0.0")
    pack_spec(specialist)["coverageTier"] = "specialist"
    pack_spec(specialist)["appliesToVersions"] = ">=1.0.0"
    selected = select_packs([baseline, specialist], "efda-test-agent", "1.4.0")
    assert pack_spec(selected[0])["coverageTier"] == "specialist"


def test_a_pack_does_not_cover_a_version_outside_its_range():
    specialist = baseline_pack("efda-test-agent", version="1.0.0")
    pack_spec(specialist)["coverageTier"] = "specialist"
    pack_spec(specialist)["appliesToVersions"] = ">=2.0.0"
    assert select_packs([specialist], "efda-test-agent", "1.4.0") == []


def test_the_composed_budget_is_the_minimum_of_the_chain():
    parent = baseline_pack("efda-test-agent")
    child = baseline_pack("efda-test-agent", version="1.0.0")
    pack_spec(child)["executionBudget"] = {
        "maxCpuMillicores": 50,
        "maxMemoryMib": 256,
        "maxWallClockMs": 1000,
        "maxRegexComplexity": "high",
    }
    composed = compose([parent, child])
    assert composed["executionBudget"]["maxCpuMillicores"] == 50
    assert composed["executionBudget"]["maxMemoryMib"] == 128
    assert composed["executionBudget"]["maxWallClockMs"] == 1000
    assert composed["executionBudget"]["maxRegexComplexity"] == "low"


def test_the_child_signature_overrides_the_parent():
    parent = baseline_pack("efda-test-agent")
    child = baseline_pack("efda-test-agent", version="1.0.0")
    child["spec"]["signatures"] = [
        {
            "id": "baseline-oomkill",
            "symptom": "overridden",
            "matchLogic": "true",
            "cause": "x",
            "confidenceBase": 0.4,
        }
    ]
    composed = compose([parent, child])
    overridden = [s for s in composed["signatures"] if s["id"] == "baseline-oomkill"][0]
    assert overridden["symptom"] == "overridden"


def test_a_child_cannot_introduce_a_capability_its_ancestors_do_not_have():
    parent = baseline_pack("efda-test-agent")
    child = baseline_pack("efda-test-agent", version="1.0.0")
    pack_spec(child)["capabilitiesRequired"] = ["EvidenceRead", "RemediationExecute"]
    with pytest.raises(ValueError):
        compose([parent, child])


def test_a_circular_composition_is_refused():
    parent = baseline_pack("efda-test-agent")
    child = baseline_pack("efda-test-agent", version="1.0.0")
    pack_spec(parent)["extends"] = "efda-test-agent-v1"
    pack_spec(child)["extends"] = "efda-test-agent-v0"
    with pytest.raises(ValueError):
        resolve_chain(
            {"efda-test-agent-v0": parent, "efda-test-agent-v1": child},
            child,
        )


def test_an_effective_pack_is_the_pack_itself_when_it_extends_nothing():
    pack = baseline_pack("efda-test-agent")
    assert effective_pack(pack, {})["version"] == "0.1.0"


def test_a_sunset_pack_is_sunset():
    pack = baseline_pack("efda-test-agent")
    pack_spec(pack)["deprecation"]["sunsetAt"] = "2020-01-01T00:00:00Z"
    assert is_sunset(pack)
    pack_spec(pack)["deprecation"]["sunsetAt"] = "2999-01-01T00:00:00Z"
    assert not is_sunset(pack)

"""Artifact routing spends capability only where the work and evidence require it."""

from __future__ import annotations

import copy
import importlib.util
import pathlib
import sys

import pytest

LLM_DIR = pathlib.Path(__file__).resolve().parents[1] / "platform" / "llm"


def _load():
    spec = importlib.util.spec_from_file_location(
        "artifact_tier_under_test", LLM_DIR / "artifact_tier.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def at():
    return _load()


@pytest.fixture()
def policy(at):
    return at.ArtifactPolicy.load(LLM_DIR / "artifact-tier.yaml")


def test_deterministic_control_actions_use_no_model(at, policy):
    for artifact in ("verify", "merge", "land", "bind", "status"):
        decision = policy.route(at.RoutingRequest(artifact, "deep", "high"))
        assert decision.tier == "none"
        assert decision.alias is None


def test_standard_planning_is_mid_and_deep_planning_is_frontier(at, policy):
    standard = policy.route(at.RoutingRequest("plan"))
    deep = policy.route(at.RoutingRequest("plan", reasoning="deep"))
    assert (standard.tier, standard.alias) == ("mid", "minimax")
    assert (deep.tier, deep.alias) == ("frontier", "claude-*")


def test_cheap_execution_requires_a_deterministic_gate(at, policy):
    gated = policy.route(at.RoutingRequest("build", deterministic_gate=True))
    ungated = policy.route(at.RoutingRequest("build", deterministic_gate=False))
    assert gated.tier == "cheap"
    assert ungated.tier == "mid"
    assert "ungated:cheap-refused" in ungated.reasons


def test_high_risk_execution_does_not_start_cheap(at, policy):
    decision = policy.route(at.RoutingRequest("build", risk="high"))
    assert decision.tier == "frontier"
    assert decision.alias == "claude-*"


def test_two_gated_failures_require_frontier_replanning(at, policy):
    request = at.RoutingRequest("build")
    assert policy.replan_after_failures(request, 1) is None
    decision = policy.replan_after_failures(request, 2)
    assert decision.artifact_class == "plan"
    assert decision.tier == "frontier"
    assert "gated-failures:2" in decision.reasons


def test_failover_candidates_stay_inside_the_required_tier(policy):
    tier, candidates = policy.rescue_aliases("minimax")
    assert tier == "mid"
    assert candidates
    assert not set(candidates) & set(policy.document["tiers"]["cheap"]["aliases"])
    assert not set(candidates) & set(policy.document["tiers"]["frontier"]["aliases"])
    assert policy.rescue_aliases("default") is None  # legacy mixed alias


def test_every_policy_alias_is_a_real_router_group(policy, at):
    at.validate_configured_aliases(policy, LLM_DIR / "config.yaml")


def test_local_floor_cannot_be_removed(at, policy):
    document = copy.deepcopy(policy.document)
    document["tiers"]["cheap"]["aliases"].remove(document["local_floor"])
    with pytest.raises(at.ArtifactRoutingError, match="local_floor"):
        at.validate_schema(document)


def test_an_alias_cannot_occupy_two_capability_tiers(at, policy):
    document = copy.deepcopy(policy.document)
    document["tiers"]["cheap"]["aliases"].append("minimax")
    with pytest.raises(at.ArtifactRoutingError, match="occurs in both"):
        at.validate_schema(document)


def test_unknown_artifact_class_fails_closed(at, policy):
    with pytest.raises(at.ArtifactRoutingError, match="unknown artifact class"):
        policy.route(at.RoutingRequest("mystery"))

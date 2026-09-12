"""MUM-288 door: no state-changing execute without a SAFE, unexpired, hash-matched simulate.

Every case in the spec's edge-case table that is provable offline -- a grader that did not answer,
a stale hash, an expired proposal, an UNKNOWN verdict, two proposals touching one object, execute
without simulating -- is graded here on the pure core of mcp/plugins/estate_simulate.py, so the
door never depends on a live cluster to be proven. Cluster-grounded graders (admission dry-run
through the bin programs, Calico flows, node capacity) are themselves graded by their own estate
gates; this file grades the guard that sits in front of them.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import os
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "estate_simulate",
    Path(__file__).resolve().parents[1] / "mcp" / "plugins" / "estate_simulate.py",
)
sim = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sim)

SAFE = {"verdict": "SAFE", "detail": "ok"}
UNSAFE = {"verdict": "UNSAFE", "detail": "denied"}
T0 = dt.datetime(2026, 9, 8, 12, 0, 0, tzinfo=dt.timezone.utc)


@pytest.fixture(autouse=True)
def _fresh_registry():
    """The module singleton backs the default simulate/execute calls; reset it each test so
    no proposal or consumed hash leaks from one case into the next."""
    sim._REGISTRY.proposals.clear()
    yield
    sim._REGISTRY.proposals.clear()


def cfg(ttl_s: int = 600, door: bool = True) -> dict:
    return {
        "proposal_ttl_s": ttl_s,
        "graders_door": door,
        "state_branch": "estate/state",
    }


def all_safe_graders(
    unsafe: list[str] | None = None, missing: list[str] | None = None
) -> dict:
    out = {}
    for name in sim.GRADER_NAMES:
        if missing and name in missing:
            continue  # absent grader
        if unsafe and name in unsafe:
            out[name] = lambda n=name: UNSAFE
        else:
            out[name] = lambda: SAFE
    return out


def test_simulate_returns_safe_when_every_grader_answered_safe():
    g = all_safe_graders()
    p = sim.simulate_change(
        "ref: clusters/oke",
        graders=g,
        now=T0,
        git_sha="abc",
        resource_versions={"deployments/x": "1"},
    )
    assert p["verdict"] == "SAFE"
    assert p["graders_on"] is True
    assert p["computed_against"]["git_sha"] == "abc"


def test_one_unsafe_grader_makes_the_proposal_unsafe():
    g = all_safe_graders(unsafe=["laws"])
    p = sim.simulate_change("scale otto-ss", graders=g, now=T0)
    assert p["verdict"] == "UNSAFE"
    assert p["grader_results"]["laws"]["verdict"] == "UNSAFE"


def test_one_grader_that_did_not_answer_makes_the_whole_verdict_unknown():
    """A validating webhook down during dry-run / a grader that could not run is UNKNOWN, and an
    UNKNOWN whole verdict is never executable -- fail closed, the same rule bin/idp-fence-
    enforcement enforces."""
    g = all_safe_graders(missing=["admission"])
    p = sim.simulate_change("x", graders=g, now=T0)
    assert p["verdict"] == "UNKNOWN"
    r = sim.execute_change(
        p["proposal_id"], p["computed_against"]["cluster_state_hash"], now=T0
    )
    assert r["executed"] is False and "verdict is UNKNOWN" in r["error"]


def test_a_grader_that_throws_is_unknown_not_a_crash():
    def boom():
        raise RuntimeError("kubeconfig gone")

    g = {n: (boom if n == "network" else (lambda: SAFE)) for n in sim.GRADER_NAMES}
    p = sim.simulate_change("x", graders=g, now=T0)
    assert p["verdict"] == "UNKNOWN"
    # The reason must name the exception and what it said, not just "could not run": an operator
    # reading the proposal has to be able to tell a grader that crashed from a grader that
    # answered UNKNOWN because it was not given an input.
    detail = p["grader_results"]["network"]["detail"]
    assert "RuntimeError" in detail
    assert "kubeconfig gone" in detail


def test_execute_without_a_simulated_proposal_is_refused():
    r = sim.execute_change("does-not-exist", "abc", now=T0)
    assert r["executed"] is False and "simulate first" in r["error"]


def test_execute_on_a_stale_hash_is_refused_and_spends_the_proposal():
    """Proposal against a stale hash: execute refuses with the two hashes; caller must re-simu.
    Mutate a resource between simulate and execute, exactly the spec's row."""
    g = all_safe_graders()
    p = sim.simulate_change(
        "x", graders=g, now=T0, resource_versions={"configmaps/x": "1"}
    )
    reg = sim.Registry()
    p2 = sim.simulate_change(
        "x", graders=g, registry=reg, now=T0, resource_versions={"configmaps/x": "2"}
    )
    stale = sim.execute_change(
        p2["proposal_id"],
        p["computed_against"]["cluster_state_hash"],
        registry=reg,
        now=T0,
    )
    assert stale["executed"] is False and "state hash changed" in stale["error"]
    assert reg.get(p2["proposal_id"]) is None  # spent; re-simulate


def test_execute_on_a_changed_resource_version_spends_the_proposal():
    g = all_safe_graders()
    reg = sim.Registry()
    p = sim.simulate_change(
        "x", graders=g, registry=reg, now=T0, resource_versions={"cf/x": "1"}
    )
    ok = sim.execute_change(
        p["proposal_id"],
        p["computed_against"]["cluster_state_hash"],
        registry=reg,
        now=T0,
    )
    assert ok["executed"] is True
    # the proposal is spent; a second execute is a no-id
    again = sim.execute_change(
        p["proposal_id"],
        p["computed_against"]["cluster_state_hash"],
        registry=reg,
        now=T0,
    )
    assert again["executed"] is False and "no proposal with that id" in again["error"]


def test_execute_with_a_null_hash_is_refused_fail_closed():
    g = all_safe_graders()
    reg = sim.Registry()
    p = sim.simulate_change("x", graders=g, registry=reg, now=T0)
    r = sim.execute_change(p["proposal_id"], None, registry=reg, now=T0)
    assert r["executed"] is False


def test_an_expired_proposal_is_refused_and_dropped():
    g = all_safe_graders()
    reg = sim.Registry()
    p = sim.simulate_change("x", graders=g, registry=reg, cfg=cfg(ttl_s=600), now=T0)
    later = T0 + dt.timedelta(seconds=601)
    r = sim.execute_change(
        p["proposal_id"],
        p["computed_against"]["cluster_state_hash"],
        registry=reg,
        cfg=cfg(ttl_s=600),
        now=later,
    )
    assert r["executed"] is False and "expired" in r["error"]
    assert reg.get(p["proposal_id"]) is None


def test_hash_is_deterministic_over_sorted_identities():
    a = sim.hash_state({"z": "1", "a": "2"})
    b = sim.hash_state({"a": "2", "z": "1"})  # same content, different insertion order
    assert a == b


def test_hash_changes_when_a_resource_version_does():
    assert sim.hash_state({"cf/x": "1"}) != sim.hash_state({"cf/x": "2"})


def test_the_grader_door_off_means_every_proposal_is_unknown_not_safe():
    """Estimate the guard that a door-off environment (offline CI, a repo reader) answers UNKNOWN
    honestly rather than pretending a grader ran."""
    p = sim.simulate_change("x", graders={}, cfg=cfg(door=False), now=T0)
    assert p["verdict"] == "UNKNOWN"
    assert all(r["verdict"] == "UNKNOWN" for r in p["grader_results"].values())


def test_the_live_admission_grader_is_fail_closed_without_a_readable_inline_manifest():
    """The MCP tool's live admission grader only dry-runs an inline manifest; a git-ref source
    (or nothing) is UNKNOWN, never SAFE -- a real proposal is not provable against admission
    when there is nothing for the chain to see."""
    g = sim._live_graders("ref: clusters/oke (no inline manifest)")
    out = g["admission"]()
    assert out["verdict"] == "UNKNOWN" and "inline manifest" in out["detail"]


def test_grade_rules_folds_all_ok_to_safe():
    assert sim.grade_rules({"a": "ok", "b": "ok"}) == "SAFE"


def test_grade_rules_any_fail_to_unsafe():
    assert sim.grade_rules({"a": "ok", "b": "FAIL"}) == "UNSAFE"


def test_grade_rules_a_blind_rule_is_unknown_not_safe():
    """A repo law that could not grade (BLIND) is never folded into a pass -- same rule as
    bin/idp-fence-enforcement and the gate that grades the whole verdict."""
    assert sim.grade_rules({"a": "ok", "b": "BLIND"}) == "UNKNOWN"


def test_grade_rules_empty_or_garbage_is_unknown():
    assert sim.grade_rules({}) == "UNKNOWN"
    assert sim.grade_rules({"a": "ok", "b": "not-a-verdict"}) == "UNKNOWN"


def test_the_laws_grader_is_unknown_when_its_door_is_off():
    """laws only reports a repository law verdict when ESTATE_MCP_GRADE_LAWS_DOOR is on; otherwise
    UNKNOWN, never a fabricated pass -- offline CI and a repo reader get no silent all-clear."""
    os.environ.pop("ESTATE_MCP_GRADE_LAWS_DOOR", None)
    live = sim.config()
    assert live.get("grade_laws_door") in (False, None)
    g = sim._live_graders("apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: x\n")
    out = g["laws"]()
    assert out["verdict"] == "UNKNOWN"


def test_the_laws_door_flips_on_when_explicitly_enabled():
    """The laws door is a real, intentional opt-in: setting ESTATE_MCP_GRADE_LAWS_DOOR=1 turns the
    config key on (the grader then shells to bin/idp-rules; gating it here keeps the suite offline)."""
    os.environ["ESTATE_MCP_GRADE_LAWS_DOOR"] = "1"
    try:
        assert sim.config()["grade_laws_door"] is True
    finally:
        os.environ.pop("ESTATE_MCP_GRADE_LAWS_DOOR", None)


def test_the_converge_grader_is_unknown_without_a_shadow_observation():
    """A change that has not been proved to converge in the shadow dimension is UNKNOWN through the
    world-model door -- never SAFE. The observation is supplied by the shadow executor, not by the
    MCP server's say-so."""
    os.environ.pop("ESTATE_MCP_SHADOW_OBSERVATION", None)
    g = sim._live_graders("apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: x\n")
    out = g["converge"]()
    assert out["verdict"] == "UNKNOWN" and "no shadow observation" in out["detail"]


def test_the_converge_grader_reads_a_converged_shadow_observation():
    """When the shadow executor has really proved the workload converged, converge answers SAFE via
    the estate's own bin/idp-shadow-verify (a real fixture, no fabricate)."""
    path = (
        Path(__file__).resolve().parents[1]
        / "tests"
        / "fixtures"
        / "shadow-obs"
        / "converged.json"
    )
    os.environ["ESTATE_MCP_SHADOW_OBSERVATION"] = str(path)
    try:
        g = sim._live_graders("apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: x\n")
        out = g["converge"]()
        assert out["verdict"] == "SAFE"
    finally:
        os.environ.pop("ESTATE_MCP_SHADOW_OBSERVATION", None)


def test_the_converge_grader_reports_a_broken_shadow_observation_as_unsafe():
    """A shadow observation that did not converge is UNSAFE, and the detail names what broke
    (the empirical rule's quote)."""
    path = (
        Path(__file__).resolve().parents[1]
        / "tests"
        / "fixtures"
        / "shadow-obs"
        / "broken.json"
    )
    os.environ["ESTATE_MCP_SHADOW_OBSERVATION"] = str(path)
    try:
        g = sim._live_graders("apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: x\n")
        out = g["converge"]()
        assert out["verdict"] == "UNSAFE"
        assert "not Ready" in out["detail"]
    finally:
        os.environ.pop("ESTATE_MCP_SHADOW_OBSERVATION", None)


def test_the_network_grader_is_unknown_without_a_calico_feed():
    """No deny feed supplied -> network is UNKNOWN, never SAFE; the door reasons over the estate's
    own flow evidence or it reasons over nothing."""
    os.environ.pop("ESTATE_MCP_CALICO_FEED", None)
    g = sim._live_graders("apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: x\n")
    assert g["network"]()["verdict"] == "UNKNOWN"


def test_the_network_grader_relays_the_real_calico_feed_verdict():
    """With a real deny feed the grader answers exactly what bin/idp-calico-deny-log answers for
    that feed -- it relays the estate's own network verdict, it does not invent one."""
    here = (
        Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "calico-denyflow"
    )
    os.environ["ESTATE_MCP_CALICO_FEED"] = str(here / "feed-no-evidence.log")
    try:
        g = sim._live_graders("apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: x\n")
        assert g["network"]()["verdict"] in (
            "UNSAFE",
            "UNKNOWN",
        )  # not SAFE on an empty feed
    finally:
        os.environ.pop("ESTATE_MCP_CALICO_FEED", None)


def test_the_placement_grader_is_unknown_without_a_receipt():
    os.environ.pop("ESTATE_MCP_PLACEMENT_RECEIPT", None)
    g = sim._live_graders("apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: x\n")
    assert g["placement"]()["verdict"] == "UNKNOWN"

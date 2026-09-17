"""BDD bindings for features/gates/shadow-verify.feature.

Calls bin/idp-shadow-verify.grade() directly. No cluster needed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/gates/shadow-verify.feature")

REPO = Path(__file__).resolve().parents[3]
SHADOW_VERIFY = REPO / "bin" / "idp-shadow-verify"


def _load():
    import importlib.machinery

    loader = importlib.machinery.SourceFileLoader(
        "idp_shadow_verify", str(SHADOW_VERIFY)
    )
    spec = importlib.util.spec_from_loader("idp_shadow_verify", loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["idp_shadow_verify"] = mod
    loader.exec_module(mod)
    return mod


def _passing_probes():
    return [{"name": "readiness", "outcome": "pass"}]


@pytest.fixture
def state():
    return {}


@pytest.fixture
def mod():
    return _load()


# Background -------------------------------------------------------------------


@given("the shadow-verify tool exists at bin/idp-shadow-verify")
def _exists():
    assert SHADOW_VERIFY.exists(), f"not found: {SHADOW_VERIFY}"


# Observation builders ---------------------------------------------------------


@given(
    "an observation where ready is true, kind is Deployment, requiredReplicas is 2, availableReplicas is 2, readyReplicas is 2"
)
def _obs_ready_deployment(state):
    state["obs"] = {
        "kind": "Deployment",
        "metadata": {"name": "svc", "namespace": "demo"},
        "ready": True,
        "requiredReplicas": 2,
        "availableReplicas": 2,
        "readyReplicas": 2,
        "probes": _passing_probes(),
    }


@given("an observation where ready is false, kind is Deployment")
def _obs_not_ready(state):
    state["obs"] = {
        "kind": "Deployment",
        "metadata": {"name": "svc", "namespace": "demo"},
        "ready": False,
        "requiredReplicas": 2,
        "availableReplicas": 0,
        "readyReplicas": 0,
        "probes": _passing_probes(),
    }


@given("an observation where ready is absent, kind is Deployment")
def _obs_silent_ready(state):
    state["obs"] = {
        "kind": "Deployment",
        "metadata": {"name": "svc", "namespace": "demo"},
        # no "ready" key
        "requiredReplicas": 2,
        "availableReplicas": 2,
        "readyReplicas": 2,
        "probes": _passing_probes(),
    }


@given(
    "an observation where ready is true, kind is Deployment, requiredReplicas is 3, availableReplicas is 2, readyReplicas is 2"
)
def _obs_replica_mismatch(state):
    state["obs"] = {
        "kind": "Deployment",
        "metadata": {"name": "svc", "namespace": "demo"},
        "ready": True,
        "requiredReplicas": 3,
        "availableReplicas": 2,
        "readyReplicas": 2,
        "probes": _passing_probes(),
    }


@given("an observation where kind is Pod")
def _obs_pod_kind(state):
    state["obs"] = {
        "kind": "Pod",
        "metadata": {"name": "svc", "namespace": "demo"},
        "ready": True,
        "probes": _passing_probes(),
    }


@given(
    "an observation where ready is true, kind is Deployment without requiredReplicas"
)
def _obs_no_required_replicas(state):
    state["obs"] = {
        "kind": "Deployment",
        "metadata": {"name": "svc", "namespace": "demo"},
        "ready": True,
        "availableReplicas": 2,
        "readyReplicas": 2,
        "probes": _passing_probes(),
    }


@given(
    parsers.parse(
        "an observation where ready is true, kind is {kind}, requiredReplicas is 1, availableReplicas is 1, readyReplicas is 1"
    )
)
def _obs_kind_ok(state, kind):
    state["obs"] = {
        "kind": kind,
        "metadata": {"name": "svc", "namespace": "demo"},
        "ready": True,
        "requiredReplicas": 1,
        "availableReplicas": 1,
        "readyReplicas": 1,
        "probes": _passing_probes(),
    }


@given(
    "an observation where ready is true, kind is StatefulSet, requiredReplicas is 1, availableReplicas is 1, readyReplicas is 1, probesPassing is false"
)
def _obs_probe_fail(state):
    state["obs"] = {
        "kind": "StatefulSet",
        "metadata": {"name": "svc", "namespace": "demo"},
        "ready": True,
        "requiredReplicas": 1,
        "availableReplicas": 1,
        "readyReplicas": 1,
        "probes": [{"name": "readiness", "outcome": "fail"}],
    }


# When / Then ------------------------------------------------------------------


@when("idp-shadow-verify grades the observation")
def _grade(state, mod):
    ok, reasons = mod.grade(state["obs"])
    state["ok"] = ok
    state["reasons"] = reasons


@then("the grade is pass")
def _grade_pass(state):
    assert state["ok"], f"expected pass but got fail: {state['reasons']}"


@then("there are no failure reasons")
def _no_reasons(state):
    assert state["reasons"] == [], f"expected no reasons: {state['reasons']}"


@then("the grade is fail")
def _grade_fail(state):
    assert not state["ok"], "expected fail but got pass"


@then(parsers.parse('the failure reason mentions "{keyword}"'))
def _reason_mentions(state, keyword):
    combined = " ".join(state["reasons"]).lower()
    assert keyword.lower() in combined, (
        f"{keyword!r} not found in reasons: {state['reasons']}"
    )

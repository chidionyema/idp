"""Binds features/policy/operating-model-gate.feature (crew#286, crew#297). bin/pr-report reshapes a
pull request into the input policy/operating_model.rego reads and runs conftest on it; here the
checked-in policy/fixtures/opmodel-*.json are that input, so each rule is judged by the same
policy and the same conftest, without GitHub."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/policy/operating-model-gate.feature")

IDP = Path(__file__).resolve().parents[3]
FIX = IDP / "policy" / "fixtures"


@pytest.fixture
def state() -> dict:
    return {"fixtures": []}


def _fx(name: str) -> dict:
    return json.loads((FIX / name).read_text())


def _conftest(name: str) -> subprocess.CompletedProcess:
    assert shutil.which("conftest"), "conftest is not installed; the bdd job installs it"
    return subprocess.run(["conftest", "test", str(FIX / name), "-p", "policy/", "-n", "main", "--no-color"],
                          cwd=IDP, capture_output=True, text=True)


def _refused_with(state: dict, name: str, *rules: str) -> None:
    r = state["runs"][name]
    assert r.returncode != 0, name + " passed: " + r.stdout
    assert any(f"rule={rule}" in r.stdout for rule in rules), (name, rules, r.stdout)


@when("bin/pr-report runs")
@when("bin/pr-report judges it")
def _run(state: dict) -> None:
    state["runs"] = {n: _conftest(n) for n in state["fixtures"]}


# --- provisioning_complete ---------------------------------------------------------------------

@given('a PR adds resource "oci_identity_domains_app" and no grant, policy or membership')
def _half(state: dict) -> None:
    fx = _fx("opmodel-half-provisioned.json")
    assert "oci_identity_domains_app" in fx["pr"]["added"], fx["pr"]["added"]
    for scope in ("oci_identity_domains_grant", "oci_identity_policy", "oci_identity_domains_group_membership"):
        assert scope not in fx["pr"]["added"], scope
    state["fixtures"].append("opmodel-half-provisioned.json")


@then("it exits 1 with a line starting rule=provisioning_complete and a fix:")
def _half_refused(state: dict) -> None:
    _refused_with(state, "opmodel-half-provisioned.json", "provisioning_complete")
    line = next(l for l in state["runs"]["opmodel-half-provisioned.json"].stdout.splitlines() if "rule=provisioning_complete" in l)
    assert "fix:" in line, line


# --- no_gui_actions ----------------------------------------------------------------------------

@given(parsers.parse('a PR body line "{line}"'))
def _gui(state: dict, line: str) -> None:
    fx = _fx("opmodel-gui.json")
    assert "FOUNDER ACTION" in fx["pr"]["body"] and "console" in fx["pr"]["body"].lower(), fx["pr"]["body"]
    state["fixtures"].append("opmodel-gui.json")


@then("it exits 1 with rule=no_gui_actions")
def _gui_refused(state: dict) -> None:
    _refused_with(state, "opmodel-gui.json", "no_gui_actions")


# --- founder_denied (crew#473: no APPROVE: wait, DENY: still refuses) -----------------------------------------------------------------

@given('a PR touching backstage/ or platform/identity/ with no "Approval-word:" line')
def _no_approval(state: dict) -> None:
    fx = _fx("opmodel-no-approval.json")
    assert any("backstage/" in f or f.startswith("platform/identity/") for f in fx["pr"]["files"]), fx["pr"]["files"]
    assert "Approval-word:" not in fx["pr"]["body"]
    state["fixtures"].append("opmodel-no-approval.json")


@then("the founder-facing change passes with no founder word")
def _no_approval_passes(state: dict) -> None:
    r = state["runs"]["opmodel-no-approval.json"]
    assert r.returncode == 0, r.stdout + r.stderr


@given('a PR whose "Approval-word:" the founder answered with DENY: from his GitHub login')
def _denied(state: dict) -> None:
    fx = _fx("opmodel-denied.json")
    word = next(l.split(":", 1)[1].strip() for l in fx["pr"]["body"].splitlines() if l.startswith("Approval-word:"))
    assert word in fx["pr"]["denials"], (word, fx["pr"]["denials"])
    state["fixtures"].append("opmodel-denied.json")


@then("it exits 1 with rule=founder_denied")
def _denied_refused(state: dict) -> None:
    _refused_with(state, "opmodel-denied.json", "founder_denied")


# --- cost_budget / canary ----------------------------------------------------------------------

@given("a PR touching platform/oci/ whose Cost-delta-usd-month beats estate-defaults.yaml infrastructure.monthly_cap_usd, or with no canary label")
def _cost(state: dict) -> None:
    cap = yaml.safe_load((IDP / "estate-defaults.yaml").read_text())["infrastructure"]["monthly_cap_usd"]
    over = _fx("opmodel-over-budget.json")
    assert any(f.startswith("platform/oci/") for f in over["pr"]["files"]), over["pr"]["files"]
    delta = float(next(l.split(":", 1)[1] for l in over["pr"]["body"].splitlines() if l.startswith("Cost-delta-usd-month:")))
    assert delta > float(cap), (delta, cap)
    state["fixtures"] += ["opmodel-over-budget.json", "opmodel-no-canary.json"]


@then("it exits 1 with rule=cost_budget or rule=canary")
def _cost_refused(state: dict) -> None:
    _refused_with(state, "opmodel-over-budget.json", "cost_budget")
    _refused_with(state, "opmodel-no-canary.json", "canary")


# --- drill_named, drill added in the PR --------------------------------------------------------

@given("a pull request that changes a platform layer and adds a row to drills/catalogue.yaml")
def _drill_added(state: dict) -> None:
    fx = _fx("opmodel-drill-added-in-pr.json")
    assert any(f.startswith(("platform/", "clusters/")) for f in fx["pr"]["files"])
    assert "drills/catalogue.yaml" in fx["pr"]["files"] and "- name:" in fx["pr"]["added"]
    state["fixtures"].append("opmodel-drill-added-in-pr.json")
    state["fx"] = fx


@given('its body says "Drill: <that row>"')
def _drill_body(state: dict) -> None:
    import re
    name = re.search(r"(?m)^\+\s*-\s*name:\s*(\S+)", state["fx"]["pr"]["added"]).group(1)
    assert f"Drill: {name}" in state["fx"]["pr"]["body"]
    assert name not in state["fx"]["drills"], "the fixture must name a drill the catalogue on main does not hold"


@then("the drill names come from the catalogue on main and the catalogue at the PR head")
def _two_sources(state: dict) -> None:
    rego = (IDP / "policy/operating_model.rego").read_text()
    assert "input.drills" in rego and "drills_added_in_pr" in rego


@then("the gate passes")
def _passes(state: dict) -> None:
    r = state["runs"]["opmodel-drill-added-in-pr.json"]
    assert r.returncode == 0, r.stdout + r.stderr


# --- architecture_laws (crew#254) ------------------------------------------------------------


@given('a PR body with no "## Architecture laws" section, or one whose law line is a sentence')
def _laws_bad(state: dict) -> None:
    assert "## Architecture laws" not in _fx("opmodel-no-laws.json")["pr"]["body"]
    assert "- LAW 3 nervous system: we will wire tracing later" in _fx("opmodel-laws-sentence.json")["pr"]["body"]
    state["fixtures"] += ["opmodel-no-laws.json", "opmodel-laws-sentence.json", "opmodel-ok.json"]


@then("it exits 1 with rule=architecture_laws")
def _laws_refused(state: dict) -> None:
    _refused_with(state, "opmodel-no-laws.json", "architecture_laws")
    _refused_with(state, "opmodel-laws-sentence.json", "architecture_laws")


@then("a body whose four law lines are commands, paths or n/a with a reason passes")
def _laws_pass(state: dict) -> None:
    r = state["runs"]["opmodel-ok.json"]
    assert r.returncode == 0, r.stdout

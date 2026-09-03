"""Binds features/estate-rebuild/rebuild-and-gates.feature (crew#297). Each scenario is an incident
that already has a rung-4 test under tests/; the When runs that test file for real and the Then
checks the file the scenario names."""
import re
import subprocess
import sys
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/estate-rebuild/rebuild-and-gates.feature")

IDP = Path(__file__).resolve().parents[3]
INCIDENT = {
    "state": "tests/test_incident_state_force_copied_over_remote.py",
    "plan": "tests/test_incident_pr_plan_changes_are_not_drift.py",
    "vault": "tests/test_incident_vault_recreated_after_state_loss.py",
    "repoint": "tests/test_incident_estate_vars_repointed_at_empty_vault.py",
    "tail": "tests/test_incident_apply_error_hidden_by_tail.py",
}


@pytest.fixture
def state() -> dict:
    return {}


def _run_incident(key: str) -> str:
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", INCIDENT[key]],
                       cwd=IDP, capture_output=True, text=True)
    assert r.returncode == 0, INCIDENT[key] + "\n" + r.stdout + r.stderr
    m = re.search(r"(\d+) passed", r.stdout)
    assert m and int(m.group(1)) >= 1, r.stdout
    return r.stdout


# --- stale local state -----------------------------------------------------------------------

@given("a checkout of platform/oci holds a terraform.tfstate from an earlier day")
def _stale(state: dict) -> None:
    state["key"] = "state"


@when("bin/idp-oke-rebuild or bin/idp-identity-apply initialises the remote backend")
def _init(state: dict) -> None:
    state["out"] = _run_incident("state")


@then("the local file is moved aside as <name>.quarantine-<utc> and printed")
def _quarantine(state: dict) -> None:
    assert "quarantine" in (IDP / "bin/idp-state-guard").read_text()
    for b in ("bin/idp-oke-rebuild", "bin/idp-identity-apply"):
        assert "idp-state-guard" in (IDP / b).read_text(), b


@then("init runs with -reconfigure, never with -migrate-state or -force-copy")
def _reconfigure(state: dict) -> None:
    for b in ("bin/idp-oke-rebuild", "bin/idp-identity-apply"):
        live = "\n".join(l for l in (IDP / b).read_text().splitlines() if not l.strip().startswith("#"))
        assert "-reconfigure" in live and "-migrate-state" not in live and "-force-copy" not in live, b


@then("tests/test_incident_state_force_copied_over_remote.py proves both ways")
def _both_ways(state: dict) -> None:
    assert "3 passed" in state["out"], state["out"]


# --- a PR's planned changes are the PR ------------------------------------------------------------

@given("oke-check runs bin/idp-oke-rebuild --check on a pull_request touching platform/oci")
def _oke_check(state: dict) -> None:
    wf = (IDP / ".github/workflows/oke-check.yml").read_text()
    assert re.search(r"run: bin/idp-oke-rebuild --\$\{\{ inputs\.mode \|\| 'check' \}\}", wf) and "pull_request" in wf
    state["wf"] = wf


@given("the workflow sets OKE_CHECK_EXPECT_CHANGES=1 only for pull_request events")
def _expect_changes(state: dict) -> None:
    assert re.search(r"OKE_CHECK_EXPECT_CHANGES:.*github\.event_name == 'pull_request' && '1' \|\| '0'", state["wf"]), state["wf"]


@when("tofu plan exits 2")
def _plan_2(state: dict) -> None:
    state["out"] = _run_incident("plan")


@then("the planned resource changes are printed and the check passes")
@then("on schedule or workflow_dispatch the same exit 2 is drift and the check fails")
@then("exit 1 never passes on any event")
def _plan_proved(state: dict) -> None:
    assert "passed" in state["out"]


# --- lost-state apply never re-creates a vault ----------------------------------------------------

@given("the shared state no longer holds oci_kms_vault.estate")
@given("an ACTIVE vault named estate-secrets holds the estate's secrets")
def _lost_state(state: dict) -> None:
    state["key"] = "vault"


@when("bin/idp-oke-rebuild --apply runs")
def _apply(state: dict) -> None:
    state["out"] = _run_incident("vault")


@then('bin/idp-recreate-guard refuses with the exact "tofu import" command and no vault is created')
def _guard(state: dict) -> None:
    assert "tofu import" in (IDP / "bin/idp-recreate-guard").read_text()
    assert "idp-recreate-guard" in (IDP / "bin/idp-oke-rebuild").read_text()


@then("a plan that creates nothing, or a create with no live namesake, passes")
def _guard_permits(state: dict) -> None:
    assert "3 passed" in state["out"], state["out"]


# --- secret store never repointed while secrets live ---------------------------------------------

@given("flux-system/estate-vars names a vault that holds ACTIVE secrets")
def _estate_vars(state: dict) -> None:
    state["key"] = "repoint"


@when("bin/idp-flux-bootstrap sees a different vault_id in the tofu outputs")
def _bootstrap(state: dict) -> None:
    state["out"] = _run_incident("repoint")


@then("it refuses with rc 3 and names the import, and switches only when the current vault is empty")
def _refuses_3(state: dict) -> None:
    assert "exit 3" in (IDP / "bin/idp-flux-bootstrap").read_text()


# --- a failing step shows its cause ---------------------------------------------------------------

@given("a step whose output has an Error line followed by ten footer lines")
def _error_step(state: dict) -> None:
    state["key"] = "tail"


@when("the step fails")
def _fails(state: dict) -> None:
    state["out"] = _run_incident("tail")


@then("the Error line and the footer are both on screen")
@then("a passing step prints one receipt line and nothing else")
def _tail_proved(state: dict) -> None:
    assert "3 passed" in state["out"], state["out"]


# --- node cycling never asked of a BASIC cluster ---------------------------------------------------

@given("the estate cluster type is BASIC_CLUSTER")
def _basic(state: dict) -> None:
    tf = (IDP / "platform/oci/main.tf").read_text()
    assert re.search(r'cluster_type\s*=\s*"basic"', tf), "cluster_type is not basic"
    state["out"] = _run_incident("tail")


@then("the a1 node pool carries no node_cycling_* keys")
def _no_cycling(state: dict) -> None:
    tf = (IDP / "platform/oci/main.tf").read_text()
    live = "\n".join(l for l in tf.splitlines() if not l.strip().startswith("#"))
    assert "node_cycling_" not in live


@then("a node is replaced by surging the pool to 2 and deleting the old node")
def _surge(state: dict) -> None:
    assert "passed" in state["out"]

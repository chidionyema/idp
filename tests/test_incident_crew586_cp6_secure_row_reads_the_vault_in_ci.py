"""crew#586 CP6 (2026-08-28): on the CI runner the `secure` row (bin/static-secret-gate) could not
read the vault: estate-secrets is private and github.token cannot fetch it, so the row was BLIND
on every hourly run. Now the estate's GitHub App is exchanged for a read-only installation token
(lane conscience-reader, metadata+contents read) from the vault entry github-app, estate-secrets
is cloned beside idp, and the grade reads it through ESTATE_SECRETS. Both ways: a refused mint or
clone is named as BLIND in the log and the row stays BLIND (the gate refuses an absent vault);
the lane can never write; the session and the checkout come before the grade, not after."""
import json
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows" / "conscience.yml"
LANES = ROOT / "platform" / "github-app" / "lanes.json"


def _steps():
    return yaml.safe_load(WF.read_text())["jobs"]["grade"]["steps"]


def _names():
    return [s.get("name") or s.get("uses") for s in _steps()]


def test_the_reader_lane_reads_and_never_writes():
    lane = json.loads(LANES.read_text())["conscience-reader"]
    assert lane == {"metadata": "read", "contents": "read"}


def test_session_then_vault_checkout_then_grade():
    n = _names()
    assert n.index("OCI session token from the GitHub OIDC token") < n.index("vault checkout for the secure row") < n.index("bin/idp-conscience")
    for s in _steps():
        if s.get("name") in ("oci cli", "OCI session token from the GitHub OIDC token", "vault checkout for the secure row"):
            assert "if" not in s, s["name"]


def test_grade_reads_the_checkout_through_estate_secrets():
    grade = next(s for s in _steps() if s.get("id") == "grade")
    assert grade["env"]["ESTATE_SECRETS"] == "${{ github.workspace }}/estate-secrets"


def test_a_refused_mint_or_clone_is_named_blind_and_the_token_is_masked():
    step = next(s for s in _steps() if s.get("name") == "vault checkout for the secure row")
    run = step["run"]
    assert "bin/idp-github-app token conscience-reader" in run
    assert run.count("BLIND vault checkout") == 2
    assert "::add-mask::$tok" in run and "x-access-token:***@" in run
    assert "exit 1" not in run  # the row goes BLIND; the run is not killed before it grades

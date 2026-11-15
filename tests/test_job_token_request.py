"""Adversarial tests for GitHub App repository-scoped token requests."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "platform/github-app/job_token_request.py"
spec = importlib.util.spec_from_file_location("job_token_request", MODULE)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
LANES = {
    "ticket-verifier": {"metadata": "read", "issues": "write", "actions": "read"},
    "agent-workforce": {"metadata": "read", "contents": "write", "issues": "write"},
}
SCOPES = {
    "schema": "job-token-scopes/v1",
    "enrolled_lanes": {"ticket-verifier": {"repository_ids": [1342523800, 1344360654]}},
}


def test_enrolled_lane_has_explicit_single_repository():
    assert mod.compile_request("ticket-verifier", LANES, SCOPES) == {
        "permissions": LANES["ticket-verifier"],
        "repository_ids": [1342523800, 1344360654],
    }


def test_legacy_uninventoried_lane_retains_permissions():
    assert mod.compile_request("agent-workforce", LANES, SCOPES) == {
        "permissions": LANES["agent-workforce"],
    }


@pytest.mark.parametrize(
    "bad_ids",
    [
        [],
        ["*"],
        ["chidionyema/idp"],
        [1344360654, 1344360654],
        "idp",
        ["idp\n"],
    ],
)
def test_invalid_repository_ids_refused(bad_ids):
    rule = {
        "schema": "job-token-scopes/v1",
        "enrolled_lanes": {"ticket-verifier": {"repository_ids": bad_ids}},
    }
    with pytest.raises(mod.ScopeError):
        mod.compile_request("ticket-verifier", LANES, rule)


@pytest.mark.parametrize(
    "scopes",
    [
        {"schema": "wrong", "enrolled_lanes": {}},
        {"schema": "job-token-scopes/v1", "enrolled_lanes": None},
        {
            "schema": "job-token-scopes/v1",
            "enrolled_lanes": {
                "ticket-verifier": {
                    "repository_ids": [1344360654],
                    "permissions": {"contents": "write"},
                }
            },
        },
    ],
)
def test_malformed_policy_refused(scopes):
    with pytest.raises(mod.ScopeError):
        mod.compile_request("ticket-verifier", LANES, scopes)


@pytest.mark.parametrize("lane", ["", "unknown", "ticket-verifier\\n"])
def test_unknown_lane_refused(lane):
    with pytest.raises(mod.ScopeError):
        mod.compile_request(lane, LANES, SCOPES)


def test_scope_does_not_expand_permission_envelope():
    assert (
        "contents"
        not in mod.compile_request("ticket-verifier", LANES, SCOPES)["permissions"]
    )


def test_invalid_permission_refused():
    with pytest.raises(mod.ScopeError):
        mod.compile_request(
            "ticket-verifier", {"ticket-verifier": {"metadata": "admin"}}, SCOPES
        )


def test_repository_config_matches_real_declared_file():
    reg = json.loads((ROOT / "platform/github-app/job-token-scopes.json").read_text())
    lanes_path = ROOT / "platform/github-app/lanes.json"
    data = json.loads(lanes_path.read_text())
    assert mod.compile_request("ticket-verifier", data, reg)["repository_ids"] == [
        1342523800,
        1344360654,
    ]


def test_ticket_verifier_covers_actual_crew_and_idp_consumers():
    """The issuer must not break real tickets in crew while reading IDP verdicts."""
    workflow = (ROOT / ".github/workflows/ticket-verification.yml").read_text()
    source = (ROOT / "bin/idp-ticket-verify").read_text()
    request = mod.compile_request("ticket-verifier", LANES, SCOPES)
    assert 'f"{owner}/crew"' in source
    assert 'f"{owner}/idp"' in source
    assert "--repo chidionyema/crew" in workflow
    assert request["repository_ids"] == [1342523800, 1344360654]
    assert len(request["repository_ids"]) == 2


def test_ticket_verifier_does_not_grant_other_repository():
    req = mod.compile_request("ticket-verifier", LANES, SCOPES)
    assert 1342523800 in req["repository_ids"]
    assert 1344360654 in req["repository_ids"]
    assert 1 not in req["repository_ids"]
    assert "contents" not in req["permissions"]


def _provider_receipt():
    return {
        "token": "ghs_NEVER_PRINT_THIS_BEARER_SECRET",
        "repository_selection": "selected",
        "repositories": [{"id": 1342523800}, {"id": 1344360654}],
        "permissions": LANES["ticket-verifier"],
    }


def test_provider_attests_exact_two_repository_scope():
    request = mod.compile_request("ticket-verifier", LANES, SCOPES)
    mod.verify_issued_token(request, _provider_receipt())


@pytest.mark.parametrize(
    "mutation",
    [
        {"repository_selection": "all"},
        {"repositories": [{"id": 1344360654}]},
        {"repositories": [{"id": 1342523800}, {"id": 1344360654}, {"id": 1}]},
        {"repositories": [{"id": 1342523800}, {"id": 1342523800}]},
        {"repositories": [{"id": True}, {"id": 1344360654}]},
        {"repositories": None},
        {"permissions": {"issues": "write", "contents": "write"}},
        {"permissions": None},
    ],
)
def test_unproven_provider_scope_is_refused(mutation):
    request = mod.compile_request("ticket-verifier", LANES, SCOPES)
    receipt = _provider_receipt() | mutation
    with pytest.raises(mod.ScopeError):
        mod.verify_issued_token(request, receipt)


def test_invalid_provider_receipt_is_refused_without_printing_secret():
    request = mod.compile_request("ticket-verifier", LANES, SCOPES)
    with pytest.raises(mod.ScopeError, match="receipt") as error:
        mod.verify_issued_token(request, [])
    assert "ghs_" not in str(error.value)


def test_cli_verifies_receipt_without_ever_echoing_token():
    fixture = _provider_receipt()
    fixture["repositories"] = [{"id": 1}]
    result = subprocess.run(
        [sys.executable, str(MODULE), "ticket-verifier", "--verify-response"],
        input=json.dumps(fixture),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 3
    assert result.stdout == ""
    assert "REFUSED" in result.stderr
    assert "ghs_" not in result.stderr


def test_cli_fail_closed_when_policy_missing(tmp_path):
    isolated = tmp_path / "job_token_request.py"
    shutil.copyfile(MODULE, isolated)
    result = subprocess.run(
        [sys.executable, str(isolated), "ticket-verifier"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 3
    assert result.stdout == ""
    assert "REFUSED" in result.stderr

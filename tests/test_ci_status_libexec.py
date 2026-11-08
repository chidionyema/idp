"""Required-check status must never claim merge-ready from a partial GitHub page.

These tests drive the actual estate CI status subprocess and the REAL ruleset,
with a fake gh API response. They are source-only; no privileged or live writes.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "platform/estate/libexec/ci-status.py"
POLICY = ROOT / "platform/github/ruleset.idp.required-checks.json"
REQUIRED = [
    c["context"]
    for rule in json.loads(POLICY.read_text())["rules"]
    if rule["type"] == "required_status_checks"
    for c in rule["parameters"]["required_status_checks"]
]

FAKE_GH = r'''#!/usr/bin/env python3
import json, os, sys
from urllib.parse import parse_qs, urlparse
path = sys.argv[2]
mode = os.environ.get("FAKE_CI_MODE", "missing")
if path.endswith("/commits/main"):
    print(json.dumps({"sha": "a1df4b42c0ffee", "commit": {"message": "head of main\n\nbody"}}))
    sys.exit(0)
if "/check-runs?" in path:
    query = parse_qs(urlparse(path).query)
    if "check_name" not in query:
        # A page of seemingly green unrelated checks is *not* an all-green CI verdict.
        print(json.dumps({"total_count": 523, "check_runs": [
            {"name": "unrelated", "status": "completed", "conclusion": "success"}
        ] * 100}))
        sys.exit(0)
    name = query["check_name"][0]
    if mode == "api_error":
        print("403 API rate limit exceeded", file=sys.stderr)
        sys.exit(1)
    if mode == "missing" and name != "test":
        print(json.dumps({"total_count": 0, "check_runs": []}))
        sys.exit(0)
    if mode == "partial" and name not in ("test", "greenlane"):
        print(json.dumps({"total_count": 0, "check_runs": []}))
        sys.exit(0)
    if mode == "failed" and name == "bdd":
        state = "failure"
    elif mode == "pending" and name == "bdd":
        state = None
    else:
        state = "success"
    if mode == "stale_green" and name == "bdd":
        print(json.dumps({"total_count": 2, "check_runs": [
            {"id": 42, "name": "bdd", "status": "completed", "conclusion": "failure",
             "app": {"id": 15368}},
            {"id": 41, "name": "bdd", "status": "completed", "conclusion": "success",
             "app": {"id": 15368}},
        ]}))
        sys.exit(0)
    if mode == "wrong_app" and name == "bdd":
        app_id = 12345
    else:
        app_id = 15368
    print(json.dumps({"total_count": 1, "check_runs": [
        {"id": 5, "name": name, "status": "completed" if state is not None else "in_progress",
         "conclusion": state, "app": {"id": app_id}}
    ]}))
    sys.exit(0)
print("not mocked", path, file=sys.stderr)
sys.exit(1)
'''


def _run(tmp_path, mode="missing", *args):
    gh = tmp_path / "gh"
    gh.write_text(FAKE_GH)
    gh.chmod(0o755)
    env = {**os.environ, "PATH": f"{tmp_path}:/usr/bin:/bin",
           "FAKE_CI_MODE": mode}
    p = subprocess.run([sys.executable, str(SCRIPT), *args],
                       capture_output=True, text=True, env=env, timeout=40)
    return p, json.loads(p.stdout)


def test_default_status_is_current_main_and_policy_source_pinned(tmp_path):
    p, body = _run(tmp_path)
    assert p.returncode == 0, p.stdout + p.stderr
    assert body["sha"] == "a1df4b42"
    assert body["branch"] == "main"
    assert body["required_policy_sha256"]
    assert body["required_policy"] == "platform/github/ruleset.idp.required-checks.json"


def test_one_success_out_of_all_required_contexts_is_not_merge_ready(tmp_path):
    p, body = _run(tmp_path)
    assert body["passed"] == 100
    assert body["merge_ready"] is False
    assert body["required_verdict"] == "ABSENT_REQUIRED_CHECKS"
    assert "required 1/" in body["summary"]
    assert set(body["required_missing"]) == set(REQUIRED) - {"test"}
    assert body["next_estate_action"]["code"] == "RECONCILE_REQUIRED_CHECK_PRODUCERS"


def test_all_required_exact_names_and_proper_app_can_be_green(tmp_path):
    p, body = _run(tmp_path, "all_green")
    assert p.returncode == 0
    assert body["merge_ready"] is True
    assert body["required_verdict"] == "REQUIRED_CHECKS_GREEN"
    assert set(body["required_green"]) == set(REQUIRED)


def test_any_required_red_overrides_raw_page_of_green(tmp_path):
    _, body = _run(tmp_path, "failed")
    assert not body["merge_ready"]
    assert body["required_checks"]["bdd"]["state"] == "failure"
    assert "bdd" in body["required_failed"]
    assert body["next_estate_action"]["code"] == "REMEDIATE_FAILED_CHECK_CLASS"


def test_an_in_progress_required_check_never_passes(tmp_path):
    _, body = _run(tmp_path, "pending")
    assert not body["merge_ready"]
    assert body["required_verdict"] == "PENDING_REQUIRED_CHECKS"
    assert "bdd" in body["required_pending"]


def test_old_green_does_not_override_latest_red(tmp_path):
    _, body = _run(tmp_path, "stale_green")
    assert body["required_checks"]["bdd"]["state"] == "failure"
    assert not body["merge_ready"]


def test_a_check_from_wrong_app_does_not_satisfy_required_integration(tmp_path):
    _, body = _run(tmp_path, "wrong_app")
    assert body["required_checks"]["bdd"]["state"] == "absent"
    assert not body["merge_ready"]


def test_github_403_is_unknown_not_a_success_or_an_absence(tmp_path):
    _, body = _run(tmp_path, "api_error")
    assert body["required_verdict"] == "BLIND_REQUIRED_CHECKS"
    assert set(body["required_unreadable"]) == set(REQUIRED)
    assert not body["merge_ready"]


def test_other_repository_cannot_inherit_idp_required_check_contract(tmp_path):
    p, body = _run(tmp_path, "all_green", "repo=other/repo")
    assert p.returncode == 0
    assert body["merge_ready"] is False
    assert body["required_verdict"] == "BLIND_REQUIRED_POLICY"
    assert body["next_estate_action"]["code"] == "REPAIR_CHECK_VISIBILITY"

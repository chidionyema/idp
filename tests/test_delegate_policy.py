"""Falsifier for bin/idp-delegate-policy and the contract of the delegate-signer workflow.

Every DENY case below is paired with a control that differs in exactly one thing and is ALLOWED,
so a judge that denied everything would fail here.
"""

from __future__ import annotations

import datetime as dt
import importlib.machinery
import importlib.util
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "bin" / "idp-delegate-policy"
WORKFLOW = ROOT / ".github" / "workflows" / "delegate-signer.yml"
POLICY = ROOT / "docs" / "keys" / "delegate-policy.json"

_loader = importlib.machinery.SourceFileLoader("idp_delegate_policy", str(SCRIPT))
_spec = importlib.util.spec_from_loader("idp_delegate_policy", _loader)
m = importlib.util.module_from_spec(_spec)
_loader.exec_module(m)

NOW = dt.datetime(2026, 11, 28, 12, 0, tzinfo=dt.timezone.utc)
ACTOR = "estate-agents[bot]"


def policy(**over):
    d = {
        "id": "d1",
        "actors": [ACTOR],
        "allow": ["catalog/**"],
        "deny": [],
        "expires": "2026-12-28T00:00:00Z",
        "max_commits": 5,
        "revoked": False,
    }
    d.update(over)
    return {"version": 1, "floor_deny": [], "delegates": [d]}


def judge(paths, pol=None, actor=ACTOR, commits=1, now=NOW, **kw):
    return m.evaluate(
        pol if pol is not None else policy(), actor, commits, paths, now, **kw
    )[0]


def test_control_catalog_change_is_allowed():
    assert judge(["catalog/issue-classes.json"]) == "ALLOW"


def test_denylist_beats_allowlist_and_removing_it_flips_the_result():
    pol = policy(allow=["catalog/**"], deny=["catalog/secret/**"])
    assert judge(["catalog/secret/x.json"], pol) == "DENY"
    assert (
        judge(["catalog/secret/x.json"], policy(allow=["catalog/**"], deny=[]))
        == "ALLOW"
    )


def test_every_founder_only_path_is_denied_even_when_allowed_by_glob():
    allow_all = policy(allow=["**"])
    for p in (
        ".githooks/pre-push",
        "bin/idp-ci-guarded-paths",
        "bin/idp-guarded-paths",
        "bin/idp-auth",
        "bin/idp-auth-verify",
        "docs/keys/founder.pub",
        "docs/keys/delegate-policy.json",
        ".github/workflows/delegate-signer.yml",
    ):
        assert judge([p], allow_all) == "DENY", p
    assert judge(["docs/readme.md"], allow_all) == "ALLOW"


def test_the_floor_is_the_evaluators_own_not_only_the_policys():
    # the policy lists no floor at all; the hard-coded floor still denies, and an empty floor would not
    allow_all = policy(allow=["**"])
    assert judge([".githooks/pre-push"], allow_all) == "DENY"
    assert judge([".githooks/pre-push"], allow_all, floor=()) == "ALLOW"


def test_path_tricks_do_not_slip_past_the_floor():
    allow_all = policy(allow=["**"])
    for p in (
        "./.githooks/pre-push",
        ".GITHOOKS/pre-push",
        "catalog/../.githooks/pre-push",
        "BIN/IDP-AUTH",
        "bin//idp-auth",
        "/etc/passwd",
        "catalog\\..\\.githooks\\x",
        "../x",
        "a\x00b",
        "",
    ):
        assert judge([p], allow_all) == "DENY", repr(p)


def test_expired_delegate_is_denied_and_a_later_clock_is_the_only_difference():
    pol = policy(expires="2026-11-28T11:59:59Z")
    assert judge(["catalog/a.json"], pol) == "DENY"
    assert judge(["catalog/a.json"], pol, now=NOW - dt.timedelta(days=1)) == "ALLOW"
    assert judge(["catalog/a.json"], policy(expires="")) == "DENY"
    assert judge(["catalog/a.json"], policy(expires="not-a-date")) == "DENY"
    assert judge(["catalog/a.json"], policy(expires=None)) == "DENY"


def test_revoked_delegate_is_denied_and_unrevoking_flips_it():
    assert judge(["catalog/a.json"], policy(revoked=True)) == "DENY"
    assert judge(["catalog/a.json"], policy(revoked=False)) == "ALLOW"
    bad = policy()
    del bad["delegates"][0]["revoked"]
    assert (
        judge(["catalog/a.json"], bad) == "DENY"
    )  # a missing flag is not "not revoked"


def test_commit_cap():
    assert judge(["catalog/a.json"], commits=5) == "ALLOW"
    assert judge(["catalog/a.json"], commits=6) == "DENY"
    assert judge(["catalog/a.json"], commits=0) == "DENY"


def test_empty_diff_is_blind_not_allowed():
    assert judge([]) == "BLIND"


def test_unresolvable_ref_is_denied_not_blind_and_not_allowed():
    assert judge(None) == "DENY"


def test_unknown_actor_and_broken_policy_are_denied():
    assert judge(["catalog/a.json"], actor="someone-else") == "DENY"
    assert judge(["catalog/a.json"], pol={"version": 2, "delegates": []}) == "DENY"
    assert judge(["catalog/a.json"], pol={}) == "DENY"
    assert (
        judge(["catalog/a.json"], pol=None) == "ALLOW"
    )  # the default policy() control


def test_a_path_matching_no_allow_is_denied():
    assert judge(["docs/readme.md"]) == "DENY"
    assert (
        judge(["catalog/a.json", "docs/readme.md"]) == "DENY"
    )  # one bad path denies the lot


def test_cli_exit_codes_and_receipt(tmp_path):
    pol = tmp_path / "p.json"
    pol.write_text(json.dumps(policy()))
    paths = tmp_path / "paths.txt"

    def run(*extra, paths_file=paths):
        return subprocess.run(  # noqa: S603
            [
                sys.executable,
                "-I",
                str(SCRIPT),
                "--policy",
                str(pol),
                "--actor",
                ACTOR,
                "--commits",
                "1",
                "--paths-file",
                str(paths_file),
                "--now",
                "2026-11-28T12:00:00Z",
                *extra,
            ],
            capture_output=True,
            text=True,
        )

    paths.write_text("catalog/a.json\n")
    receipt = tmp_path / "r.json"
    r = run("--receipt", str(receipt))
    assert r.returncode == 0 and r.stdout.startswith("ALLOW")
    body = json.loads(receipt.read_text())
    assert body["verdict"] == "ALLOW" and len(body["policy_sha256"]) == 64
    paths.write_text(".githooks/pre-push\n")
    assert run().returncode == 1
    paths.write_text("")
    assert run().returncode == 2
    assert run(paths_file=tmp_path / "missing.txt").returncode == 1
    pol.write_text("{not json")
    paths.write_text("catalog/a.json\n")
    assert run().returncode == 1


def test_shipped_policy_is_valid_and_judges_a_catalog_change_but_not_a_workflow_change():
    pol = json.loads(POLICY.read_text())
    now = dt.datetime(2026, 11, 29, tzinfo=dt.timezone.utc)
    assert (
        m.evaluate(pol, "estate-agents[bot]", 1, ["catalog/optimus-metrics.json"], now)[
            0
        ]
        == "ALLOW"
    )
    assert (
        m.evaluate(pol, "estate-agents[bot]", 1, [".github/workflows/ci.yml"], now)[0]
        == "DENY"
    )
    assert set(m.FLOOR) <= set(
        pol["floor_deny"]
    )  # the file and the code agree on the floor


def test_signer_workflow_contract():
    text = WORKFLOW.read_text()
    assert "pull_request_target" not in text
    assert re.search(r'workflows:\s*\["greenlane"\]', text)
    names = [
        re.search(r"^name:\s*(\S+)", p.read_text(), re.M)
        for p in (ROOT / ".github" / "workflows").glob("*.yml")
    ]
    assert "greenlane" in {
        x.group(1) for x in names if x
    }  # the trigger names a workflow that exists
    assert re.search(r"^permissions:\s*\n\s+contents:\s*read\s*$", text, re.M)
    assert "environment: delegate-signer" in text
    assert "head_repository.full_name == github.repository" in text
    assert "workflow_run.conclusion == 'success'" in text
    assert "bin/idp-delegate-policy" in text
    # nothing the head branch controls is checked out or interpolated into a shell line
    assert not re.search(r"ref:\s*\$\{\{\s*github\.event\.workflow_run\.head", text)
    for line in text.splitlines():
        # an expression may feed an env value or the concurrency key; it never sits in a command
        if "${{" in line and not line.lstrip().startswith("#"):
            assert re.match(r"^\s+([A-Z_]+|group):\s*\$\{\{", line), line

"""Founder, 2026-08-30, docs/reference/incidents/2026-08-30-three-incidents-one-defect.md:
"Every infra change ships a control or says why not." He asked for it machine-checked on the
pull request rather than written in a rules file, in his own words: "prose in a CLAUDE.md is
itself an invariant living in someone's head, you'd be violating your own pattern". The doc
listed it under "Named here so it is not mistaken for done: ... Not built."

Three incidents in one day shared one defect -- a change went in and the thing that would have
caught it did not exist. The rule is policy/operating_model.rego `control_shipped`.

PROOF OBLIGATION. A control is not proved by a fixture invented to suit it. The refused case
here is the shape of the real pull request the incident is named for, #1027: it changed
clusters/oke/platform.yaml, three platform/ manifests and three test files, and its body named
no control for the nine-row automatic-uninstall sweep -- the change that then destroyed the
evidence of the next incident and that the founder ordered undone in #1032. Its body is carried
verbatim in policy/fixtures/opmodel-no-control.json minus the Control: line it never had.

What this test does NOT claim: that naming a control file proves the control covers the change.
It does not, and the rule's own comment says so. What is proved here is that a pull request
touching platform/, clusters/ or bin/idp-* cannot reach a merge without either pointing at a
control it ships or writing down why there is none.

Rung 2 on the control ladder (fail before merge). Runs conftest on a fixture; opens no socket.
"""

import json
import pathlib
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy"
FIX = POLICY / "fixtures"
RULE = "rule=control_shipped"

pytestmark = pytest.mark.skipif(
    shutil.which("conftest") is None,
    reason="conftest is not installed, so NOTHING here was judged; CI installs it (ci.yml)",
)


def _rules(path: pathlib.Path) -> set[str]:
    out = subprocess.run(
        [
            "conftest",
            "test",
            "--parser",
            "json",
            "-p",
            str(POLICY),
            "-o",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    return {
        f["msg"].split(" | ")[0]
        for r in json.loads(out)
        for f in (r.get("failures") or [])
    }


def _edit(tmp_path: pathlib.Path, fixture: str, **change) -> pathlib.Path:
    d = json.loads((FIX / fixture).read_text())
    d["pr"].update(change)
    p = tmp_path / "pr.json"
    p.write_text(json.dumps(d))
    return p


def test_the_real_pull_request_the_incident_is_named_for_is_refused():
    """The proof obligation: the rule is watched refusing the pre-fix state, not a straw man."""
    assert RULE in _rules(FIX / "opmodel-no-control.json")


def test_saying_why_not_is_accepted_because_that_is_half_the_rule():
    assert RULE not in _rules(FIX / "opmodel-control-none.json")


def test_the_canonical_good_pull_request_is_still_clean():
    """LAW 38: a guard that refuses correct work is an outage. opmodel-ok.json is the fixture
    every rule in the file must permit, and two other gate tests assert it fires nothing."""
    assert _rules(FIX / "opmodel-ok.json") == set()


def test_a_control_the_pull_request_does_not_ship_is_refused(tmp_path):
    """The line cannot be satisfied by pointing at a test that already existed."""
    p = _edit(
        tmp_path,
        "opmodel-no-control.json",
        body="Control: tests/test_something_that_already_existed.py\n",
    )
    assert RULE in _rules(p)


def test_a_named_file_that_is_not_a_control_is_refused(tmp_path):
    """Naming a manifest the PR happens to change is not naming a control."""
    p = _edit(
        tmp_path,
        "opmodel-no-control.json",
        body="Control: platform/edge/traefik.yaml\n",
    )
    assert RULE not in _rules(
        p
    )  # platform/edge/ IS a control prefix: an admission rule counts
    p = _edit(
        tmp_path,
        "opmodel-no-control.json",
        body="Control: platform/chaos/mesh/helmrelease.yaml\n",
    )
    assert RULE in _rules(p)


def test_a_reason_has_to_be_a_reason(tmp_path):
    assert RULE in _rules(
        _edit(tmp_path, "opmodel-no-control.json", body="Control: none: no\n")
    )


def test_a_pull_request_that_touches_nothing_in_the_world_is_never_asked(tmp_path):
    p = _edit(
        tmp_path,
        "opmodel-no-control.json",
        files=["docs/reference/incidents/2026-08-30-three-incidents-one-defect.md"],
    )
    assert RULE not in _rules(p)


def test_a_pull_request_opened_before_the_rule_landed_is_not_refused(tmp_path):
    """Same grandfather clause as optimised_plan and self_heal_has_breaker: nobody is refused
    for a line they could not have known to write (LAW 38)."""
    assert RULE not in _rules(
        _edit(tmp_path, "opmodel-no-control.json", createdAt="2026-08-30T12:00:00Z")
    )
    assert RULE in _rules(
        _edit(tmp_path, "opmodel-no-control.json", createdAt="2026-09-01T12:00:00Z")
    )


def test_the_rule_grades_the_same_three_prefixes_verify_claims_does():
    """One definition of "touches the world", not a second one invented here (LAW 23)."""
    rego = (POLICY / "operating_model.rego").read_text()
    assert 'world_prefixes := {"platform/", "clusters/", "bin/idp-"}' in rego
    wf = (ROOT / ".github/workflows/verify-claims.yml").read_text()
    assert "platform/, clusters/ or bin/idp-*" in wf

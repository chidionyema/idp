"""Incident 2026-08-27 (crew#473): eight fully green idp PRs waited a median 6.1 hours (44 hours
in total) for an `APPROVE: <word>` comment from the founder, and nothing else. Founder ruling:
"you need to approve all / no founder friction if can be avoided / yes portal".

Rule: the operating-model gate never waits for the founder's word on any path. A change under a
founder-facing prefix with no `Approval-word:` line, or with a word he has not answered, passes.
His veto stays: a `DENY: <word>` from his GitHub login on the declared word still refuses.
Rung 4, one test per bug. Runs conftest over the policy directory; opens no socket."""

import json
import pathlib
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy"
FIX = POLICY / "fixtures"

pytestmark = pytest.mark.skipif(
    shutil.which("conftest") is None, reason="conftest not installed"
)


def _deny_rules(fixture: str) -> set[str]:
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
            str(FIX / fixture),
        ],
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    rules = set()
    for result in json.loads(out):
        for failure in result.get("failures") or []:
            rules.add(failure["msg"].split(" | ")[0])
    return rules


def test_founder_facing_change_without_a_word_passes():
    rules = _deny_rules("opmodel-no-approval.json")
    assert "rule=founder_approval_required" not in rules
    assert not rules, rules


def test_founder_facing_change_with_an_unanswered_word_passes():
    rules = _deny_rules("opmodel-approval-pending.json")
    assert "rule=founder_approval_pending" not in rules
    assert not rules, rules


def test_a_deny_from_the_founder_still_refuses():
    assert "rule=founder_denied" in _deny_rules("opmodel-denied.json")

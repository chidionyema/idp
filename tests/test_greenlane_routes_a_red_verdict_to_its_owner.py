"""idp#8303: a red lane is told to its owner, not left in the abyss.

Before: report() wrote the head's commit status and published to NATS at 127.0.0.1:4222, which
from a GitHub runner is nothing. lane/seal-only parked red after 3 attempts with its owner
(Agent: opencode-deepseek-seal, claim #8273) told nothing. Each test fails on main.
"""

from __future__ import annotations

import json

import greenlane.github as gh_mod
from greenlane.engine import CONFLICT, RED, TESTING
from greenlane.github import VERDICT_MARK, GitHubBackend

MESSAGE = "fix(x): y\n\nClaim: chidionyema/idp#8273\nAgent: opencode-deepseek-seal\n"
REASON = (
    "fast-gate / fast-gate failure "
    "https://github.com/chidionyema/idp/actions/runs/1/job/2 -- fast gate"
)


def _backend(monkeypatch, comments=None, message=MESSAGE):
    calls: list[tuple] = []
    existing = comments or []

    def fake_run(*args, check=True, input=None, env=None):
        calls.append(args)
        if args[:2] == ("gh", "api") and str(args[2]).endswith("comments?per_page=100"):
            return json.dumps(existing)
        return ""

    monkeypatch.setattr(gh_mod, "_run", fake_run)
    b = GitHubBackend.__new__(GitHubBackend)
    b.repo, b.run_url = "chidionyema/idp", "https://run"
    b.gh = lambda path, method="GET", fields=None: (
        {"commit": {"message": message}} if path.startswith("commits/") else None
    )
    return b, calls


def _posts(calls):
    return [c for c in calls if "-X" in c and "POST" in c]


def test_a_red_verdict_reaches_the_claim_issue_with_the_owner_named(monkeypatch):
    b, calls = _backend(monkeypatch)
    b._route_to_owner("lane/seal-only", "a" * 40, RED, REASON)
    posts = _posts(calls)
    comment = [c for c in posts if str(c[2]).endswith("issues/8273/comments")]
    assert comment, calls
    body = next(a for a in comment[0] if str(a).startswith("body="))
    assert "opencode-deepseek-seal" in body
    assert "actions/runs/1/job/2" in body, "the owner gets the failing log"
    assert VERDICT_MARK in body
    labels = [c for c in posts if str(c[2]).endswith("issues/8273/labels")]
    assert labels and "labels[]=P1" in labels[0], "a parked lane is owned at P1"


def test_the_same_verdict_is_told_once(monkeypatch):
    marker = f"{VERDICT_MARK} lane=lane/x head={'a' * 40} status={RED} -->"
    b, calls = _backend(monkeypatch, comments=[{"body": marker}])
    b._route_to_owner("lane/x", "a" * 40, RED, REASON)
    assert not _posts(calls), "a verdict already on the issue is not repeated"


def test_a_conflict_is_routed_without_escalation(monkeypatch):
    b, calls = _backend(monkeypatch)
    b._route_to_owner("lane/x", "b" * 40, CONFLICT, "does not rebase onto main")
    posts = _posts(calls)
    assert any(str(c[2]).endswith("comments") for c in posts)
    assert not any(str(c[2]).endswith("labels") for c in posts)


def test_testing_is_not_routed(monkeypatch):
    b, calls = _backend(monkeypatch)
    b._route_to_owner("lane/x", "c" * 40, TESTING, "testing in b1")
    assert not calls


def test_a_lane_with_no_claim_is_said_not_swallowed(monkeypatch, capsys):
    b, calls = _backend(monkeypatch, message="no trailers")
    b._route_to_owner("lane/x", "d" * 40, RED, REASON)
    assert not _posts(calls)
    assert "no owner to tell" in capsys.readouterr().err

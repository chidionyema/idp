"""idp#5758: the claim/lane loop deadlocked finished work three ways, all measured on
2026-10-11 (PRs #5617, #5632, #5704 sat red for a day+).

Mechanism 1: foreign_prs() exempted PRs by author login -- but every agent pushes with the
shared gh auth, so every agent PR was exempt and the auto-adopt never fired. Now a PR is
founder hand work only when nothing declares an agent (no Claim/Agent line in the body or
the head commit message); declared work is adopted and proven.

Mechanism 2: heartbeat(). While the lane holds a branch its claim must not lapse; the
backend stamps the same agent and paths with a fresh heartbeat, at most about hourly.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from greenlane import github as G  # noqa: E402


def _pr(number=1, body="", sha="s1", ref="fix/face", login="chidionyema"):
    return {
        "number": number,
        "user": {"login": login},
        "body": body,
        "head": {"sha": sha, "ref": ref},
    }


class Stub(G.GitHubBackend):
    def __init__(self, responses=None, messages=None):
        self.repo = "Mumchimp/idp"
        self.app_login = "idp-app[bot]"
        self.responses = responses or {}
        self.messages = messages or {}
        self.posted = []

    def gh(self, path, method="GET", fields=None):
        if method == "POST":
            self.posted.append((path, (fields or {}).get("body", "")))
            return {}
        return self.responses.get(path)

    def git(self, *args, check=True):
        if args[:2] == ("merge-base", "origin/main"):
            return "base"
        if args[:2] == ("log", "--format=%B"):
            return self.messages.get("branch", "")
        return ""


def test_a_declared_pr_from_the_founders_login_is_still_adopted():
    """The measured pile: agents push under the founder's login; the declaration, not the
    login, is what says agent work."""
    b = Stub(
        responses={
            "pulls?state=open&per_page=100": [_pr()],
            "commits/s1": {
                "commit": {
                    "message": "fix\n\nClaim: Mumchimp/idp#5755\nAgent: opencode\n"
                }
            },
        }
    )
    assert b.foreign_prs() == [
        {"number": 1, "lane": "fix/face", "head": "s1", "user": "chidionyema"}
    ]


def test_an_undeclared_pr_is_founder_hand_work_and_untouched():
    b = Stub(
        responses={
            "pulls?state=open&per_page=100": [_pr()],
            "commits/s1": {"commit": {"message": "founder: workflows change\n"}},
        }
    )
    assert b.foreign_prs() == []


def test_a_body_declaration_is_enough_no_commit_lookup(monkeypatch):
    b = Stub()
    seen = []

    def gh(path, method="GET", fields=None):
        seen.append(path)
        return None

    monkeypatch.setattr(b, "gh", gh)
    assert b.declared(_pr(body="Claim: Mumchimp/idp#5755\nAgent: opencode\n")) is True
    assert seen == []  # the head commit was never fetched


def _claim(agent="opencode", paths="bin/x", age=timedelta(minutes=90), model=None):
    # Ages are measured from the real clock: the production check compares against
    # datetime.now(), so a frozen fixture here would drift from fresh to lapsed mid-run.
    hb = (datetime.now(timezone.utc) - age).strftime("%Y-%m-%dT%H:%M:%SZ")
    model_field = f" model={model} " if model else " "
    return f"CLAIM agent={agent}{model_field}paths={paths} heartbeat={hb}"


def test_a_lapsed_claim_on_a_held_lane_is_stamped_with_the_same_agent_and_paths():
    b = Stub(
        responses={
            "issues/5755": {"state": "open"},
            "issues/5755/comments?per_page=100": [{"body": _claim()}],
        },
        messages={
            "branch": "fix: x\n\nClaim: Mumchimp/idp#5755\nAgent: opencode\n",
        },
    )
    b.heartbeat("lane/face", "head1")
    (path, body) = b.posted[0]
    assert path == "issues/5755/comments"
    assert "CLAIM agent=opencode paths=bin/x heartbeat=" in body
    assert "model=" not in body.split("\n")[0]


def test_a_fresh_claim_is_not_re_stamped_and_no_trailer_means_no_stamp():
    b = Stub(
        responses={
            "issues/5755/comments?per_page=100": [
                {"body": _claim(age=timedelta(minutes=10))}
            ]
        },
        messages={"branch": "Claim: Mumchimp/idp#5755\nAgent: opencode\n"},
    )
    b.heartbeat("lane/face", "head1")
    assert b.posted == []

    b2 = Stub(messages={"branch": "no trailers here\n"})
    b2.heartbeat("lane/face", "head1")
    assert b2.posted == []


def test_a_stamping_failure_never_raises(monkeypatch):
    b = Stub(messages={"branch": "Claim: Mumchimp/idp#5755\nAgent: opencode\n"})

    def boom(*a, **k):
        raise RuntimeError("gh down")

    monkeypatch.setattr(b, "gh", boom)
    b.heartbeat("lane/face", "head1")  # must not raise
    assert b.posted == []

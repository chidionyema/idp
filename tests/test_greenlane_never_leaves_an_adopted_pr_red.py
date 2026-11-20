"""idp#8331: a hand-raised PR the Greenlane adopted is closed; its lane lands the work.

Before: adopted PRs stayed open and their own CI failed the bddproof rung until landing, so
every agent PR reached the founder red for the same reason (#8316 #8318 #8319 #8320 #8322
#8327, 2026-11-19). Each test fails on main.
"""

from __future__ import annotations

from greenlane.engine import Engine
from greenlane.github import ADOPTED, GitHubBackend


def _backend(prs):
    calls = []

    def gh(path, method="GET", fields=None):
        calls.append((path, method, fields))
        return prs if path.startswith("pulls?") else {}

    b = GitHubBackend.__new__(GitHubBackend)
    b.app_login = "estate-agents[bot]"
    b.gh = gh
    return b, calls


def test_an_adopted_agent_pr_is_closed_and_told_where_its_work_is():
    prs = [
        {
            "number": 1,
            "body": f"{ADOPTED} lane/x\n\nwork",
            "user": {"login": "chidionyema"},
        },
        {
            "number": 2,
            "body": "Greenlane-Head: proof",
            "user": {"login": "estate-agents[bot]"},
        },
        {
            "number": 3,
            "body": "founder hand work, undeclared",
            "user": {"login": "chidionyema"},
        },
    ]
    b, calls = _backend(prs)
    assert b.retire_adopted_prs() == [1]
    assert ("pulls/1", "PATCH", {"state": "closed"}) in calls
    comment = next(c for c in calls if c[0] == "issues/1/comments")
    assert "lane/x" in comment[2]["body"]
    assert not any(c[0] in ("pulls/2", "pulls/3") for c in calls), (
        "app and founder PRs untouched"
    )


def test_the_app_own_adopted_pr_is_never_closed():
    prs = [
        {
            "number": 9,
            "body": f"{ADOPTED} lane/y",
            "user": {"login": "estate-agents[bot]"},
        }
    ]
    b, calls = _backend(prs)
    assert b.retire_adopted_prs() == []


def test_every_tick_retires_adopted_prs():
    src = open(Engine.tick.__code__.co_filename).read()
    tick = src.split("    def tick(", 1)[1].split("\n    def ", 1)[0]
    assert "retire_adopted_prs" in tick

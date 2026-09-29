"""greenlane/github.py against a real git repository and a recorded GitHub: the verdict on a
candidate, which pull requests are foreign, how a hand-raised branch becomes a lane, and that a
lane's work squashes onto main or is refused as a conflict. Nothing here talks to GitHub."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from greenlane.engine import CONFLICT, LANDED, RED  # noqa: E402
from greenlane.github import BOT_LANE, MARKER, GitHubBackend  # noqa: E402

REQUIRED = ["fast-gate / fast-gate", "bdd", "test"]


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path, monkeypatch):
    r = tmp_path / "r"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "user.email", "t@t")
    _git(r, "config", "user.name", "t")
    _git(r, "config", "commit.gpgsign", "false")
    (r / "a.txt").write_text("one\n")
    _git(r, "add", "a.txt")
    _git(r, "commit", "-q", "-m", "root")
    monkeypatch.chdir(r)
    return r


class Recorded(GitHubBackend):
    """gh() answers from a table; every write is recorded."""

    def __init__(self, table: dict, **kw):
        super().__init__("o/idp", REQUIRED, **kw)
        self.table, self.writes = table, []

    def gh(self, path, method="GET", fields=None):
        if method != "GET":
            self.writes.append((method, path, fields))
            return None
        return self.table.get(path.split("?")[0])


def _run(name, conclusion, status="completed", rid=1):
    return {
        "name": name,
        "conclusion": conclusion,
        "status": status,
        "id": rid,
        "html_url": f"u/{rid}",
    }


def test_verdict_needs_every_required_check_and_the_latest_run_wins():
    b = Recorded(
        {
            "commits/c1/check-runs": {
                "check_runs": [_run("bdd", "success"), _run("test", "success")]
            }
        }
    )
    assert b.checks("c1") == ("pending", "waiting on fast-gate / fast-gate")
    b = Recorded(
        {
            "commits/c2/check-runs": {
                "check_runs": [
                    _run("fast-gate / fast-gate", "success"),
                    _run("bdd", "failure", rid=3),
                    _run("bdd", "success", rid=4),
                    _run("test", "skipped"),
                ]
            }
        }
    )
    assert b.checks("c2") == ("green", "")
    b = Recorded(
        {
            "commits/c3/check-runs": {
                "check_runs": [
                    _run("fast-gate / fast-gate", "success"),
                    _run("bdd", "failure", rid=9),
                    _run("test", None, status="in_progress"),
                ]
            }
        }
    )
    verdict, reason = b.checks("c3")
    assert verdict == "red" and reason.startswith("bdd failure u/9")


def test_only_the_engines_own_pull_requests_are_not_foreign():
    prs = [
        {
            "number": 1,
            "user": {"login": "estate-agents[bot]"},
            "body": f"x {MARKER} candidate abc",
            "head": {"ref": "lane/a", "sha": "s1"},
        },
        {
            "number": 2,
            "user": {"login": "estate-agents[bot]"},
            "body": "no marker",
            "head": {"ref": "feat/b", "sha": "s2"},
        },
        {
            "number": 3,
            "user": {"login": "someone"},
            "body": f"{MARKER} forged",
            "head": {"ref": "feat/c", "sha": "s3"},
        },
    ]
    b = Recorded({"pulls": prs})
    assert [p["number"] for p in b.foreign_prs()] == [2, 3]


def test_a_hand_raised_pull_request_is_closed_and_its_branch_becomes_a_lane(repo):
    b = Recorded({})
    pushed = []
    b.git = lambda *a, check=True: pushed.append(a) or ""
    b.relane({"number": 7, "lane": "feat/x", "head": "deadbeef", "user": "someone"})
    assert (
        "push",
        "-q",
        "origin",
        "deadbeef:refs/heads/lane/feat/x",
    ) == pushed[0][:4]
    assert [w[:2] for w in b.writes] == [
        ("POST", "issues/7/comments"),
        ("PATCH", "pulls/7"),
    ]
    assert "lane/feat/x" in b.writes[0][2]["body"]
    pushed.clear()
    b.relane(
        {"number": 8, "lane": BOT_LANE, "head": "cafe", "user": "github-actions[bot]"}
    )
    assert pushed == []  # already a lane name: no second ref


def test_a_lane_squashes_onto_main_or_is_refused_as_a_conflict(repo):
    main = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "-q", "-b", "work")
    (repo / "b.txt").write_text("b\n")
    _git(repo, "add", "b.txt")
    _git(repo, "commit", "-q", "-m", "add b")
    (repo / "b.txt").write_text("bb\n")
    _git(repo, "commit", "-q", "-am", "grow b")
    head = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "-q", "main")
    (repo / "a.txt").write_text("two\n")
    _git(repo, "commit", "-q", "-am", "main moves on")
    onto = _git(repo, "rev-parse", "HEAD")
    b = Recorded({})
    new = b.rebase(head, onto)
    assert new and _git(repo, "rev-parse", f"{new}^") == onto
    assert _git(repo, "log", "-1", "--format=%s", new) == "grow b"
    assert f"Greenlane-Head: {head}" in _git(repo, "log", "-1", "--format=%B", new)
    assert (
        _git(repo, "show", f"{new}:b.txt") == "bb"
        and _git(repo, "show", f"{new}:a.txt") == "two"
    )
    # a lane that edits the same line main changed does not apply: refused, nothing left behind
    _git(repo, "checkout", "-q", "-b", "clash", main)
    (repo / "a.txt").write_text("three\n")
    _git(repo, "commit", "-q", "-am", "clash")
    clash = _git(repo, "rev-parse", "HEAD")
    assert b.rebase(clash, onto) is None
    assert _git(repo, "worktree", "list").count("\n") == 0


def test_statuses_map_the_engines_verdicts():
    b = Recorded({}, run_url="https://run")
    for status, state in ((LANDED, "success"), (RED, "failure"), (CONFLICT, "failure")):
        b.report("lane/x", "abc", status, "why")
        assert b.writes[-1] == (
            "POST",
            "statuses/abc",
            {
                "state": state,
                "context": "greenlane",
                "description": "why",
                "target_url": "https://run",
            },
        )

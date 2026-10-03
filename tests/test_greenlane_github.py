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
from greenlane.github import ADOPTED, BOT_LANE, MARKER, GitHubBackend  # noqa: E402

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
        base, _, query = path.partition("?")
        rows = self.table.get(base)
        if base == "pulls" and "head=" in query and isinstance(rows, list):
            ref = query.split("head=")[1].split("&")[0].split(":", 1)[1]
            return [r for r in rows if r["head"]["ref"] == ref]
        return rows


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
    prs.append(
        {
            "number": 4,
            "user": {
                "login": "o"
            },  # the repository owner: the founder's landing vehicle
            "body": "workflow fix, founder lands",
            "head": {"ref": "fix/x", "sha": "s4"},
        }
    )
    b = Recorded({"pulls": prs})
    assert [p["number"] for p in b.foreign_prs()] == [2, 3]


def test_a_hand_raised_pull_request_is_adopted_never_closed(repo):
    """Edge cases mapped (founder 2026-09-29, "I don't just discard stuff"):
    1. plain branch -> lane/<branch> ref created, PR body marked, PR stays open (no PATCH state)
    2. branch already lane/* or the bot lane -> adopted in place, no second ref
    3. an adopted PR is not foreign on the next tick (no comment spam, no second adoption)
    4. the owner's PR is never touched (founder's landing vehicle)
    5. a draft is work too: adopted like any other
    6. a fork PR is adopted from its head sha; its branch cannot be rewritten, the lane still lands
    """
    b = Recorded({"pulls/7": {"body": "original body"}})
    pushed = []
    b.git = lambda *a, check=True: pushed.append(a) or ""
    b.relane({"number": 7, "lane": "feat/x", "head": "deadbeef", "user": "someone"})
    assert pushed[0][:5] == (
        "push",
        "-q",
        "-f",
        "origin",
        "deadbeef:refs/heads/lane/feat/x",
    )
    assert [w[:2] for w in b.writes] == [
        ("PATCH", "pulls/7"),
        ("POST", "issues/7/comments"),
    ]
    assert b.writes[0][2]["body"].startswith(f"{ADOPTED} lane/feat/x\n")
    assert "original body" in b.writes[0][2]["body"]
    assert (
        "stays open" in b.writes[1][2]["body"]
        and "lane/feat/x" in b.writes[1][2]["body"]
    )
    assert not any(w[2].get("state") for w in b.writes)  # never closed
    pushed.clear()
    b.relane(
        {"number": 8, "lane": BOT_LANE, "head": "cafe", "user": "github-actions[bot]"}
    )
    assert pushed == []  # already a lane name: no second ref
    b.relane({"number": 9, "lane": "lane/feat/y", "head": "f00d", "user": "someone"})
    assert pushed == []


def test_adopted_and_owner_pull_requests_are_not_foreign_and_adopted_heads_are_followed(
    repo,
):
    prs = [
        {  # adopted last tick: not foreign again
            "number": 1,
            "user": {"login": "someone"},
            "body": f"{ADOPTED} lane/feat/a\n\nbody",
            "head": {"ref": "feat/a", "sha": "a2"},
            "draft": False,
        },
        {  # the repository owner's: the founder lands it by hand, the engine never touches it
            "number": 2,
            "user": {"login": "o"},
            "body": "workflow fix",
            "head": {"ref": "fix/w", "sha": "w1"},
        },
        {  # a draft by an agent is work: foreign, to be adopted
            "number": 3,
            "user": {"login": "someone"},
            "body": "",
            "head": {"ref": "feat/d", "sha": "d1"},
            "draft": True,
        },
    ]
    b = Recorded({"pulls": prs})
    assert [p["number"] for p in b.foreign_prs()] == [3]
    assert b.adopted_prs() == [
        {"number": 1, "branch": "feat/a", "lane": "lane/feat/a", "head": "a2"}
    ]
    # lanes(): the adopted PR's head moved (a1 -> a2): the lane ref follows it
    pushed = []
    real_git = b.git

    def git(*a, check=True):
        if a[0] == "ls-remote" and a[-1] == "refs/heads/lane/feat/a":
            return "a1\trefs/heads/lane/feat/a"
        if a[0] == "ls-remote":
            return ""
        if a[0] == "push":
            pushed.append(a)
            return ""
        return real_git(*a, check=check)

    b.git = git
    b.main = lambda: _git(repo, "rev-parse", "HEAD")
    b.lanes()
    assert ("push", "-q", "-f", "origin", "a2:refs/heads/lane/feat/a") == pushed[0][:5]


def test_landing_marks_an_adopted_pull_request_merged_and_raises_none_for_it():
    b = Recorded(
        {
            "pulls": [
                {
                    "number": 5,
                    "user": {"login": "someone"},
                    "body": f"{ADOPTED} lane/feat/a",
                    "head": {"ref": "feat/a", "sha": "a1"},
                }
            ]
        }
    )
    pushed = []
    b.git = lambda *a, check=True: pushed.append(a) or ""
    b.land([("lane/feat/a", "a1", "r1"), ("lane/feat/b", "b1", "r2")], "tip")
    refs = [a[-1] for a in pushed if a[0] == "push"]
    # adopted lane: lane ref AND the PR's own branch take the landed sha, before main moves
    assert refs.index("r1:refs/heads/lane/feat/a") < refs.index("r1:refs/heads/feat/a")
    assert refs.index("r1:refs/heads/feat/a") < refs.index("tip:refs/heads/main")
    # unadopted lane: the engine raises its own PR; the adopted one gets none
    assert [w[1] for w in b.writes if w[0] == "POST" and w[1] == "pulls"] == ["pulls"]
    assert b.writes[-1][2]["head"] == "lane/feat/b"


def test_a_lane_squashes_onto_main_or_is_refused_as_a_conflict(repo):
    main = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "-q", "-b", "work")
    (repo / "b.txt").write_text("b\n")
    _git(repo, "add", "b.txt")
    _git(repo, "commit", "-q", "-m", "add b")
    (repo / "b.txt").write_text("bb\n")
    # The commit-msg hook stamps this on every real commit; bin/idp-ci-guarded-paths refuses a
    # candidate whose HEAD has no X-Idp-Signed trailer. The engine re-commits the lane, so the
    # trailer has to survive the squash or every non-founder lane fails a check it earned.
    _git(
        repo, "commit", "-q", "-am", "grow b", "-m", "", "-m", "X-Idp-Signed: deadbeef"
    )
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
    # The lane's signature is carried onto the candidate, and git reads it as a real trailer.
    assert (
        _git(repo, "log", "-1", "--format=%(trailers:key=X-Idp-Signed)", new).strip()
        == "X-Idp-Signed: deadbeef"
    )
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

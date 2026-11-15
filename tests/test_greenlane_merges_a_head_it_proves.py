"""A land proves the head it merges, not only the candidate it tested.

2026-10-17, PR #6375 (lane/fix/greenlane-queue-clog): b2961 and b2963 both reached land
green, and both were refused with `405: Required status check "greenlane" is pending`.
The engine had waited for the checks of `rebased` -- the squash it pushed -- but merged
the PR's *current* head, which had moved (the batch pushes b.tip to the lane branch, a
refresh rebases it), and whose checks nobody had awaited. The ruleset evaluates the PR
head, so no amount of blind 20 s retrying clears a check on a sha that was never proven.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from greenlane.github import GitHubBackend  # noqa: E402


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


class Backend(GitHubBackend):
    """The candidate rebased is green; the PR head is a different sha, late to go green,
    and GitHub's first merge answer is a stale 405 no matter what."""

    LAND_SETTLE_S = 0
    LAND_POLL_S = 0.05
    LAND_RETRY_S = 0.05

    def __init__(self, pr_head: str, pend_calls: int):
        super().__init__("o/idp", ["test"])
        self.pr_head = pr_head
        self.pend_calls = pend_calls  # checks(head) calls before it answers green
        self.head_checks = 0
        self.merge_calls = 0
        self.merged_sha = ""

    def gh(self, path, method="GET", fields=None):
        if path == "pulls/7" and method == "GET":
            return {"head": {"sha": self.pr_head}}
        if path == "pulls/7/merge" and method == "PUT":
            self.merge_calls += 1
            if self.merge_calls == 1:
                return {"message": "HTTP 405: Pull Request is not mergeable"}
            self.merged_sha = (fields or {}).get("sha", "")
            return {"merged": True}
        return {} if method == "GET" else None

    def checks(self, tip: str):
        if tip == self.pr_head:
            self.head_checks += 1
            if self.head_checks <= self.pend_calls:
                return ("pending", 'Required status check "greenlane" is pending')
        return ("green", "")

    def adopted_prs(self):
        return []

    def _ensure_pr(self, lane, head, rebased, tip):
        return 7

    def _status(self, sha, fields):
        pass


def _repo(tmp_path, monkeypatch):
    r = tmp_path / "r"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "user.email", "t@t")
    _git(r, "config", "user.name", "t")
    _git(r, "config", "commit.gpgsign", "false")
    (r / "a.txt").write_text("one\n")
    _git(r, "add", "a.txt")
    _git(r, "commit", "-q", "-m", "root")
    bare = tmp_path / "o.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)
    _git(r, "remote", "add", "origin", str(bare))
    _git(r, "push", "-q", "origin", "main")
    monkeypatch.chdir(r)
    return r, bare


def _commit(r: Path, name: str, msg: str) -> str:
    (r / name).write_text(f"{name}\n")
    _git(r, "add", name)
    _git(r, "commit", "-q", "-m", msg)
    return _git(r, "rev-parse", "HEAD")


def test_a_land_that_merges_a_moved_head_waits_for_that_head(monkeypatch, tmp_path):
    r, _ = _repo(tmp_path, monkeypatch)
    head = _commit(r, "head.txt", "lane work")  # the head the batch tested
    _git(r, "push", "-q", "origin", f"{head}:refs/heads/lane/x")
    rebased = _commit(r, "sq.txt", "rebased squash")  # what land pushes over the lane
    pr_head = _commit(r, "moved.txt", "moved under the land")  # the PR head GitHub sees

    b = Backend(pr_head=pr_head, pend_calls=3)
    tip = _git(r, "rev-parse", "HEAD")

    b.land([("lane/x", head, rebased)], tip)  # must not raise

    assert b.merged_sha == pr_head, "the merge pins the PR's current head"
    assert b.merge_calls == 2, "the stale first 405 is retried, not fatal"
    assert b.head_checks >= 3, "the head was proven green before the merge landed"


def test_a_land_whose_head_is_its_candidate_does_not_wait_twice(monkeypatch, tmp_path):
    r, _ = _repo(tmp_path, monkeypatch)
    head = _commit(r, "head.txt", "lane work")
    _git(r, "push", "-q", "origin", f"{head}:refs/heads/lane/x")
    rebased = _commit(r, "sq.txt", "rebased squash")

    b = Backend(pr_head=rebased, pend_calls=0)  # head already == what was awaited
    tip = _git(r, "rev-parse", "HEAD")

    b.land([("lane/x", head, rebased)], tip)

    assert b.merged_sha == rebased
    assert b.head_checks == 1, "no second wait when the head is the proven candidate"


def test_the_merge_is_preceded_by_a_machine_review_of_the_same_sha(
    monkeypatch, tmp_path
):
    """2026-11-15: main requires one approving review (I-8046) and the App that opens every
    lane PR cannot approve its own, so #8117 -- proven green -- was refused at merge and sat
    waiting for the founder. The second identity approves exactly the sha being merged, first."""
    r, _ = _repo(tmp_path, monkeypatch)
    head = _commit(r, "head.txt", "lane work")
    _git(r, "push", "-q", "origin", f"{head}:refs/heads/lane/x")
    rebased = _commit(r, "sq.txt", "rebased squash")
    pr_head = _commit(r, "moved.txt", "moved under the land")
    b = Backend(pr_head=pr_head, pend_calls=0)
    order: list[str] = []
    real_gh = b.gh

    def gh(path, method="GET", fields=None):
        if path.endswith("/merge"):
            order.append("merge")
        return real_gh(path, method, fields)

    def approve(number, sha, tip):
        order.append(f"approve {number} {sha}")

    b.gh = gh
    b._approve = approve
    b.land([("lane/x", head, rebased)], _git(r, "rev-parse", "HEAD"))
    assert order and order[0] == f"approve 7 {pr_head}", order
    assert "merge" in order[1:], order


def test_the_review_uses_the_workflow_identity_not_the_app(monkeypatch):
    from greenlane import github as gl

    calls = []
    monkeypatch.setattr(
        gl,
        "_run",
        lambda *a, **k: calls.append((a, k.get("env", {}).get("GH_TOKEN"))) or "",
    )
    gl.GitHubBackend(repo="o/r", required=[], status_token="WORKFLOW")._approve(
        7, "a" * 40, "b" * 40
    )
    assert calls and calls[0][1] == "WORKFLOW" and "pulls/7/reviews" in calls[0][0][2]
    calls.clear()
    gl.GitHubBackend(repo="o/r", required=[], status_token="")._approve(
        7, "a" * 40, "b" * 40
    )
    assert calls == [], "no second identity, no review: never approve as the App itself"

"""The proof reaches the pull request BEFORE the push that grades it.

2026-11-15. The Greenlane landed by force-pushing the rebased squash onto the lane branch,
and that push started fast-gate on the pull request the branch carries. The BDD-PROOF block
was written afterwards, in `_ensure_pr`, so the run grading the push read the previous
attempt's body -- or no block at all -- and refused it:

    FAIL  bddproof pull request #8099 carries no BDD-PROOF ... END-BDD-PROOF block
          (run 43703361365)

and #8124/#8110/#8115/#8117 hit the stale-head half of the same class. The body was repaired
after each push, which fixed the *next* attempt and never the run being graded, so a lane the
engine had proven green could not land at all.

This is the falsifier: it records the order of the two side effects and fails when the push
comes first.
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


class OrderingBackend(GitHubBackend):
    """One real lane, one open PR whose body is stale, and a record of what happened when."""

    LAND_SETTLE_S = 0
    LAND_POLL_S = 0.01
    LAND_RETRY_S = 0.01

    def __init__(self) -> None:
        super().__init__("o/idp", ["test"])
        self.order: list[str] = []
        self.patched_body = ""

    def gh(self, path, method="GET", fields=None):
        if path.startswith("pulls?state=open&head="):
            return [{"number": 7, "body": self.patched_body or "the previous attempt"}]
        if path == "pulls/7" and method == "PATCH":
            self.patched_body = (fields or {}).get("body", "")
            self.order.append("proof")
            return {}
        if path == "pulls/7" and method == "GET":
            return {"head": {"sha": ""}}
        if path == "pulls/7/merge":
            return {"merged": True, "sha": (fields or {}).get("sha", "")}
        return {}

    def git(self, *args, **kwargs):
        if "push" in args:
            self.order.append("push")
        return super().git(*args, **kwargs)

    def checks(self, tip):
        return ("green", "")

    def adopted_prs(self):
        return []

    def _status(self, sha, fields):
        pass

    def _update_check_run(self, sha, status, conclusion, reason):
        pass

    def _approve(self, number, sha, tip):
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
    return r


def _commit(r: Path, name: str, msg: str) -> str:
    (r / name).write_text(f"{name}\n")
    _git(r, "add", name)
    _git(r, "commit", "-q", "-m", msg)
    return _git(r, "rev-parse", "HEAD")


def test_the_proof_reaches_the_pull_request_before_the_push_that_grades_it(
    monkeypatch, tmp_path
):
    r = _repo(tmp_path, monkeypatch)
    head = _commit(r, "head.txt", "lane work")  # the head the batch tested
    _git(r, "push", "-q", "origin", f"{head}:refs/heads/lane/x")
    rebased = _commit(r, "sq.txt", "rebased squash")  # what land pushes over the lane
    tip = _git(r, "rev-parse", "HEAD")

    b = OrderingBackend()
    b.land([("lane/x", head, rebased)], tip)

    assert b.order[:2] == ["proof", "push"], (
        f"the proof must reach the pull request before the push that grades it: {b.order}"
    )
    assert f"head: {rebased}" in b.patched_body, (
        "the proof in the body must name the commit the push makes the head"
    )

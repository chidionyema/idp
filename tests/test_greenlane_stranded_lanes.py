"""Lanes the Greenlane stranded (idp#5618). Nothing here deletes a lane that has work main lacks.

Measured 2026-10-09 on refs/greenlane/state: 35 lanes, 34 of them red or conflict, the oldest from
2026-09-28. Seven "conflicts" were lanes whose every change was already on main -- the Greenlane
lands by squash, so work that reached main through another lane is never an ancestor of it, and
ancestry was the only test. Six more were conflicts judged before conflicts were retried: no main
to expire against, so never retried and never counted.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from greenlane import engine as E  # noqa: E402
from greenlane.github import GitHubBackend  # noqa: E402


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def _commit(r: Path, text: str, msg: str) -> str:
    (r / "a.txt").write_text(text)
    _git(r, "commit", "-q", "-am", msg)
    return _git(r, "rev-parse", "HEAD")


def _touch_other(r: Path) -> None:
    """main moves first, so a cherry-pick of the lane gets a sha of its own."""
    (r / "b.txt").write_text("other\n")
    _git(r, "add", "b.txt")
    _git(r, "commit", "-q", "-m", "other work on main")


class Quiet(GitHubBackend):
    """No GitHub: no adopted PRs, and every API write recorded."""

    def __init__(self):
        super().__init__("o/idp", ["test"])
        self.writes: list[tuple] = []

    def gh(self, path, method="GET", fields=None):
        if method != "GET":
            self.writes.append((method, path, fields))
        return [] if method == "GET" else None


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
    bare = tmp_path / "o.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)
    _git(r, "remote", "add", "origin", str(bare))
    _git(r, "push", "-q", "origin", "main")
    monkeypatch.chdir(r)
    return r


def _push_lane(r: Path, name: str, sha: str) -> None:
    _git(r, "push", "-q", "-f", "origin", f"{sha}:refs/heads/{name}")


def _lanes(r: Path) -> dict[str, str]:
    _git(r, "fetch", "-q", "--prune", "origin", "+refs/heads/*:refs/remotes/origin/*")
    return Quiet().lanes()


def _remote_has(r: Path, ref: str) -> bool:
    return bool(_git(r, "ls-remote", "origin", ref))


# -- 1. work already on main is not a conflict ---------------------------------------------


def test_a_lane_whose_work_landed_through_another_lane_is_retired(repo):
    """The Dependabot shape: the lane's change reached main under another sha, and main has since
    moved the same line on. A three-way merge conflicts; the work is on main all the same."""
    _git(repo, "checkout", "-q", "-b", "x")
    lane = _commit(repo, "two\n", "bump")
    _git(repo, "checkout", "-q", "main")
    _touch_other(repo)
    _git(repo, "cherry-pick", lane)  # landed by another lane: same patch, new sha
    assert _git(repo, "rev-parse", "HEAD") != lane
    _commit(repo, "three\n", "main moves the same line on")
    _git(repo, "push", "-q", "origin", "main")
    _push_lane(repo, "lane/x", lane)

    assert "lane/x" not in _lanes(repo)
    assert not _remote_has(repo, "refs/heads/lane/x")


def test_a_lane_that_merges_into_main_as_a_no_op_is_retired(repo):
    """A lane that changed something and changed it back adds nothing: merged into main, main is
    unchanged. None of its commits is on main, so only the merge says so."""
    _git(repo, "checkout", "-q", "-b", "x")
    _commit(repo, "two\n", "try")
    lane = _commit(repo, "one\n", "undo")
    _git(repo, "checkout", "-q", "main")
    _push_lane(repo, "lane/x", lane)

    assert "lane/x" not in _lanes(repo)


def test_a_lane_with_work_main_lacks_stays_a_lane(repo):
    _git(repo, "checkout", "-q", "-b", "x")
    lane = _commit(repo, "two\n", "real work")
    _git(repo, "checkout", "-q", "main")
    _commit(repo, "three\n", "main conflicts with it")
    _git(repo, "push", "-q", "origin", "main")
    _push_lane(repo, "lane/x", lane)

    assert _lanes(repo) == {"lane/x": lane}
    assert _remote_has(repo, "refs/heads/lane/x")


def test_a_merge_resolution_is_work_even_when_every_commit_is_on_main(repo):
    """`git cherry` skips merge commits, so a resolution carrying new content would be invisible
    to it. A lane with a merge is never retired on patch-equivalence alone."""
    _git(repo, "checkout", "-q", "-b", "x")
    picked = _commit(repo, "two\n", "landed elsewhere")
    _git(repo, "checkout", "-q", "main")
    _touch_other(repo)
    _git(repo, "cherry-pick", picked)
    _commit(repo, "three\n", "main moves on")
    _git(repo, "push", "-q", "origin", "main")
    _git(repo, "checkout", "-q", "x")
    subprocess.run(["git", "merge", "-q", "main"], cwd=repo, capture_output=True)
    (repo / "a.txt").write_text("four\n")  # the resolution is new work
    _git(repo, "commit", "-q", "-am", "merge main")
    lane = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "-q", "main")
    _push_lane(repo, "lane/x", lane)

    assert _lanes(repo) == {"lane/x": lane}


# -- 2. a conflict judged before retries existed is retried, never stranded -----------------


class Moving:
    def __init__(self):
        self.main_sha = "m2"

    def main(self):
        return self.main_sha

    def lanes(self):
        return {"lane/old": "h1"}

    def main_red(self, sha):
        return False

    def report(self, *a):
        pass


def _old_conflict() -> E.State:
    st = E.State()
    lane = E.Lane("lane/old", "h1", status=E.CONFLICT, seq=1)
    lane.reason, lane.judged_on = "does not rebase onto 049632481985", ""
    st.lanes[lane.name] = lane
    return st


def test_a_conflict_with_no_main_recorded_is_retried():
    st = _old_conflict()

    E.Engine(Moving(), st)._observe_lanes()

    lane = st.lanes["lane/old"]
    assert lane.status == E.PENDING
    assert lane.reason == "main moved; retrying"


def test_a_red_verdict_with_no_main_recorded_is_still_final():
    """Only the stranded conflicts change: a lane red on a green main stays red until a push."""
    st = _old_conflict()
    st.lanes["lane/old"].status = E.RED

    E.Engine(Moving(), st)._observe_lanes()

    assert st.lanes["lane/old"].status == E.RED

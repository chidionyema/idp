"""GitHub's answer to a merge that worked is a landing, not a refusal (2026-10-19).

The merge PUT's 200 body is {"sha": ..., "merged": true, "message": "Pull Request successfully
merged"}. `_land` read any `message` as a refusal, so from 5289b06b0 (2026-10-17) every merge
that worked raised: 31 of the 51 single-lane reds in 30 hours of greenlane ticks read "land
refused: Pull Request successfully merged" -- PR #6587 merged at 18:04:33Z in the same tick
b3219 called red. landed_total sat at 460, land() put each landed lane back on its old head, and
the origin/main refresh after the merge loop was skipped, so the next batch was voided as "main
moved under it". The fakes in the other suites answer a merge with None or {"merged": True},
never with GitHub's real body, which is why none of them could fail for this.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from greenlane.github import GitHubBackend  # noqa: E402

SUCCESS = {
    "sha": "f" * 40,
    "merged": True,
    "message": "Pull Request successfully merged",
}


class Merges(GitHubBackend):
    LAND_SETTLE_S = 0
    LAND_POLL_S = 0
    LAND_RETRY_S = 0

    def __init__(self, answer: dict):
        super().__init__("o/idp", ["test"])
        self.answer = answer
        self.merges = 0
        self.pushes: list[tuple] = []

    def git(self, *a, check=True):
        self.pushes.append(a)
        return "subject" if a[:1] == ("log",) else ""

    def gh(self, path, method="GET", fields=None):
        if path == "pulls/7/merge" and method == "PUT":
            self.merges += 1
            return dict(self.answer)
        if path == "pulls/7":
            return {"head": {"sha": "r1"}}
        return {} if method == "GET" else None

    def checks(self, tip):
        return ("green", "")

    def adopted_prs(self):
        return []

    def _ensure_pr(self, lane, head, rebased, tip):
        return 7

    def _update_check_run(self, *a, **kw):
        pass


def test_githubs_success_body_lands_and_refreshes_main():
    b = Merges(SUCCESS)
    b.land([("lane/feat/a", "a1", "r1")], "tip")  # did not raise
    assert b.merges == 1
    # the lane is not put back on its old head, and main is fetched for the next batch
    assert not [
        p for p in b.pushes if p[:1] == ("push",) and "a1:refs/heads/lane/feat/a" in p
    ]
    assert any("+refs/heads/main:refs/remotes/origin/main" in p for p in b.pushes)


def test_a_body_that_does_not_say_merged_is_still_a_refusal():
    b = Merges({"message": "Base branch was modified. Review and try the merge again."})
    with pytest.raises(RuntimeError, match="Base branch was modified"):
        b.land([("lane/feat/a", "a1", "r1")], "tip")

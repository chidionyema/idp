"""A land refused after a green candidate keeps the lane on its own head and counts as a retry.

2026-10-08, PR #5511 (lane/fix/fleet-proxy-to-mac): candidate b1990 was green on queue/b1990;
land() force-pushed the squash over the lane ref, the pull_request re-run of claim-gate went red,
land() raised and the tick died. The next tick read the lane head as moved (it was the squash),
requeued it as a NEW claim with a fresh retry budget, and squashed the squash: b1991, then b1992.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from greenlane import engine as E  # noqa: E402
from greenlane.github import GitHubBackend  # noqa: E402


class Refuses:
    """Engine backend whose candidate is green and whose land is refused."""

    def __init__(self) -> None:
        self.reported: list[tuple[str, str, str, str]] = []
        self.landed = 0

    def main(self) -> str:
        return "m" * 40

    def main_red(self, sha: str) -> bool:
        return False

    def checks(self, tip: str):
        return ("green", "")

    def land(self, members, tip):
        self.landed += 1
        raise RuntimeError("land: r1 went red after the push: claim-gate failure")

    def report(self, lane, head, status, reason):
        self.reported.append((lane, head, status, reason))

    def now(self) -> float:
        return 0.0


def _engine(retries: int):
    b = Refuses()
    st = E.State()
    lane = E.Lane("lane/x", "head1", seq=1)
    lane.status = E.TESTING
    st.lanes["lane/x"] = lane
    st.batch = E.Batch("b1", "m" * 40, "tip", [("lane/x", "head1", "r1")], 0.0)
    return E.Engine(b, st, retries=retries), b, st


def test_a_refused_land_is_a_red_verdict_that_spends_a_retry():
    eng, b, st = _engine(retries=1)
    eng._judge_batch()  # did not raise: the tick survives
    lane = st.lanes["lane/x"]
    assert st.batch is None
    assert lane.attempts == 1 and lane.status == E.PENDING
    assert "land refused" in lane.reason
    st.batch = E.Batch("b2", "m" * 40, "tip", [("lane/x", "head1", "r1")], 0.0)
    lane.status = E.TESTING
    eng._judge_batch()
    assert lane.status == E.RED, (
        "the retry budget must end a land that is always refused"
    )
    assert b.reported[-1][2] == E.RED


def test_land_puts_every_lane_back_on_its_own_head_when_it_is_refused():
    pushes: list[tuple] = []

    class B(GitHubBackend):
        def __init__(self):
            super().__init__("o/idp", ["bdd"])

        def git(self, *a, check=True):
            pushes.append(a)
            return ""

        def _land(self, members, tip):
            for lane, _head, rebased in members:
                self.git("push", "-q", "-f", "origin", f"{rebased}:refs/heads/{lane}")
            raise RuntimeError("land: r1 went red after the push")

    with pytest.raises(RuntimeError, match="went red"):
        B().land([("lane/a", "a1", "r1"), ("lane/b", "b1", "r2")], "tip")
    assert pushes[-2:] == [
        ("push", "-q", "-f", "origin", "a1:refs/heads/lane/a"),
        ("push", "-q", "-f", "origin", "b1:refs/heads/lane/b"),
    ]

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

    def report_check_run_completed(self, sha: str, result: str, note: str) -> None:
        pass


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
    # Land refusal resets attempts to 0 so the lane is retried without penalty
    # (the batch was already green; only the merge step failed)
    assert lane.attempts == 0 and lane.status == E.PENDING
    assert "land refused" in lane.reason


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
        (
            "push",
            "-q",
            "--force-with-lease=refs/heads/lane/a:r1",
            "origin",
            "a1:refs/heads/lane/a",
        ),
        (
            "push",
            "-q",
            "--force-with-lease=refs/heads/lane/b:r2",
            "origin",
            "b1:refs/heads/lane/b",
        ),
    ]


def _origin(tmp_path: Path) -> tuple[Path, Path, dict[str, str]]:
    """A bare origin with lane/x on head1, and a clone the backend pushes from."""
    import subprocess

    def g(cwd, *a):
        return subprocess.run(
            ["git", "-C", str(cwd), *a], capture_output=True, text=True, check=True
        ).stdout.strip()

    origin, work = tmp_path / "origin.git", tmp_path / "work"
    subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)
    subprocess.run(["git", "clone", "-q", str(origin), str(work)], check=True)
    g(work, "config", "user.email", "t@t")
    g(work, "config", "user.name", "t")
    shas = {}
    for name in ("head1", "squash", "author"):
        g(work, "checkout", "-q", "--orphan", name)
        g(work, "commit", "-q", "--allow-empty", "-m", name)
        shas[name] = g(work, "rev-parse", "HEAD")
    g(work, "push", "-q", "origin", f"{shas['head1']}:refs/heads/lane/x")
    return origin, work, shas


def _backend(work: Path):
    class B(GitHubBackend):
        def __init__(self):
            super().__init__("o/idp", ["bdd"])

        def git(self, *a, check=True):
            return super().git("-C", str(work), *a, check=check)

        def adopted_prs(self):
            return []

    return B()


def _lane_ref(origin: Path) -> str:
    import subprocess

    return subprocess.run(
        ["git", "-C", str(origin), "rev-parse", "refs/heads/lane/x"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def test_an_author_push_mid_land_is_not_erased_by_the_squash(tmp_path):
    """2026-10-13, #6084: the author pushed 2c0156b01 while b2709 tested the old head; the
    squash went over it unleased, and so did the restore."""
    origin, work, s = _origin(tmp_path)
    b = _backend(work)
    b.git("push", "-q", "-f", "origin", f"{s['author']}:refs/heads/lane/x")
    with pytest.raises(RuntimeError):
        b._land([("lane/x", s["head1"], s["squash"])], "tip")
    assert _lane_ref(origin) == s["author"]


def test_the_restore_leaves_an_author_push_alone(tmp_path):
    origin, work, s = _origin(tmp_path)
    b = _backend(work)
    b.git("push", "-q", "-f", "origin", f"{s['author']}:refs/heads/lane/x")

    class Refused(type(b)):
        def _land(self, members, tip):
            raise RuntimeError("land: went red after the push")

    r = Refused()
    with pytest.raises(RuntimeError):
        r.land([("lane/x", s["head1"], s["squash"])], "tip")
    assert _lane_ref(origin) == s["author"]


def test_the_restore_still_puts_a_squashed_lane_back(tmp_path):
    origin, work, s = _origin(tmp_path)
    b = _backend(work)

    class SquashThenRefuse(type(b)):
        def _land(self, members, tip):
            for lane, head, rebased in members:
                self.git(
                    "push",
                    "-q",
                    f"--force-with-lease=refs/heads/{lane}:{head}",
                    "origin",
                    f"{rebased}:refs/heads/{lane}",
                )
            raise RuntimeError("land: went red after the push")

    with pytest.raises(RuntimeError):
        SquashThenRefuse().land([("lane/x", s["head1"], s["squash"])], "tip")
    assert _lane_ref(origin) == s["head1"]

"""idp#5612: a lane that does not land on a live claim waits outside the batch.

PR #5606 (lane/fix/voice-tts-breaker) carried no Claim line. The Greenlane put it in b2181
anyway, and claim-gate in ci-success refused it there -- a whole batch later, with its
batch-mates waiting on the verdict. The engine now asks first, and the GitHub backend answers
with main's own bin/claim-gate, so the question and CI's answer cannot drift apart.
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

NO_CLAIM = "no live claim: no `Claim: <owner>/<repo>#<n>` line"


class Backend:
    def __init__(self, heads: dict[str, str], unclaimed: set[str]):
        self.heads, self.held = heads, unclaimed
        self.candidates: list[str] = []
        self.reported: list[tuple[str, str, str, str]] = []

    def now(self):
        return 0.0

    def main(self):
        return "m1"

    def lanes(self):
        return dict(self.heads)

    def rebase(self, head, onto):
        return f"{head}@{onto}"

    def push_candidate(self, batch_id, tip):
        self.candidates.append(tip)

    def checks(self, tip):
        return ("pending", "")

    def main_red(self, sha):
        return False

    def report(self, lane, head, status, reason):
        self.reported.append((lane, head, status, reason))

    def foreign_prs(self):
        return []

    def unclaimed(self, head, base):
        return NO_CLAIM if head in self.held else ""


def test_an_unclaimed_lane_is_held_and_the_lanes_behind_it_go_ahead():
    b = Backend({"lane/a": "ha", "lane/b": "hb"}, unclaimed={"ha"})
    st = E.Engine(b, E.State()).tick()
    assert [n for n, _, _ in st.batch.members] == ["lane/b"]
    held = st.lanes["lane/a"]
    assert (held.status, held.reason) == (E.PENDING, NO_CLAIM)
    assert ("lane/a", "ha", E.RED, NO_CLAIM) in b.reported


def test_the_reason_is_reported_once_not_every_tick():
    b = Backend({"lane/a": "ha"}, unclaimed={"ha"})
    st = E.State()
    for _ in range(3):
        st = E.Engine(b, st).tick()
    assert st.batch is None and b.candidates == []
    assert [r for r in b.reported if r[0] == "lane/a"] == [
        ("lane/a", "ha", E.RED, NO_CLAIM)
    ]


def test_posting_the_claim_is_enough_the_next_tick_admits_the_same_head():
    b = Backend({"lane/a": "ha"}, unclaimed={"ha"})
    st = E.Engine(b, E.State()).tick()
    assert st.batch is None
    b.held.clear()  # the CLAIM comment went up; nothing was pushed
    st = E.Engine(b, st).tick()
    assert [(n, h) for n, h, _ in st.batch.members] == [("lane/a", "ha")]


def test_held_lanes_do_not_count_against_the_batch_size():
    heads = {f"lane/{i}": f"h{i}" for i in range(4)}
    b = Backend(heads, unclaimed={"h0", "h1"})
    st = E.Engine(b, E.State(), batch_size=2).tick()
    assert [n for n, _, _ in st.batch.members] == ["lane/2", "lane/3"]


# -- GitHubBackend.unclaimed: main's bin/claim-gate, stubbed ---------------------------------

GATE = """import os, sys
open(os.environ["GATE_LOG"], "a").write(" ".join([os.environ["GITHUB_REPOSITORY"], *sys.argv[1:]]) + "\\n")
says = os.environ["GATE_SAYS"]
if says == "ok":
    print("ok    claim-gate  every change lands on a live claim")
elif says == "fail":
    print("FAIL  claim-gate  no `Claim: <owner>/<repo>#<n>` line")
    print("FAIL  claim-gate  o/idp#7 is not labelled in-progress")
    sys.exit(1)
else:
    print("Traceback (most recent call last):", file=sys.stderr)
    sys.exit(1)
"""


@pytest.fixture
def gated(tmp_path, monkeypatch):
    r = tmp_path / "r"
    r.mkdir()
    for a in (
        ("init", "-q", "-b", "main"),
        ("config", "user.email", "t@t"),
        ("config", "user.name", "t"),
        ("commit", "-q", "--allow-empty", "-m", "root"),
    ):
        subprocess.run(["git", "-C", str(r), *a], check=True, capture_output=True)
    monkeypatch.chdir(r)
    gate = tmp_path / "claim-gate"
    gate.write_text(GATE)
    monkeypatch.setattr(GitHubBackend, "CLAIM_GATE", gate)
    log = tmp_path / "gate.log"
    monkeypatch.setenv("GATE_LOG", str(log))
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    return GitHubBackend("o/idp", []), sha, log, monkeypatch


def test_a_failing_gate_is_the_reason_and_names_every_failure(gated):
    b, sha, log, mp = gated
    mp.setenv("GATE_SAYS", "fail")
    assert b.unclaimed(sha, sha) == (
        "no live claim: no `Claim: <owner>/<repo>#<n>` line; "
        "o/idp#7 is not labelled in-progress"
    )
    assert log.read_text().split() == ["o/idp", sha, sha]


@pytest.mark.parametrize("says", ["ok", "crash"])
def test_a_passing_gate_or_one_that_cannot_judge_admits_the_lane(gated, says):
    b, sha, _, mp = gated
    mp.setenv("GATE_SAYS", says)
    assert b.unclaimed(sha, sha) == ""


def test_no_gate_in_the_checkout_admits_the_lane(gated, tmp_path):
    b, sha, _, mp = gated
    mp.setattr(GitHubBackend, "CLAIM_GATE", tmp_path / "absent")
    assert b.unclaimed(sha, sha) == ""

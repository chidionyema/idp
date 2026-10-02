"""A red or conflicted lane is judged again once main moves, and not before.

2026-09-30: all 28 lanes sat red or conflict with none pending, so Greenlane tested nothing while
main was green. Nine of them had gone red only because main's own bdd check was red; the engine
kept those verdicts forever, lifting one only when the lane's author pushed a new head.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "greenlane_engine", Path(__file__).resolve().parents[1] / "greenlane" / "engine.py"
)
engine = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = engine  # dataclasses resolve their module through sys.modules
_spec.loader.exec_module(engine)


class Backend:
    def __init__(self):
        self.main_sha = "m1"
        self.heads = {"lane/a": "h1"}
        self.verdict = ("red", "bdd failure")
        self.main_verdict = ("red", "bdd failure")  # main's own checks
        self.conflict = False
        self.candidates: list[str] = []

    def now(self):
        return 0.0

    def main(self):
        return self.main_sha

    def lanes(self):
        return dict(self.heads)

    def rebase(self, head, onto):
        return None if self.conflict else f"{head}@{onto}"

    def push_candidate(self, batch_id, tip):
        self.candidates.append(tip)

    def checks(self, tip):
        return self.verdict

    def main_red(self, sha):
        return self.main_verdict[0] == "red"

    def land(self, members, tip):
        self.main_sha = tip

    def report(self, lane, head, status, reason):
        pass

    def foreign_prs(self):
        return []

    def relane(self, pr):
        pass


def _settle(e, ticks=10):
    for _ in range(ticks):
        e.tick()


def test_a_lane_red_on_a_red_main_is_tested_again_when_main_moves():
    b = Backend()
    e = engine.Engine(b, engine.State())
    _settle(e)
    assert e.s.lanes["lane/a"].status == engine.RED
    tested = len(b.candidates)

    _settle(e)  # main has not moved: the verdict stands and nothing is re-tested
    assert e.s.lanes["lane/a"].status == engine.RED
    assert len(b.candidates) == tested

    b.main_sha, b.main_verdict, b.verdict = "m2", ("green", ""), ("green", "")
    _settle(e)
    assert e.s.lanes["lane/a"].status == engine.LANDED
    assert b.main_sha == "h1@m2"


def test_a_lane_red_on_a_red_main_waits_while_main_stays_red():
    b = Backend()
    e = engine.Engine(b, engine.State())
    _settle(e)
    tested = len(b.candidates)

    b.main_sha = "m2"  # main moved (an image bump) but is still red
    _settle(e)
    assert e.s.lanes["lane/a"].status == engine.RED
    assert len(b.candidates) == tested

    b.main_sha, b.main_verdict, b.verdict = "m3", ("green", ""), ("green", "")
    _settle(e)
    assert e.s.lanes["lane/a"].status == engine.LANDED


def test_a_lane_red_on_a_green_main_keeps_its_verdict():
    b = Backend()
    b.main_verdict = ("green", "")
    e = engine.Engine(b, engine.State())
    _settle(e)
    assert e.s.lanes["lane/a"].status == engine.RED
    tested = len(b.candidates)

    b.main_sha = "m2"
    _settle(e)
    assert e.s.lanes["lane/a"].status == engine.RED
    assert len(b.candidates) == tested


def test_a_conflicted_lane_is_rebased_again_when_main_moves():
    b = Backend()
    b.conflict = True
    e = engine.Engine(b, engine.State())
    _settle(e)
    assert e.s.lanes["lane/a"].status == engine.CONFLICT

    b.main_sha, b.conflict, b.verdict = "m2", False, ("green", "")
    _settle(e)
    assert e.s.lanes["lane/a"].status == engine.LANDED


def test_state_saved_before_the_fix_still_loads():
    old = '{"lanes": {"lane/a": {"name": "lane/a", "head": "h1", "status": "red", "reason": "x", "attempts": 3, "seq": 1}}}'
    st = engine.State.loads(old)
    assert st.lanes["lane/a"].judged_on == ""

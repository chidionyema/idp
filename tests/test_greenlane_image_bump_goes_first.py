"""The image bump forms the next batch first: it is the deploy leg of work that already waited once.

2026-10-19: landing to image-update commit was ~16 min, because flux/image-updates queued in
arrival order behind agent lanes. Code that has landed is not live until its tag reaches main.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from greenlane import engine as E  # noqa: E402
from greenlane import simulate  # noqa: E402

MAIN = "m" * 40


class B:
    def __init__(self):
        self.pushed: list = []

    def main(self):
        return MAIN

    def rebase(self, head, onto, lane=""):
        return f"{head}+"

    def unclaimed(self, head, base):
        return ""

    def push_candidate(self, bid, tip):
        self.pushed.append(tip)

    def report(self, *a):
        pass

    def now(self):
        return 0.0


def test_the_image_bump_is_first_in_the_batch_whatever_its_arrival():
    st = E.State()
    for seq, name in enumerate(["lane/a", "lane/b", "lane/c", E.IMAGE_LANE], 1):
        st.lanes[name] = E.Lane(name, f"h{seq}", seq=seq, arrived=1.0)
    E.Engine(B(), st, batch_size=2)._start_batch()
    assert [m[0] for m in st.batch.members] == [E.IMAGE_LANE, "lane/a"]
    assert st.lanes["lane/b"].status == E.PENDING  # the rest keep their arrival order


def test_agent_lanes_keep_arrival_order_without_a_bump():
    st = E.State()
    for seq, name in [(3, "lane/c"), (1, "lane/a"), (2, "lane/b")]:
        st.lanes[name] = E.Lane(name, f"h{seq}", seq=seq, arrived=1.0)
    E.Engine(B(), st, batch_size=8)._start_batch()
    assert [m[0] for m in st.batch.members] == ["lane/a", "lane/b", "lane/c"]


def test_under_chaos_putting_the_bump_first_keeps_every_invariant():
    for seed in (0, 1):
        r = simulate.run(lanes=120, seed=seed, ticks=900)
        assert r.work_lost == 0 and r.main_ever_red == 0, seed
        assert r.broken_lanes_landed == 0 and r.good_lanes_not_landed == 0, seed
        assert r.open_red_pr_observations == 0, seed

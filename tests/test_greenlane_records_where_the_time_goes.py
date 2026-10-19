"""The engine keeps a record of every batch verdict and every landing, so latency is read, not guessed.

2026-10-19: push to live was a 19 min median with a 4 h tail, and nothing could say why. The
state held the batch in flight and nothing about the ones before it, and refs/greenlane/state
keeps no history -- every tick rewrites its one commit (`git rev-list --count` = 1). These pin the
record: written at every way a batch can end, bounded, and loadable from a state written before
it existed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from greenlane import engine as E  # noqa: E402
from greenlane import simulate  # noqa: E402

MAIN = "m" * 40


class B:
    def __init__(self, verdict="green", main=MAIN, now=10.0, refuse=False):
        self.verdict, self._main, self.t, self.refuse = verdict, main, now, refuse
        self.reported: list = []

    def main(self):
        return self._main

    def main_red(self, sha):
        return False

    def checks(self, tip):
        return (self.verdict, "bdd failure" if self.verdict == "red" else "")

    def land(self, members, tip):
        if self.refuse:
            raise RuntimeError("claim-gate failure")

    def report(self, *a):
        self.reported.append(a)

    def now(self):
        return self.t


def _state(*names, arrived=2.0):
    st = E.State()
    for i, n in enumerate(names):
        lane = E.Lane(n, f"h{i}", status=E.TESTING, seq=i + 1, arrived=arrived)
        st.lanes[n] = lane
    st.batch = E.Batch(
        "b7", MAIN, "tip", [(n, f"h{i}", f"r{i}") for i, n in enumerate(names)], 4.0
    )
    return st


def test_a_state_written_before_the_record_existed_loads_empty():
    old = json.dumps(
        {
            "lanes": {},
            "batch": None,
            "queued": [],
            "seq": 3,
            "landed": 460,
            "candidates": 3141,
        }
    )
    st = E.State.loads(old)
    assert st.history == [] and st.landings == []
    assert E.latency(st)["queue_to_land_min"] == {"n": 0, "p50": None, "p90": None}


def test_a_landing_records_the_batch_and_each_lane_wait_and_survives_the_round_trip():
    st = _state("lane/a", "lane/b")
    E.Engine(B(), st)._judge_batch()
    st = E.State.loads(st.dumps())  # every tick is a fresh process
    assert st.history[-1]["outcome"] == "landed"
    assert st.history[-1]["members"] == ["lane/a", "lane/b"]
    assert [r["landed"] - r["queued"] for r in st.landings] == [8.0, 8.0]
    lat = E.latency(st)
    assert lat["queue_to_land_min"]["p50"] == 8.0
    assert lat["batch_cycle_min"] == {"n": 1, "p50": 6.0, "p90": 6.0}


def test_every_way_a_batch_ends_is_recorded():
    cases = [
        (B("red"), ("lane/a", "lane/b"), ("red", "bisected")),
        (B("red"), ("lane/a",), ("red", "retried")),
        (B(main="n" * 40), ("lane/a",), ("main-moved", None)),
        (B(refuse=True), ("lane/a",), ("land-refused", "retried")),
        (B("pending", now=500.0), ("lane/a",), ("timeout", "retried")),
    ]
    for backend, names, want in cases:
        st = _state(*names)
        E.Engine(backend, st)._judge_batch()
        r = st.history[-1]
        assert (r["outcome"], r.get("action")) == want, r
    st = _state("lane/a")
    st.lanes["lane/a"].attempts = E.DEFAULT_RETRIES
    E.Engine(B("red"), st)._judge_batch()
    assert st.history[-1]["action"] == "parked"


def test_a_conflict_is_counted_but_does_not_take_a_slot_in_the_record():
    class Conflicts(B):
        def rebase(self, head, onto, lane=""):
            return None

        def unclaimed(self, head, base):
            return ""

    st = E.State()
    st.lanes["lane/c"] = E.Lane("lane/c", "hc", seq=1, arrived=1.0)
    E.Engine(Conflicts(), st)._start_batch()
    st = E.State.loads(st.dumps())
    assert st.history == []
    assert E.latency(st)["conflicts_total"] == 1


def test_the_record_is_bounded():
    st = E.State()
    for i in range(E.HISTORY_KEEP + 50):
        st.batch = E.Batch(f"b{i}", MAIN, "tip", [("lane/a", "h0", "r0")], 0.0)
        st.lanes["lane/a"] = E.Lane("lane/a", "h0", status=E.TESTING, arrived=1.0)
        E.Engine(B(), st)._judge_batch()
    st = E.State.loads(st.dumps())
    assert len(st.history) == E.HISTORY_KEEP and len(st.landings) == E.HISTORY_KEEP
    assert st.history[-1]["id"] == f"b{E.HISTORY_KEEP + 49}"


def test_under_chaos_the_record_survives_every_tick_and_the_invariants_hold():
    r = simulate.run(lanes=60, seed=3, ticks=600, reload_state=True)
    assert r.work_lost == 0 and r.main_ever_red == 0 and r.broken_lanes_landed == 0
    assert r.landed > 0
    # the record came through a JSON round trip on every tick and still accounts for the run
    assert r.latency["queue_to_land_min"]["n"] > 0
    assert r.latency["outcomes"].get("landed", 0) > 0

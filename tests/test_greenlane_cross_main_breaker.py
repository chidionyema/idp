"""#8289: durable cross-main failure-class cap on the existing Greenlane state ref.

The founder's deployment control plane must not burn a second independent CI
cycle on the same immutable source and causal failure when main keeps moving.
Unknown/flaky symptoms are not treated as proof of an identical root cause.
"""

from greenlane.cross_main_breaker import record_failure
from greenlane.engine import RED, Batch, Engine, Lane, State
from greenlane.learning import fingerprint

CAUSE = (
    "fast-gate / fast-gate failure https://github.com/o/idp/actions/runs/1 "
    "-- FAIL language-gate: new Python source missing a required language exception"
)
A = "a" * 40
B = "b" * 40
H = "c" * 40
NEW = "d" * 40
LANE = "lane/cross-main-proof"


class World:
    def __init__(self, main=A):
        self.base = main
        self.reports = []
        self.minute = 120

    def main(self):
        return self.base

    def now(self):
        return self.minute

    def checks(self, tip):
        return "red", CAUSE

    def main_red(self, sha):
        return False

    def report(self, *args):
        self.reports.append(args)


def note(engine, head, base, cause):
    return record_failure(engine.s.failure_epochs, LANE, head, base, cause)


def run_one(engine, base, head, batch):
    engine.b.base = base
    engine.s.lanes[LANE] = Lane(LANE, head)
    engine.s.batch = Batch(batch, base, head, [(LANE, head, head)], 110)
    engine._judge_batch()


def test_two_distinct_mains_park_one_unchanged_source_with_one_causal_class():
    state = State()
    engine = Engine(World(), state, retries=2)
    run_one(engine, A, H, "b1")
    assert state.lanes[LANE].status != RED
    assert state.failure_epochs[LANE]["bases"] == [A]
    assert state.history[-1]["distinct_failed_mains"] == 1
    run_one(engine, B, H, "b2")
    lane = state.lanes[LANE]
    assert lane.status == RED
    assert lane.judged_on == ""
    assert "cross-main" in lane.reason
    assert state.history[-1]["action"] == "cross-main-hold"
    assert state.history[-1]["distinct_failed_mains"] == 2
    assert len(engine.b.reports) == 2


def test_repeated_cause_on_same_main_does_not_inflate_distinct_mains():
    engine = Engine(World(), State(), retries=2)
    sig = fingerprint(CAUSE)
    assert sig
    assert note(engine, H, A, sig) == 1
    assert note(engine, H, A, sig) == 1
    assert engine.s.failure_epochs[LANE]["bases"] == [A]


def test_source_or_cause_change_resets_counter():
    engine = Engine(World(), State())
    sig = fingerprint(CAUSE)
    assert note(engine, H, A, sig) == 1
    assert note(engine, H, B, sig) == 2
    assert note(engine, NEW, B, sig) == 1
    assert note(engine, NEW, B, "different-cause") == 1


def test_flaky_or_generic_failure_is_not_a_causal_park():
    engine = Engine(World(), State())
    assert fingerprint("fast-gate failure: timed out") == ""
    assert note(engine, H, A, "") == 0
    assert note(engine, H, B, "") == 0
    assert not engine.s.failure_epochs


def test_cross_main_history_survives_reload_and_old_state_migrates():
    engine = Engine(World(), State())
    sig = fingerprint(CAUSE)
    assert note(engine, H, A, sig) == 1
    restored = State.loads(engine.s.dumps())
    assert restored.failure_epochs[LANE] == {
        "head": H,
        "cause": sig,
        "bases": [A],
    }
    assert State.loads('{"landed":7}').failure_epochs == {}


def test_new_branch_head_releases_old_park_without_new_controller():
    world = World()
    engine = Engine(world, State())
    engine.s.failure_epochs[LANE] = {
        "head": H,
        "cause": fingerprint(CAUSE),
        "bases": [A, B],
    }
    engine.s.lanes[LANE] = Lane(LANE, H, status=RED)

    # The exact transition performed by _observe_lanes is a source-head reset.
    class NewHeadWorld(World):
        def lanes(self):
            return {LANE: NEW}

        def foreign_prs(self):
            return []

        def unclaimed(self, *args):
            return ""

        def heartbeat(self, *args):
            return None

        def work_age(self, *args):
            return None

    fresh = NewHeadWorld()
    engine.b = fresh
    engine._observe_lanes()
    assert engine.s.lanes[LANE].head == NEW
    assert LANE not in engine.s.failure_epochs


def test_independent_optimus_measure_exercises_real_engine():
    from greenlane.cross_main_breaker import measure_operational_cap

    assert measure_operational_cap()

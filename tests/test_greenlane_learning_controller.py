"""Real-engine policy experiments; full CI and protected merge still own authorization."""

from greenlane.engine import Batch, Engine, Lane, State, TESTING, RED
from greenlane.learning import choose_batch_size, fingerprint, repeated_exact_failure
from greenlane.simulate import run

BASE = "a" * 40
HEAD = "b" * 40
REASON = ("land refused: land: " + "f" * 40 + " went red: "
          "ci-success failure https://github.com/o/idp/actions/runs/777/job/222 "
          "-- offline-gate > FAIL static validation: independent source does not satisfy rule")


def records(outcomes):
    return [{"members": [f"lane/l{i}"], "heads": [f"{i:040x}"],
             "base_full": BASE, "outcome": result}
            for i, result in enumerate(outcomes)]


def test_policy_learns_from_evidence():
    assert choose_batch_size(records(["landed"] * 40), 100, 8).size == 8
    assert choose_batch_size(records(["red"] * 40), 100, 8).size == 1
    assert choose_batch_size([], 100, 8).size == 8
    assert choose_batch_size(records(["landed"] * 20), 1, 8).size == 1


def test_retried_heads_do_not_masquerade_as_independent_training_data():
    rows = records(["red"] * 10)
    rows += [rows[-1]] * 40
    assert choose_batch_size(rows, 8, 8).observed == 10


def test_fingerprint_requires_a_specific_repeated_root_cause():
    cause = fingerprint(REASON)
    assert len(cause) == 20
    assert fingerprint(REASON.replace("/777/job/222", "/999/job/888")) == cause
    assert not fingerprint("ci-success failure https://github.com/o/idp/actions/runs/777")
    assert not fingerprint("flaky: test-x failed")
    assert not fingerprint("land refused: HTTP 405")
    assert not repeated_exact_failure([], "lane/a", HEAD, BASE, cause)


class FailedBackend:
    def __init__(self):
        self.t = 10.0
        self.reports = []

    def main(self): return BASE
    def main_red(self, sha): return False
    def checks(self, sha): return ("red", REASON)
    def report(self, *args): self.reports.append(args)
    def now(self): return self.t


def test_second_identical_failure_holds_without_a_third_ci_cycle():
    b, st = FailedBackend(), State()
    st.lanes["lane/a"] = Lane("lane/a", HEAD, status=TESTING, arrived=1.0)
    st.batch = Batch("b1", BASE, "c" * 40, [("lane/a", HEAD, "c" * 40)], 9.0)
    Engine(b, st)._judge_batch()
    assert st.lanes["lane/a"].attempts == 1
    st.batch = Batch("b2", BASE, "d" * 40, [("lane/a", HEAD, "d" * 40)], 11.0)
    st.lanes["lane/a"].status = TESTING
    b.t = 12.0
    Engine(b, st)._judge_batch()
    lane = st.lanes["lane/a"]
    assert lane.status == RED
    assert lane.reason.startswith("learned hold [")
    assert lane.judged_on == BASE
    assert st.history[-1]["action"] == "learned-hold"
    assert State.loads(st.dumps()).history[-1]["heads"] == [HEAD]
    assert not repeated_exact_failure(st.history, "lane/a", HEAD, "e" * 40, fingerprint(REASON))


def test_both_policies_preserve_trunk_proof_under_chaos():
    for seed in (0, 1, 2):
        for policy in ("fixed", "adaptive"):
            r = run(lanes=100, seed=seed, ticks=900, batch_policy=policy,
                    realistic_ci=True, p_broken=0.19, p_repush=0.002)
            assert r.main_ever_red == 0 and r.broken_lanes_landed == 0, r
            assert r.work_lost == 0 and r.direct_push_succeeded == 0, r
            assert r.open_red_pr_observations == 0 and r.good_lanes_not_landed == 0, r


def test_policy_tournament_executes_real_engine_and_completes_three_regimes():
    from greenlane.tournament import REGIMES, run_tournament

    out = run_tournament(lanes=40, seeds=(0,))
    assert out["schema"] == "greenlane.policy-tournament.v1"
    assert set(out["regimes"]) == set(REGIMES)
    for entry in out["regimes"].values():
        assert entry["fixed"]["landed_mean"] >= 0
        assert entry["adaptive"]["landed_mean"] >= 0
        assert entry["verdict"] in ("adaptive-dominates", "fixed-dominates", "trade-off")


def test_successful_eight_lane_batch_teaches_eight_positive_outcomes():
    from greenlane.learning import choose_batch_size

    row = {
        "outcome": "landed", "base_full": BASE,
        "members": [f"lane/w{i}" for i in range(8)],
        "heads": [f"{i:040x}" for i in range(8)],
    }
    decision = choose_batch_size([row], 10, 8)
    assert decision.observed == 8
    assert decision.size == 8, decision


def test_speed_optimised_policy_uses_a_distinct_experimental_arm():
    from greenlane.learning import choose_batch_size

    rows = records(["landed"] * 24 + ["red"] * 8)
    economy = choose_batch_size(rows, 8, 8, overhead=0.30)
    speed = choose_batch_size(rows, 8, 8, overhead=0.60)
    assert speed.size >= economy.size

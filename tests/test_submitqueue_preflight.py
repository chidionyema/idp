"""Ferrari preflight acceptance tests: unsafe skips and queue starvation fail."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from greenlane.ferrari import Verdict, assess, interpret
from greenlane.engine import Engine, Lane, State, PENDING, RED

BASE = "a" * 40
NEW_BASE = "b" * 40


def payload(ok, commitments):
    return json.dumps({"gate": "dof", "ok": ok,
                       "open_incidents": [{"id": "estate-doors", "issue": 7334}],
                       "commits": commitments})


def denied(reason="missing Genesis-Resolves while a critical service is down"):
    return {"sha": "1" * 40, "admitted": False, "reason": reason}


def accepted():
    return {"sha": "2" * 40, "admitted": True, "reason": "admitted"}


class TinyBackend:
    def __init__(self, blocked=()):
        self.base = BASE
        self.heads = {}
        self.blocked = set(blocked)
        self.pushed = []
        self.reports = []

    def main(self):
        return self.base

    def now(self):
        return 1.0

    def rebase(self, head, onto, lane=""):
        return head

    def preflight(self, base, candidate):
        if candidate in self.blocked:
            return False, "trusted DoF [proof]: candidate cannot pass"
        return True, "admitted"

    def push_candidate(self, batch_id, tip):
        self.pushed.append((batch_id, tip))

    def report(self, lane, head, status, reason):
        self.reports.append((lane, head, status, reason))

    def unclaimed(self, head, base):
        return ""

    def lanes(self):
        return self.heads


def test_explicit_doctor_deny_has_stable_fingerprint():
    one = interpret(BASE, 1, payload(False, [denied()]))
    two = interpret(BASE, 1, payload(False, [denied()]))
    assert one.state == "REFUSE" and not one.admissible
    assert one.fingerprint == two.fingerprint
    assert interpret(NEW_BASE, 1, payload(False, [denied()])).fingerprint != one.fingerprint


def test_preflight_never_certifies_or_skips_without_real_denial():
    invalid = [
        (0, ""), (1, "not-json"), (2, payload(False, [denied()])),
        (1, payload(True, [denied()])), (1, payload(False, [accepted()])),
        (1, payload(False, [])),
        (1, json.dumps({"gate": "dof", "ok": False,
                        "commits": [{"admitted": "false", "reason": "bad"}]})),
        (1, payload(False, [{"admitted": False}])),
    ]
    assert all(interpret(BASE, rc, text).admissible for rc, text in invalid)
    assert interpret(BASE, 0, payload(True, [accepted()])).state == "ADMIT"
    assert interpret(BASE, 1, payload(False, [denied()])).state == "REFUSE"


def test_assess_executes_only_trusted_main_file_not_candidate_code():
    called = []
    def runner(argv, **kwargs):
        called.append((argv, kwargs))
        return SimpleNamespace(returncode=1, stdout=payload(False, [denied()]))
    verdict = assess(BASE, "c" * 40, "chidionyema/idp", runner=runner)
    assert verdict.state == "REFUSE"
    assert Path(called[0][0][1]).name == "dof-gate"
    assert called[0][0][2:] == [BASE, "c" * 40]
    assert called[0][1]["env"]["GITHUB_REPOSITORY"] == "chidionyema/idp"


def test_all_unadmittable_candidates_consume_zero_ci_builds():
    heads = [f"h{i}" for i in range(100)]
    backend = TinyBackend(heads)
    state = State(lanes={f"lane/{i}": Lane(f"lane/{i}", h, seq=i + 1)
                         for i, h in enumerate(heads)})
    engine = Engine(backend, state, batch_size=100)
    engine._start_batch()
    assert backend.pushed == [] and state.candidates == 0
    assert all(x.status == RED for x in state.lanes.values())
    assert all(x.judged_on == BASE for x in state.lanes.values())


def test_independent_admissible_lane_progresses_despite_common_blocker():
    backend = TinyBackend({"bad"})
    state = State(lanes={
        "lane/a": Lane("lane/a", "bad", seq=1),
        "lane/b": Lane("lane/b", "good", seq=2),
    })
    Engine(backend, state)._start_batch()
    assert state.lanes["lane/a"].status == RED
    assert state.lanes["lane/b"].status == "testing"
    assert backend.pushed == [("b1", "good")]
    assert state.batch.members[0][0] == "lane/b"


def test_change_of_trusted_base_reactivates_same_head_without_repush():
    backend = TinyBackend({"bad"})
    backend.heads = {"lane/a": "bad"}
    state = State(lanes={"lane/a": Lane("lane/a", "bad", seq=1)})
    engine = Engine(backend, state)
    engine._start_batch()
    assert state.lanes["lane/a"].status == RED
    backend.blocked.clear()
    backend.base = NEW_BASE
    engine._observe_lanes()
    assert state.lanes["lane/a"].status == PENDING
    engine._start_batch()
    assert backend.pushed == [("b1", "bad")]


def test_unknown_preflight_always_falls_through_to_required_ci():
    backend = TinyBackend()
    backend.preflight = lambda base, candidate: (True, "UNKNOWN: DoF unavailable")
    state = State(lanes={"lane/a": Lane("lane/a", "candidate", seq=1)})
    Engine(backend, state)._start_batch()
    assert state.candidates == 1


def test_incident_issue_callback_wakes_same_head_on_same_main(monkeypatch):
    backend = TinyBackend({"bad"})
    backend.heads = {"lane/a": "bad"}
    state = State(lanes={"lane/a": Lane("lane/a", "bad", seq=1)})
    engine = Engine(backend, state)
    engine._start_batch()
    assert state.lanes["lane/a"].status == RED
    backend.blocked.clear()
    monkeypatch.setenv("GITHUB_EVENT_NAME", "issues")
    engine._observe_lanes()
    assert state.lanes["lane/a"].status == PENDING
    engine._start_batch()
    assert backend.pushed == [("b1", "bad")]


def test_known_policy_refusal_is_not_silently_retired():
    backend = TinyBackend()
    state = State(lanes={"lane/a": Lane(
        "lane/a", "bad", status=RED,
        reason="trusted DoF [proof]: no authorized release",
        arrived=-100000, judged_on=BASE)})
    engine = Engine(backend, state)
    engine._retire_stale_lanes()
    assert "lane/a" in state.lanes
    assert state.retired == {}

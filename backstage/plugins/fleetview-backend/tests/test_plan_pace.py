"""The time-left arithmetic, and the claims block that carries it to /fleet and Face.

Founder, 2026-10-23: "can we estimate based on goals and subgoals how much time or work left?"
These tests pin both halves of the answer: the estimate from a claim's own pace, and the refusals
that keep it honest (no pace -> unknown, no plan -> unknown, finished -> none).
"""

from __future__ import annotations

import pytest

from fleetview_backend import plan_pace


def test_checklist_reads_the_issues_own_sub_goals():
    body = (
        "Founder, 2026-10-23: something.\n\n"
        "- [x] pin the behaviour\n"
        "- [X] write the reader\n"
        "- [ ] land on main\n"
        "* [ ] render on the strip\n"
        "- not a checkbox\n"
    )
    plan = plan_pace.checklist(body)
    assert plan["done"] == 2
    assert plan["total"] == 4
    assert plan["open"] == ["land on main", "render on the strip"]


def test_checklist_of_nothing_is_empty_not_an_error():
    assert plan_pace.checklist(None) == {"done": 0, "total": 0, "open": []}
    assert plan_pace.checklist("") == {"done": 0, "total": 0, "open": []}


def test_a_claim_that_has_closed_nothing_has_no_pace_and_says_so():
    est = plan_pace.estimate(0, 5, 3.0)
    assert est["hours_left"] is None
    assert "no pace yet" in est["basis"]
    assert plan_pace.phrase(est).startswith("unknown --")


def test_a_claim_with_no_plan_has_nothing_to_pace():
    est = plan_pace.estimate(0, 0, 3.0)
    assert est["hours_left"] is None
    assert "no sub-goals" in est["basis"]


def test_a_finished_plan_has_no_time_left_rather_than_an_unknown():
    est = plan_pace.estimate(5, 5, 4.0)
    assert est["hours_left"] == 0.0
    assert plan_pace.phrase(est).startswith("none --")


def test_time_left_is_a_band_from_the_claims_own_pace():
    # 2 of 5 closed in 4h = 0.5/h; 3 left = 6h, reported as 3h..9h.
    est = plan_pace.estimate(2, 5, 4.0)
    assert est["pace_per_h"] == pytest.approx(0.5)
    assert est["hours_left"] == pytest.approx(6.0)
    assert est["lo"] == pytest.approx(3.0)
    assert est["hi"] == pytest.approx(9.0)
    assert plan_pace.phrase(est) == (
        "3.0h-9.0h left (2 of 5 closed in 4.0h (this claim's own pace), +/-50%)"
    )


def test_zero_hours_since_the_claim_does_not_divide_by_zero():
    # A claim posted in the same second its plan is read: the pace is enormous, so the time left
    # rounds to nothing -- but it must stay a finite number, never an exception or an infinity.
    est = plan_pace.estimate(1, 4, 0.0)
    assert est["hours_left"] is not None
    assert est["hours_left"] == pytest.approx(3e-9)
    assert plan_pace.phrase(est).startswith("0m-0m left")


def test_phrase_switches_units_so_a_strip_stays_short():
    assert plan_pace.hours_phrase(0.5) == "30m"
    assert plan_pace.hours_phrase(6) == "6.0h"
    assert plan_pace.hours_phrase(72) == "3.0d"


def test_glance_names_the_claim_closest_to_done_and_carries_its_time_left():
    snapshot = {
        "available": True,
        "read_at": "2026-10-23T19:00:00Z",
        "claims": [
            {
                "agent": "pi",
                "issue": 6999,
                "title": "status: one block",
                "live": True,
                "reason": "live",
                "url": "https://github.com/o/r/issues/6999",
                "subgoals_done": 4,
                "subgoals_total": 6,
                "time_left_s": "5m-17m left (4 of 6 closed in 0.4h (this claim's own pace), +/-50%)",
            },
            {
                "agent": "claude",
                "issue": 6974,
                "title": "fleet: time left",
                "live": True,
                "reason": "live",
                "subgoals_done": 0,
                "subgoals_total": 3,
                "time_left_s": "unknown -- no pace yet: 0 of 3 closed in 7.2h",
            },
            {"agent": "x", "issue": 1, "live": False, "reason": "stale heartbeat"},
        ],
    }
    glance = _glance(snapshot)
    assert glance["available"] is True
    assert glance["live"] == 2
    assert glance["stale"] == 1
    assert glance["next"]["issue"] == 6999  # fewest sub-goals left: 2, against 6974's 3
    assert glance["next"]["subgoals"] == "4/6"
    assert glance["next"]["time_left"].startswith("5m-17m left")


def test_an_unreadable_claims_read_is_unavailable_with_its_reason():
    glance = _glance({"available": False, "error": "TimeoutError: gh stalled"})
    assert glance["available"] is False
    assert glance["error"] == "TimeoutError: gh stalled"


def test_no_live_claims_is_zero_live_not_an_error():
    glance = _glance({"available": True, "claims": [], "read_at": "now"})
    assert glance["available"] is True
    assert glance["live"] == 0
    assert glance["next"] is None


def _glance(snapshot):
    from fleetview_backend import claims

    return claims.claims_glance(snapshot)

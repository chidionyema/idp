"""The lane in three answers: quiet when nothing needs a person, loud when something does.

2026-10-20, founder: the greenlane should be one quiet dot, loud only on alarm, a red lane, a
conflict or a long test, and its detail should answer only what is landing and for how long, what
is stuck and why, and what is red and who owns it. These pin that, from the status JSON alone.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from greenlane.brief import LONG_TESTING_MIN, brief  # noqa: E402

NOW = 1000.0
GREEN_MAIN = {"required": {"test": "success", "ci-success": "success"}}


def status(**kw):
    base = {
        "now_min": NOW,
        "main": GREEN_MAIN,
        "alarm": False,
        "invariants": {"work_lost": 0},
        "open_prs": [],
        "state": {"lanes": {}, "batch": None},
    }
    base.update(kw)
    return base


def batch(started, *names):
    return {"started": started, "members": [[n, "h", "t"] for n in names]}


def test_idle_and_green_is_quiet():
    b = brief(status())
    assert b["loud"] is False
    assert b["summary"] == "nothing landing. all clear."


def test_a_batch_under_test_says_what_lands_and_for_how_long_and_stays_quiet():
    s = status(
        state={
            "lanes": {"lane/a": {"status": "testing"}},
            "batch": batch(NOW - 7, "lane/a"),
        }
    )
    b = brief(s)
    assert b["landing"] == {"lanes": ["lane/a"], "minutes": 7}
    assert b["loud"] is False
    assert b["summary"].startswith("1 lane landing, testing 7 minutes")


def test_a_long_test_is_loud_and_says_why():
    s = status(
        state={
            "lanes": {"lane/a": {"status": "testing"}},
            "batch": batch(NOW - LONG_TESTING_MIN - 5, "lane/a"),
        }
    )
    b = brief(s)
    assert b["loud"] is True
    assert b["stuck"][0]["lane"] == "lane/a"
    assert "past" in b["stuck"][0]["why"]


def test_a_conflict_is_stuck_with_the_engines_reason():
    s = status(
        state={
            "lanes": {"lane/c": {"status": "conflict", "reason": "conflicts with main"}}
        }
    )
    b = brief(s)
    assert b["loud"] is True
    assert b["stuck"] == [
        {"lane": "lane/c", "why": "conflicts with main", "status": "conflict"}
    ]


def test_a_red_lane_names_its_owner_from_the_commit_then_the_pr():
    s = status(
        open_prs=[{"number": 9, "head": "lane/r2", "user": "estate-agents[bot]"}],
        state={
            "lanes": {
                "lane/r1": {
                    "status": "red",
                    "reason": "portal-app failure",
                    "owner": "alice",
                },
                "lane/r2": {"status": "red", "reason": "test failure"},
                "lane/r3": {"status": "red", "reason": "x"},
            }
        },
    )
    owners = {r["lane"]: r["owner"] for r in brief(s)["red"]}
    assert owners == {
        "lane/r1": "alice",
        "lane/r2": "estate-agents[bot] #9",
        "lane/r3": "no open PR",
    }
    assert brief(s)["loud"] is True


def test_the_engines_alarm_and_a_red_main_are_loud():
    assert brief(status(alarm=True))["loud"] is True
    red_main = status(main={"required": {"ci-success": "failure"}})
    b = brief(red_main)
    assert b["loud"] is True and b["main_red"] == ["ci-success"]
    assert "main is red on ci-success" in b["summary"]


def test_waiting_lanes_alone_are_not_news():
    s = status(state={"lanes": {"lane/w": {"status": "pending"}}})
    b = brief(s)
    assert b["loud"] is False and b["waiting"] == 1
    assert b["summary"] == "nothing under test, 1 waiting. all clear."


def test_lost_work_is_loud_and_counted():
    s = status(invariants={"work_lost": 2}, alarm=True)
    b = brief(s)
    assert b["loud"] is True and "2 pull requests lost work" in b["summary"]

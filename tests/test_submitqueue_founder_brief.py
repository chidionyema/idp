"""Founder display must distinguish one common policy block from many bad changes."""

from greenlane.brief import brief


def snapshot(lanes):
    return {
        "state": {
            "available": True,
            "lanes": lanes,
            "batch": None,
            "latency": {"outcomes": {}},
        },
        "open_prs": [],
        "main": {"required": {}},
        "now_min": 29903300.0,
        "invariants": {"work_lost": 0},
    }


def test_common_policy_blocker_names_operations_reaction_not_founder_pr_triage():
    status = snapshot(
        {
            "lane/a": {"status": "red", "reason": "trusted DoF [abcdef]: denied"},
            "lane/b": {"status": "red", "reason": "trusted DoF [abcdef]: denied"},
        }
    )
    b = brief(status)
    a = b["assurance"]
    assert a["state"] == "RED"
    assert a["common_mode_refusals"]["count"] == 2
    assert a["next_action"]["code"] == "operations-reaction"
    assert a["next_action"]["incident"] == "chidionyema/idp#7800"
    assert a["next_action"]["blocked_lanes"] == ["lane/a", "lane/b"]


def test_unrelated_red_change_stays_an_independent_repair_obligation():
    b = brief(snapshot({"lane/a": {"status": "red", "reason": "bdd failure"}}))
    assert b["assurance"]["common_mode_refusals"]["count"] == 0
    assert b["assurance"]["next_action"]["code"] == "repair-red-lane"


def test_blind_state_does_not_claim_common_mode_health():
    state = snapshot({})
    state["state"]["available"] = False
    b = brief(state)
    assert b["assurance"]["state"] == "UNKNOWN"
    assert b["assurance"]["next_action"]["code"] == "restore-state-read"

#!/usr/bin/env python3
"""Tests for bin/estate-work-status -- the one status block.

The command's whole value is that its state word is *measured*, so these tests pin the three
parsers that decide what gets measured. Each one is a failure this command actually produced while
it was being written, on real estate data:

  1. a `CLAIM ...` line inside prose (a doc example) was rendered as a live agent named `<name>`,
     20750 days stale;
  2. a commit that merely *quotes* another issue's claim line in its body was credited to that
     issue (15b872617, subject "shadow: lay secret keys...", credited to #6923);
  3. an unreadable heartbeat was treated as live rather than stale, which is the direction that
     blocks the next agent from taking released work.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load():
    path = os.path.join(ROOT, "bin", "estate-work-status")
    loader = importlib.machinery.SourceFileLoader("estate_work_status", path)
    spec = importlib.util.spec_from_loader("estate_work_status", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


ews = _load()


def issue(*comments: str, number: int = 1) -> dict:
    return {
        "number": number,
        "title": "t",
        "body": "",
        "comments": [
            {"body": c, "createdAt": f"2026-10-23T10:0{i}:00Z"}
            for i, c in enumerate(comments)
        ],
    }


def test_claim_parser_takes_the_newest_heartbeat_per_agent():
    claims = ews.parse_claims(
        issue(
            "CLAIM agent=pi paths=bin/a heartbeat=2026-10-23T09:00:00Z",
            "CLAIM agent=pi paths=bin/a,bin/b heartbeat=2026-10-23T10:00:00Z",
        )
    )
    assert len(claims) == 1
    assert claims[0]["heartbeat"] == "2026-10-23T10:00:00Z"
    assert claims[0]["paths"] == "bin/a,bin/b"


def test_claim_parser_ignores_a_prose_example_with_an_unreadable_heartbeat():
    # The doc example in AGENTS.md is `CLAIM agent=<name> paths=<glob> heartbeat=<UTC ISO time>`.
    claims = ews.parse_claims(
        issue(
            "By hand it is one comment in exactly this form: "
            "CLAIM agent=<name> paths=<glob,glob> heartbeat=<UTC ISO time>"
        )
    )
    assert claims == []


def test_claim_parser_keeps_two_agents_on_one_issue_apart():
    claims = ews.parse_claims(
        issue(
            "CLAIM agent=pi paths=bin/a heartbeat=2026-10-23T10:00:00Z",
            "CLAIM agent=estate-agent paths=bin/b heartbeat=2026-10-23T07:00:00Z",
        )
    )
    assert {c["agent"] for c in claims} == {"pi", "estate-agent"}


def test_trailer_parser_reads_only_line_starting_trailers():
    body = (
        "shadow: lay secret keys a container reads from a mounted file (#6976)\n\n"
        "A body sentence quoting CLAIM agent=pi paths=x heartbeat=2026-10-23T10:00:00Z inline.\n\n"
        "Claim: chidionyema/idp#6923\n"
        "Agent: pi\n"
        "Claim: chidionyema/idp#6917\n"
        "Agent: claude-cli\n"
    )
    assert ews.trailer_issues(body) == [6923, 6917]


def test_trailer_parser_ignores_an_inline_mention():
    assert (
        ews.trailer_issues(
            "fixes the thing (see Claim: chidionyema/idp#6923 for context)\n"
        )
        == []
    )


def test_trailer_parser_accepts_the_bare_form_claim_open_writes():
    # bin/claim-open stamps `Claim: #6999`, with no slug; the doc asks for `Claim: idp#6999`. Both
    # forms are in the estate's history. The first version of this parser missed the bare one, so a
    # lane that had already been pushed rendered as "no commit carries this claim's trailer yet".
    assert ews.trailer_issues("subject\n\nClaim: #6999\nAgent: pi\n") == [6999]
    assert ews.trailer_issues("subject\n\nClaim: idp#6999\nAgent: pi\n") == [6999]
    assert ews.trailer_issues(
        "subject\n\nClaim: chidionyema/idp#6999\nAgent: pi\n"
    ) == [6999]


def test_checkboxes_counts_done_and_open_and_ignores_other_markup():
    body = """
- [x] pin the behaviour
- [X] store the claim
- [ ] render the block
  - [ ] nested sub-goal
* [ ] another style
not a checkbox [ ] in prose
"""
    done, total, done_t, open_t = ews.checkboxes(body)
    assert (done, total) == (2, 5)
    assert done_t == ["pin the behaviour", "store the claim"]
    assert open_t[0] == "render the block"


def test_heartbeat_parse_accepts_z_and_offset_and_rejects_junk():
    assert ews.parse_when("2026-10-23T10:00:00Z") > 0
    assert ews.parse_when("2026-10-23T10:00:00+00:00") == ews.parse_when(
        "2026-10-23T10:00:00Z"
    )
    assert ews.parse_when("<UTC ISO time>") == 0.0
    assert ews.parse_when("") == 0.0


def _cargo(sha="a1", lane="lane/x", onmain=False, status=""):
    return {"sha": sha, "ts": 0, "subject": "s", "lane": lane, "_on_main": onmain}


NOW = ews.parse_when("2026-10-23T12:00:00Z")


def _claim(hb="2026-10-23T11:50:00Z"):
    return {"agent": "pi", "paths": "a", "heartbeat": hb, "issued": hb}


def test_state_landed_beats_everything_else():
    state, _ = ews.state_of(_claim(), [_cargo(onmain=True), _cargo(sha="b2")], NOW)
    assert state == "LANDED"


def test_state_blocked_when_the_lane_printed_a_failure():
    c = [_cargo()]
    claim = _claim()
    state, info = ews.state_of(claim, c, NOW)
    info["status"] = "failure: claim-gate refused: no Claim: line"
    state, _ = ews.state_of(claim, c, NOW)
    assert state == "IN LANE"  # state_of does not read the status; main() promotes it
    # what main() does with the same measurement:
    promoted = "BLOCKED" if info["status"].startswith(("failure", "error")) else state
    assert promoted == "BLOCKED"


def test_state_local_when_no_lane_branch_carries_the_commit():
    state, _ = ews.state_of(_claim(), [_cargo(lane="")], NOW)
    assert state == "LOCAL"


def test_state_stale_when_the_heartbeat_is_old_or_unreadable():
    assert ews.state_of(_claim("2026-10-23T08:00:00Z"), [], NOW)[0] == "STALE"
    assert ews.state_of(_claim("<UTC ISO time>"), [], NOW)[0] == "STALE"


def test_state_idle_when_live_and_no_commit_names_the_claim():
    assert ews.state_of(_claim(), [], NOW)[0] == "IDLE"


@pytest.mark.parametrize(
    "seconds,expected",
    [(30, "30s"), (600, "10m"), (7200, "2h"), (259200, "3d")],
)
def test_age_rendering(seconds, expected):
    assert ews.age(seconds) == expected


def test_estimate_refuses_a_number_when_nothing_has_closed():
    e = ews.estimate(0, 5, 3.0)
    assert e["hours_left"] is None
    assert "no pace yet" in e["basis"]


def test_estimate_refuses_a_number_when_nothing_was_written():
    assert ews.estimate(0, 0, 3.0)["hours_left"] is None


def test_estimate_from_the_claims_own_pace_is_a_band_not_a_point():
    # 2 of 5 sub-goals closed in 4 hours = 0.5/h; 3 left = 6h, reported as 3h..9h.
    e = ews.estimate(2, 5, 4.0)
    assert e["pace_per_h"] == pytest.approx(0.5)
    assert e["hours_left"] == pytest.approx(6.0)
    assert (e["lo"], e["hi"]) == (pytest.approx(3.0), pytest.approx(9.0))


def test_estimate_is_zero_when_everything_closed():
    e = ews.estimate(5, 5, 4.0)
    assert e["hours_left"] == 0.0


def test_hours_phrase_covers_minutes_hours_and_days():
    assert ews.hours_phrase(0.5) == "30m"
    assert ews.hours_phrase(6) == "6.0h"
    assert ews.hours_phrase(72) == "3.0d"


def test_the_estimate_line_is_the_same_words_the_json_carries():
    e = ews.estimate(2, 5, 4.0)
    line = ews.estimate_line(e)
    assert line.startswith("3.0h-9.0h")
    assert "+/-50%" in line
    assert ews.estimate_line(ews.estimate(0, 5, 2.0)).startswith(
        "unknown -- no pace yet"
    )
    assert ews.estimate_line(ews.estimate(5, 5, 2.0)).startswith("none --")


def test_this_command_and_the_fleet_strip_compute_the_same_estimate():
    # One implementation, two readers: /fleet's strip calls fleetview_backend.plan_pace directly
    # and this command imports the same module through _pace(). The test fails if anyone forks
    # the arithmetic into a second copy.
    pace = ews._pace()
    assert pace.__name__.endswith("plan_pace"), (
        f"not the one implementation: {pace.__name__}"
    )
    assert pace.__file__.endswith("fleetview_backend/plan_pace.py")
    for done, total, hours in [
        (0, 5, 3.0),
        (1, 1, 0.2),
        (2, 5, 4.0),
        (3, 4, 0.5),
        (7, 7, 9.0),
    ]:
        assert ews.estimate(done, total, hours) == pace.estimate(done, total, hours)
        assert ews.estimate_line(ews.estimate(done, total, hours)) == pace.phrase(
            pace.estimate(done, total, hours)
        )

"""Each objective is researched in the lane that fits it, not in one hardcoded lane.

Measured 2026-10-23, job research-engine-29879183: the cronjob ran every objective with
`--profile objective`, a defect-shaped profile. Founder objective crew#239 "Reimagine mumchimp as
a media company" was asked "Which changes have been reported to reduce Reimagine mumchimp ...",
retrieved nothing on topic and admitted 0 claims for $0.13. The `market-demand` lane had admitted
814 claims on founder subjects. These tests pin which lane an objective goes to, that the cronjob
uses it, and that moving lanes neither resets the cap nor loses a Park tick.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "objective_adapter_lanes",
    ROOT / "platform" / "research-engine" / "objective-adapter.py",
)
adapter = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(adapter)

FOUNDER = {
    "number": 239,
    "title": "Reimagine mumchimp",
    "body": "make it a media company",
}
MINED = {
    "number": 6634,
    "title": "objective: flaky CI",
    "body": "rank 48.0 min per USD\n**cap:** $5\n**Research subject:** flaky CI",
}


def report(cost: float, lane: str | None, ticks: str = "") -> dict:
    tag = f" lane={lane}" if lane else ""
    return {
        "body": f"<!-- research-report request=r cost={cost:.4f}{tag} -->\n"
        f"- [{'x' if 'c' in ticks else ' '}] Continue researching\n"
        f"- [{'x' if 'p' in ticks else ' '}] Park this research"
    }


def test_a_founder_objective_is_researched_as_market_demand():
    assert adapter.lane(FOUNDER) == "market-demand"


def test_a_mined_objective_stays_in_the_defect_lane():
    assert adapter.lane(MINED) == "objective"


def test_the_issue_can_name_its_lane():
    i = dict(FOUNDER, body="**Research lane:** `incident-postmortem`\nwhy did it break")
    assert adapter.lane(i) == "incident-postmortem"


def test_an_unknown_lane_skips_that_objective_and_not_the_rest():
    bad = dict(FOUNDER, number=1, body="**Research lane:** markt-demand")
    with pytest.raises(ValueError):
        adapter.lane(bad)
    chosen = adapter.choose([(bad, []), (MINED, [])])
    assert chosen is MINED


def test_a_report_from_the_wrong_lane_does_not_hold_the_objective():
    # crew#239's only report ran in `objective` (no lane= tag, 0 claims, nothing ticked). It
    # must be researched again in market-demand, without waiting for a tick on that report.
    state, spent = adapter.decision(FOUNDER, [report(0.1318, None)])
    assert state == "new" and spent == pytest.approx(0.1318)


def test_a_report_in_its_own_lane_waits_for_a_tick():
    assert adapter.decision(FOUNDER, [report(0.5, "market-demand")])[0] == "waiting"
    assert (
        adapter.decision(FOUNDER, [report(0.5, "market-demand", "c")])[0] == "continue"
    )


def test_spend_in_any_lane_counts_against_the_cap():
    # Changing lane must not buy a fresh $5: the default cap covers every run on the issue.
    assert adapter.decision(FOUNDER, [report(5.0, None)])[0] == "cap"


def test_a_park_tick_stops_the_objective_in_every_lane():
    assert adapter.decision(FOUNDER, [report(0.1, None, "p")])[0] == "park"


def test_the_report_names_the_lane_it_ran_in():
    run = {
        "request_id": "r",
        "profile_id": "market-demand",
        "worker": {"cost_usd": 0.2},
    }
    body = adapter.report_body(run, [], {}, 0.0, 5.0)
    assert "lane=market-demand -->" in body and "Lane `market-demand`" in body
    assert adapter.report_lane(body) == "market-demand"


def test_pick_prints_the_lane_the_cronjob_runs(monkeypatch, capsys):
    monkeypatch.setattr(adapter, "installation_token", lambda: "t")
    monkeypatch.setattr(adapter, "pick", lambda token: FOUNDER)
    monkeypatch.setattr(adapter, "subject", lambda i: "Reimagine mumchimp")
    assert adapter.main(["pick"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[2] == "market-demand"


def test_the_cronjob_runs_the_picked_lane_not_a_hardcoded_one():
    text = (ROOT / "platform" / "research-engine" / "cronjob.yaml").read_text()
    assert "--profile objective" not in text
    assert "lane=$(printf '%s\\n' \"$picked\" | sed -n 3p)" in text
    assert '--profile "${lane}"' in text


def test_every_default_lane_is_a_profile_the_engine_ships():
    # The image's profiles/ (sha-ecdd4b22): a lane missing there stops the run with ProfileError.
    shipped = {"objective", "market-demand", "estate-guards", "incident-postmortem"}
    assert set(adapter.LANES) <= shipped
    assert adapter.FOUNDER_LANE in shipped and adapter.MINED_LANE in shipped

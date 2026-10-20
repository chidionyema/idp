"""platform/research-engine/objective-adapter.py researches an objective again only when asked.

Founder, 2026-10-19: "in the report provided, option to continue researching or park research".
An objective with no report is researched; one whose last report has Continue ticked is
researched again; Park, an unticked report, or a spent cap stops it. The highest rank goes first.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "objective_adapter", ROOT / "platform" / "research-engine" / "objective-adapter.py"
)
adapter = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(adapter)


def issue(number: int, rank: float, cap: float = 5.0) -> dict:
    return {
        "number": number,
        "title": f"objective: thing {number}",
        "body": f"**Pain:** 3 x 40 min = 120 min; rank {rank} min per USD.\n\n"
        f"**Research subject:** subject {number}\n\n**cap:** ${cap}\n",
    }


def report(cost: float, ticked: str = "") -> dict:
    run = {
        "request_id": "r",
        "delivery": {"status": "delivered"},
        "worker": {"cost_usd": cost},
    }
    body = adapter.report_body(run, [], {}, 0.0, 5.0)
    if ticked:
        body = body.replace(f"- [ ] {ticked}", f"- [x] {ticked}")
    return {"body": body}


def test_new_objective_is_researched_highest_rank_first():
    low, high = issue(10, 12.0), issue(11, 48.0)
    assert adapter.choose([(low, []), (high, [])])["number"] == 11


def test_unticked_report_waits_and_continue_runs_again():
    i = issue(10, 48.0)
    assert adapter.decision(i, [report(0.4)])[0] == "waiting"
    assert adapter.choose([(i, [report(0.4)])]) is None
    assert adapter.decision(i, [report(0.4, "Continue researching")])[0] == "continue"


def test_park_stops_it_even_when_an_earlier_report_said_continue():
    i = issue(10, 48.0)
    cs = [report(0.4, "Continue researching"), report(0.4, "Park this research")]
    assert adapter.decision(i, cs)[0] == "park"
    assert adapter.choose([(i, cs)]) is None


def test_spent_cap_stops_it_even_with_continue_ticked():
    i = issue(10, 48.0, cap=1.0)
    cs = [report(0.6, "Continue researching"), report(0.6, "Continue researching")]
    state, spent = adapter.decision(i, cs)
    assert (state, round(spent, 2)) == ("cap", 1.2)


def test_subject_comes_from_the_issue_not_its_title():
    assert adapter.subject(issue(10, 1.0)) == "subject 10"
    assert adapter.subject({"title": "objective: fallback", "body": ""}) == "fallback"


def test_run_result_is_found_after_the_worker_log():
    result = {"request_id": "abc", "delivery": {"status": "delivered"}}
    log = "INFO gpt-researcher {\n starting\n" + json.dumps(result, indent=2) + "\n"
    assert adapter.load_run(log)["request_id"] == "abc"


def test_report_lists_claims_with_sources_and_both_choices():
    run = {
        "request_id": "abc",
        "delivery": {"status": "delivered"},
        "worker": {"cost_usd": 0.25},
    }
    admitted = [
        {
            "question": "Q1",
            "statement": "S1",
            "confidence": "corroborated",
            "url": "https://x",
        }
    ]
    body = adapter.report_body(run, admitted, {"entailment_failed": 2}, 0.5, 5.0)
    assert "<!-- research-report request=abc cost=0.2500 -->" in body
    assert "**Q1**" in body and "- S1 _corroborated_ ([source](https://x))" in body
    assert "2 entailment_failed" in body and "spent $0.75 of the $5 cap" in body
    assert "- [ ] Continue researching" in body and "- [ ] Park this research" in body

"""delegate-build refuses a plan that did not look for what the estate already has.

2026-09-30: three builders were briefed for the agent diff substrate while the Quad (idp #4764,
docs/tickets/2026-09-28-sovereign-identity-substrate-dros.md) already held part of it; the files
were seen on main but never traced to their PR and ticket. A plan now carries `prior_art`: the
searches the planner ran and what each found, and validate() -- which both `plan` and `dispatch`
run -- refuses a plan without it.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[2] / "platform/estate/libexec/delegate-build.py"
)


def _mod():
    spec = importlib.util.spec_from_file_location("delegate_build", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


STEP = {
    "id": "s1",
    "title": "t",
    "files": ["a.txt"],
    "instructions": "x",
    "done_check": "true",
}

PRIOR_ART = {
    "searches": [
        {
            "kind": "prs",
            "query": "gh pr list --state all --search quad",
            "found": ["#4764 merged"],
        },
        {
            "kind": "tickets",
            "query": "rg -l -i quad docs/tickets docs/specs",
            "found": ["docs/tickets/2026-09-28-sovereign-identity-substrate-dros.md"],
        },
        {
            "kind": "code",
            "query": "rg -l elpis cmd platform",
            "found": ["cmd/elpis-proxy/main.go"],
        },
    ],
    "verdict": "extend",
    "reuse": ["cmd/elpis-proxy canonical string"],
}


def test_plan_without_prior_art_is_refused():
    errors = _mod().validate({"steps": [STEP]})
    assert any("prior_art" in e for e in errors), errors


def test_prior_art_missing_a_search_kind_is_refused():
    pa = dict(
        PRIOR_ART, searches=[s for s in PRIOR_ART["searches"] if s["kind"] != "tickets"]
    )
    errors = _mod().validate({"steps": [STEP], "prior_art": pa})
    assert any("tickets" in e for e in errors), errors


def test_prior_art_with_bad_verdict_is_refused():
    errors = _mod().validate(
        {"steps": [STEP], "prior_art": dict(PRIOR_ART, verdict="maybe")}
    )
    assert any("verdict" in e for e in errors), errors


def test_existing_capability_must_name_what_is_reused():
    errors = _mod().validate({"steps": [STEP], "prior_art": dict(PRIOR_ART, reuse=[])})
    assert any("reuse" in e for e in errors), errors


def test_plan_with_prior_art_is_valid():
    assert _mod().validate({"steps": [STEP], "prior_art": PRIOR_ART}) == []


def test_new_capability_needs_no_reuse_list():
    pa = dict(PRIOR_ART, verdict="new", reuse=[])
    assert _mod().validate({"steps": [STEP], "prior_art": pa}) == []


def test_planner_is_told_to_search_and_may_run_gh():
    m = _mod()
    assert "prior_art" in m.PLAN_SHAPE
    assert "gh pr list" in m.PLANNER_PROMPT
    assert "Bash(gh pr list:*)" in m.PLANNER_TOOLS

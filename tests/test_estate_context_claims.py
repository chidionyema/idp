"""tests/test_estate_context_claims.py -- the broker's claim rules, and the drift fence.

The broker reads the SAME claim record CI reads. If the two ever disagree about what a CLAIM
comment looks like, one of them is enforcing a fiction. The first test here reads bin/claim-gate
and fails when the pattern drifts; the rest drive the rules.
"""

from __future__ import annotations

import datetime as dt
import importlib.machinery
import importlib.util
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "platform"))

from estate.context import claims as claim_rules  # noqa: E402

GATE = os.path.join(os.path.dirname(__file__), "..", "bin", "claim-gate")
PLAN = "a" * 64


def _hb(minutes_ago: float = 1.0) -> str:
    """A heartbeat `minutes_ago` minutes old, as the comment writes it.

    The tests must not be pinned to a date: a claim is LIVE while its heartbeat is inside two
    hours (AGENTS.md 5.4), so a hard-coded 2026-10-27 heartbeat stops being a live claim the
    moment the wall clock moves past it -- and a test that quietly changes meaning is worse
    than no test.
    """
    when = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=minutes_ago)
    return when.strftime("%Y-%m-%dT%H:%M:%SZ")


def _claim_line(
    *,
    agent="pi",
    paths="a/**",
    heartbeat=None,
    instruction="INS-00004",
    plan=PLAN,
    model="",
):
    model_field = f" model={model}" if model else ""
    return (
        f"CLAIM agent={agent} instruction={instruction} plan={plan}{model_field} "
        f"paths={paths} heartbeat={heartbeat or _hb()}"
    )


def test_the_broker_and_gate_share_one_claim_parser():
    loader = importlib.machinery.SourceFileLoader("claim_gate_contract", GATE)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    gate = importlib.util.module_from_spec(spec)
    loader.exec_module(gate)
    assert (
        Path(gate.parse_claim_line.__code__.co_filename).resolve()
        == Path(claim_rules.parse_claim_lines.__code__.co_filename).resolve()
    )


def test_a_claim_comment_is_parsed():
    parsed = claim_rules.parse_claims(
        _claim_line(paths="a/**,b/c.py", heartbeat="2026-10-27T02:39:57Z")
    )
    assert len(parsed) == 1
    c = parsed[0]
    assert c.agent == "pi"
    assert c.instruction == "INS-00004"
    assert c.plan == PLAN
    assert c.paths == ("a/**", "b/c.py")
    assert c.heartbeat is not None and c.heartbeat.year == 2026


def test_the_model_field_is_optional_like_the_gates():
    parsed = claim_rules.parse_claims(
        _claim_line(model="minimax", heartbeat="2026-10-27T02:39:57Z")
    )
    assert len(parsed) == 1 and parsed[0].agent == "pi"


def test_an_open_issue_with_a_claim_and_a_path_inside_it_is_allowed():
    d = claim_rules.verify_claim(
        issue_state="open",
        issue_comments=_claim_line(paths="platform/estate/context/**"),
        agent="pi",
        requested_paths=["platform/estate/context/broker.py"],
        issue_number=7262,
    )
    assert d.allow


def test_a_path_outside_the_claim_is_refused():
    d = claim_rules.verify_claim(
        issue_state="open",
        issue_comments=_claim_line(paths="platform/estate/context/**"),
        agent="pi",
        requested_paths=["platform/estate/pi/estate-commands.ts"],
        issue_number=7262,
    )
    assert not d.allow and d.verdict == "PATH_REFUSED"


def test_a_closed_issue_is_refused():
    d = claim_rules.verify_claim(
        issue_state="closed",
        issue_comments=_claim_line(),
        agent="pi",
        issue_number=7262,
    )
    assert not d.allow and "closed" in d.reason


def test_an_agent_with_no_claim_is_refused():
    d = claim_rules.verify_claim(
        issue_state="open",
        issue_comments=_claim_line(agent="other"),
        agent="pi",
        issue_number=7262,
    )
    assert not d.allow


def test_a_path_another_agent_holds_is_refused():
    d = claim_rules.verify_claim(
        issue_state="open",
        issue_comments=(
            _claim_line(paths="platform/estate/context/**")
            + "\n"
            + _claim_line(agent="other", paths="platform/estate/context/broker.py")
        ),
        agent="pi",
        requested_paths=["platform/estate/context/broker.py"],
        issue_number=7262,
    )
    assert not d.allow and "another agent" in d.reason
    assert d.evidence.get("holder") == "other"


def test_a_dead_agents_claim_does_not_fence_the_door():
    """A lapsed claim holds nothing (AGENTS.md 5.4), so it cannot refuse a live holder.

    Measured 2026-10-28 on issue #7262: a claim from `pi` whose last heartbeat was 17 hours
    old refused the live holder's own request for its own file, and the door was unusable for
    the whole issue until the dead claim was ignored.
    """
    d = claim_rules.verify_claim(
        issue_state="open",
        issue_comments=(
            _claim_line(
                heartbeat=_hb(minutes_ago=17 * 60),
                paths="platform/estate/context/broker.py",
            )
            + "\n"
            + _claim_line(agent="estate-agent", paths="platform/estate/context/**")
        ),
        agent="estate-agent",
        requested_paths=["platform/estate/context/broker.py"],
        issue_number=7262,
    )
    assert d.allow, d.reason
    assert (
        claim_rules.paths_held_by_others(
            claim_rules.parse_claims(_claim_line(heartbeat="2020-01-01T00:00:00Z")),
            "estate-agent",
        )
        == []
    )


def test_a_lapsed_heartbeat_alone_does_not_refuse():
    """The gate stopped refusing on a stale heartbeat on 2026-10-14; the broker must agree."""
    d = claim_rules.verify_claim(
        issue_state="open",
        issue_comments=_claim_line(heartbeat="2020-01-01T00:00:00Z"),
        agent="pi",
        requested_paths=["a/b.py"],
        issue_number=7262,
    )
    assert d.allow


def test_the_paths_an_agent_holds_are_the_union_of_its_claims():
    parsed = claim_rules.parse_claims(
        _claim_line(paths="a/**")
        + "\n"
        + _claim_line(paths="b/**")
        + "\n"
        + _claim_line(agent="other", paths="c/**")
    )
    assert claim_rules.paths_held_by(parsed, "pi") == ["a/**", "b/**"]
    assert claim_rules.paths_held_by_others(parsed, "pi") == ["c/**"]

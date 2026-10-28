"""tests/test_estate_context_claims.py -- the broker's claim rules, and the drift fence.

The broker reads the SAME claim record CI reads. If the two ever disagree about what a CLAIM
comment looks like, one of them is enforcing a fiction. The first test here reads bin/claim-gate
and fails when the pattern drifts; the rest drive the rules.
"""

from __future__ import annotations

import datetime as dt
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "platform"))

from estate.context import claims as claim_rules  # noqa: E402

GATE = os.path.join(os.path.dirname(__file__), "..", "bin", "claim-gate")


def _hb(minutes_ago: float = 1.0) -> str:
    """A heartbeat `minutes_ago` minutes old, as the comment writes it.

    The tests must not be pinned to a date: a claim is LIVE while its heartbeat is inside two
    hours (AGENTS.md 5.4), so a hard-coded 2026-10-27 heartbeat stops being a live claim the
    moment the wall clock moves past it -- and a test that quietly changes meaning is worse
    than no test.
    """
    when = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=minutes_ago)
    return when.strftime("%Y-%m-%dT%H:%M:%SZ")


def _gate_pattern() -> str:
    """The CLAIM pattern as bin/claim-gate writes it, read out of the gate's own source."""
    with open(GATE, "r", encoding="utf-8") as fh:
        source = fh.read()
    m = re.search(r"^CLAIM = re\.compile\(\s*(.*?)\s*,?\s*re\.M", source, re.S | re.M)
    assert m, (
        "bin/claim-gate no longer has a CLAIM pattern; the broker's copy needs a new source"
    )
    return m.group(1)


def test_the_brokers_claim_pattern_is_the_gates_claim_pattern():
    """The copy in claims.py and the gate's own pattern must be the same pattern."""
    with open(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "platform",
            "estate",
            "context",
            "claims.py",
        ),
        "r",
        encoding="utf-8",
    ) as fh:
        source = fh.read()
    m = re.search(r"CLAIM = re\.compile\(\s*(.*?)\s*,?\s*re\.M", source, re.S | re.M)
    assert m, "the broker's CLAIM pattern is gone"
    broker = m.group(1)
    gate = _gate_pattern()
    # The gate's pattern is written across two source lines; compare the pattern text, not the
    # formatting: strip whitespace and quotes.
    norm = lambda s: re.sub(r"\s+", "", s).replace('"', "")
    assert norm(broker) == norm(gate), (
        f"the broker and the gate disagree:\n{gate}\n{broker}"
    )


def test_a_claim_comment_is_parsed():
    parsed = claim_rules.parse_claims(
        "CLAIM agent=pi paths=a/**,b/c.py heartbeat=2026-10-27T02:39:57Z"
    )
    assert len(parsed) == 1
    c = parsed[0]
    assert c.agent == "pi"
    assert c.paths == ("a/**", "b/c.py")
    assert c.heartbeat is not None and c.heartbeat.year == 2026


def test_the_model_field_is_optional_like_the_gates():
    parsed = claim_rules.parse_claims(
        "CLAIM agent=pi model=minimax paths=a/** heartbeat=2026-10-27T02:39:57Z"
    )
    assert len(parsed) == 1 and parsed[0].agent == "pi"


def test_an_open_issue_with_a_claim_and_a_path_inside_it_is_allowed():
    d = claim_rules.verify_claim(
        issue_state="open",
        issue_comments="CLAIM agent=pi paths=platform/estate/context/** heartbeat=2026-10-27T02:39:57Z",
        agent="pi",
        requested_paths=["platform/estate/context/broker.py"],
        issue_number=7262,
    )
    assert d.allow


def test_a_path_outside_the_claim_is_refused():
    d = claim_rules.verify_claim(
        issue_state="open",
        issue_comments="CLAIM agent=pi paths=platform/estate/context/** heartbeat=2026-10-27T02:39:57Z",
        agent="pi",
        requested_paths=["platform/estate/pi/estate-commands.ts"],
        issue_number=7262,
    )
    assert not d.allow and d.verdict == "PATH_REFUSED"


def test_a_closed_issue_is_refused():
    d = claim_rules.verify_claim(
        issue_state="closed",
        issue_comments="CLAIM agent=pi paths=a/** heartbeat=2026-10-27T02:39:57Z",
        agent="pi",
        issue_number=7262,
    )
    assert not d.allow and "closed" in d.reason


def test_an_agent_with_no_claim_is_refused():
    d = claim_rules.verify_claim(
        issue_state="open",
        issue_comments="CLAIM agent=other paths=a/** heartbeat=2026-10-27T02:39:57Z",
        agent="pi",
        issue_number=7262,
    )
    assert not d.allow


def test_a_path_another_agent_holds_is_refused():
    d = claim_rules.verify_claim(
        issue_state="open",
        issue_comments=(
            f"CLAIM agent=pi paths=platform/estate/context/** heartbeat={_hb()}\n"
            f"CLAIM agent=other paths=platform/estate/context/broker.py heartbeat={_hb()}"
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
            "CLAIM agent=pi paths=platform/estate/context/broker.py "
            "heartbeat=2026-10-27T08:15:51Z\n"
            f"CLAIM agent=estate-agent paths=platform/estate/context/** heartbeat={_hb()}"
        ),
        agent="estate-agent",
        requested_paths=["platform/estate/context/broker.py"],
        issue_number=7262,
    )
    assert d.allow, d.reason
    assert (
        claim_rules.paths_held_by_others(
            claim_rules.parse_claims(
                "CLAIM agent=pi paths=a/** heartbeat=2020-01-01T00:00:00Z"
            ),
            "estate-agent",
        )
        == []
    )


def test_a_lapsed_heartbeat_alone_does_not_refuse():
    """The gate stopped refusing on a stale heartbeat on 2026-10-14; the broker must agree."""
    d = claim_rules.verify_claim(
        issue_state="open",
        issue_comments="CLAIM agent=pi paths=a/** heartbeat=2020-01-01T00:00:00Z",
        agent="pi",
        requested_paths=["a/b.py"],
        issue_number=7262,
    )
    assert d.allow


def test_the_paths_an_agent_holds_are_the_union_of_its_claims():
    parsed = claim_rules.parse_claims(
        f"CLAIM agent=pi paths=a/** heartbeat={_hb()}\n"
        f"CLAIM agent=pi paths=b/** heartbeat={_hb()}\n"
        f"CLAIM agent=other paths=c/** heartbeat={_hb()}"
    )
    assert claim_rules.paths_held_by(parsed, "pi") == ["a/**", "b/**"]
    assert claim_rules.paths_held_by_others(parsed, "pi") == ["c/**"]

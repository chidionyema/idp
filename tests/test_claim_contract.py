"""The claim comment is a typed contract shared by its writer, gate and broker."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "platform"))

from estate.context.claim_contract import (
    ClaimContractError,
    format_claim,
    parse_claim_line,
    parse_claim_lines,
)

PLAN = "a" * 64
HEARTBEAT = "2026-11-11T00:00:00Z"


def test_a_claim_requires_an_instruction_and_plan_digest():
    text = (
        "CLAIM agent=codex instruction=INS-00004 "
        f"plan={PLAN} paths=bin/instruction,tests/test_instruction_tracker.py "
        f"heartbeat={HEARTBEAT}"
    )
    claim = parse_claim_lines(text)[0]
    assert claim.agent == "codex"
    assert claim.instruction == "INS-00004"
    assert claim.plan == PLAN
    assert claim.paths == (
        "bin/instruction",
        "tests/test_instruction_tracker.py",
    )


def test_optional_fields_may_appear_in_any_order():
    text = (
        "CLAIM heartbeat="
        + HEARTBEAT
        + " paths=bin/instruction plan="
        + PLAN
        + " model=glm instruction=INS-00004 agent=codex"
    )
    claim = parse_claim_line(text)
    assert claim.model == "glm"
    assert claim.instruction == "INS-00004"


@pytest.mark.parametrize(
    ("line", "message"),
    [
        (
            f"CLAIM agent=codex plan={PLAN} paths=a heartbeat={HEARTBEAT}",
            "instruction",
        ),
        (
            "CLAIM agent=codex instruction=INS-00004 paths=a heartbeat=" + HEARTBEAT,
            "plan",
        ),
        (
            "CLAIM agent=codex instruction=bad plan="
            + PLAN
            + f" paths=a heartbeat={HEARTBEAT}",
            "instruction",
        ),
        (
            "CLAIM agent=codex instruction=INS-00004 plan=abc paths=a heartbeat="
            + HEARTBEAT,
            "plan",
        ),
        (
            "CLAIM agent=codex instruction=INS-00004 plan="
            + PLAN
            + " paths=a heartbeat=not-a-time",
            "heartbeat",
        ),
        (
            "CLAIM agent=codex instruction=INS-00004 plan="
            + PLAN
            + f" paths=a heartbeat={HEARTBEAT} surprise=yes",
            "unknown field",
        ),
    ],
)
def test_malformed_claims_name_the_broken_field(line, message):
    with pytest.raises(ClaimContractError, match=message):
        parse_claim_line(line)


def test_format_round_trips_the_contract():
    rendered = format_claim(
        agent="codex",
        instruction="INS-00004",
        plan=PLAN,
        paths=["bin/instruction", "tests/test_instruction_tracker.py"],
        heartbeat=HEARTBEAT,
        model="glm",
    )
    claim = parse_claim_line(rendered)
    assert rendered.startswith("CLAIM agent=codex instruction=INS-00004 plan=" + PLAN)
    assert claim.paths == ("bin/instruction", "tests/test_instruction_tracker.py")
    assert claim.model == "glm"

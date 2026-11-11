"""Exhaustive finite-state checks for the instruction -> plan -> claim -> evidence contract.

The universe outside this contract is not enumerable: providers fail, disks fill, and users add
new inputs. The contract itself has a finite state space. These tests exhaust it instead of
sampling a few happy and unhappy paths.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import itertools
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "platform"))
sys.path.insert(0, str(ROOT / "platform/estate/memory"))

from estate.context.claim_contract import (  # noqa: E402
    ClaimContractError,
    parse_claim_line,
)
import plan  # noqa: E402


def _instruction_cli():
    source = ROOT / "bin/instruction"
    loader = importlib.machinery.SourceFileLoader(
        "instruction_failure_matrix", str(source)
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("has_plan", "has_claim", "has_evidence"),
    list(itertools.product((False, True), repeat=3)),
)
def test_verified_state_is_exhaustive_over_plan_claim_and_evidence(
    tmp_path, monkeypatch, has_plan, has_claim, has_evidence
):
    monkeypatch.setenv("ESTATE_INSTRUCTIONS", str(tmp_path / "ledger.jsonl"))
    module = _instruction_cli()
    item = {"plan_digest": "", "claims": [], "evidence": []}
    if has_plan:
        item["plan_digest"] = "a" * 64
    if has_claim:
        item["claims"] = ["idp#7901"]
    if has_evidence:
        item["evidence"] = [{"kind": "test", "ref": "pytest"}]

    problems = module.verification_problems(item)

    assert bool(problems) is not (has_plan and has_claim and has_evidence)
    if not has_plan:
        assert "PLAN BLIND" in problems
    if not has_claim:
        assert "CLAIM BLIND" in problems
    if not has_evidence:
        assert "EVIDENCE BLIND" in problems


REQUIRED = {
    "agent": "codex",
    "instruction": "INS-00004",
    "plan": "a" * 64,
    "paths": "bin/instruction",
    "heartbeat": "2026-11-11T00:00:00Z",
}


@pytest.mark.parametrize(
    "present",
    list(itertools.product((False, True), repeat=5)),
)
def test_claim_parser_is_exhaustive_over_required_fields(present):
    fields = {}
    for index, (key, value) in enumerate(REQUIRED.items()):
        if present[index]:
            fields[key] = value
    line = "CLAIM " + " ".join(f"{key}={value}" for key, value in fields.items())
    if all(present):
        parsed = parse_claim_line(line)
        assert parsed.instruction == "INS-00004" and len(parsed.plan) == 64
    else:
        with pytest.raises(ClaimContractError):
            parse_claim_line(line)


def _complete_plan() -> dict:
    return {
        "goal": "prove every claim executes the founder instruction",
        "instruction_id": "INS-00004",
        "prompt": "founder-a",
        "subgoals": [{"id": "g1", "text": "bind the claim"}],
        "bdd": {
            "g1": {
                "given": "a complete plan",
                "when": "a claim is opened",
                "then": "the instruction and digest match",
            }
        },
        "edgecases": {"g1": ["an incomplete plan is refused"]},
        "effects": {"g1": ["the claim and tracker share one key"]},
    }


@pytest.mark.parametrize(
    ("goal", "subgoal", "bdd", "edges", "effects"),
    list(itertools.product((False, True), repeat=5)),
)
def test_plan_claim_validation_is_exhaustive_over_required_dimensions(
    goal, subgoal, bdd, edges, effects
):
    linked = _complete_plan()
    if not goal:
        linked["goal"] = ""
    if not subgoal:
        linked["subgoals"] = []
    if not bdd:
        linked["bdd"] = {}
    if not edges:
        linked["edgecases"] = {}
    if not effects:
        linked["effects"] = {}

    problems = plan.claim_contract_problems(linked, "INS-00004")

    assert bool(problems) is not all((goal, subgoal, bdd, edges, effects))

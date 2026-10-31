# ruff: noqa
# fmt: off
"""The protocol typology. Each protocol is an ordered, closed list of stages."""
from __future__ import annotations

from dataclasses import dataclass

from . import gates as g
from .model import ProtocolId, Stage


@dataclass(frozen=True)
class Protocol:
    id: ProtocolId
    stages: tuple[Stage, ...]
    validators: dict
    proofset_stage: Stage | None  # which stage's claimset the response may draw from
    contract: str  # human/LLM-readable stage contract injected into the agent prompt


S = Stage

GROUNDED_INQUIRY = Protocol(
    id=ProtocolId.GROUNDED_INQUIRY,
    stages=(S.INVOCATION, S.INSTRUCTION, S.DISCOVERY, S.CLAIMSET_PROOFSET, S.RESPONSE),
    validators={
        S.INVOCATION: g.v_invocation,
        S.INSTRUCTION: g.v_instruction,
        S.DISCOVERY: g.make_v_discovery(min_sources=1),
        S.CLAIMSET_PROOFSET: g.make_v_proofset(S.DISCOVERY),
        S.RESPONSE: g.make_v_response(S.CLAIMSET_PROOFSET),
    },
    proofset_stage=S.CLAIMSET_PROOFSET,
    contract=(
        "Retrieve evidence first. State each claim separately and attach a verbatim quote "
        "from retrieved evidence as its proof. Your response may only assert claims that "
        "passed proof; connective text must contain no facts or numbers."
    ),
)

EXECUTION = Protocol(
    id=ProtocolId.EXECUTION,
    stages=(S.INVOCATION, S.INSTRUCTION, S.STATE_ASSESSMENT, S.ACTION_PLAN_DRY_RUN, S.COMMIT, S.RESPONSE),
    validators={
        S.INVOCATION: g.v_invocation,
        S.INSTRUCTION: g.v_instruction,
        S.STATE_ASSESSMENT: g.v_state_assessment,
        S.ACTION_PLAN_DRY_RUN: g.v_dry_run,
        S.COMMIT: g.v_commit,
        S.RESPONSE: g.make_v_response(None),
    },
    proofset_stage=None,
    contract=(
        "Assess current state and declare your scope. Produce a plan and dry-run exactly "
        "that plan; commit only the same plan against unchanged state. Irreversible steps "
        "need explicit approval. Report with a receipt for the committed action."
    ),
)

DEEP_SYNTHESIS = Protocol(
    id=ProtocolId.DEEP_SYNTHESIS,
    stages=(
        S.INVOCATION, S.INSTRUCTION, S.DIVERGENT_DISCOVERY,
        S.CONTRADICTION_RESOLUTION, S.UNIFIED_CLAIMSET_PROOFSET, S.RESPONSE,
    ),
    validators={
        S.INVOCATION: g.v_invocation,
        S.INSTRUCTION: g.v_instruction,
        S.DIVERGENT_DISCOVERY: g.make_v_discovery(min_sources=2),
        S.CONTRADICTION_RESOLUTION: g.v_contradiction_resolution,
        S.UNIFIED_CLAIMSET_PROOFSET: g.make_v_proofset(S.DIVERGENT_DISCOVERY, unified=True),
        S.RESPONSE: g.make_v_response(S.UNIFIED_CLAIMSET_PROOFSET),
    },
    proofset_stage=S.UNIFIED_CLAIMSET_PROOFSET,
    contract=(
        "Gather from at least two independent sources. Compare all evidence for conflicts; "
        "resolve each with a rationale or mark it unresolved. Build one proved claimset "
        "that cites the winning evidence; disclose every unresolved conflict in the response."
    ),
)

REGISTRY: dict[ProtocolId, Protocol] = {
    p.id: p for p in (GROUNDED_INQUIRY, EXECUTION, DEEP_SYNTHESIS)
}

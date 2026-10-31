# ruff: noqa
# fmt: off
"""Typed artifacts exchanged between pipeline stages.

Every stage must emit one of these. Free text never advances a run.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum


class Stage(str, Enum):
    INVOCATION = "invocation"
    INSTRUCTION = "instruction"
    DISCOVERY = "discovery"
    CLAIMSET_PROOFSET = "claimset_proofset"
    STATE_ASSESSMENT = "state_assessment"
    ACTION_PLAN_DRY_RUN = "action_plan_dry_run"
    COMMIT = "commit"
    DIVERGENT_DISCOVERY = "divergent_discovery"
    CONTRADICTION_RESOLUTION = "contradiction_resolution"
    UNIFIED_CLAIMSET_PROOFSET = "unified_claimset_proofset"
    RESPONSE = "response"


class ProtocolId(str, Enum):
    GROUNDED_INQUIRY = "grounded_inquiry"
    EXECUTION = "execution"
    DEEP_SYNTHESIS = "deep_synthesis"


# ---- shared -----------------------------------------------------------
@dataclass(frozen=True)
class Invocation:
    request: str
    principal: str = ""


@dataclass(frozen=True)
class Instruction:
    directive: str


# ---- discovery / proof -------------------------------------------------
@dataclass(frozen=True)
class Evidence:
    id: str
    source: str  # where it came from (URL, file, tool name)
    text: str  # the retrieved content, verbatim


@dataclass(frozen=True)
class Discovery:
    evidence: tuple[Evidence, ...]
    passes: int = 1


@dataclass(frozen=True)
class Claim:
    id: str
    text: str
    contested: bool = False


@dataclass(frozen=True)
class Proof:
    claim_id: str
    evidence_id: str
    quote: str  # verbatim span from the evidence supporting the claim


@dataclass(frozen=True)
class ClaimProofSet:
    claims: tuple[Claim, ...]
    proofs: tuple[Proof, ...]


# ---- execution ---------------------------------------------------------
@dataclass(frozen=True)
class Assessment:
    snapshot_digest: str  # digest of the state the plan is based on
    scope: tuple[str, ...]  # target prefixes the agent may touch


@dataclass(frozen=True)
class Step:
    action: str
    target: str
    reversible: bool = True


@dataclass(frozen=True)
class Plan:
    steps: tuple[Step, ...]

    def digest(self) -> str:
        blob = json.dumps(
            [[s.action, s.target, s.reversible] for s in self.steps], separators=(",", ":")
        )
        return hashlib.sha256(blob.encode()).hexdigest()


@dataclass(frozen=True)
class DryRunResult:
    plan_digest: str
    passed: bool
    checks: dict = field(default_factory=dict)  # name -> bool


@dataclass(frozen=True)
class ActionPlanDryRun:
    plan: Plan
    result: DryRunResult


@dataclass(frozen=True)
class Commit:
    plan_digest: str
    snapshot_digest: str  # re-read immediately before commit
    idempotency_key: str
    approvals: tuple[str, ...] = ()  # "action:target" for each irreversible step


# ---- synthesis ---------------------------------------------------------
@dataclass(frozen=True)
class Contradiction:
    id: str
    evidence_ids: tuple[str, ...]
    status: str  # "resolved" | "unresolved"
    rationale: str = ""
    preferred_evidence_id: str | None = None


@dataclass(frozen=True)
class ContradictionReport:
    examined: tuple[str, ...]  # evidence ids the detector actually compared
    contradictions: tuple[Contradiction, ...] = ()


# ---- response ----------------------------------------------------------
@dataclass(frozen=True)
class Segment:
    kind: str  # "claim" | "text" | "disclosure" | "receipt"
    claim_id: str | None = None
    text: str = ""
    contradiction_id: str | None = None


@dataclass(frozen=True)
class Response:
    segments: tuple[Segment, ...]

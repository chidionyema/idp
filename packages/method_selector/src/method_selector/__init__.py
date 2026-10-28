"""The estate's adaptive problem-solving method selector (SF-1).

A pure library beside the estate's decision layer: given an evidence-backed problem
fingerprint it recommends a bounded, context-appropriate method and its proof obligation,
or it abstains and asks for a bounded probe. It never executes, never authorises and
never writes.

The founder's operational contract is the specification of record
(`~/Downloads/OPERATIONAL_SPEC.md`, v0.1); the design decision is in
`docs/decisions/2026-10-28-the-method-selector-is-a-library-beside-the-decision-layer.md`.
"""

from __future__ import annotations

from .catalog import BY_ID, METHODS, MethodSpec, PREREQUISITE_SATISFIERS, get
from .contracts import (
    AUTHORITIES,
    FINGERPRINT_VERSION,
    PROBLEM_KINDS,
    RISK_TIERS,
    SCHEMA_VERSION,
    SELECTION_VERSION,
    Budget,
    ContractError,
    EvidenceRef,
    MethodSelection,
    ProblemRequest,
    SelectionOutcome,
    assess_outcome,
    validate_request,
)
from .select import DECIDER, RISK_ALLOWANCE, select, select_request, select_safe

__version__ = "0.1.0"

__all__ = [
    "AUTHORITIES",
    "BY_ID",
    "Budget",
    "ContractError",
    "DECIDER",
    "EvidenceRef",
    "FINGERPRINT_VERSION",
    "METHODS",
    "MethodSelection",
    "MethodSpec",
    "PREREQUISITE_SATISFIERS",
    "PROBLEM_KINDS",
    "ProblemRequest",
    "RISK_ALLOWANCE",
    "RISK_TIERS",
    "SCHEMA_VERSION",
    "SELECTION_VERSION",
    "SelectionOutcome",
    "__version__",
    "assess_outcome",
    "get",
    "select",
    "select_request",
    "select_safe",
    "validate_request",
]

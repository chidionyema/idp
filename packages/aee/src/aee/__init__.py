"""The Adaptive Intelligence and Execution Economy (AEE): the shared contracts.

The specification names ten entities -- Objective, WorkGraph, WorkNode,
ExecutionContract, ExecutionAttempt, IntelligenceLane, CapacityReservation,
VerificationReceipt, EconomicReceipt, GraphRevision. They live in
``aee.contracts``; the work graph and its mutations live in ``aee.graph``.

What this package is NOT, deliberately, because the estate already has one of each:

  * not a scheduler. ``platform/queue/dispatcher.py`` claims tasks and makes
    worktrees; this says what depends on what.
  * not an authority over money. ``sovereign/engine/budget.py`` is the budget
    authority; a CapacityReservation names the budget it reserves against.
  * not a second signer. ``platform/llm/action_ledger.py`` is the economic
    spine and ``sovereign/engine/receipts.py`` the verification spine; an
    EconomicReceipt here POINTS at the ledger row that already carries the
    signature.
  * not a second capability registry. ``bin/capability-index`` is the one.

Two structures are genuinely new, and only two: the WorkGraph (with its
GraphRevision) and the ExecutionContract. The other eight extend what the
estate already runs.
"""

from .allocation import (
    Allocation,
    AllocationError,
    AllocationRequest,
    SupplyOffer,
    allocate,
    estimate_cost_usd,
    select_offer,
)
from .contracts import (
    AcceptanceCriterion,
    AttemptOutcome,
    CapacityReservation,
    ContractError,
    Correlation,
    EconomicReceipt,
    ExecutionAttempt,
    ExecutionContract,
    GraphRevision,
    IntelligenceLane,
    MutationOp,
    NodeKind,
    NodeState,
    Objective,
    ReservationState,
    Verdict,
    VerificationLevel,
    VerificationReceipt,
    WASTE_CLASSES,
    WorkNode,
)
from .digest import canonical_bytes, digest_of
from .graph import (
    AcceptanceRequiredError,
    ContractViolation,
    CycleError,
    GraphError,
    OwnershipError,
    ReservationError,
    ScopeError,
    UnknownNodeError,
    VerificationRequiredError,
    WorkGraph,
)

__all__ = [
    "AcceptanceCriterion",
    "AcceptanceRequiredError",
    "Allocation",
    "AllocationError",
    "AllocationRequest",
    "AttemptOutcome",
    "CapacityReservation",
    "ContractError",
    "ContractViolation",
    "Correlation",
    "CycleError",
    "EconomicReceipt",
    "ExecutionAttempt",
    "ExecutionContract",
    "GraphError",
    "GraphRevision",
    "IntelligenceLane",
    "MutationOp",
    "NodeKind",
    "NodeState",
    "Objective",
    "OwnershipError",
    "ReservationError",
    "ReservationState",
    "ScopeError",
    "SupplyOffer",
    "UnknownNodeError",
    "Verdict",
    "VerificationLevel",
    "VerificationReceipt",
    "VerificationRequiredError",
    "WASTE_CLASSES",
    "WorkGraph",
    "WorkNode",
    "allocate",
    "canonical_bytes",
    "digest_of",
    "estimate_cost_usd",
    "select_offer",
]

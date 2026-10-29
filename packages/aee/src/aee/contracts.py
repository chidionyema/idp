"""The AEE shared contracts: the typed vocabulary every execution surface speaks.

The specification names ten entities -- Objective, WorkGraph, WorkNode,
ExecutionContract, ExecutionAttempt, IntelligenceLane, CapacityReservation,
VerificationReceipt, EconomicReceipt, GraphRevision. They live here as plain,
frozen, self-validating data.

What this module deliberately does NOT do:

  * it does not sign anything. The economic spine is
    ``platform/llm/action_ledger.py``'s signed hash chain and the verification
    spine is ``sovereign/engine/receipts.py``'s. An EconomicReceipt here POINTS
    at the ledger row that already carries the signature -- a second signer
    would be a second authority, and the estate has one of each.
  * it does not spend anything. A CapacityReservation names the budget
    authority (``sovereign/engine/budget.py``) it reserves against.
  * it does not schedule. ``platform/queue/dispatcher.py`` claims tasks and
    makes worktrees; this says what depends on what.

Every entity refuses to be constructed in an invalid shape, so a malformed
contract cannot reach a worker.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Tuple

__all__ = [
    "AcceptanceCriterion",
    "AttemptOutcome",
    "CapacityReservation",
    "ContractError",
    "Correlation",
    "EconomicReceipt",
    "ExecutionAttempt",
    "ExecutionContract",
    "GraphRevision",
    "IntelligenceLane",
    "MutationOp",
    "NodeKind",
    "NodeState",
    "Objective",
    "ReservationState",
    "Verdict",
    "VerificationLevel",
    "VerificationReceipt",
    "WASTE_CLASSES",
    "WorkNode",
]

ID_RE = re.compile(r"^[a-z0-9][a-z0-9._:-]{2,127}$")

# What a spend turned into. The vocabulary is closed: the estate reports a spend
# as productive, wasted, reserved (held but not yet spent) or unknown, and
# "unknown" is never quietly read as "free". G4's allocation writes "reserved";
# the runtime writes the rest once the attempt is measured.
WASTE_CLASSES = ("productive", "wasted", "reserved", "unknown")


class ContractError(ValueError):
    """A contract that cannot exist, refused at construction rather than later."""


def _check_id(value: object, what: str) -> str:
    if not isinstance(value, str) or not ID_RE.match(value):
        raise ContractError(
            "%s must be a lowercase identifier (a-z, 0-9, . _ : -), got %r"
            % (what, value)
        )
    return value


def _check_text(value: object, what: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError("%s must be a non-empty string, got %r" % (what, value))
    return value


def _as_enum(enum_cls, value):
    """Accept the enum or its string value; refuse anything else."""
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)
    except ValueError as err:
        raise ContractError(
            "%s must be one of %s, got %r"
            % (enum_cls.__name__, [e.value for e in enum_cls], value)
        ) from err


class NodeState(str, Enum):
    PENDING = "pending"
    READY = "ready"
    BLOCKED = "blocked"
    RUNNING = "running"
    VERIFIED = "verified"
    ACCEPTED = "accepted"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REPLACED = "replaced"


TERMINAL_STATES = (
    NodeState.ACCEPTED,
    NodeState.FAILED,
    NodeState.CANCELLED,
    NodeState.REPLACED,
)


class NodeKind(str, Enum):
    TASK = "task"
    BARRIER = "barrier"
    JOIN = "join"
    SPLIT = "split"
    INTEGRATE = "integrate"


class VerificationLevel(str, Enum):
    OPERATION = "operation"
    INTEGRATION = "integration"
    OBJECTIVE = "objective"


class Verdict(str, Enum):
    PASS = "pass"  # noqa: S105 -- a verdict, not a password
    FAIL = "fail"


class ReservationState(str, Enum):
    HELD = "held"
    COMMITTED = "committed"
    RELEASED = "released"


class AttemptOutcome(str, Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MutationOp(str, Enum):
    ADD = "add"
    SPLIT = "split"
    SPAWN = "spawn"
    MERGE = "merge"
    JOIN = "join"
    BLOCK = "block"
    UNBLOCK = "unblock"
    RETRY = "retry"
    REPLACE = "replace"
    CANCEL = "cancel"
    REPRIORITISE = "reprioritise"
    REPLAN = "replan"
    INTEGRATE = "integrate"
    COMPLETE = "complete"
    RUN = "run"
    FAIL = "fail"


@dataclass(frozen=True)
class Correlation:
    """The five identifiers every record carries.

    A receipt that cannot be traced to its objective, graph, node, attempt and
    contract is not evidence; it is a story.
    """

    objective_id: str
    graph_id: str
    node_id: str
    attempt_id: str
    contract_id: str

    def __post_init__(self) -> None:
        for name in (
            "objective_id",
            "graph_id",
            "node_id",
            "attempt_id",
            "contract_id",
        ):
            _check_id(getattr(self, name), name)

    def as_dict(self) -> Dict[str, str]:
        return {
            "objective_id": self.objective_id,
            "graph_id": self.graph_id,
            "node_id": self.node_id,
            "attempt_id": self.attempt_id,
            "contract_id": self.contract_id,
        }


@dataclass(frozen=True)
class AcceptanceCriterion:
    """One thing that must be true, and the level at which it is judged.

    Verification has three levels and they are not interchangeable: OPERATION
    (it ran), INTEGRATION (it ran inside the whole), OBJECTIVE (the original
    objective is satisfied).
    """

    id: str
    description: str
    level: VerificationLevel = VerificationLevel.OPERATION

    def __post_init__(self) -> None:
        _check_id(self.id, "acceptance criterion id")
        _check_text(self.description, "acceptance criterion description")
        object.__setattr__(self, "level", _as_enum(VerificationLevel, self.level))


@dataclass(frozen=True)
class Objective:
    """What the estate is trying to achieve, and how anyone will know.

    ``scope`` is the authorised surface: the paths this objective may touch.
    An empty scope means unrestricted, and a contract that declares a path
    outside a non-empty scope is refused.
    """

    id: str
    statement: str
    acceptance: Tuple[AcceptanceCriterion, ...] = ()
    authority: str = ""
    scope: Tuple[str, ...] = ()
    deadline_s: Optional[int] = None

    def __post_init__(self) -> None:
        _check_id(self.id, "objective id")
        _check_text(self.statement, "objective statement")
        _check_text(self.authority, "objective authority")
        if not isinstance(self.acceptance, (tuple, list)) or not self.acceptance:
            raise ContractError("an objective needs at least one acceptance criterion")
        if not all(isinstance(a, AcceptanceCriterion) for a in self.acceptance):
            raise ContractError("acceptance must be a sequence of AcceptanceCriterion")
        object.__setattr__(self, "acceptance", tuple(self.acceptance))
        for path in self.scope:
            _check_text(path, "objective scope entry")
        object.__setattr__(self, "scope", tuple(self.scope))
        if self.deadline_s is not None and self.deadline_s <= 0:
            raise ContractError("objective deadline_s must be positive when given")

    def criterion(self, criterion_id: str) -> AcceptanceCriterion:
        for c in self.acceptance:
            if c.id == criterion_id:
                return c
        raise ContractError(
            "no acceptance criterion %r on objective %r" % (criterion_id, self.id)
        )


@dataclass(frozen=True)
class WorkNode:
    """One unit of work in the graph, with its dependencies and its evidence."""

    id: str
    kind: NodeKind = NodeKind.TASK
    title: str = ""
    scope: Tuple[str, ...] = ()
    depends_on: Tuple[str, ...] = ()
    state: NodeState = NodeState.PENDING
    owner: str = ""
    priority: int = 0
    attempt_id: str = ""
    contract_id: str = ""
    verification_ids: Tuple[str, ...] = ()
    reservation_id: str = ""
    reason: str = ""

    def __post_init__(self) -> None:
        _check_id(self.id, "node id")
        object.__setattr__(self, "kind", _as_enum(NodeKind, self.kind))
        object.__setattr__(self, "state", _as_enum(NodeState, self.state))
        if self.title:
            _check_text(self.title, "node title")
        for path in self.scope:
            _check_text(path, "node scope entry")
        object.__setattr__(self, "scope", tuple(self.scope))
        deps = tuple(self.depends_on)
        if len(set(deps)) != len(deps):
            raise ContractError("node %r lists a dependency twice" % self.id)
        if self.id in deps:
            raise ContractError("node %r depends on itself" % self.id)
        for dep in deps:
            _check_id(dep, "dependency id")
        object.__setattr__(self, "depends_on", deps)
        object.__setattr__(self, "verification_ids", tuple(self.verification_ids))

    def depends(self, other: str) -> bool:
        return other in self.depends_on


@dataclass(frozen=True)
class IntelligenceLane:
    """A way to think: a model, a tool, or a human.

    ``deterministic`` is the flag that matters most. A deterministic lane is
    preferred wherever the work allows it, because its cost is bounded and its
    output is reproducible; a probabilistic lane is a choice with a price.
    """

    id: str
    provider: str
    model: str = ""
    lane_type: str = "model"
    deterministic: bool = False
    cost_usd_per_1k: float = 0.0
    quality_prior: float = 0.0
    availability: float = 1.0
    latency_p95_ms: int = 0

    def __post_init__(self) -> None:
        _check_id(self.id, "lane id")
        _check_text(self.provider, "lane provider")
        if self.lane_type not in ("model", "tool", "human"):
            raise ContractError("lane_type must be model, tool or human")
        if not 0.0 <= self.quality_prior <= 1.0:
            raise ContractError("lane quality_prior must be within 0..1")
        if not 0.0 <= self.availability <= 1.0:
            raise ContractError("lane availability must be within 0..1")
        if self.cost_usd_per_1k < 0:
            raise ContractError("lane cost_usd_per_1k cannot be negative")
        if self.latency_p95_ms < 0:
            raise ContractError("lane latency_p95_ms cannot be negative")


@dataclass(frozen=True)
class CapacityReservation:
    """Capacity held against a budget authority before the work is run.

    It is a claim on a budget, not money: the budget authority stays
    ``sovereign/engine/budget.py``. A reservation is never silently dropped --
    it is HELD, then COMMITTED (spent) or RELEASED (given back), and the graph
    refuses to lose one.
    """

    id: str
    lane_id: str
    units: int = 1
    usd: float = 0.0
    budget_ref: str = ""
    state: ReservationState = ReservationState.HELD
    window_s: int = 0

    def __post_init__(self) -> None:
        _check_id(self.id, "reservation id")
        _check_id(self.lane_id, "reservation lane id")
        _check_text(self.budget_ref, "reservation budget_ref")
        object.__setattr__(self, "state", _as_enum(ReservationState, self.state))
        if self.units <= 0:
            raise ContractError("a reservation must hold at least one unit")
        if self.usd < 0:
            raise ContractError("a reservation cannot hold negative usd")
        if self.window_s < 0:
            raise ContractError("a reservation window cannot be negative")


@dataclass(frozen=True)
class ExecutionContract:
    """The agreement a worker signs up to before it runs a node.

    It states the authority (the scope it may touch), the price (budget), the
    evidence it must produce (verification levels), and how many times it may
    be tried. Everything a worker needs is here, so nothing is implied.
    """

    id: str
    node_id: str
    lane: IntelligenceLane
    scope: Tuple[str, ...] = ()
    budget_usd: float = 0.0
    budget_seconds: int = 0
    verification_levels: Tuple[VerificationLevel, ...] = (VerificationLevel.OPERATION,)
    max_attempts: int = 1
    idempotency_key: str = ""
    reservation_id: str = ""
    deadline_s: Optional[int] = None

    def __post_init__(self) -> None:
        _check_id(self.id, "contract id")
        _check_id(self.node_id, "contract node id")
        if not isinstance(self.lane, IntelligenceLane):
            raise ContractError("a contract needs an IntelligenceLane")
        for path in self.scope:
            _check_text(path, "contract scope entry")
        object.__setattr__(self, "scope", tuple(self.scope))
        levels = tuple(_as_enum(VerificationLevel, v) for v in self.verification_levels)
        if not levels:
            raise ContractError(
                "a contract must require at least one verification level"
            )
        object.__setattr__(self, "verification_levels", levels)
        if self.max_attempts < 1:
            raise ContractError("a contract must allow at least one attempt")
        if self.budget_usd < 0 or self.budget_seconds < 0:
            raise ContractError("a contract budget cannot be negative")

    @property
    def lane_id(self) -> str:
        return self.lane.id


@dataclass(frozen=True)
class ExecutionAttempt:
    """One try of one contract, with what it cost and what it proved."""

    id: str
    contract_id: str
    node_id: str
    lane_id: str
    started_at: float = 0.0
    ended_at: Optional[float] = None
    outcome: Optional[AttemptOutcome] = None
    verification_id: str = ""
    economic_id: str = ""

    def __post_init__(self) -> None:
        _check_id(self.id, "attempt id")
        _check_id(self.contract_id, "attempt contract id")
        _check_id(self.node_id, "attempt node id")
        _check_id(self.lane_id, "attempt lane id")
        if self.outcome is not None:
            object.__setattr__(self, "outcome", _as_enum(AttemptOutcome, self.outcome))


@dataclass(frozen=True)
class VerificationReceipt:
    """Evidence that a node did what its contract said, at a named level.

    ``evidence`` is a locator (a receipt id, a ledger hash, a path), never a
    claim: a receipt without evidence cannot be produced.
    """

    id: str
    node_id: str
    attempt_id: str
    level: VerificationLevel
    verdict: Verdict
    evidence: str
    verifier: str
    at: float = 0.0
    contract_id: str = ""

    def __post_init__(self) -> None:
        _check_id(self.id, "verification receipt id")
        _check_id(self.node_id, "verification receipt node id")
        _check_id(self.attempt_id, "verification receipt attempt id")
        _check_text(self.evidence, "verification evidence")
        _check_text(self.verifier, "verification verifier")
        object.__setattr__(self, "level", _as_enum(VerificationLevel, self.level))
        object.__setattr__(self, "verdict", _as_enum(Verdict, self.verdict))


@dataclass(frozen=True)
class EconomicReceipt:
    """What an attempt cost, pointed at the ledger row that proves it.

    ``cost_usd`` is None when the cost is UNKNOWN, and unknown is not zero:
    the estate reports an unknown cost as unknown. A known cost must carry the
    ``ledger_hash`` of the signed action-ledger row it derives from, because
    that chain is the economic spine -- this receipt never signs anything.
    """

    id: str
    attempt_id: str
    node_id: str
    contract_id: str
    provider: str
    model: str = ""
    at: float = 0.0
    cost_usd: Optional[float] = None
    tokens_in: int = 0
    tokens_out: int = 0
    ledger_hash: str = ""
    unit_price_usd_per_1k: float = 0.0
    waste_class: str = "unknown"

    def __post_init__(self) -> None:
        _check_id(self.id, "economic receipt id")
        _check_id(self.attempt_id, "economic receipt attempt id")
        _check_id(self.node_id, "economic receipt node id")
        _check_id(self.contract_id, "economic receipt contract id")
        _check_text(self.provider, "economic receipt provider")
        if self.cost_usd is not None:
            if self.cost_usd < 0:
                raise ContractError("an economic receipt cannot carry a negative cost")
            if not self.ledger_hash:
                raise ContractError(
                    "a receipt with a known cost must name the ledger_hash it derives from"
                )
        if self.tokens_in < 0 or self.tokens_out < 0:
            raise ContractError("token counts cannot be negative")
        if self.unit_price_usd_per_1k < 0:
            raise ContractError("a unit price cannot be negative")
        if self.waste_class not in WASTE_CLASSES:
            raise ContractError(
                "waste_class must be one of %s, got %r"
                % (list(WASTE_CLASSES), self.waste_class)
            )

    @property
    def cost_known(self) -> bool:
        return self.cost_usd is not None


@dataclass(frozen=True)
class GraphRevision:
    """One version of the work graph: its digest, and who changed it.

    The digest is computed over the estate's one canonical serialisation, so
    two agents that build the same graph agree on its address without a
    server, and a revision that changes nothing has the same address as the
    state it describes.
    """

    number: int
    digest: str
    parent_digest: str
    op: MutationOp
    actor: str
    at: float = 0.0
    summary: str = ""
    node_states: Tuple[Tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        _check_text(self.digest, "revision digest")
        _check_text(self.actor, "revision actor")
        object.__setattr__(self, "op", _as_enum(MutationOp, self.op))
        object.__setattr__(self, "node_states", tuple(self.node_states))

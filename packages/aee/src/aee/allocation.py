"""The one allocation policy: (node, supply, budget, deadline) -> contract.

Deterministic first. The same request always produces the same contract, the
same reservation and the same receipt -- no clock, no randomness and no model
in the path. The only inputs are the arguments; ``now`` is one of them, which
is why the receipt can carry a moment and the contract cannot.

The rules, in the order they are applied:

 1. Some lane must be able to do the work. If none can, the allocation is
    refused with the reason -- never a guess, never a quiet fallback.
 2. A deterministic lane is preferred over any model lane whenever it
    satisfies the contract. A formatter, a grep, a hash: bounded cost,
    reproducible output. This is the bypass the programme measures.
 3. Among the lanes that remain the order is fixed and lexicographic:
    quality first (the programme's rule -- verified outcome quality, then
    total cost, then completion time), then the cheaper price, then the
    faster lane, then the lane id. The id breaks every tie, so the order is
    total and the policy is deterministic.
 4. A learned policy may only PROPOSE. It runs in shadow: the deterministic
    policy decides, and the disagreement is recorded in the receipt. Learned
    routing is not introduced until a benchmark shows it beats this policy.
 5. Every allocation produces an EconomicReceipt carrying a unit price and a
    waste class. It does not write to the action ledger: the ledger is the
    economic spine, it is written once, by the runtime, when the attempt has
    actually been measured. This module never signs and never spends.

What this module deliberately does NOT do: it does not decide what work
exists (that is the work graph), it does not schedule (the dispatcher does),
and it does not hold a budget (the reservation names the authority that
does). It decides one thing -- which lane runs this node, and what it is
allowed to spend.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from .contracts import (
    CapacityReservation,
    EconomicReceipt,
    ExecutionContract,
    IntelligenceLane,
    ReservationState,
    VerificationLevel,
    WorkNode,
)
from .digest import digest_of

__all__ = [
    "Allocation",
    "AllocationError",
    "AllocationRequest",
    "SupplyOffer",
    "allocate",
    "estimate_cost_usd",
    "select_offer",
]


class AllocationError(RuntimeError):
    """No lane can run the node, and the reason is part of the refusal."""


@dataclass(frozen=True)
class SupplyOffer:
    """What one lane offers for one node.

    ``capabilities`` is what the lane can actually do; the request names the
    capabilities the node needs. A lane that cannot do the work is not a
    candidate, whatever it costs.

    ``units_available`` is the capacity the lane can hold right now. Zero
    means the lane is drained, and the allocation moves on -- it does not
    fail the node while another lane can take it.

    ``max_usd`` is the ceiling this offer itself accepts, on top of the
    request's budget. Zero means the request's budget is the only ceiling.
    """

    lane: IntelligenceLane
    capabilities: Tuple[str, ...] = ()
    units_available: int = 1
    max_usd: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.lane, IntelligenceLane):
            raise AllocationError("a supply offer needs an IntelligenceLane")
        object.__setattr__(self, "capabilities", tuple(self.capabilities))
        if self.units_available < 0:
            raise AllocationError("a supply offer cannot hold negative capacity")
        if self.max_usd < 0:
            raise AllocationError("a supply offer cannot accept a negative ceiling")


@dataclass(frozen=True)
class AllocationRequest:
    """Everything the policy is allowed to know.

    There is no clock, no environment and no network in here. A caller that
    wants a different lane fact puts it in ``offers``.
    """

    node: WorkNode
    offers: Tuple[SupplyOffer, ...] = ()
    required_capabilities: Tuple[str, ...] = ()
    budget_usd: float = 0.0
    deadline_s: Optional[int] = None
    estimated_tokens: int = 0
    units: int = 1
    max_attempts: int = 1
    now: float = 0.0
    attempt_id: str = ""
    budget_ref: str = "sovereign/engine/budget.py"
    shadow_lane_id: str = ""
    verification_levels: Tuple[VerificationLevel, ...] = (VerificationLevel.OPERATION,)

    def __post_init__(self) -> None:
        if not isinstance(self.node, WorkNode):
            raise AllocationError("an allocation request needs a WorkNode")
        object.__setattr__(self, "offers", tuple(self.offers))
        object.__setattr__(
            self, "required_capabilities", tuple(self.required_capabilities)
        )
        object.__setattr__(self, "verification_levels", tuple(self.verification_levels))
        if self.budget_usd < 0:
            raise AllocationError("an allocation budget cannot be negative")
        if self.estimated_tokens < 0:
            raise AllocationError("an allocation cannot estimate negative tokens")
        if self.units < 1:
            raise AllocationError("an allocation must hold at least one unit")
        if self.max_attempts < 1:
            raise AllocationError("an allocation must allow at least one attempt")


@dataclass(frozen=True)
class Allocation:
    """The decision: what runs, what it may spend, and what it cost to plan."""

    contract: ExecutionContract
    reservation: CapacityReservation
    receipt: EconomicReceipt
    unit_price_usd_per_1k: float = 0.0
    waste_class: str = "reserved"
    shadow_disagreement: str = ""
    reason: str = ""


def estimate_cost_usd(lane: IntelligenceLane, estimated_tokens: int) -> float:
    """What a lane is expected to cost for a workload of this size.

    The estimate is a price times a size, rounded to the micro-dollar. It is
    an estimate and it is labelled as one: the measured cost arrives with the
    ledger row when the attempt is done.
    """
    if estimated_tokens < 0:
        raise AllocationError("cannot estimate a negative token count")
    return round(lane.cost_usd_per_1k * estimated_tokens / 1000.0, 6)


def _order_key(offer: SupplyOffer):
    """The one order every allocation uses.

    The bypass rule comes first: a deterministic lane outranks a model lane
    whatever the model's quality prior says, because a deterministic lane
    costs what it costs and gives the same answer twice. Within a class the
    programme's rule applies -- quality, then cost, then time -- and the
    lane id breaks the last tie so the order is total.
    """
    lane = offer.lane
    return (
        0 if lane.deterministic else 1,
        -lane.quality_prior,
        lane.cost_usd_per_1k,
        lane.latency_p95_ms,
        lane.id,
    )


def _refusal_for(request: AllocationRequest, offer: SupplyOffer) -> str:
    """Why this one offer cannot take the node, or "" when it can.

    One place decides, so the reason the caller reads and the reason the
    refusal carries cannot drift apart.
    """
    lane = offer.lane
    if lane.availability <= 0:
        return "%s: unavailable" % lane.id
    if offer.units_available < request.units:
        return "%s: no capacity" % lane.id
    missing = sorted(
        c for c in request.required_capabilities if c not in offer.capabilities
    )
    if missing:
        return "%s: cannot do %s" % (lane.id, ",".join(missing))
    cost = estimate_cost_usd(lane, request.estimated_tokens)
    if request.budget_usd > 0 and cost > request.budget_usd:
        return "%s: costs %.6f over the budget %.6f" % (
            lane.id,
            cost,
            request.budget_usd,
        )
    if offer.max_usd > 0 and cost > offer.max_usd:
        return "%s: costs %.6f over its own ceiling %.6f" % (
            lane.id,
            cost,
            offer.max_usd,
        )
    return ""


def select_offer(request: AllocationRequest) -> Tuple[SupplyOffer, str]:
    """The lane that runs the node, and the reason it was chosen.

    The reason is returned with the offer because a decision nobody can read
    is a decision nobody can audit: the receipt carries the same words.
    """
    candidates = []
    reasons: List[str] = []
    for offer in request.offers:
        refusal = _refusal_for(request, offer)
        if refusal:
            reasons.append(refusal)
        else:
            candidates.append(offer)
    if not candidates:
        raise AllocationError(
            "no lane can run node %s: %s"
            % (request.node.id, "; ".join(reasons) or "the supply is empty")
        )
    chosen = min(candidates, key=_order_key)
    lane = chosen.lane
    if lane.deterministic:
        reason = (
            "deterministic bypass: %s needs no model and satisfies the contract"
            % lane.id
        )
    else:
        reason = (
            "no deterministic lane satisfied the contract; chose %s on quality, then cost"
            % lane.id
        )
    return chosen, reason


def allocate(request: AllocationRequest) -> Allocation:
    """Turn a request into a contract, a reservation and a receipt.

    The ids are derived, not generated: the same request produces the same
    contract id and the same idempotency key, so a retry of the same work
    cannot become a second execution. The receipt's id carries the moment,
    because a receipt is an event and an event happens once.
    """
    offer, reason = select_offer(request)
    lane = offer.lane
    cost = estimate_cost_usd(lane, request.estimated_tokens)

    fingerprint = {
        "node": request.node.id,
        "lane": lane.id,
        "scope": sorted(request.node.scope),
        "budget_usd": round(request.budget_usd, 6),
        "deadline_s": request.deadline_s,
        "units": request.units,
        "tokens": request.estimated_tokens,
        "capabilities": sorted(request.required_capabilities),
    }
    contract_digest = digest_of(fingerprint)
    contract_id = "ctr-%s" % contract_digest[:16]
    reservation_id = (
        "res-%s" % digest_of({"contract": contract_id, "at": request.now})[:16]
    )
    attempt_id = request.attempt_id or ("att-%s" % contract_digest[16:32])
    receipt_id = "eco-%s" % digest_of({"contract": contract_id, "at": request.now})[:16]

    reservation = CapacityReservation(
        id=reservation_id,
        lane_id=lane.id,
        units=request.units,
        usd=cost,
        budget_ref=request.budget_ref,
        state=ReservationState.HELD,
        window_s=request.deadline_s or 0,
    )

    contract = ExecutionContract(
        id=contract_id,
        node_id=request.node.id,
        lane=lane,
        scope=request.node.scope,
        budget_usd=cost,
        budget_seconds=request.deadline_s or 0,
        verification_levels=request.verification_levels,
        max_attempts=request.max_attempts,
        idempotency_key=contract_digest,
        reservation_id=reservation_id,
        deadline_s=request.deadline_s,
    )

    receipt = EconomicReceipt(
        id=receipt_id,
        attempt_id=attempt_id,
        node_id=request.node.id,
        contract_id=contract_id,
        provider=lane.provider,
        model=lane.model,
        at=request.now,
        cost_usd=None,
        unit_price_usd_per_1k=lane.cost_usd_per_1k,
        waste_class="reserved",
    )

    disagreement = ""
    if request.shadow_lane_id and request.shadow_lane_id != lane.id:
        disagreement = "shadow proposed %s, the deterministic policy chose %s" % (
            request.shadow_lane_id,
            lane.id,
        )

    return Allocation(
        contract=contract,
        reservation=reservation,
        receipt=receipt,
        unit_price_usd_per_1k=lane.cost_usd_per_1k,
        waste_class="reserved",
        shadow_disagreement=disagreement,
        reason=reason,
    )

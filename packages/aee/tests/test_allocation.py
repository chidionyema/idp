"""G4: the allocation policy is deterministic, prefers the bypass, and accounts.

The falsifier this module has to pass is not "the code runs": it is that the
same request cannot produce two different answers. If the policy ever grows a
clock, a random id or a model in the path, the hundred-identical-requests
test fails and the policy is wrong.
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
for _path in (str(HERE.parents[1] / "src"), str(HERE.parents[3])):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from aee.allocation import (  # noqa: E402
    AllocationError,
    AllocationRequest,
    SupplyOffer,
    allocate,
    estimate_cost_usd,
    select_offer,
)
from aee.contracts import IntelligenceLane, WorkNode  # noqa: E402


NODE = WorkNode(id="node-1", title="summarise the incident", scope=("platform/llm",))

DETERMINISTIC = IntelligenceLane(
    id="lane-deterministic",
    provider="estate",
    lane_type="tool",
    deterministic=True,
    cost_usd_per_1k=0.0,
    quality_prior=0.0,
    availability=1.0,
    latency_p95_ms=10,
)

MODEL_CHEAP = IntelligenceLane(
    id="lane-model-cheap",
    provider="groq",
    model="cheap",
    lane_type="model",
    deterministic=False,
    cost_usd_per_1k=0.0001,
    quality_prior=0.6,
    availability=1.0,
    latency_p95_ms=800,
)

MODEL_BEST = IntelligenceLane(
    id="lane-model-best",
    provider="anthropic",
    model="best",
    lane_type="model",
    deterministic=False,
    cost_usd_per_1k=0.003,
    quality_prior=0.9,
    availability=1.0,
    latency_p95_ms=2000,
)

DRAINED = IntelligenceLane(
    id="lane-drained",
    provider="groq",
    model="cheap",
    lane_type="model",
    deterministic=False,
    cost_usd_per_1k=0.0001,
    quality_prior=0.95,
    availability=1.0,
    latency_p95_ms=100,
)


def offer(
    lane: IntelligenceLane, capabilities=("summarise",), units: int = 1
) -> SupplyOffer:
    return SupplyOffer(lane=lane, capabilities=capabilities, units_available=units)


def request(offers=None, **kwargs) -> AllocationRequest:
    base = {
        "node": NODE,
        "offers": tuple(
            offers if offers is not None else (offer(DETERMINISTIC), offer(MODEL_BEST))
        ),
        "required_capabilities": ("summarise",),
        "budget_usd": 1.0,
        "deadline_s": 300,
        "estimated_tokens": 1000,
        "now": 1000.0,
    }
    base.update(kwargs)
    return AllocationRequest(**base)


def test_the_same_request_always_produces_the_same_allocation():
    """The falsifier: a hundred identical requests, a hundred identical answers."""
    allocations = [allocate(request()) for _ in range(100)]
    first = allocations[0]
    for other in allocations[1:]:
        assert other.contract == first.contract
        assert other.reservation == first.reservation
        assert other.receipt == first.receipt
        assert other.reason == first.reason


def test_a_deterministic_lane_is_preferred_over_a_model_lane():
    allocation = allocate(request())
    assert allocation.contract.lane_id == DETERMINISTIC.id
    assert "deterministic bypass" in allocation.reason


def test_the_bypass_does_not_apply_when_the_lane_cannot_do_the_work():
    allocation = allocate(
        request(
            offers=(offer(DETERMINISTIC, capabilities=("format",)), offer(MODEL_BEST))
        )
    )
    assert allocation.contract.lane_id == MODEL_BEST.id
    assert "no deterministic lane satisfied the contract" in allocation.reason


def test_quality_comes_before_price_and_price_comes_before_time():
    allocation = allocate(request(offers=(offer(MODEL_CHEAP), offer(MODEL_BEST))))
    assert allocation.contract.lane_id == MODEL_BEST.id


def test_a_drained_lane_is_skipped_for_one_that_can_take_the_work():
    allocation = allocate(request(offers=(offer(DRAINED, units=0), offer(MODEL_CHEAP))))
    assert allocation.contract.lane_id == MODEL_CHEAP.id


def test_no_lane_that_can_do_the_work_is_a_refusal_with_the_reason():
    with pytest.raises(AllocationError) as caught:
        allocate(request(offers=(offer(DETERMINISTIC, capabilities=("format",)),)))
    assert "cannot do summarise" in str(caught.value)


def test_a_lane_that_costs_more_than_the_budget_is_refused():
    with pytest.raises(AllocationError) as caught:
        allocate(request(budget_usd=0.0005, offers=(offer(MODEL_BEST),)))
    assert "over the budget" in str(caught.value)


def test_an_empty_supply_is_a_refusal_not_a_guess():
    with pytest.raises(AllocationError) as caught:
        allocate(request(offers=()))
    assert "the supply is empty" in str(caught.value)


def test_a_shadow_proposal_never_changes_the_decision_but_is_recorded():
    straight = allocate(request())
    shadowed = allocate(request(shadow_lane_id=MODEL_BEST.id))
    assert shadowed.contract == straight.contract
    assert shadowed.receipt == straight.receipt
    assert "shadow proposed lane-model-best" in shadowed.shadow_disagreement


def test_a_shadow_proposal_that_agrees_is_not_a_disagreement():
    allocation = allocate(request(shadow_lane_id=DETERMINISTIC.id))
    assert allocation.shadow_disagreement == ""


def test_the_receipt_carries_the_unit_price_and_the_waste_class():
    allocation = allocate(request())
    assert allocation.receipt.unit_price_usd_per_1k == DETERMINISTIC.cost_usd_per_1k
    assert allocation.receipt.waste_class == "reserved"
    assert allocation.receipt.cost_usd is None


def test_the_cost_is_unknown_until_the_attempt_is_measured():
    """Unknown is not zero: the receipt says so rather than claiming a free call."""
    receipt = allocate(request()).receipt
    assert receipt.cost_usd is None
    assert receipt.ledger_hash == ""


def test_the_reservation_holds_the_estimate_and_names_the_budget_authority():
    allocation = allocate(request(offers=(offer(MODEL_CHEAP),), estimated_tokens=2000))
    assert allocation.reservation.usd == estimate_cost_usd(MODEL_CHEAP, 2000)
    assert allocation.reservation.budget_ref == "sovereign/engine/budget.py"
    assert allocation.reservation.state.value == "held"
    assert allocation.contract.reservation_id == allocation.reservation.id


def test_the_contract_is_the_same_work_for_a_retry_but_the_receipt_is_a_new_event():
    first = allocate(request(now=1000.0))
    later = allocate(request(now=2000.0))
    assert first.contract.id == later.contract.id
    assert first.contract.idempotency_key == later.contract.idempotency_key
    assert first.receipt.id != later.receipt.id


def test_the_node_scope_and_the_verification_levels_reach_the_contract():
    allocation = allocate(request())
    assert allocation.contract.scope == ("platform/llm",)
    assert [level.value for level in allocation.contract.verification_levels] == [
        "operation"
    ]


def test_the_supply_is_never_mutated_by_an_allocation():
    offers = (offer(DETERMINISTIC), offer(MODEL_BEST))
    before = tuple(repr(o) for o in offers)
    allocate(request(offers=offers))
    assert tuple(repr(o) for o in offers) == before


def test_select_offer_returns_the_offer_and_the_reason():
    chosen, reason = select_offer(request())
    assert chosen.lane.id == DETERMINISTIC.id
    assert reason


def test_a_lane_with_no_availability_is_refused():
    dead = replace(MODEL_CHEAP, availability=0.0)
    with pytest.raises(AllocationError) as caught:
        allocate(request(offers=(offer(dead),)))
    assert "unavailable" in str(caught.value)

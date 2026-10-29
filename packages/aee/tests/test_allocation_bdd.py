"""G4's feature, bound to the real allocation policy.

Each scenario calls packages/aee/src/aee/allocation.py: the same function a
worker would call. A scenario nobody runs is prose (bin/spec-gate), so these
steps drive the library rather than restate it.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when

HERE = Path(__file__).resolve()
for _path in (str(HERE.parents[1] / "src"), str(HERE.parents[3])):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from aee.allocation import (  # noqa: E402
    AllocationError,
    AllocationRequest,
    SupplyOffer,
    allocate,
)
from aee.contracts import IntelligenceLane, WorkNode  # noqa: E402

scenarios("../../../features/assurance/economic-allocation.feature")


def _node() -> WorkNode:
    return WorkNode(
        id="node-1", title="summarise the incident", scope=("platform/llm",)
    )


def _deterministic() -> IntelligenceLane:
    return IntelligenceLane(
        id="lane-deterministic",
        provider="estate",
        lane_type="tool",
        deterministic=True,
        cost_usd_per_1k=0.0,
        latency_p95_ms=10,
    )


def _model() -> IntelligenceLane:
    return IntelligenceLane(
        id="lane-model",
        provider="groq",
        model="cheap",
        lane_type="model",
        deterministic=False,
        cost_usd_per_1k=0.0001,
        quality_prior=0.8,
        latency_p95_ms=800,
    )


@pytest.fixture
def ctx():
    return {}


def _request(offers, **kwargs) -> AllocationRequest:
    base = {
        "node": _node(),
        "offers": offers,
        "required_capabilities": ("summarise",),
        "budget_usd": 1.0,
        "deadline_s": 300,
        "estimated_tokens": 1000,
        "now": 1000.0,
    }
    base.update(kwargs)
    return AllocationRequest(**base)


# ---- given -------------------------------------------------------------


@given("a node that needs summarising")
def _node_given(ctx):
    ctx["node"] = _node()


@given("a supply of one deterministic lane and one model lane")
def _supply_given(ctx):
    ctx["offers"] = (
        SupplyOffer(lane=_deterministic(), capabilities=("summarise",)),
        SupplyOffer(lane=_model(), capabilities=("summarise",)),
    )


@given("a supply of one deterministic lane that cannot summarise")
def _useless_supply_given(ctx):
    ctx["offers"] = (SupplyOffer(lane=_deterministic(), capabilities=("format",)),)


# ---- when --------------------------------------------------------------


@when("the node is allocated one hundred times")
def _allocate_hundred(ctx):
    ctx["allocations"] = [allocate(_request(ctx["offers"])) for _ in range(100)]


@when("the node is allocated")
def _allocate_once(ctx):
    try:
        ctx["allocation"] = allocate(_request(ctx["offers"]))
    except AllocationError as err:
        ctx["refusal"] = err


@when("the node is allocated with the model lane proposed in shadow")
def _allocate_in_shadow(ctx):
    ctx["allocation"] = allocate(_request(ctx["offers"], shadow_lane_id="lane-model"))


# ---- then --------------------------------------------------------------


@then("every allocation is identical")
def _then_identical(ctx):
    allocations = ctx["allocations"]
    first = allocations[0]
    for other in allocations[1:]:
        assert other.contract == first.contract
        assert other.reservation == first.reservation
        assert other.receipt == first.receipt


@then("the contract names the deterministic lane")
def _then_deterministic(ctx):
    assert ctx["allocation"].contract.lane_id == "lane-deterministic"


@then("the reason is the deterministic bypass")
def _then_reason(ctx):
    assert "deterministic bypass" in ctx["allocation"].reason


@then("the contract still names the deterministic lane")
def _then_still_deterministic(ctx):
    assert ctx["allocation"].contract.lane_id == "lane-deterministic"


@then("the disagreement is recorded")
def _then_disagreement(ctx):
    assert "shadow proposed lane-model" in ctx["allocation"].shadow_disagreement


@then("the allocation is refused")
def _then_refused(ctx):
    assert isinstance(ctx.get("refusal"), AllocationError)


@then("the refusal names the lane and what it cannot do")
def _then_refusal_reason(ctx):
    refusal = str(ctx["refusal"])
    assert "lane-deterministic" in refusal
    assert "cannot do summarise" in refusal

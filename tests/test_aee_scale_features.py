"""features/assurance/execution-economics-at-scale.feature, bound to the real AEE library.

A feature that cannot run is prose. Every step here runs against ``packages/aee/src/aee`` --
the same code the estate's admission controller runs -- and nothing is mocked: the lanes are
real lane values, the supply is real supply, and the money lands in the real ``WorkGraph``.

The suites live in the repository's root ``tests/`` tree rather than in ``packages/aee/tests/``
because that is where CI collects them: ``bin/idp-tests-for`` selects a test by grepping
``tests/`` and ``sovereign/tests/`` for the changed paths, and no workflow collects
``packages/``. The precedent is ``tests/test_aei_features.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "packages" / "aee" / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from aee.allocation import SupplyOffer  # noqa: E402
from aee.contracts import (  # noqa: E402
    AcceptanceCriterion,
    IntelligenceLane,
    Objective,
    VerificationLevel,
    WorkNode,
)
from aee.graph import WorkGraph  # noqa: E402
from aee.scale import (  # noqa: E402
    AdmissionOutcome,
    NodeSupply,
    ScalePolicy,
    ScaleScheduler,
)

scenarios("../features/assurance/execution-economics-at-scale.feature")


def _objective() -> Objective:
    return Objective(
        id="obj-scale",
        statement="the estate's work runs at the right scale",
        acceptance=(
            AcceptanceCriterion(
                id="ac-runs",
                description="the admitted work runs and is measured",
                level=VerificationLevel.OPERATION,
            ),
        ),
        authority="founder",
        scope=("packages/aee", "features", "tests"),
    )


def _node(
    node_id: str, scope: tuple[str, ...], depends_on: tuple[str, ...] = ()
) -> WorkNode:
    return WorkNode(
        id=node_id,
        title="the %s work" % node_id,
        scope=scope,
        depends_on=depends_on,
        owner="agent-1",
    )


def _lane(lane_id: str = "lane-a") -> IntelligenceLane:
    return IntelligenceLane(
        id=lane_id,
        provider="estate",
        model="test-model",
        lane_type="model",
        deterministic=False,
        cost_usd_per_1k=0.001,
        quality_prior=0.9,
        availability=1.0,
        latency_p95_ms=100,
    )


def _supply() -> NodeSupply:
    return NodeSupply(
        offers=(
            SupplyOffer(lane=_lane(), capabilities=("summarise",), units_available=1),
        ),
        estimated_tokens=1000,
        required_capabilities=("summarise",),
        budget_usd=1.0,
    )


@pytest.fixture
def world():
    """The state the steps share: the graph, the envelope and what came of it."""
    return {}


# --- the scenarios ------------------------------------------------------------------------------


@given(
    "a graph of two independent nodes and one dependent node", target_fixture="world"
)
def _graph_with_a_dependent(world) -> dict:
    graph = WorkGraph(_objective(), "graph-scale", owner="agent-1")
    graph.add_node(_node("node-a", ("packages/aee/src/aee",)))
    graph.add_node(_node("node-b", ("packages/aee/tests",)))
    graph.add_node(_node("node-c", ("features/assurance",), depends_on=("node-a",)))
    world["graph"] = graph
    return world


@given("a concurrency envelope that holds two at a time", target_fixture="world")
def _envelope_of_two(world) -> dict:
    world["scheduler"] = ScaleScheduler(
        world["graph"], policy=ScalePolicy(max_concurrent=2)
    )
    world["supply"] = {node_id: _supply() for node_id in ("node-a", "node-b", "node-c")}
    return world


@when("the envelope admits the ready work", target_fixture="world")
def _admit(world) -> dict:
    world["results"] = world["scheduler"].admit(world["supply"], now=10.0)
    return world


@then("two nodes are admitted together")
def _two_admitted(world) -> None:
    admitted = [r for r in world["results"] if r.outcome is AdmissionOutcome.ADMITTED]
    assert {r.node_id for r in admitted} == {"node-a", "node-b"}


@then("the dependent node is not admitted")
def _dependent_waits(world) -> None:
    admitted = [r for r in world["results"] if r.outcome is AdmissionOutcome.ADMITTED]
    assert "node-c" not in {r.node_id for r in admitted}
    assert world["graph"].node("node-c").state.value == "pending"


@given("a graph of two nodes whose scopes overlap", target_fixture="world")
def _graph_with_overlap(world) -> dict:
    graph = WorkGraph(_objective(), "graph-scale", owner="agent-1")
    graph.add_node(_node("node-a", ("packages/aee/src/aee",)))
    graph.add_node(_node("node-b", ("packages/aee/src",)))
    world["graph"] = graph
    world["scheduler"] = ScaleScheduler(graph, policy=ScalePolicy(max_concurrent=4))
    world["supply"] = {"node-a": _supply(), "node-b": _supply()}
    return world


@then("one node is admitted")
def _one_admitted(world) -> None:
    admitted = [r for r in world["results"] if r.outcome is AdmissionOutcome.ADMITTED]
    assert len(admitted) == 1


@then("the refusal names the conflicting node and the path")
def _refusal_names_the_conflict(world) -> None:
    refused = [r for r in world["results"] if r.outcome is AdmissionOutcome.REFUSED]
    assert len(refused) == 1
    assert "node-a" in refused[0].reason
    assert "packages/aee/src/aee" in refused[0].reason


@given("an admitted node holding a reservation", target_fixture="world")
def _admitted_node(world) -> dict:
    graph = WorkGraph(_objective(), "graph-scale", owner="agent-1")
    graph.add_node(_node("node-a", ("packages/aee/src/aee",)))
    scheduler = ScaleScheduler(graph, policy=ScalePolicy(max_concurrent=2))
    results = scheduler.admit({"node-a": _supply()}, now=10.0)
    admitted = [r for r in results if r.outcome is AdmissionOutcome.ADMITTED]
    assert len(admitted) == 1
    world["graph"] = graph
    world["scheduler"] = scheduler
    world["admission"] = admitted[0]
    return world


@when("the node is cancelled")
def _cancel(world) -> None:
    world["scheduler"].cancel(
        "node-a", reason="the founder changed their mind", now=11.0
    )


@then("the reservation is released")
def _reservation_released(world) -> None:
    reservation = world["admission"].reservation
    assert world["graph"].reservations[reservation.id].state.value == "released"


@then("no money is committed")
def _no_money_committed(world) -> None:
    assert world["scheduler"].committed_usd() == 0.0
    assert world["scheduler"].held_usd() == 0.0


@given("a concurrency envelope with a budget ceiling", target_fixture="world")
def _envelope_with_a_ceiling(world) -> dict:
    graph = WorkGraph(_objective(), "graph-scale", owner="agent-1")
    graph.add_node(_node("node-a", ("packages/aee/src/aee",)))
    world["graph"] = graph
    world["scheduler"] = ScaleScheduler(
        graph, policy=ScalePolicy(max_concurrent=2, budget_ceiling_usd=0.0005)
    )
    world["supply"] = {"node-a": _supply()}
    return world


@given("a node whose reservation would cross the ceiling", target_fixture="world")
def _node_over_the_ceiling(world) -> dict:
    # The node's own reservation costs 0.001 usd against a ceiling of 0.0005 usd.
    assert world["supply"]["node-a"].offers[0].lane.cost_usd_per_1k == 0.001
    return world


@then("the node is refused")
def _node_refused(world) -> None:
    refused = [r for r in world["results"] if r.outcome is AdmissionOutcome.REFUSED]
    assert len(refused) == 1


@then("the cutoff reason names the ceiling")
def _cutoff_names_the_ceiling(world) -> None:
    reason = world["scheduler"].journal.cutoff_reason
    assert reason
    assert "ceiling" in reason


@given("a node whose work has already been committed", target_fixture="world")
def _committed_work(world) -> dict:
    graph = WorkGraph(_objective(), "graph-scale", owner="agent-1")
    graph.add_node(_node("node-a", ("packages/aee/src/aee",)))
    scheduler = ScaleScheduler(graph, policy=ScalePolicy(max_concurrent=2))
    scheduler.admit({"node-a": _supply()}, now=10.0)
    scheduler.commit("node-a", cost_usd=0.004, ledger_hash="ledger-row-1", now=12.0)

    # The plan is rebuilt from durable state; the journal is what survives.
    rebuilt = WorkGraph(_objective(), "graph-scale", owner="agent-1")
    rebuilt.add_node(_node("node-a", ("packages/aee/src/aee",)))
    world["graph"] = rebuilt
    world["scheduler"] = ScaleScheduler(
        rebuilt, policy=ScalePolicy(max_concurrent=2), journal=scheduler.journal
    )
    world["supply"] = {"node-a": _supply()}
    world["committed_before"] = scheduler.committed_usd()
    return world


@when("the scheduler restarts from its journal and admits the work again")
def _restart_and_admit(world) -> None:
    world["results"] = world["scheduler"].admit(world["supply"], now=20.0)


@then("the node is not admitted again")
def _not_admitted_again(world) -> None:
    admitted = [r for r in world["results"] if r.outcome is AdmissionOutcome.ADMITTED]
    assert not admitted
    assert "no second execution" in world["results"][0].reason


@then("the committed spend is unchanged")
def _committed_spend_unchanged(world) -> None:
    assert world["scheduler"].committed_usd() == world["committed_before"]
    assert world["scheduler"].committed_usd() == pytest.approx(0.004)

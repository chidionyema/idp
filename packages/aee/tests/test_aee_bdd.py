"""The AEE feature, bound to the real library in packages/aee/src/aee.

Each scenario drives the real graph: the same objects the dispatcher and the
workers would use. A scenario nobody runs is prose (bin/spec-gate), so these
steps call the library rather than restating it.
"""

from __future__ import annotations

import pytest
from pytest_bdd import given, scenarios, then, when

from aee.contracts import (
    AcceptanceCriterion,
    ContractError,
    EconomicReceipt,
    ExecutionAttempt,
    ExecutionContract,
    IntelligenceLane,
    NodeState,
    Objective,
    ReservationState,
    Verdict,
    VerificationLevel,
    VerificationReceipt,
    WorkNode,
)
from aee.graph import (
    AcceptanceRequiredError,
    CycleError,
    OwnershipError,
    ScopeError,
    VerificationRequiredError,
    WorkGraph,
)

scenarios("../../../features/assurance/aee.feature")


def _lane():
    return IntelligenceLane(
        id="lane-model", provider="groq", model="llama-3.1-8b", cost_usd_per_1k=0.0002
    )


def _objective(scope=("packages/aee/**",)):
    return Objective(
        id="obj-1",
        statement="prove the thing",
        authority="founder",
        acceptance=(
            AcceptanceCriterion(
                id="acc-1", description="it works", level=VerificationLevel.OPERATION
            ),
        ),
        scope=scope,
    )


def _receipt(node_id, receipt_id, verdict=Verdict.PASS):
    return VerificationReceipt(
        id=receipt_id,
        node_id=node_id,
        attempt_id="attempt-%s" % node_id,
        level=VerificationLevel.OPERATION,
        verdict=verdict,
        evidence="ledger:abc123",
        verifier="judge",
    )


@pytest.fixture
def ctx():
    return {}


# ---- given -------------------------------------------------------------


@given("an objective with one acceptance criterion")
def _objective_given(ctx):
    ctx["objective"] = _objective()


@given("a graph owned by agent-a")
def _graph_given(ctx):
    ctx["graph"] = WorkGraph(ctx["objective"], "graph-1", owner="agent-a")


@given("a graph with one node and no evidence")
def _one_node(ctx):
    ctx["graph"].add_node(WorkNode(id="node-a"))


@given("a graph with one node and a failed verification")
def _one_node_failed(ctx):
    graph = ctx["graph"]
    graph.add_node(WorkNode(id="node-a"))
    graph.record_verification(_receipt("node-a", "ver-a", verdict=Verdict.FAIL))


@given("a graph with two nodes and evidence for the second")
def _two_nodes(ctx):
    graph = ctx["graph"]
    graph.add_node(WorkNode(id="node-a"))
    graph.add_node(WorkNode(id="node-b"))
    graph.record_verification(_receipt("node-b", "ver-b"))


@given("a graph with a parent and a child")
def _parent_child(ctx):
    graph = ctx["graph"]
    graph.add_node(WorkNode(id="node-a"))
    graph.add_node(WorkNode(id="node-b", depends_on=("node-a",)))


@given("the child has a passing verification")
def _child_evidence(ctx):
    ctx["graph"].record_verification(_receipt("node-b", "ver-b"))


@given("both nodes have a passing verification")
def _both_evidence(ctx):
    graph = ctx["graph"]
    graph.record_verification(_receipt("node-a", "ver-a"))
    graph.record_verification(_receipt("node-b", "ver-b"))


@given("a graph with two dependent nodes")
def _dependent_nodes(ctx):
    graph = ctx["graph"]
    graph.add_node(WorkNode(id="node-a"))
    graph.add_node(WorkNode(id="node-b", depends_on=("node-a",)))


@given("a graph with an authorised scope")
def _scoped_graph(ctx):
    ctx["scope"] = ctx["objective"].scope


@given("a graph with one node")
def _single(ctx):
    ctx["graph"].add_node(WorkNode(id="node-a"))


@given("a graph with a reserved node and a dependent")
def _reserved(ctx):
    graph = ctx["graph"]
    graph.add_node(WorkNode(id="node-a"))
    graph.add_node(WorkNode(id="node-b", depends_on=("node-a",)))
    graph.attach_contract(
        ExecutionContract(id="c-a", node_id="node-a", lane=_lane(), budget_usd=1.0)
    )
    graph.reserve("node-a", lane=_lane(), usd=0.5, budget_ref="budget-1")


@given("a graph with a failed node")
def _failed(ctx):
    graph = ctx["graph"]
    graph.add_node(WorkNode(id="node-a"))
    graph.attach_contract(
        ExecutionContract(id="c-a", node_id="node-a", lane=_lane(), max_attempts=2)
    )
    graph.mark_running("node-a", attempt_id="attempt-1")
    graph.record_attempt(
        ExecutionAttempt(
            id="attempt-1",
            contract_id="c-a",
            node_id="node-a",
            lane_id="lane-model",
            outcome="failed",
        )
    )
    graph.fail("node-a", reason="the worker died")


@given("two graphs with the same node")
def _two_graphs(ctx):
    one = WorkGraph(ctx["objective"], "graph-1", owner="agent-a")
    other = WorkGraph(ctx["objective"], "graph-1", owner="agent-a")
    one.add_node(WorkNode(id="node-a"))
    other.add_node(WorkNode(id="node-a"))
    ctx["one"] = one
    ctx["other"] = other


@given("an economic receipt with a known cost and no ledger hash")
def _economic(ctx):
    ctx["receipt_args"] = {
        "id": "econ-1",
        "attempt_id": "attempt-1",
        "node_id": "node-a",
        "contract_id": "c-a",
        "provider": "groq",
        "cost_usd": 0.0031,
    }


# ---- when -------------------------------------------------------------


@when("the node is completed")
def _complete(ctx):
    with pytest.raises((VerificationRequiredError, AcceptanceRequiredError)) as caught:
        ctx["graph"].complete("node-a")
    ctx["error"] = caught.value


@when("the first node is completed")
def _complete_first(ctx):
    with pytest.raises(VerificationRequiredError) as caught:
        ctx["graph"].complete("node-a", verification_ids=["ver-b"])
    ctx["error"] = caught.value


@when("the child is completed")
def _complete_child(ctx):
    with pytest.raises((AcceptanceRequiredError, VerificationRequiredError)) as caught:
        ctx["graph"].complete("node-b", verification_ids=["ver-b"])
    ctx["error"] = caught.value


@when("the parent and then the child are completed")
def _complete_both(ctx):
    graph = ctx["graph"]
    graph.complete("node-a", verification_ids=["ver-a"])
    graph.complete("node-b", verification_ids=["ver-b"])


@when("the plan is changed to close a loop")
def _close_a_loop(ctx):
    graph = ctx["graph"]
    graph.add_node(WorkNode(id="node-c", depends_on=("node-b",)))
    with pytest.raises(CycleError) as caught:
        graph.replan("node-a", ("node-c",))
    ctx["error"] = caught.value


@when("a node outside that scope is added")
def _out_of_scope(ctx):
    with pytest.raises(ScopeError) as caught:
        ctx["graph"].add_node(WorkNode(id="node-x", scope=("platform/llm/config.yaml",)))
    ctx["error"] = caught.value


@when("another agent adds a node")
def _other_agent(ctx):
    with pytest.raises(OwnershipError) as caught:
        ctx["graph"].add_node(WorkNode(id="node-x"), actor="agent-b")
    ctx["error"] = caught.value


@when("the reserved node is cancelled")
def _cancel(ctx):
    ctx["graph"].cancel("node-a", reason="the plan changed")


@when("the node is retried")
def _retry(ctx):
    ctx["graph"].retry("node-a", attempt_id="attempt-2")


# ---- then -------------------------------------------------------------


@then("both nodes are accepted")
def _both_accepted(ctx):
    graph = ctx["graph"]
    assert graph.node("node-a").state is NodeState.ACCEPTED
    assert graph.node("node-b").state is NodeState.ACCEPTED


@then("the completion is refused for want of verification")
def _refused_for_verification(ctx):
    assert isinstance(ctx["error"], VerificationRequiredError)


@then("the completion is refused for want of acceptance")
def _refused_for_acceptance(ctx):
    assert isinstance(ctx["error"], AcceptanceRequiredError)


@then("the replan is refused for a cycle")
def _refused_for_cycle(ctx):
    assert isinstance(ctx["error"], CycleError)


@then("the node is refused for want of scope")
def _refused_for_scope(ctx):
    assert isinstance(ctx["error"], ScopeError)


@then("the mutation is refused for want of ownership")
def _refused_for_ownership(ctx):
    assert isinstance(ctx["error"], OwnershipError)


@then("the reservation is released")
def _released(ctx):
    assert ctx["graph"].reservations["res-node-a-1"].state is ReservationState.RELEASED


@then("the dependent is blocked")
def _blocked(ctx):
    assert ctx["graph"].node("node-b").state is NodeState.BLOCKED


@then("the earlier attempt is still on the record")
def _attempt_kept(ctx):
    assert [a.id for a in ctx["graph"].attempts["node-a"]] == ["attempt-1"]
    assert ctx["graph"].node("node-a").state is NodeState.PENDING


@then("they have the same digest")
def _same_digest(ctx):
    assert ctx["one"].digest() == ctx["other"].digest()


@then("a third node changes the address")
def _changed_digest(ctx):
    before = ctx["one"].digest()
    ctx["one"].add_node(WorkNode(id="node-z"))
    assert ctx["one"].digest() != before


@then("the receipt is refused")
def _receipt_refused(ctx):
    with pytest.raises(ContractError):
        EconomicReceipt(**ctx["receipt_args"])

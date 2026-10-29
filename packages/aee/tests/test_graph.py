"""The graph's invariants, each one proved by the refusal it promises.

Every rule in the specification's invariant list has a test here that shows
it FAILING on a bad graph. A rule that has only been seen permitting has
never been shown to hold.
"""

import pytest

from aee.contracts import (
    AcceptanceCriterion,
    AttemptOutcome,
    ExecutionAttempt,
    ExecutionContract,
    IntelligenceLane,
    MutationOp,
    NodeKind,
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
    ContractViolation,
    CycleError,
    OwnershipError,
    ReservationError,
    ScopeError,
    VerificationRequiredError,
    WorkGraph,
)


def lane(lane_id="lane-model"):
    return IntelligenceLane(
        id=lane_id, provider="groq", model="llama-3.1-8b", cost_usd_per_1k=0.0002
    )


def make_graph(scope=("packages/aee/**",), owner="agent-a"):
    objective = Objective(
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
    return WorkGraph(objective, "graph-1", owner=owner)


def passing(node_id="node-a", receipt_id="ver-a", level=VerificationLevel.OPERATION):
    return VerificationReceipt(
        id=receipt_id,
        node_id=node_id,
        attempt_id="attempt-%s" % node_id,
        level=level,
        verdict=Verdict.PASS,
        evidence="ledger:abc123",
        verifier="judge",
    )


# ---- scope -------------------------------------------------------------


def test_a_node_outside_the_objective_scope_is_refused():
    graph = make_graph()
    with pytest.raises(ScopeError):
        graph.add_node(WorkNode(id="node-x", scope=("platform/llm/config.yaml",)))


def test_a_node_inside_the_objective_scope_is_accepted():
    graph = make_graph()
    node = graph.add_node(WorkNode(id="node-a", scope=("packages/aee/src/aee/graph.py",)))
    assert node.id == "node-a"


def test_a_contract_may_not_authorise_a_path_the_node_does_not_hold():
    graph = make_graph()
    graph.add_node(WorkNode(id="node-a", scope=("packages/aee/src/aee/graph.py",)))
    with pytest.raises(ScopeError):
        graph.attach_contract(
            ExecutionContract(
                id="c-a",
                node_id="node-a",
                lane=lane(),
                scope=("packages/aee/src/aee/other.py",),
            )
        )


# ---- cycles ------------------------------------------------------------


def test_a_dependency_loop_is_refused():
    graph = make_graph()
    graph.add_node(WorkNode(id="node-a"))
    graph.add_node(WorkNode(id="node-b", depends_on=("node-a",)))
    with pytest.raises(CycleError):
        graph.replan("node-a", ("node-b",))


def test_a_replan_that_would_close_a_loop_is_refused():
    graph = make_graph()
    graph.add_node(WorkNode(id="node-a"))
    graph.add_node(WorkNode(id="node-b", depends_on=("node-a",)))
    graph.add_node(WorkNode(id="node-c", depends_on=("node-b",)))
    with pytest.raises(CycleError):
        graph.replan("node-a", ("node-c",))


# ---- verification and acceptance --------------------------------------


def test_a_node_cannot_be_accepted_without_evidence():
    graph = make_graph()
    graph.add_node(WorkNode(id="node-a"))
    with pytest.raises(VerificationRequiredError):
        graph.complete("node-a")


def test_a_failed_verification_does_not_accept_a_node():
    graph = make_graph()
    graph.add_node(WorkNode(id="node-a"))
    graph.record_verification(
        VerificationReceipt(
            id="ver-a",
            node_id="node-a",
            attempt_id="attempt-node-a",
            level=VerificationLevel.OPERATION,
            verdict=Verdict.FAIL,
            evidence="ledger:abc123",
            verifier="judge",
        )
    )
    with pytest.raises(VerificationRequiredError):
        graph.complete("node-a", verification_ids=["ver-a"])


def test_evidence_for_another_node_does_not_accept_this_one():
    graph = make_graph()
    graph.add_node(WorkNode(id="node-a"))
    graph.add_node(WorkNode(id="node-b"))
    graph.record_verification(passing(node_id="node-b", receipt_id="ver-b"))
    with pytest.raises(VerificationRequiredError):
        graph.complete("node-a", verification_ids=["ver-b"])


def test_a_node_whose_parent_is_unaccepted_cannot_complete():
    graph = make_graph()
    graph.add_node(WorkNode(id="node-a"))
    graph.add_node(WorkNode(id="node-b", depends_on=("node-a",)))
    graph.record_verification(passing(node_id="node-b", receipt_id="ver-b"))
    with pytest.raises(AcceptanceRequiredError):
        graph.complete("node-b", verification_ids=["ver-b"])


def test_a_node_with_passing_evidence_and_accepted_parents_is_accepted():
    graph = make_graph()
    graph.add_node(WorkNode(id="node-a"))
    graph.add_node(WorkNode(id="node-b", depends_on=("node-a",)))
    graph.record_verification(passing(node_id="node-a", receipt_id="ver-a"))
    graph.record_verification(passing(node_id="node-b", receipt_id="ver-b"))
    graph.complete("node-a", verification_ids=["ver-a"])
    assert graph.complete("node-b", verification_ids=["ver-b"]).state is NodeState.ACCEPTED


def test_a_contract_can_demand_the_integration_level_too():
    graph = make_graph()
    graph.add_node(WorkNode(id="node-a"))
    graph.attach_contract(
        ExecutionContract(
            id="c-a",
            node_id="node-a",
            lane=lane(),
            verification_levels=(VerificationLevel.OPERATION, VerificationLevel.INTEGRATION),
        )
    )
    graph.record_verification(passing(node_id="node-a", receipt_id="ver-a"))
    with pytest.raises(VerificationRequiredError):
        graph.complete("node-a", verification_ids=["ver-a"])
    graph.record_verification(
        passing(
            node_id="node-a",
            receipt_id="ver-a2",
            level=VerificationLevel.INTEGRATION,
        )
    )
    assert graph.complete("node-a", verification_ids=["ver-a", "ver-a2"]).state is NodeState.ACCEPTED


# ---- ownership ---------------------------------------------------------


def test_a_second_agent_may_not_mutate_a_graph_it_does_not_own():
    graph = make_graph(owner="agent-a")
    with pytest.raises(OwnershipError):
        graph.add_node(WorkNode(id="node-a"), actor="agent-b")


def test_a_handover_moves_the_ownership_and_is_recorded():
    graph = make_graph(owner="agent-a")
    revision = graph.handover("agent-b", actor="agent-a")
    assert revision.summary.endswith("agent-b")
    graph.add_node(WorkNode(id="node-a"), actor="agent-b")
    assert graph.owner == "agent-b"


# ---- no silent loss ---------------------------------------------------


def test_cancelling_a_node_releases_its_reservation_and_blocks_its_dependents():
    graph = make_graph()
    graph.add_node(WorkNode(id="node-a"))
    graph.add_node(WorkNode(id="node-b", depends_on=("node-a",)))
    graph.attach_contract(ExecutionContract(id="c-a", node_id="node-a", lane=lane(), budget_usd=1.0))
    graph.reserve("node-a", lane=lane(), usd=0.5, budget_ref="budget-1")
    graph.cancel("node-a", reason="the plan changed")

    assert graph.reservations["res-node-a-1"].state is ReservationState.RELEASED
    assert graph.node("node-b").state is NodeState.BLOCKED
    assert "cancelled" in graph.node("node-b").reason


def test_a_reservation_over_the_contract_budget_is_refused():
    graph = make_graph()
    graph.add_node(WorkNode(id="node-a"))
    graph.attach_contract(
        ExecutionContract(id="c-a", node_id="node-a", lane=lane(), budget_usd=0.1)
    )
    with pytest.raises(ReservationError):
        graph.reserve("node-a", lane=lane(), usd=1.0, budget_ref="budget-1")


def test_a_reservation_is_never_spent_twice():
    graph = make_graph()
    graph.add_node(WorkNode(id="node-a"))
    graph.reserve("node-a", lane=lane(), usd=0.5, budget_ref="budget-1")
    graph.commit_reservation("res-node-a-1")
    with pytest.raises(ReservationError):
        graph.commit_reservation("res-node-a-1")


# ---- evidence invalidation and attempts -------------------------------


def test_replacing_a_node_invalidates_its_evidence_but_keeps_the_receipt():
    graph = make_graph()
    graph.add_node(WorkNode(id="node-a"))
    graph.record_verification(passing(node_id="node-a", receipt_id="ver-a"))
    graph.mark_running("node-a", attempt_id="attempt-node-a")
    graph.replace("node-a", contract=ExecutionContract(id="c-a2", node_id="node-a", lane=lane()))

    assert graph.node("node-a").verification_ids == ()
    assert graph.node("node-a").state is NodeState.PENDING
    assert "ver-a" in graph.verifications


def test_a_retry_keeps_the_earlier_attempts_and_honours_the_attempt_budget():
    graph = make_graph()
    graph.add_node(WorkNode(id="node-a"))
    graph.attach_contract(
        ExecutionContract(id="c-a", node_id="node-a", lane=lane(), max_attempts=2)
    )
    graph.mark_running("node-a", attempt_id="attempt-1")
    graph.record_attempt(
        ExecutionAttempt(
            id="attempt-1",
            contract_id="c-a",
            node_id="node-a",
            lane_id="lane-model",
            outcome=AttemptOutcome.FAILED,
        )
    )
    graph.fail("node-a", reason="the worker died")
    graph.retry("node-a", attempt_id="attempt-2")

    assert len(graph.attempts["node-a"]) == 1
    assert graph.node("node-a").state is NodeState.PENDING
    assert graph.node("node-a").attempt_id == "attempt-2"

    graph.mark_running("node-a", attempt_id="attempt-2")
    graph.record_attempt(
        ExecutionAttempt(
            id="attempt-2",
            contract_id="c-a",
            node_id="node-a",
            lane_id="lane-model",
            outcome=AttemptOutcome.FAILED,
        )
    )
    graph.fail("node-a", reason="the worker died again")
    with pytest.raises(ContractViolation):
        graph.retry("node-a", attempt_id="attempt-3")


# ---- the revision chain ----------------------------------------------


def test_the_revisions_chain_and_the_digest_follows_the_state():
    graph = make_graph()
    graph.add_node(WorkNode(id="node-a"))
    graph.add_node(WorkNode(id="node-b", depends_on=("node-a",)))

    numbers = [r.number for r in graph.revisions]
    assert numbers == [1, 2, 3]
    assert graph.revisions[-1].parent_digest == graph.revisions[-2].digest
    assert graph.revisions[-1].op is MutationOp.ADD


def test_the_same_graph_state_has_the_same_address():
    one = make_graph()
    one.add_node(WorkNode(id="node-a"))
    other = make_graph()
    other.add_node(WorkNode(id="node-a"))
    assert one.digest() == other.digest()

    other.add_node(WorkNode(id="node-b"))
    assert one.digest() != other.digest()


def test_a_revision_records_the_state_of_every_node():
    graph = make_graph()
    graph.add_node(WorkNode(id="node-a"))
    graph.add_node(WorkNode(id="node-b"))
    assert graph.revisions[-1].node_states == (("node-a", "pending"), ("node-b", "pending"))


# ---- the plan's own mutations -----------------------------------------


def test_ready_nodes_are_the_ones_whose_parents_are_accepted():
    graph = make_graph()
    graph.add_node(WorkNode(id="node-a"))
    graph.add_node(WorkNode(id="node-b", depends_on=("node-a",)))
    assert [n.id for n in graph.ready_nodes()] == ["node-a"]

    graph.record_verification(passing(node_id="node-a", receipt_id="ver-a"))
    graph.complete("node-a", verification_ids=["ver-a"])
    assert [n.id for n in graph.ready_nodes()] == ["node-b"]


def test_splitting_a_node_replaces_it_with_its_parts():
    graph = make_graph()
    graph.add_node(WorkNode(id="node-a", scope=("packages/aee/**",)))
    created = graph.split(
        "node-a",
        [
            WorkNode(id="node-a-1", scope=("packages/aee/**",)),
            WorkNode(id="node-a-2", scope=("packages/aee/**",)),
        ],
    )
    assert [n.id for n in created] == ["node-a-1", "node-a-2"]
    assert graph.node("node-a").state is NodeState.REPLACED


def test_spawning_adds_work_that_depends_on_the_parent():
    graph = make_graph()
    graph.add_node(WorkNode(id="node-a"))
    spawned = graph.spawn("node-a", WorkNode(id="node-b"))
    assert spawned.depends_on == ("node-a",)


def test_merging_combines_the_dependencies_of_the_nodes_it_replaces():
    graph = make_graph()
    graph.add_node(WorkNode(id="node-a"))
    graph.add_node(WorkNode(id="node-b"))
    graph.add_node(WorkNode(id="node-c", depends_on=("node-a", "node-b")))
    merged = graph.merge(["node-a", "node-b"], WorkNode(id="node-merged"))
    assert merged.depends_on == ()
    assert graph.node("node-a").state is NodeState.REPLACED
    assert graph.node("node-c").depends_on == ("node-a", "node-b")


def test_joining_creates_a_barrier_over_the_nodes():
    graph = make_graph()
    graph.add_node(WorkNode(id="node-a"))
    graph.add_node(WorkNode(id="node-b"))
    barrier = graph.join(["node-a", "node-b"])
    assert barrier.kind is NodeKind.BARRIER
    assert set(barrier.depends_on) == {"node-a", "node-b"}


def test_integrating_a_node_requires_passing_evidence():
    graph = make_graph()
    graph.add_node(WorkNode(id="node-a"))
    graph.add_node(WorkNode(id="node-b", depends_on=("node-a",)))
    with pytest.raises(VerificationRequiredError):
        graph.integrate("node-a", "node-b")

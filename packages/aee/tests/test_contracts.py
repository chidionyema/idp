"""The contracts refuse invalid shapes at construction.

A contract that can be built wrong is a contract that can reach a worker
wrong, so every rule here is a refusal with a name.
"""

import pytest

from aee.contracts import (
    AcceptanceCriterion,
    CapacityReservation,
    ContractError,
    Correlation,
    EconomicReceipt,
    ExecutionContract,
    IntelligenceLane,
    NodeState,
    Objective,
    Verdict,
    VerificationLevel,
    VerificationReceipt,
    WorkNode,
)


def lane(lane_id="lane-model"):
    return IntelligenceLane(id=lane_id, provider="groq", model="llama-3.1-8b", cost_usd_per_1k=0.0002)


def criterion():
    return AcceptanceCriterion(
        id="acc-1", description="the thing is proved", level=VerificationLevel.OPERATION
    )


def test_an_identifier_must_be_an_identifier():
    with pytest.raises(ContractError):
        WorkNode(id="Not An Id")


def test_a_node_may_not_depend_on_itself():
    with pytest.raises(ContractError):
        WorkNode(id="node-a", depends_on=("node-a",))


def test_a_node_may_not_list_a_dependency_twice():
    with pytest.raises(ContractError):
        WorkNode(id="node-a", depends_on=("node-b", "node-b"))


def test_an_objective_needs_acceptance_criteria():
    with pytest.raises(ContractError):
        Objective(id="obj-1", statement="do the thing", authority="founder", acceptance=())


def test_an_objective_may_be_read_for_its_criteria():
    objective = Objective(
        id="obj-1", statement="do the thing", authority="founder", acceptance=(criterion(),)
    )
    assert objective.criterion("acc-1").level is VerificationLevel.OPERATION


def test_correlation_carries_the_five_identifiers():
    correlation = Correlation(
        objective_id="obj-1",
        graph_id="graph-1",
        node_id="node-1",
        attempt_id="attempt-1",
        contract_id="contract-1",
    )
    assert set(correlation.as_dict()) == {
        "objective_id",
        "graph_id",
        "node_id",
        "attempt_id",
        "contract_id",
    }


def test_correlation_refuses_a_missing_identifier():
    with pytest.raises(ContractError):
        Correlation(
            objective_id="obj-1",
            graph_id="graph-1",
            node_id="node-1",
            attempt_id="",
            contract_id="contract-1",
        )


def test_a_known_cost_must_name_the_ledger_row_it_derives_from():
    """One economics spine: the receipt points at the signed ledger row."""
    with pytest.raises(ContractError):
        EconomicReceipt(
            id="econ-1",
            attempt_id="attempt-1",
            node_id="node-1",
            contract_id="contract-1",
            provider="groq",
            cost_usd=0.0031,
        )


def test_a_known_cost_with_its_ledger_hash_is_accepted():
    receipt = EconomicReceipt(
        id="econ-1",
        attempt_id="attempt-1",
        node_id="node-1",
        contract_id="contract-1",
        provider="groq",
        cost_usd=0.0031,
        ledger_hash="a" * 64,
    )
    assert receipt.cost_known


def test_an_unknown_cost_is_unknown_and_not_zero():
    receipt = EconomicReceipt(
        id="econ-2",
        attempt_id="attempt-1",
        node_id="node-1",
        contract_id="contract-1",
        provider="groq",
    )
    assert not receipt.cost_known
    assert receipt.cost_usd is None


def test_a_verification_without_evidence_cannot_be_made():
    with pytest.raises(ContractError):
        VerificationReceipt(
            id="ver-1",
            node_id="node-1",
            attempt_id="attempt-1",
            level=VerificationLevel.OPERATION,
            verdict=Verdict.PASS,
            evidence="",
            verifier="judge",
        )


def test_a_contract_needs_at_least_one_attempt_and_one_level():
    with pytest.raises(ContractError):
        ExecutionContract(id="c-1", node_id="node-1", lane=lane(), max_attempts=0)
    with pytest.raises(ContractError):
        ExecutionContract(
            id="c-2", node_id="node-1", lane=lane(), verification_levels=()
        )


def test_a_reservation_holds_something_and_names_its_budget():
    with pytest.raises(ContractError):
        CapacityReservation(id="res-1", lane_id="lane-model", units=0, budget_ref="budget-1")
    with pytest.raises(ContractError):
        CapacityReservation(id="res-2", lane_id="lane-model", units=1, budget_ref="")
    held = CapacityReservation(
        id="res-3", lane_id="lane-model", units=1, usd=0.5, budget_ref="budget-1"
    )
    assert held.state.value == "held"


def test_a_node_starts_pending_and_can_be_read():
    node = WorkNode(id="node-1", title="build the thing")
    assert node.state is NodeState.PENDING
    assert not node.depends("node-2")

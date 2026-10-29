"""G6: independent verification -- the rules, each one proved by the refusal.

The subject is the seam between the estate's verification engine and the AEE's
work graph: an NSVEE pipeline report becomes a VerificationReceipt, and the
agent that did the work cannot sign its own objective acceptance.

Every rule below has a test that shows it FAILING on a bad input. A rule that
has only ever been seen permitting has never been shown to hold.
"""

import pytest

from aee.contracts import (
    AcceptanceCriterion,
    ContractError,
    Objective,
    Verdict,
    VerificationLevel,
    VerificationReceipt,
    WorkNode,
)
from aee.graph import (
    IndependenceRequiredError,
    VerificationRequiredError,
    WorkGraph,
)
from aee.verification import (
    NSVEE_STATUSES,
    level_for_tier,
    receipt_for,
    receipt_from_nsvee,
    report_digest,
    verdict_for_status,
)

OWNER = "pi-aee-research"


def report(status="VERIFIED", **extra):
    payload = {
        "status": status,
        "attempts": 1,
        "events": [{"tier": "tier3.verify", "ok": status == "VERIFIED"}],
    }
    payload.update(extra)
    return payload


def make_graph(owner=OWNER):
    objective = Objective(
        id="obj-1",
        statement="prove the work independently",
        authority="founder",
        acceptance=(
            AcceptanceCriterion(
                id="acc-1", description="it works", level=VerificationLevel.OPERATION
            ),
        ),
        scope=("packages/aee/**",),
    )
    return WorkGraph(objective, "graph-1", owner=owner)


def add_node(graph, node_id="node-a", owner=OWNER):
    return graph.add_node(
        WorkNode(id=node_id, scope=("packages/aee/src/aee/graph.py",), owner=owner)
    )


# ---- the status to verdict mapping --------------------------------------


@pytest.mark.parametrize(
    "status,expected",
    [
        ("VERIFIED", Verdict.PASS),
        ("EXHAUSTED", Verdict.FAIL),
        ("FORMALIZATION_ERROR", Verdict.FAIL),
        ("SANDBOX_DEGRADED", Verdict.INCONCLUSIVE),
        ("HUMAN_INPUT_REQUIRED", Verdict.INCONCLUSIVE),
    ],
)
def test_each_known_status_maps_to_its_verdict(status, expected):
    assert verdict_for_status(status) is expected


def test_an_unknown_status_is_inconclusive_and_never_a_pass():
    assert verdict_for_status("SOMETHING_NEW") is Verdict.INCONCLUSIVE
    assert verdict_for_status("") is Verdict.INCONCLUSIVE
    assert verdict_for_status(None) is Verdict.INCONCLUSIVE


def test_the_status_is_read_case_insensitively():
    assert verdict_for_status("verified") is Verdict.PASS


def test_every_status_nsvee_documents_is_known_to_the_mapping():
    assert set(NSVEE_STATUSES) == {
        "VERIFIED",
        "HUMAN_INPUT_REQUIRED",
        "EXHAUSTED",
        "SANDBOX_DEGRADED",
        "FORMALIZATION_ERROR",
    }


# ---- which tier can testify --------------------------------------------


def test_only_tier_three_can_attest_the_operation():
    assert level_for_tier("tier3") is VerificationLevel.OPERATION
    assert level_for_tier("tier3.verify") is VerificationLevel.OPERATION


def test_the_other_tiers_can_attest_nothing():
    for tier in ("tier1", "tier1.formalize.done", "tier2", "tier4"):
        assert level_for_tier(tier) is None


def test_an_unknown_tier_can_attest_nothing():
    assert level_for_tier("tier9") is None
    assert level_for_tier("") is None


# ---- the receipt --------------------------------------------------------


def test_a_verified_report_becomes_a_passing_receipt():
    receipt = receipt_from_nsvee(
        node_id="node-a", attempt_id="attempt-a", report=report("VERIFIED")
    )
    assert receipt.verdict is Verdict.PASS
    assert receipt.level is VerificationLevel.OPERATION
    assert receipt.verifier == "nsvee"
    assert receipt.evidence.startswith("nsvee-report:")


def test_the_evidence_points_at_the_exact_report():
    payload = report("VERIFIED")
    receipt = receipt_from_nsvee(
        node_id="node-a", attempt_id="attempt-a", report=payload
    )
    assert receipt.evidence == "nsvee-report:%s" % report_digest(payload)


def test_the_receipt_id_is_derived_so_a_replay_is_the_same_receipt():
    first = receipt_from_nsvee(
        node_id="node-a", attempt_id="attempt-a", report=report()
    )
    second = receipt_from_nsvee(
        node_id="node-a", attempt_id="attempt-a", report=report()
    )
    assert first.id == second.id


def test_a_different_report_is_a_different_receipt():
    first = receipt_from_nsvee(
        node_id="node-a", attempt_id="attempt-a", report=report()
    )
    second = receipt_from_nsvee(
        node_id="node-a", attempt_id="attempt-a", report=report("EXHAUSTED")
    )
    assert first.id != second.id


def test_a_degraded_report_is_inconclusive_not_a_failure():
    receipt = receipt_from_nsvee(
        node_id="node-a", attempt_id="attempt-a", report=report("SANDBOX_DEGRADED")
    )
    assert receipt.verdict is Verdict.INCONCLUSIVE


def test_a_report_that_is_not_a_mapping_is_refused():
    with pytest.raises(ContractError):
        receipt_from_nsvee(node_id="node-a", attempt_id="attempt-a", report=["nope"])


def test_a_report_that_cannot_be_evidence_is_refused():
    with pytest.raises(ContractError):
        receipt_from_nsvee(
            node_id="node-a",
            attempt_id="attempt-a",
            report={"status": "VERIFIED", "x": object()},
        )


def test_a_receipt_can_be_built_for_any_level_by_hand():
    receipt = receipt_for(
        node_id="node-a",
        attempt_id="attempt-a",
        level=VerificationLevel.OBJECTIVE,
        verdict=Verdict.PASS,
        evidence="ledger:abc123",
        verifier="pi-aee-ops",
    )
    assert receipt.level is VerificationLevel.OBJECTIVE
    assert receipt.id.startswith("ver-")


# ---- independence -------------------------------------------------------


def test_the_agent_that_did_the_work_cannot_sign_its_own_objective_acceptance():
    graph = make_graph()
    add_node(graph)
    receipt = VerificationReceipt(
        id="ver-own",
        node_id="node-a",
        attempt_id="attempt-a",
        level=VerificationLevel.OBJECTIVE,
        verdict=Verdict.PASS,
        evidence="ledger:abc123",
        verifier=OWNER,
    )
    with pytest.raises(IndependenceRequiredError) as caught:
        graph.record_verification(receipt)
    assert "independent" in str(caught.value)
    assert receipt.id not in graph.verifications


def test_another_agent_may_sign_the_objective_acceptance():
    graph = make_graph()
    add_node(graph)
    receipt = VerificationReceipt(
        id="ver-other",
        node_id="node-a",
        attempt_id="attempt-a",
        level=VerificationLevel.OBJECTIVE,
        verdict=Verdict.PASS,
        evidence="ledger:abc123",
        verifier="pi-aee-ops",
    )
    assert graph.record_verification(receipt).id == "ver-other"
    assert "ver-other" in graph.verifications


def test_the_rule_is_about_the_objective_level_only():
    graph = make_graph()
    add_node(graph)
    receipt = VerificationReceipt(
        id="ver-op",
        node_id="node-a",
        attempt_id="attempt-a",
        level=VerificationLevel.OPERATION,
        verdict=Verdict.PASS,
        evidence="nsvee-report:abc",
        verifier=OWNER,
    )
    assert graph.record_verification(receipt).id == "ver-op"


def test_a_node_with_no_owner_has_nobody_to_be_independent_of():
    graph = make_graph()
    add_node(graph, owner="")
    receipt = VerificationReceipt(
        id="ver-unowned",
        node_id="node-a",
        attempt_id="attempt-a",
        level=VerificationLevel.OBJECTIVE,
        verdict=Verdict.PASS,
        evidence="ledger:abc123",
        verifier="pi-aee-research",
    )
    assert graph.record_verification(receipt).id == "ver-unowned"


def test_an_inconclusive_receipt_does_not_accept_a_node():
    graph = make_graph()
    add_node(graph)
    receipt = receipt_from_nsvee(
        node_id="node-a", attempt_id="attempt-a", report=report("SANDBOX_DEGRADED")
    )
    graph.record_verification(receipt)
    with pytest.raises(VerificationRequiredError):
        graph.complete("node-a", verification_ids=(receipt.id,))
    assert graph.node("node-a").state.value != "accepted"

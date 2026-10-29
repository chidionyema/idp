"""G6's feature, bound to the real verification seam.

Each scenario calls packages/aee/src/aee/verification.py and
packages/aee/src/aee/graph.py: the same functions a worker would call. A
scenario nobody runs is prose (bin/spec-gate), so these steps drive the
library rather than restate it.
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

from aee.contracts import (  # noqa: E402
    AcceptanceCriterion,
    ExecutionContract,
    IntelligenceLane,
    Objective,
    VerificationLevel,
    VerificationReceipt,
    WorkNode,
)
from aee.graph import (  # noqa: E402
    IndependenceRequiredError,
    VerificationRequiredError,
    WorkGraph,
)
from aee.verification import receipt_from_nsvee  # noqa: E402

scenarios("../../../features/assurance/independent-verification.feature")

OWNER = "pi-aee-research"


@pytest.fixture
def ctx():
    return {}


def _graph() -> WorkGraph:
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
    graph = WorkGraph(objective, "graph-1", owner=OWNER)
    graph.add_node(
        WorkNode(
            id="node-a",
            scope=("packages/aee/src/aee/graph.py",),
            owner=OWNER,
        )
    )
    # The node's contract asks for the objective level: the work is only
    # accepted when someone other than its owner says the objective was met.
    graph.attach_contract(
        ExecutionContract(
            id="contract-a",
            node_id="node-a",
            lane=IntelligenceLane(
                id="lane-model", provider="groq", model="cheap", cost_usd_per_1k=0.0001
            ),
            scope=("packages/aee/src/aee/graph.py",),
            verification_levels=(VerificationLevel.OBJECTIVE,),
        )
    )
    return graph


def _report(status: str) -> dict:
    return {
        "status": status,
        "attempts": 1,
        "events": [{"tier": "tier3.verify"}],
    }


# ---- given -------------------------------------------------------------


@given('a node owned by "pi-aee-research"')
def _node_given(ctx):
    ctx["graph"] = _graph()


@given('an NSVEE report whose status is "VERIFIED"')
def _verified_report(ctx):
    ctx["report"] = _report("VERIFIED")


@given('an NSVEE report whose status is "SANDBOX_DEGRADED"')
def _degraded_report(ctx):
    ctx["report"] = _report("SANDBOX_DEGRADED")


@given('an objective-level receipt signed by "pi-aee-research"')
def _own_objective_receipt(ctx):
    ctx["receipt"] = VerificationReceipt(
        id="ver-own",
        node_id="node-a",
        attempt_id="attempt-a",
        level=VerificationLevel.OBJECTIVE,
        verdict="pass",
        evidence="ledger:abc123",
        verifier=OWNER,
    )


@given('an objective-level receipt signed by "pi-aee-ops"')
def _other_objective_receipt(ctx):
    ctx["receipt"] = VerificationReceipt(
        id="ver-other",
        node_id="node-a",
        attempt_id="attempt-a",
        level=VerificationLevel.OBJECTIVE,
        verdict="pass",
        evidence="ledger:abc123",
        verifier="pi-aee-ops",
    )


# ---- when --------------------------------------------------------------


@when("the report is turned into a verification receipt")
def _turn_into_receipt(ctx):
    ctx["receipt"] = receipt_from_nsvee(
        node_id="node-a",
        attempt_id="attempt-a",
        report=ctx["report"],
    )


@when('an objective-level receipt signed by "pi-aee-research" is recorded')
def _record_own_receipt(ctx):
    receipt = ctx.get("receipt") or VerificationReceipt(
        id="ver-own",
        node_id="node-a",
        attempt_id="attempt-a",
        level=VerificationLevel.OBJECTIVE,
        verdict="pass",
        evidence="ledger:abc123",
        verifier=OWNER,
    )
    ctx["receipt"] = receipt
    try:
        ctx["graph"].record_verification(receipt)
    except IndependenceRequiredError as err:
        ctx["refusal"] = err


@when("the receipt is recorded")
def _record_receipt(ctx):
    ctx["recorded"] = ctx["graph"].record_verification(ctx["receipt"])


# ---- then --------------------------------------------------------------


@then('the receipt\'s verdict is "pass"')
def _then_pass(ctx):
    assert ctx["receipt"].verdict.value == "pass"


@then('the receipt\'s verdict is "inconclusive"')
def _then_inconclusive(ctx):
    assert ctx["receipt"].verdict.value == "inconclusive"


@then("the receipt's evidence points at the report")
def _then_evidence(ctx):
    assert ctx["receipt"].evidence.startswith("nsvee-report:")


@then('the receipt\'s verifier is "nsvee"')
def _then_verifier(ctx):
    assert ctx["receipt"].verifier == "nsvee"


@then("the node is not accepted by that receipt")
def _then_not_accepted(ctx):
    graph = ctx["graph"]
    graph.record_verification(ctx["receipt"])
    with pytest.raises(VerificationRequiredError):
        graph.complete("node-a", verification_ids=(ctx["receipt"].id,))
    assert graph.node("node-a").state.value != "accepted"


@then("the recording is refused")
def _then_refused(ctx):
    assert isinstance(ctx.get("refusal"), IndependenceRequiredError)


@then("the refusal says the acceptance must be independent")
def _then_refusal_reason(ctx):
    assert "independent" in str(ctx["refusal"])


@then("the receipt is in the graph")
def _then_in_graph(ctx):
    assert ctx["recorded"].id in ctx["graph"].verifications


@then("the node can be accepted with it")
def _then_can_accept(ctx):
    graph = ctx["graph"]
    accepted = graph.complete("node-a", verification_ids=(ctx["recorded"].id,))
    assert accepted.state.value == "accepted"

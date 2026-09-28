"""UX-01 (idp#3525 CP9, spec section 10). ACCEPT, verbatim: "client-side integration test
issuing identical requests across 5 different config cells receives schema-identical responses;
only the Langfuse trace differs." METHOD: contract test.

Uses the real cells from platform/llm/routing-matrix.yaml (4, per ROUTE-02's own >= 4 floor)
plus one more cell built the same way test_routing_matrix.py's own
test_dispatch_cell_needs_no_code_change_for_a_new_cell builds its "brand new cell" -- a plain
dict of fields dispatch_cell has never seen -- to reach the ACCEPT line's own "5 different
config cells" without editing the production matrix file for a test's sake.
"""

from __future__ import annotations

import json

import pytest

from sovereign.engine import routing_matrix
from sovereign.engine.response_contract import RESPONSE_KEYS, build_response


def _five_cells() -> list[dict]:
    matrix = routing_matrix.load_matrix()
    cells = list(routing_matrix.active_cells(matrix))
    assert len(cells) >= 4
    fifth = {
        "config_id": "ux01-synthetic-fifth-cell",
        "resource_tier": "rung3_gpu_burst",
        "candidate_volume": 5,
        "selection_method": "multi_verifier",
        "escalation_pattern": "hybrid",
        "filter_depth": "off",
        "enabled": True,
    }
    return cells[:4] + [fifth]


def test_identical_request_across_5_config_cells_gets_schema_identical_responses() -> (
    None
):
    cells = _five_cells()
    assert len(cells) == 5
    same_answer = {
        "result": "42"
    }  # the requester's own answer content, held fixed across cells

    envelopes = [build_response(cell, same_answer) for cell in cells]
    shapes = {frozenset(env.as_dict()) for env in envelopes}
    assert shapes == {RESPONSE_KEYS}, (
        "response shape differed across config cells -- UX-01 requires one shape regardless "
        "of which cell served the request"
    )
    bodies = {json.dumps(env.as_dict(), sort_keys=True) for env in envelopes}
    assert len(bodies) == 1, (
        "response body differed across cells with an identical answer"
    )


def test_response_body_never_carries_the_cells_own_config_fields() -> None:
    """Only the trace (ORCH-03's config_id tag) shows which cell ran -- the response body
    itself must never leak resource_tier, selection_method, escalation_pattern or config_id."""
    for cell in _five_cells():
        body = build_response(cell, "some answer").as_dict()
        for leaking_field in (
            "resource_tier",
            "selection_method",
            "escalation_pattern",
            "config_id",
        ):
            assert leaking_field not in body


def test_an_unrecognized_cell_raises_before_any_envelope_is_built() -> None:
    bad_cell = {
        "config_id": "bad",
        "selection_method": "no-such-method",
        "escalation_pattern": "route",
    }
    with pytest.raises(routing_matrix.RoutingMatrixError):
        build_response(bad_cell, "answer")

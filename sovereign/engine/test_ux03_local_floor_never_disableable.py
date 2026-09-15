"""UX-03 (idp#3525 CP9, spec section 10). ACCEPT, verbatim: "attempted CFG-01 write disabling
all lanes including the local floor is rejected at the schema layer, not the runtime layer --
the write never lands." METHOD: schema validation test.
"""

from __future__ import annotations

import copy

import pytest

from sovereign.engine import routing_matrix


def _real_matrix() -> dict:
    return copy.deepcopy(routing_matrix.load_matrix())


def test_the_real_matrix_on_disk_already_satisfies_ux03() -> None:
    routing_matrix.assert_lanes_reachable(_real_matrix())


def test_disabling_every_cell_is_rejected_at_schema_layer() -> None:
    matrix = _real_matrix()
    for row in matrix["cells"]:
        row["enabled"] = False
    with pytest.raises(routing_matrix.RoutingMatrixError, match="zero enabled lanes"):
        routing_matrix.assert_lanes_reachable(matrix)
    with pytest.raises(routing_matrix.RoutingMatrixError):
        routing_matrix.validate_schema(matrix)


def test_disabling_only_the_local_floor_cell_is_rejected_even_with_other_lanes_enabled() -> (
    None
):
    """The always-on local tiny model is never a togglable field -- it is the floor, not one
    more cell a config edit may switch off, even when every other lane stays enabled."""
    matrix = _real_matrix()
    floor_rows = [
        row
        for row in matrix["cells"]
        if row["resource_tier"] == routing_matrix.LOCAL_FLOOR_TIER
    ]
    assert floor_rows, "fixture drifted: no local-floor cell to disable in this test"
    for row in floor_rows:
        row["enabled"] = False
    with pytest.raises(routing_matrix.RoutingMatrixError, match="local floor"):
        routing_matrix.assert_lanes_reachable(matrix)


def test_a_matrix_with_no_local_floor_cell_at_all_is_rejected() -> None:
    matrix = _real_matrix()
    matrix["cells"] = [
        row
        for row in matrix["cells"]
        if row["resource_tier"] != routing_matrix.LOCAL_FLOOR_TIER
    ]
    assert matrix["cells"], "fixture drifted: removed every cell, not just the floor"
    with pytest.raises(
        routing_matrix.RoutingMatrixError, match=routing_matrix.LOCAL_FLOOR_TIER
    ):
        routing_matrix.assert_lanes_reachable(matrix)


def test_a_write_that_passes_ux03_but_fails_another_schema_rule_still_never_lands() -> (
    None
):
    """assert_lanes_reachable alone is not the whole gate -- validate_schema calls it last, so
    a write already invalid for another reason (e.g. an unknown selection_method) is rejected
    by validate_schema even though it would pass assert_lanes_reachable on its own."""
    matrix = _real_matrix()
    matrix["cells"][0]["selection_method"] = "not-a-real-method"
    routing_matrix.assert_lanes_reachable(matrix)  # lanes are fine on their own
    with pytest.raises(routing_matrix.RoutingMatrixError):
        routing_matrix.validate_schema(matrix)  # the write as a whole still never lands

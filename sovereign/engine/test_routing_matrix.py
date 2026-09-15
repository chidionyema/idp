"""Tests for sovereign/engine/routing_matrix.py (idp#3525 CP3, ROUTE-02/ROUTE-05).

ROUTE-02's ACCEPT, verbatim: "matrix run: same 50-task set executed against >= 4 config cells;
results queryable by config_id in Langfuse; no code change between cells; toggling a cell off
mid-run reroutes new requests within one poll interval." ROUTE-05's ACCEPT: "gap recorded; axis
present and toggleable in config schema even when disabled."
"""

from __future__ import annotations

import pytest
import yaml

from sovereign.engine import routing_matrix


def test_real_matrix_has_at_least_four_cells() -> None:
    matrix = routing_matrix.load_matrix()
    assert len(matrix["cells"]) >= 4
    routing_matrix.validate_schema(matrix)


def test_every_real_cell_has_a_distinct_config_id() -> None:
    matrix = routing_matrix.load_matrix()
    ids = [row["config_id"] for row in matrix["cells"]]
    assert len(ids) == len(set(ids))


def test_filter_depth_axis_present_toggleable_and_default_off() -> None:
    matrix = routing_matrix.load_matrix()
    routing_matrix.validate_schema(matrix)
    assert matrix["axes"]["filter_depth"]["enabled"] is False
    assert "gap" in matrix["axes"]["filter_depth"]


def test_filter_depth_enabled_by_default_fails_schema_review() -> None:
    matrix = routing_matrix.load_matrix()
    matrix["axes"]["filter_depth"]["enabled"] = True
    with pytest.raises(routing_matrix.RoutingMatrixError, match="filter_depth"):
        routing_matrix.validate_schema(matrix)


def test_dispatch_cell_needs_no_code_change_for_a_new_cell() -> None:
    """A cell this module has never seen still dispatches, because dispatch_cell looks up
    fields, not config_id -- the concrete proof that a new cell is a config edit only."""
    matrix = routing_matrix.load_matrix()
    for row in matrix["cells"]:
        tag = routing_matrix.dispatch_cell(row)
        assert tag == f"{row['selection_method']}/{row['escalation_pattern']}"

    brand_new_cell = {
        "config_id": "not-in-the-yaml-yet",
        "selection_method": "multi_verifier",
        "escalation_pattern": "hybrid",
    }
    assert routing_matrix.dispatch_cell(brand_new_cell) == "multi_verifier/hybrid"


def test_dispatch_cell_refuses_a_value_off_no_known_axis() -> None:
    with pytest.raises(routing_matrix.RoutingMatrixError):
        routing_matrix.dispatch_cell(
            {"selection_method": "coinflip", "escalation_pattern": "route"}
        )


def test_active_cells_excludes_a_disabled_cell() -> None:
    matrix = routing_matrix.load_matrix()
    matrix["cells"][0]["enabled"] = False
    active = routing_matrix.active_cells(matrix)
    assert matrix["cells"][0]["config_id"] not in {c["config_id"] for c in active}
    assert len(active) == len(matrix["cells"]) - 1


def test_toggling_a_cell_off_reroutes_only_after_one_poll_interval(tmp_path) -> None:
    matrix_path = tmp_path / "routing-matrix.yaml"
    matrix_path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "axes": {"filter_depth": {"enabled": False}},
                "cells": [{"config_id": "cell-a", "enabled": True}],
            }
        )
    )
    ticks = iter([0.0, 1.0, 2.0, 10.0, 10.5])  # poll_interval_s=5.0
    watcher = routing_matrix.MatrixWatcher(
        path=matrix_path, poll_interval_s=5.0, clock=lambda: next(ticks)
    )

    assert watcher.is_enabled("cell-a") is True  # t=0.0: first load

    matrix_path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "axes": {"filter_depth": {"enabled": False}},
                "cells": [{"config_id": "cell-a", "enabled": False}],
            }
        )
    )

    assert (
        watcher.is_enabled("cell-a") is True
    )  # t=1.0: within the same poll interval, stale
    assert watcher.is_enabled("cell-a") is True  # t=2.0: still within it
    assert (
        watcher.is_enabled("cell-a") is False
    )  # t=10.0: >= 5.0s since t=0.0, reloads, sees off
    assert watcher.is_enabled("cell-a") is False  # t=10.5: still off


def test_unknown_config_id_raises() -> None:
    matrix = routing_matrix.load_matrix()
    watcher = routing_matrix.MatrixWatcher(path=None)
    watcher._matrix = matrix
    watcher._loaded_at = watcher.clock()
    with pytest.raises(routing_matrix.RoutingMatrixError):
        watcher.is_enabled("does-not-exist")

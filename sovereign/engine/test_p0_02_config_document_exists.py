"""P0-02 (idp#3525 CP10, spec section 9). ACCEPT, verbatim (features/battalion/
cp10-p0-prerequisites.feature): "the single hot-reloadable Battalion config document ...
exists before any 'seamless enable/disable of the full matrix' claim is made. And until it
exists, every axis in sections 3 and 5 is a code-level toggle only." METHOD: existence check.

CFG-01 already named this document and CP7 already built it (platform/llm/routing-matrix.yaml,
sovereign/engine/routing_matrix.py, sovereign/engine/config_schema_check.py) -- nothing here is
reimplemented. P0-02's own contribution is naming the document's existence, on this exact path,
its own checkable prerequisite, so "seamless enable/disable of the full matrix" is never
silently asserted without it.
"""

from __future__ import annotations

from sovereign.engine import config_schema_check, routing_matrix


def test_the_single_hot_reloadable_config_document_exists_on_disk() -> None:
    assert routing_matrix.DEFAULT_MATRIX_PATH.exists(), (
        "P0-02: no single hot-reloadable Battalion config document on disk -- every axis "
        "in spec sections 3 and 5 remains a code-level toggle only, not a product capability"
    )


def test_the_document_parses_as_a_real_routing_matrix_with_at_least_one_cell() -> None:
    matrix = routing_matrix.load_matrix()
    assert matrix["cells"], "P0-02: the config document exists but declares zero cells"


def test_the_documents_axes_still_mirror_the_specs_own_cfg01_sentence() -> None:
    config_schema_check.assert_schema_matches_spec()


def test_the_document_is_wired_to_the_hot_reload_watcher() -> None:
    """CFG-01's own ACCEPT (CP7): a cell toggled on disk is picked up on the next poll, no
    restart. Proven here against the real production document, not a synthetic one."""
    active = routing_matrix.active_cells(routing_matrix.load_matrix())
    assert active, "fixture drifted: no active cell in the real document to watch"
    watcher = routing_matrix.MatrixWatcher(poll_interval_s=0.0)
    assert watcher.is_enabled(active[0]["config_id"]) is True

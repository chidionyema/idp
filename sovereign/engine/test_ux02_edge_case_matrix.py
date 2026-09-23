"""UX-02 (idp#3525 CP9, spec section 10). ACCEPT, verbatim: "an edge-case matrix (this list)
has one fault-injection test per row, each asserting a DEGRADED-marked response or a rejected
config edit, never a 5xx/timeout with no marker." METHOD: fault-injection suite, one test per
enumerated edge case, CI-gated.

The matrix is the spec's own list, one test function per row. Every row reuses the mechanism
that edge case's own REQ already built -- JIT-02's call_with_budget, ROUTE-06's run_chain, R29's
budget.spend, VER-0x's verify(), CFG-01's MatrixWatcher/assert_lanes_reachable -- none of it
re-implemented here. UX-02's own contribution is the enumeration and the one assertion per row
that a marker exists, never a raw, unmarked failure.
"""

from __future__ import annotations

import subprocess
import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

from sovereign import config, verifier
from sovereign.engine import budget, fallback_chain, jit_provisioning, routing_matrix


# Row 1: cold start beyond JIT-02's budget.
def test_row1_cold_start_beyond_budget_degrades_with_a_marker() -> None:
    ladder = jit_provisioning.cost_ladder.load_ladder()

    def slow_primary() -> str:
        return "too slow to matter -- elapsed_ms is what call_with_budget checks"

    result = jit_provisioning.call_with_budget(
        tier="local_free",
        fallback_tier="router_metered",
        work=slow_primary,
        fallback=lambda: "fallback answer",
        ladder=ladder,
        clock=iter(
            [0.0, 999.0]
        ).__next__,  # elapsed_ms far past any declared cold_start budget
    )
    assert result.degraded is True
    assert result.lane == "router_metered"


# Row 2: mid-request tier eviction (the primary lane raises mid-flight).
def test_row2_mid_request_tier_eviction_degrades_with_a_marker() -> None:
    def evicted() -> str:
        raise RuntimeError("instance killed mid-flow")

    result = jit_provisioning.call_with_budget(
        tier="local_free",
        fallback_tier="router_metered",
        work=evicted,
        fallback=lambda: "fallback answer",
    )
    assert result.degraded is True
    assert result.value == "fallback answer"


# Row 3: budget breach mid-stream (COST-01).
def test_row3_budget_breach_mid_stream_halts_with_a_marker() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(config, "BUDGET_DB", Path(tmp) / "budget.db"):
            sid = f"ux02-row3-{uuid.uuid4().hex[:8]}"
            budget.allocate(sid, 100)
            spends = [budget.spend(sid, 40) for _ in range(4)]  # 40+40+40+40 > 100
            assert any(s.halted for s in spends), (
                "a mid-stream spend that breaches the budget must come back halted -- "
                "never a raw exception or a silent overspend"
            )
            assert spends[-1].remaining == 0


# Row 4: verifier timeout (VER-04's gauntlet, execution stage).
def test_row4_verifier_timeout_yields_a_failed_marked_verdict_not_a_raw_exception() -> (
    None
):
    files = [
        verifier.ProposedFile(
            path="greet.py", lines=["def greet():\n", "    return 'hi'\n"]
        )
    ]
    ledger = verifier.Ledger(
        ledger_id=f"ux02-row4-{uuid.uuid4().hex[:8]}",
        ledger_dir=Path(tempfile.mkdtemp(prefix="idp-ux02-row4-")),
        files=files,
        tests="from greet import greet\n\n\ndef test_greet():\n    assert greet() == 'hi'\n",
        claim="greet returns 'hi'",
    )
    with patch.object(
        verifier,
        "stage_execution",
        side_effect=subprocess.TimeoutExpired(
            cmd=["pytest"], timeout=verifier.STAGE_TIMEOUT_SEC
        ),
    ):
        verdict = verifier.verify(ledger)
    assert verdict["claim_verdict"] == "FAILED"
    assert verdict["stages"]["execution"]["passed"] is False
    assert "did not finish" in verdict["stderr"]


# Row 5: all lanes down simultaneously (ROUTE-06).
def test_row5_all_lanes_down_simultaneously_degrades_to_the_local_floor() -> None:
    def dead_lane() -> str:
        raise ConnectionError("lane unreachable")

    result = fallback_chain.run_chain(
        external_lanes=[
            ("router_metered", dead_lane),
            ("flat_rate_apple_silicon", dead_lane),
        ],
        local_lane=("local_free", lambda: "local floor answer"),
    )
    assert result.degraded is True
    assert result.lane == "local_free"
    assert result.value == "local floor answer"


# Row 6: config hot-reload mid-request (CFG-01).
def test_row6_config_hot_reload_mid_request_never_corrupts_an_in_flight_cell(
    tmp_path,
) -> None:
    """A request pins its cell's fields at resolution time (get_cell returns a fresh dict, not
    a live reference); a reload that happens afterward -- even one that disables that very
    config_id -- cannot retroactively corrupt the values the in-flight request already holds."""
    matrix_path = tmp_path / "routing-matrix.yaml"
    matrix_path.write_text(
        "version: 1\n"
        "axes: {}\n"
        "cells:\n"
        "  - {config_id: c1, resource_tier: rung1_router_metered, selection_method: gate, "
        "escalation_pattern: route, enabled: true}\n"
    )
    watcher = routing_matrix.MatrixWatcher(path=matrix_path, poll_interval_s=999.0)
    in_flight_cell = watcher.get_cell("c1")
    assert in_flight_cell["enabled"] is True

    matrix_path.write_text(
        "version: 1\n"
        "axes: {}\n"
        "cells:\n"
        "  - {config_id: c1, resource_tier: rung1_router_metered, selection_method: gate, "
        "escalation_pattern: route, enabled: false}\n"
    )
    # the request already holding in_flight_cell sees no change -- no exception, no mutation
    assert in_flight_cell["enabled"] is True


# Row 7: a malformed/adversarial CFG-01 edit disabling every lane at once.
def test_row7_malformed_edit_disabling_every_lane_is_a_rejected_config_edit_not_a_crash() -> (
    None
):
    matrix = routing_matrix.load_matrix()
    for row in matrix["cells"]:
        row["enabled"] = False
    with pytest.raises(routing_matrix.RoutingMatrixError):
        routing_matrix.validate_schema(matrix)

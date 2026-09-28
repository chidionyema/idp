"""Tests for sovereign/engine/fallback_chain.py (idp#3525 CP3, ROUTE-06).

ACCEPT, verbatim: "kill all external lanes -> local model answers with DEGRADED marker; no
request drops."
"""

from __future__ import annotations

import pytest

from sovereign.engine import fallback_chain


def _dead(name: str):
    def _call():
        raise RuntimeError(f"{name} is systemically down")

    return _call


def test_all_external_lanes_killed_local_answers_degraded_no_drop() -> None:
    result = fallback_chain.run_chain(
        external_lanes=[
            ("router_metered", _dead("router_metered")),
            ("gpu_burst", _dead("gpu_burst")),
        ],
        local_lane=("local_free", lambda: "local-answer"),
    )
    assert result.degraded is True
    assert result.lane == "local_free"
    assert result.value == "local-answer"


def test_a_healthy_external_lane_is_preferred_and_not_marked_degraded() -> None:
    local_calls = []
    result = fallback_chain.run_chain(
        external_lanes=[("router_metered", lambda: "router-answer")],
        local_lane=("local_free", lambda: local_calls.append(1) or "local-answer"),
    )
    assert result.degraded is False
    assert result.lane == "router_metered"
    assert (
        local_calls == []
    )  # the local floor is never touched when an external lane answers


def test_chain_walks_past_dead_lanes_in_order_to_a_healthy_one() -> None:
    result = fallback_chain.run_chain(
        external_lanes=[
            ("router_metered", _dead("router_metered")),
            ("gpu_burst", lambda: "gpu-answer"),
        ],
        local_lane=("local_free", lambda: "unreachable"),
    )
    assert result.degraded is False
    assert result.lane == "gpu_burst"
    assert result.value == "gpu-answer"


def test_no_external_lanes_at_all_still_reaches_the_local_floor() -> None:
    result = fallback_chain.run_chain(
        external_lanes=[], local_lane=("local_free", lambda: "local-answer")
    )
    assert result.degraded is True
    assert result.lane == "local_free"


def test_local_floor_itself_raising_is_not_swallowed() -> None:
    """The local lane is the floor, not one more item wrapped in try/except: if it raises,
    that is a defect this function must surface, never a silent fallback to nothing."""
    with pytest.raises(RuntimeError, match="local is down too"):
        fallback_chain.run_chain(
            external_lanes=[("router_metered", _dead("router_metered"))],
            local_lane=("local_free", _dead("local is down too")),
        )

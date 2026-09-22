"""Tests for dag.TopologicalDAG."""

from __future__ import annotations

from graphlib import CycleError

import pytest

from idp_concurrency.dag import Stage, TopologicalDAG


def test_validate_accepts_linear_order():
    dag = TopologicalDAG(
        [
            Stage("a"),
            Stage("b", frozenset({"a"})),
            Stage("c", frozenset({"b"})),
        ]
    )
    dag.validate()  # no raise


def test_validate_rejects_cycle():
    dag = TopologicalDAG(
        [
            Stage("a", frozenset({"c"})),
            Stage("b", frozenset({"a"})),
            Stage("c", frozenset({"b"})),
        ]
    )
    with pytest.raises(CycleError):
        dag.validate()


def test_validate_rejects_self_loop():
    dag = TopologicalDAG([Stage("a", frozenset({"a"}))])
    with pytest.raises(CycleError):
        dag.validate()


def test_validate_rejects_unknown_dep():
    with pytest.raises(ValueError, match="unknown deps"):
        TopologicalDAG([Stage("a", frozenset({"ghost"}))])


def test_frontier_returns_ready_nodes():
    dag = TopologicalDAG(
        [
            Stage("a"),
            Stage("b"),
            Stage("c", frozenset({"a", "b"})),
        ]
    )
    assert set(dag.frontier(set())) == {"a", "b"}
    assert dag.frontier({"a"}) == ["b"]
    assert dag.frontier({"a", "b"}) == ["c"]
    assert dag.frontier({"a", "b", "c"}) == []


def test_validate_matches_zeroedge_pipeline_order():
    """The seven ZeroEdge stages must validate. Order: 1→7."""
    try:
        from zeroedge.pipeline_order import STAGES
    except ImportError:
        pytest.skip("zeroedge not installed")
        return
    stages = [Stage(name, deps) for name, deps in STAGES.items()]
    TopologicalDAG(stages).validate()  # must not raise

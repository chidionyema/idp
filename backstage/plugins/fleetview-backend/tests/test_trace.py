"""FleetView CP7: src/trace.py unit tests.

Uses a stub HTTP layer (no live Langfuse required) following the same pattern
test_fleetview_check_receipts.py uses for its stub Langfuse client.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
TRACE_MODULE = REPO / "backstage" / "plugins" / "fleetview-backend" / "src" / "trace.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def trace(monkeypatch):
    monkeypatch.setenv("LANGFUSE_HOST", "http://langfuse.test")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")
    return _load(TRACE_MODULE, "fleetview_trace_under_test")


# ---------------------------------------------------------------------------
# Config guard tests
# ---------------------------------------------------------------------------


def test_no_langfuse_host_raises_trace_unavailable(monkeypatch):
    monkeypatch.delenv("LANGFUSE_HOST", raising=False)
    mod = _load(TRACE_MODULE, "fleetview_trace_no_host")
    with pytest.raises(mod.TraceUnavailable, match="LANGFUSE_HOST not configured"):
        mod.trace_graph("any-session")


def test_missing_keys_raise_trace_unavailable(monkeypatch):
    monkeypatch.setenv("LANGFUSE_HOST", "http://langfuse.test")
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    mod = _load(TRACE_MODULE, "fleetview_trace_no_keys")
    with pytest.raises(mod.TraceUnavailable, match="PUBLIC_KEY"):
        mod.trace_graph("any-session")


def test_blank_session_id_raises_trace_unavailable(trace):
    with pytest.raises(trace.TraceUnavailable):
        trace.trace_graph("")


# ---------------------------------------------------------------------------
# Stub HTTP helper
# ---------------------------------------------------------------------------


def _stub_http(trace, monkeypatch, trace_resp, obs_resp):
    """Patch trace._http_get to return canned responses per URL path."""

    def _fake_get(url: str, auth):
        if "/observations" in url:
            return obs_resp
        return trace_resp

    monkeypatch.setattr(trace, "_http_get", _fake_get)


# ---------------------------------------------------------------------------
# Observation → node/edge mapping
# ---------------------------------------------------------------------------


def test_a_trace_with_no_observations_returns_empty_with_flag(trace, monkeypatch):
    _stub_http(trace, monkeypatch, {"id": "s1"}, {"data": []})
    result = trace.trace_graph("s1")
    assert result == {"nodes": [], "edges": [], "empty": True}


def test_nodes_are_built_from_observations(trace, monkeypatch):
    obs = [
        {
            "id": "o1",
            "name": "span-one",
            "type": "SPAN",
            "startTime": "2026-09-09T10:00:00Z",
            "endTime": "2026-09-09T10:00:01Z",
            "parentObservationId": None,
        },
    ]
    _stub_http(trace, monkeypatch, {"id": "s1"}, {"data": obs})
    result = trace.trace_graph("s1")
    assert len(result["nodes"]) == 1
    node = result["nodes"][0]
    assert node["id"] == "o1"
    assert node["data"]["label"] == "span-one"
    assert node["data"]["kind"] == "SPAN"
    assert node["data"]["duration_ms"] == 1000
    assert node["position"] == {"x": 0, "y": 0}


def test_parent_child_link_creates_edge(trace, monkeypatch):
    obs = [
        {
            "id": "root",
            "name": "root-span",
            "type": "SPAN",
            "parentObservationId": None,
        },
        {
            "id": "child",
            "name": "child-span",
            "type": "SPAN",
            "parentObservationId": "root",
        },
    ]
    _stub_http(trace, monkeypatch, {"id": "s2"}, {"data": obs})
    result = trace.trace_graph("s2")
    assert len(result["edges"]) == 1
    edge = result["edges"][0]
    assert edge["source"] == "root"
    assert edge["target"] == "child"
    assert edge["id"] == "root-child"


def test_nodes_without_parent_produce_no_edge(trace, monkeypatch):
    obs = [
        {"id": "a", "name": "a", "type": "SPAN", "parentObservationId": None},
        {"id": "b", "name": "b", "type": "SPAN", "parentObservationId": None},
    ]
    _stub_http(trace, monkeypatch, {"id": "s3"}, {"data": obs})
    result = trace.trace_graph("s3")
    assert result["edges"] == []
    assert len(result["nodes"]) == 2


def test_y_positions_are_incremental(trace, monkeypatch):
    obs = [
        {
            "id": f"o{i}",
            "name": f"span-{i}",
            "type": "SPAN",
            "parentObservationId": None,
        }
        for i in range(3)
    ]
    _stub_http(trace, monkeypatch, {"id": "s4"}, {"data": obs})
    result = trace.trace_graph("s4")
    ys = [n["position"]["y"] for n in result["nodes"]]
    assert ys == [0, 60, 120]


def test_http_error_is_trace_unavailable(trace, monkeypatch):
    def _raise(url, auth):
        raise trace.TraceUnavailable("HTTP 404: Not Found")

    monkeypatch.setattr(trace, "_http_get", _raise)
    with pytest.raises(trace.TraceUnavailable, match="HTTP 404"):
        trace.trace_graph("missing-session")


def test_available_false_envelope_on_unavailable(monkeypatch):
    """routes.py's trace_envelope returns available:False/503 on TraceUnavailable."""
    routes_path = (
        REPO / "backstage" / "plugins" / "fleetview-backend" / "src" / "routes.py"
    )
    monkeypatch.setenv("LANGFUSE_HOST", "")
    routes = _load(routes_path, "fleetview_routes_trace_test")
    body, status = routes.trace_envelope("some-session")
    assert status == 503
    assert body["available"] is False
    assert body["nodes"] == []
    assert body["edges"] == []
    assert body["error"]

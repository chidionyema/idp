"""The /research and /estate envelopes, exercised through the HTTP layer.

WHY THIS FILE EXISTS. The first version of those two handlers called
`loop.run_in_executor(...)` from a sync handler -- a sync handler has no running loop, so
every request 500'd (RuntimeError), and nothing caught it because every other test in this
suite tests the envelope functions directly. The frontend suites mock fetch. An endpoint
whose only coverage is its own callers can ship broken and every gate stays green -- that
is exactly the honesty failure the estate's laws exist to prevent. These tests hit the app.
"""

from __future__ import annotations

import json

import pytest


@pytest.fixture()
def client(monkeypatch):
    import sys
    import types

    sys.modules.setdefault("uvicorn", types.ModuleType("uvicorn"))
    from fastapi.testclient import TestClient

    from fleetview_backend import routes, serve

    monkeypatch.setattr(
        routes,
        "research_envelope",
        lambda: ({"available": True, "count": 0, "claims": []}, 200),
    )
    monkeypatch.setattr(
        routes,
        "estate_envelope",
        lambda: (
            {
                "green": {"available": False},
                "burn": {"measured": False},
                "research": None,
            },
            200,
        ),
    )
    return TestClient(serve.build_app())


def test_research_endpoint_returns_envelope(client):
    r = client.get("/research")
    assert r.status_code == 200
    body = r.json()
    assert body["available"] is True
    assert body["claims"] == []


def test_estate_endpoint_returns_envelope(client):
    r = client.get("/estate")
    assert r.status_code == 200
    body = json.loads(r.content)
    assert "green" in body and "burn" in body


def test_research_endpoint_failure_is_an_envelope_not_a_500(client, monkeypatch):
    """A department that does not answer is an envelope with a reason, still over HTTP 200."""

    from fleetview_backend import routes

    monkeypatch.setattr(
        routes,
        "research_envelope",
        lambda: ({"available": False, "error": "/claims answered 503"}, 200),
    )
    r = client.get("/research")
    assert r.status_code == 200
    assert r.json()["available"] is False
    assert "503" in r.json()["error"]

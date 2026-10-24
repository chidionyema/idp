"""The founder's eval endpoints, exercised through the HTTP layer.

WHY THIS FILE EXISTS. The frontend suites mock fetch, and `founder_agent_evals` has its own
tests -- so an endpoint that 500s, or answers `{}` where the panel reads `latest`, could ship with
every gate green. That is the honesty failure `test_envelope_http.py` was written for, and the
founder's live eval surface (2026-10-23: "the founder surface must monitor evals across the estate
in real time") is exactly the kind of panel that fails quietly. These tests hit the app.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture()
def client(monkeypatch, tmp_path: Path):
    import sys
    import types

    sys.modules.setdefault("uvicorn", types.ModuleType("uvicorn"))
    from fastapi.testclient import TestClient

    from fleetview_backend import serve

    monkeypatch.setenv("ESTATE_FOUNDER_EVAL_LEDGER", str(tmp_path / "rounds.json"))
    monkeypatch.setenv("ESTATE_FOUNDER_EVAL_FEED", str(tmp_path / "live.jsonl"))
    return TestClient(serve.build_app()), tmp_path


def test_an_absent_ledger_is_503_with_the_path_it_looked_for(client):
    api, tmp_path = client
    r = api.get("/evals/founder-agent")
    assert r.status_code == 503, r.text
    body = r.json()
    assert "absent" in body
    assert str(tmp_path / "rounds.json") in body["absent"]
    assert "run.py --suite" in body["absent"]


def test_a_round_is_served_with_its_verdicts_and_its_latencies(client):
    api, tmp_path = client
    (tmp_path / "rounds.json").write_text(
        json.dumps(
            {
                "rounds": [
                    {
                        "round": 4,
                        "pass_rate": 1.0,
                        "verdict": {"G1": "pass", "P": "pass", "G8": "pass"},
                        "performance": {
                            "answered_ms": {"p50": 910.0, "p95": 1500.0},
                            "cost_usd": 0.03,
                        },
                        "green": True,
                        "improvement": "insufficient-data",
                    }
                ],
                "recent_green": 2,
            }
        )
    )
    (tmp_path / "live.jsonl").write_text(
        json.dumps(
            {"kind": "run.end", "session_id": "r4", "task": "table-booking", "ok": True}
        )
        + "\n"
    )
    r = api.get("/evals/founder-agent?limit=10")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["latest"]["round"] == 4
    assert body["latest"]["performance"]["answered_ms"]["p95"] == 1500.0
    # Counted over the rows this ledger carries (one green), never copied from a `recent_green`
    # key: `run.py` returns that counter and does not persist it.
    assert body["recent_green"] == 1
    assert body["latest"]["verdict"]["G8"] == "pass"
    assert body["live"][0]["task"] == "table-booking"


def test_the_stream_answers_event_stream_not_json(client, monkeypatch):
    """The route is wired to the SSE generator, not to the JSON envelope.

    The real `stream()` never ends (it is a live feed), so consuming it through TestClient would
    block for ever -- an earlier version of this test did exactly that and was SIGTERMed at the
    executor's 100s ceiling. So the generator is replaced with one finite frame: what is under
    test here is the route (media type, the `data: ` framing, the body), not the loop, which
    `test_founder_agent_evals_feed.py` drives directly with its own change/no-change cases.
    """
    api, tmp_path = client
    (tmp_path / "rounds.json").write_text(json.dumps({"rounds": []}))
    from fleetview_backend import founder_agent_evals as fa

    async def _one_frame(limit: int = 200):
        import json as _json

        yield "data: " + _json.dumps({"rounds": [], "latest": None}) + "\n\n"

    monkeypatch.setattr(fa, "stream", _one_frame)
    r = api.get("/evals/founder-agent/stream")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    body = r.text
    assert body.startswith("data: "), body
    assert json.loads(body[len("data: ") :].strip())["latest"] is None

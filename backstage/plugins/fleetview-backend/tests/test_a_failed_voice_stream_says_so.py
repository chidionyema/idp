"""A turn whose brain fails must say so, in a frame the page can read.

2026-10-14: /voice/stream built its error frame by hand as `{'error': '...'}` -- Python's repr,
not JSON. useEstateVoice JSON.parses every frame and skips one that does not parse, so a failed
brain call produced no error state and no speech: the turn just ended, reported as answered.
"""

from __future__ import annotations

import json
import sys
import types

import pytest


@pytest.fixture
def client(monkeypatch):
    sys.modules.setdefault("uvicorn", types.ModuleType("uvicorn"))
    from fastapi.testclient import TestClient

    from fleetview_backend import serve, voice, voice_intents

    def broken(question, sessions, history):
        raise RuntimeError("router said 'no'\nand then hung up")
        yield  # pragma: no cover -- makes this a generator, as stream_ask is

    monkeypatch.setattr(voice, "stream_ask", broken)
    monkeypatch.setattr(voice_intents, "handle", lambda q, s: None)
    monkeypatch.setattr(serve, "_voice_sessions", lambda: [])
    return TestClient(serve.build_app())


def _frames(text: str) -> list[tuple[str, str]]:
    out = []
    for block in text.split("\n\n"):
        lines = dict(l.split(": ", 1) for l in block.splitlines() if ": " in l)
        if "event" in lines:
            out.append((lines["event"], lines.get("data", "")))
    return out


def test_a_failed_brain_ends_in_an_error_frame_the_page_can_parse(client):
    r = client.post(
        "/voice/stream", json={"question": "what is running", "session_id": "e1"}
    )
    errors = [data for event, data in _frames(r.text) if event == "error"]
    assert errors, f"no error frame in {r.text!r}"
    payload = json.loads(errors[-1])  # what the page does; it used to throw here
    assert payload["error"] == "router said 'no'\nand then hung up"

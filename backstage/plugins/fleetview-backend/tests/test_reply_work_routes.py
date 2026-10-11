"""The /work and /replies channels, exercised through the HTTP layer.

WHY THIS FILE EXISTS. These two routes were built once, lost to a rebase, and the deployed
sidecar answered 404 to the board's own polls while every gate stayed green -- the exact
failure `test_envelope_http.py`'s docstring warns about: an endpoint whose only coverage is
its own callers can ship broken. These tests hit the app over HTTP, against a FRESH database,
which is also the only honest test of `_ensure_schema`: a database that must be complete on
first connection, not on whichever write happened to run first.
"""

from __future__ import annotations

import sys
import types

import pytest


@pytest.fixture()
def client(monkeypatch, tmp_path):
    sys.modules.setdefault("uvicorn", types.ModuleType("uvicorn"))
    from fastapi.testclient import TestClient

    from fleetview_backend import serve

    monkeypatch.setenv("ESTATE_DB", str(tmp_path / "estate.db"))
    monkeypatch.delenv("FLEETVIEW_BOARD_KEY", raising=False)
    monkeypatch.delenv("FLEETVIEW_BOARD_KEY_FILE", raising=False)
    return TestClient(serve.build_app())


def test_work_get_on_a_fresh_database_is_200_with_an_empty_map(client):
    """Nobody has reported work yet. That is an empty map, never an error -- and the table had to
    be created by this very request, which is the _ensure_schema contract."""
    r = client.get("/work")
    assert r.status_code == 200
    assert r.json() == {"work": {}}


def test_work_roundtrip_then_merge_semantics(client):
    """A report that carries only a step must not blank the branch, and vice versa: the two
    arrive from different hooks, and one hook's partial report is not the other's eraser."""
    r = client.post(
        "/work",
        json={
            "session_id": "s1",
            "runtime": "pi",
            "branch": "lane/fleetview",
            "step": "editing routes.py",
        },
    )
    assert r.status_code == 201
    assert r.json()["work"]["branch"] == "lane/fleetview"

    r = client.post(
        "/work", json={"session_id": "s1", "runtime": "pi", "step": "running tests"}
    )
    assert r.status_code == 201
    body = client.get("/work").json()["work"]
    assert body["s1"]["branch"] == "lane/fleetview"
    assert body["s1"]["step"] == "running tests"
    assert body["s1"]["pid"] is None

    # One row per session: current state, not a log.
    assert len(body) == 1


def test_work_blank_session_id_is_400_not_a_row(client):
    r = client.post("/work", json={"session_id": "", "runtime": "pi", "step": "x"})
    assert r.status_code == 400
    assert "session_id" in r.json()["error"]
    assert client.get("/work").json()["work"] == {}


def test_work_non_json_body_is_400(client):
    r = client.post(
        "/work", content=b"not json", headers={"content-type": "application/json"}
    )
    assert r.status_code == 400
    assert r.json()["error"] == "body must be JSON"


def test_work_post_is_guarded_by_the_board_key(client, monkeypatch):
    """The work row carries the pid a hard-stop will signal, so the write is the half of a
    destructive chain that a drive-by page must not forge. Unset key means no enforcement
    (laptop runs keep working); set key means a wrong or missing header is a 401."""
    monkeypatch.setenv("FLEETVIEW_BOARD_KEY", "board-secret")
    payload = {"session_id": "s2", "runtime": "pi", "pid": 4242}

    r = client.post("/work", json=payload)
    assert r.status_code == 401
    r = client.post("/work", json=payload, headers={"X-Board-Key": "wrong"})
    assert r.status_code == 401
    # The refused attempts wrote nothing.
    assert client.get("/work").json()["work"] == {}

    r = client.post("/work", json=payload, headers={"X-Board-Key": "board-secret"})
    assert r.status_code == 201
    # A read of telemetry stays open: the guard is on the write, where the damage is.
    assert client.get("/work").json()["work"]["s2"]["pid"] == 4242


def test_replies_roundtrip_and_redaction_at_the_writer(client):
    """A reply that quotes a credential is redacted BEFORE it lands: the database must never hold
    the secret, not merely the panel hide it. The marker names why, and stays greppable."""
    r = client.post(
        "/replies",
        json={
            "session_id": "s3",
            "runtime": "pi",
            "author": "agent",
            "text": "read LITELLM_API_KEY=sk-abcdef0123456789abcdef from the vault",
        },
    )
    assert r.status_code == 201
    stored = r.json()["reply"]["text"]
    assert "sk-abcdef0123456789abcdef" not in stored
    assert "[REDACTED:" in stored

    feed = client.get("/replies").json()["replies"]
    assert len(feed) == 1
    assert feed[0]["session_id"] == "s3"
    assert feed[0]["in_reply_to"] is None

    one = client.get("/replies", params={"session_id": "s3"}).json()["replies"]
    assert len(one) == 1
    other = client.get("/replies", params={"session_id": "s9"}).json()["replies"]
    assert other == []


def test_replies_blank_text_is_400(client):
    r = client.post(
        "/replies", json={"session_id": "s3", "runtime": "pi", "text": "   "}
    )
    assert r.status_code == 400
    assert "text" in r.json()["error"]


def test_replies_in_reply_to_links_the_thread(client):
    first = client.post(
        "/replies",
        json={"session_id": "s4", "runtime": "pi", "text": "starting the migration"},
    ).json()["reply"]
    r = client.post(
        "/replies",
        json={
            "session_id": "founder",
            "runtime": "human",
            "author": "founder",
            "text": "land it behind the gate",
            "in_reply_to": first["id"],
        },
    )
    assert r.status_code == 201
    feed = client.get("/replies", params={"session_id": "founder"}).json()["replies"]
    assert feed[0]["in_reply_to"] == first["id"]

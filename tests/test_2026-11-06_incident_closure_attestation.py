"""Incident closure must be independently attested, not assumed from a CLI attempt."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "incident_closure", ROOT / "platform/estate/libexec/incident-loop.py"
)
assert spec and spec.loader
loop = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loop)


@pytest.fixture
def incident(tmp_path, monkeypatch):
    monkeypatch.setattr(loop, "now_iso", lambda: "2026-11-06T18:00:00Z")
    conn = loop.open_ledger(tmp_path / "incident.db")
    policy = loop.load_policy(ROOT / "catalog/incident-policy.json")
    ident = loop.fingerprint("ci", "chidionyema/idp", "closure-test")
    loop.record_incident(conn, {
        "id": ident, "source": "ci", "repo": "chidionyema/idp",
        "severity": "critical", "blast": "main", "title": "closure test",
        "url": "https://example.invalid/1", "detail": {"run_id": 1},
    }, policy)
    loop.set_field(conn, ident, ticket=7613)
    yield conn, policy, ident
    conn.close()


def test_remote_timeout_cannot_be_recorded_as_closed(incident, monkeypatch):
    conn, policy, ident = incident
    lessons = []
    monkeypatch.setattr(loop, "ci_resolved", lambda *a: (True, "exact-source recovery"))
    monkeypatch.setattr(loop, "ticket_resolved", lambda row: (False, ""))
    monkeypatch.setattr(loop, "write_lesson", lambda p, lesson: lessons.append(lesson))
    monkeypatch.setattr(loop, "run_gh", lambda argv, timeout=45: (124, "", "timeout"))

    assert not loop.verify_incident(conn, policy, loop.get_incident(conn, ident))
    row = loop.get_incident(conn, ident)
    assert row["state"] == "verified"
    assert row["closed_at"] is None
    assert len(lessons) == 1


def test_manual_ticket_close_never_proves_source_recovery(incident, monkeypatch):
    conn, policy, ident = incident
    monkeypatch.setattr(loop, "ci_resolved", lambda *a: (False, "run remains failed"))
    monkeypatch.setattr(loop, "ticket_resolved", lambda row: (True, "manually closed"))
    assert not loop.verify_incident(conn, policy, loop.get_incident(conn, ident))
    assert loop.get_incident(conn, ident)["state"] == "open"

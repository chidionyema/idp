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


def test_successful_command_without_remote_readback_stays_verified(incident, monkeypatch):
    conn, policy, ident = incident
    remote = {"visible": False}
    calls = []
    monkeypatch.setattr(loop, "ci_resolved", lambda *a: (True, "same-source recovery"))
    monkeypatch.setattr(loop, "write_lesson", lambda *a: "journalled")
    monkeypatch.setattr(
        loop, "ticket_resolved",
        lambda row: (remote["visible"], "GitHub readback closed" if remote["visible"] else ""),
    )

    def gh(argv, timeout=45):
        calls.append(tuple(argv))
        return 0, "", ""

    monkeypatch.setattr(loop, "run_gh", gh)
    assert not loop.verify_incident(conn, policy, loop.get_incident(conn, ident))
    assert loop.get_incident(conn, ident)["state"] == "verified"
    remote["visible"] = True
    assert loop.verify_incident(conn, policy, loop.get_incident(conn, ident))
    assert loop.get_incident(conn, ident)["state"] == "closed"
    assert len(calls) == 1, "verified remote state must prevent duplicate comments"


def test_tick_reconciles_verified_rows_and_exposes_pending_closure(incident, monkeypatch):
    import sqlite3

    conn, policy, ident = incident
    db = conn.execute("PRAGMA database_list").fetchone()[2]
    loop.set_field(conn, ident, state="verified", verified_at="2026-11-06T18:00:00Z")
    remote = {"closed": False}
    monkeypatch.setattr(loop.clock_guard, "commit", lambda: {"state": "OK"})
    monkeypatch.setattr(loop, "sense_ci", lambda *a: [])
    monkeypatch.setattr(loop, "sense_doors", lambda *a: [])
    monkeypatch.setattr(loop, "ticket_resolved",
                        lambda row: (remote["closed"], "GitHub closed" if remote["closed"] else ""))
    monkeypatch.setattr(loop, "ci_resolved", lambda *a: pytest.fail("do not verify twice"))
    monkeypatch.setattr(loop, "run_gh", lambda *a, **kw: (124, "", "offline"))

    def open_db():
        opened = sqlite3.connect(db)
        opened.row_factory = sqlite3.Row
        return opened

    monkeypatch.setattr(loop, "open_ledger", open_db)
    result = loop.tick(policy, "chidionyema/idp")
    assert result["closure_pending"] == 1
    assert loop.get_incident(conn, ident)["state"] == "verified"

    remote["closed"] = True
    result = loop.tick(policy, "chidionyema/idp")
    assert result["closure_pending"] == 0
    assert result["verified"] == 1
    assert loop.get_incident(conn, ident)["state"] == "closed"

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


def test_queue_witness_requires_durable_worker_claim(incident, tmp_path):
    import sqlite3

    conn, policy, ident = incident
    db = tmp_path / "worker.db"
    with sqlite3.connect(db) as queue:
        queue.execute(
            "CREATE TABLE tasks (id INTEGER PRIMARY KEY, status TEXT, agent_id TEXT)"
        )
        queue.execute("INSERT INTO tasks VALUES (42, 'pending', NULL)")
    policy["dispatch"]["queue_db"] = str(db)
    assert loop.worker_queue_witness(policy, "")[0] == "UNPROVEN"
    assert loop.worker_queue_witness(policy, "42")[0] == "QUEUED"
    with sqlite3.connect(db) as queue:
        queue.execute("UPDATE tasks SET status='running', agent_id=NULL WHERE id=42")
    assert loop.worker_queue_witness(policy, "42")[0] == "UNOWNED"
    with sqlite3.connect(db) as queue:
        queue.execute("UPDATE tasks SET agent_id='worker-1' WHERE id=42")
    state, witness = loop.worker_queue_witness(policy, "42")
    assert state == "OWNED" and "worker-1" in witness
    with sqlite3.connect(db) as queue:
        queue.execute("UPDATE tasks SET status='completed' WHERE id=42")
    assert loop.worker_queue_witness(policy, "42")[0] == "FINISHED_UNVERIFIED"
    assert loop.worker_queue_witness(policy, "43")[0] == "MISSING"
    db.unlink()
    assert loop.worker_queue_witness(policy, "42")[0] == "BLIND"


def test_overdue_p0_worker_is_escalated_once_but_never_auto_closed(incident, monkeypatch):
    from datetime import datetime, timezone

    conn, policy, ident = incident
    loop.set_field(
        conn, ident, dispatch_leg="worker", dispatch_ref="42",
        dispatched_at="2026-11-06T12:00:00Z",
    )
    monkeypatch.setattr(loop, "wall_now", lambda: datetime(2026, 11, 6, 13, 0, tzinfo=timezone.utc))
    monkeypatch.setattr(loop, "worker_queue_witness", lambda *a: ("QUEUED", "pending, no worker"))
    posts = []

    def gh(argv, timeout=45):
        posts.append(tuple(argv))
        return 0, "", ""

    monkeypatch.setattr(loop, "run_gh", gh)
    overdue, evidence = loop.audit_p0_worker_liveness(
        conn, policy, loop.get_incident(conn, ident)
    )
    assert overdue and "QUEUED" in evidence
    assert len(posts) == 1 and posts[0][:2] == ("issue", "comment")
    assert loop.get_incident(conn, ident)["state"] == "open"
    again, _ = loop.audit_p0_worker_liveness(
        conn, policy, loop.get_incident(conn, ident)
    )
    assert again and len(posts) == 1, "one escalation per state, not every five minutes"


def test_queue_escalation_never_fabricates_confirmation_on_git_hub_error(incident, monkeypatch):
    from datetime import datetime, timezone

    conn, policy, ident = incident
    loop.set_field(
        conn, ident, dispatch_leg="worker", dispatch_ref="42",
        dispatched_at="2026-11-06T12:00:00Z",
    )
    monkeypatch.setattr(loop, "wall_now", lambda: datetime(2026, 11, 6, 13, 0, tzinfo=timezone.utc))
    monkeypatch.setattr(loop, "worker_queue_witness", lambda *a: ("BLIND", "db unavailable"))
    monkeypatch.setattr(loop, "run_gh", lambda *a, **kw: (124, "", "timeout"))
    overdue, evidence = loop.audit_p0_worker_liveness(conn, policy, loop.get_incident(conn, ident))
    assert overdue and "BLIND" in evidence
    events = [e["event"] for e in __import__("json").loads(loop.get_incident(conn, ident)["history"])]
    assert "p0-worker-overdue:BLIND" not in events
    assert loop.get_incident(conn, ident)["state"] == "open"


def test_main_ci_incident_rejects_green_on_other_branch(monkeypatch):
    import json

    row = {"detail": json.dumps({
        "run_id": 100, "workflow": "login-drill", "branch": "main",
        "run_attempt": 1,
    })}
    queries = []

    def gh(args, timeout=45):
        queries.append(args)
        return 0, json.dumps([
            {"id": 103, "name": "login-drill", "head_branch": "feature/unrelated",
             "status": "completed", "conclusion": "success", "run_attempt": 1},
            {"id": 102, "name": "login-drill", "head_branch": "main",
             "status": "completed", "conclusion": "failure", "run_attempt": 1},
            {"id": 101, "name": "login-drill", "head_branch": "main",
             "status": "completed", "conclusion": "success", "run_attempt": 1},
        ]), ""

    monkeypatch.setattr(loop, "run_gh", gh)
    ok, evidence = loop.ci_resolved("chidionyema/idp", row)
    assert not ok and not evidence
    assert "branch=main" in " ".join(queries[0])
    assert "per_page=100" in " ".join(queries[0])


def test_latest_same_branch_success_is_valid_but_not_an_earlier_green(monkeypatch):
    import json

    row = {"detail": json.dumps({
        "run_id": 100, "workflow": "login-drill", "branch": "main",
        "run_attempt": 1,
    })}
    records = [
        {"id": 102, "name": "login-drill", "head_branch": "main",
         "status": "completed", "conclusion": "failure", "run_attempt": 1},
        {"id": 101, "name": "login-drill", "head_branch": "main",
         "status": "completed", "conclusion": "success", "run_attempt": 1},
    ]
    monkeypatch.setattr(loop, "run_gh", lambda *a, **k: (0, json.dumps(records), ""))
    assert not loop.ci_resolved("chidionyema/idp", row)[0]
    records.append({
        "id": 103, "name": "login-drill", "head_branch": "main",
        "status": "completed", "conclusion": "success", "run_attempt": 1,
    })
    ok, evidence = loop.ci_resolved("chidionyema/idp", row)
    assert ok and "103" in evidence and "main" in evidence


def test_latest_run_in_progress_and_other_workflows_do_not_prove_recovery(monkeypatch):
    import json

    row = {"detail": json.dumps({
        "run_id": 100, "workflow": "login-drill", "branch": "main",
        "run_attempt": 1,
    })}
    records = [
        {"id": 103, "name": "login-drill", "head_branch": "main",
         "status": "in_progress", "conclusion": None, "run_attempt": 1},
        {"id": 102, "name": "login-drill", "head_branch": "main",
         "status": "completed", "conclusion": "success", "run_attempt": 1},
        {"id": 104, "name": "other-workflow", "head_branch": "main",
         "status": "completed", "conclusion": "success", "run_attempt": 1},
    ]
    monkeypatch.setattr(loop, "run_gh", lambda *a, **k: (0, json.dumps(records), ""))
    assert not loop.ci_resolved("chidionyema/idp", row)[0]


def test_exact_run_rerun_requires_strictly_later_attempt(monkeypatch):
    import json

    row = {"detail": json.dumps({
        "run_id": 100, "workflow": "login-drill", "branch": "main",
        "run_attempt": 1,
    })}
    attempts = {"value": 1}

    def gh(*a, **k):
        return 0, json.dumps([{
            "id": 100, "name": "login-drill", "head_branch": "main",
            "status": "completed", "conclusion": "success",
            "run_attempt": attempts["value"],
        }]), ""

    monkeypatch.setattr(loop, "run_gh", gh)
    assert not loop.ci_resolved("chidionyema/idp", row)[0]
    attempts["value"] = 2
    assert loop.ci_resolved("chidionyema/idp", row)[0]


def test_unknown_git_hub_response_fails_closed_without_main_exception(monkeypatch):
    import json

    row = {"detail": json.dumps({
        "run_id": 100, "workflow": "login-drill", "branch": "main",
    })}
    monkeypatch.setattr(loop, "run_gh", lambda *a, **k: (0, "not-json", ""))
    assert loop.ci_resolved("chidionyema/idp", row) == (False, "")
    monkeypatch.setattr(loop, "run_gh", lambda *a, **k: (0, "{}", ""))
    assert loop.ci_resolved("chidionyema/idp", row) == (False, "")

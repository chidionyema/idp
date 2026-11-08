"""FLOW protocol regression tests — the real incident ledger, no GitHub side effects.

A passing suite is SOURCE assurance, not proof that Temporal or Genesis is deployed.
"""
from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "platform" / "estate" / "libexec" / "incident-loop.py"
spec = importlib.util.spec_from_file_location("flow_incident_loop", SOURCE)
assert spec is not None and spec.loader is not None
loop = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loop)


@pytest.fixture
def incident(tmp_path, monkeypatch):
    conn = loop.open_ledger(tmp_path / "flow.db")
    policy = loop.load_policy(ROOT / "catalog" / "incident-policy.json")
    monkeypatch.setattr(loop, "now_iso", lambda: "2026-11-08T20:10:00Z")
    value = {
        "id": loop.fingerprint("report", "chidionyema/idp", "FLOW case"),
        "source": "report",
        "repo": "chidionyema/idp",
        "severity": "critical",
        "blast": "main",
        "title": "FLOW case",
        "url": "",
        "detail": {"reported_by": "estate-incident-loop"},
    }
    loop.record_incident(conn, value, policy)
    yield conn, policy, value
    conn.close()


def test_same_report_reuses_ticket_and_dispatch_without_launching_duplicate(incident, monkeypatch, capsys):
    conn, policy, value = incident
    monkeypatch.setattr(loop, "open_ledger", lambda: conn)
    monkeypatch.setattr(loop, "load_policy", lambda: policy)
    tickets, dispatched = [], []

    def ticket(c, p, row):
        if row["ticket"]:
            return row["ticket"]
        tickets.append(row["id"])
        loop.set_field(c, row["id"], ticket=7771)
        return 7771

    def dispatch(c, p, row):
        dispatched.append(row["id"])
        loop.set_field(c, row["id"], dispatch_leg="worker", dispatch_ref="42")
        return "worker", "42"

    monkeypatch.setattr(loop, "raise_ticket", ticket)
    monkeypatch.setattr(loop, "dispatch_incident", dispatch)
    args = ["report", "--title", "FLOW case", "--severity", "critical", "--blast", "main"]
    assert loop.main(args) == 0
    assert loop.main(args) == 0
    assert len(tickets) == 1
    assert len(dispatched) == 1
    assert capsys.readouterr().out.count("worker 42") == 2


def test_ambiguous_dispatch_never_leads_to_another_side_effect(incident, monkeypatch):
    conn, policy, value = incident
    loop.set_field(conn, value["id"], ticket=7771, dispatch_leg="worker", dispatch_ref="")
    monkeypatch.setattr(loop, "open_ledger", lambda: conn)
    monkeypatch.setattr(loop, "load_policy", lambda: policy)
    monkeypatch.setattr(loop, "dispatch_incident",
                        lambda *a: pytest.fail("ambiguous delivery must not repeat"))
    monkeypatch.setattr(loop, "raise_ticket", lambda c, p, row: row["ticket"])
    assert loop.main(["report", "--title", "FLOW case", "--severity", "critical",
                      "--blast", "main"]) == 0
    record = loop.flow_projection(loop.get_incident(conn, value["id"]),
                                  datetime(2026, 11, 8, 20, 10, 1, tzinfo=timezone.utc))
    assert record["state"] == "BLIND"
    assert record["next_action"] == "reconcile-ambiguous-dispatch"


def test_closed_ticket_without_source_observer_cannot_manufacture_flow_yield(incident, monkeypatch):
    conn, policy, value = incident
    loop.set_field(conn, value["id"], ticket=7771)
    monkeypatch.setattr(loop, "ticket_resolved",
                        lambda *a: pytest.fail("ticket closure is not source proof"))
    monkeypatch.setattr(loop, "write_lesson",
                        lambda *a: pytest.fail("no unproven graph lesson"))
    assert loop.verify_incident(conn, policy, loop.get_incident(conn, value["id"])) is False
    row = loop.get_incident(conn, value["id"])
    assert row["state"] == "open"
    assert row["verified_at"] is None


def test_599_vs_600_seconds_is_based_on_evidence_not_heartbeat(incident):
    conn, policy, value = incident
    # A heartbeat/updated_at write may not shift the productive clock.
    loop.set_field(conn, value["id"], last_seen="2026-11-08T20:19:59Z")
    row = loop.get_incident(conn, value["id"])
    before = loop.flow_projection(row, datetime(2026, 11, 8, 20, 19, 59, tzinfo=timezone.utc))
    at = loop.flow_projection(row, datetime(2026, 11, 8, 20, 20, 0, tzinfo=timezone.utc))
    assert before["no_verified_progress_seconds"] == 599
    assert before["state"] != "STAGNANT_UNVERIFIED"
    assert at["no_verified_progress_seconds"] == 600
    assert at["state"] == "STAGNANT_UNVERIFIED"
    assert at["next_action"] == "existing-supervisor-recovery"
    assert at["operational_yield"] is False
    assert at["founder_surface_readback"] == "UNVERIFIED"


def test_source_recovery_is_not_fake_operational_readback(incident):
    conn, policy, value = incident
    loop.set_field(conn, value["id"], state="closed",
                   verified_at="2026-11-08T20:11:00Z", lesson="source recovered")
    projection = loop.flow_projection(loop.get_incident(conn, value["id"]),
                                      datetime(2026, 11, 8, 20, 13, tzinfo=timezone.utc))
    assert projection["state"] == "SOURCE_CLOSED"
    assert projection["evidence"] == "source recovered"
    assert projection["operational_yield"] is False
    assert projection["founder_surface_readback"] == "UNVERIFIED"


def test_flow_has_one_canonical_agent_contract_and_no_new_yaml_intent_requirement():
    agents = (ROOT / "AGENTS.md").read_text()
    protocol = (ROOT / "docs" / "protocols" / "FLOW.md").read_text()
    assert "FLOW — Fractal Lifecycle of Operational Work" in agents
    assert "FLOW — Fractal Lifecycle of Operational Work" in protocol
    assert "To add a new capability: write `~/.estate/intents/" not in agents
    assert len(agents.splitlines()) <= 300, "canonical bootstrap must pass agents-md-gate"
    assert agents.count("```toml") == 1, "single live TOML authority"
    assert "AGENTS-pre-FLOW-2026-11-08.md" in agents
    archived = (ROOT / "docs" / "archive" / "AGENTS-pre-FLOW-2026-11-08.md").read_text()
    assert "## 11. Living policy" in archived, "historical laws must be preserved"
    for phrase in ("600", "PREVENTION_GAP", "Founder", "idempotency", "Temporal"):
        assert phrase in protocol

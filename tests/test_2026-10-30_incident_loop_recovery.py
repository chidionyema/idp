"""2026-10-30: the saturated incident loop opened no tickets or dispatches."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

SOURCE = (
    Path(__file__).resolve().parents[1] / "platform/estate/libexec/incident-loop.py"
)
POLICY = Path(__file__).resolve().parents[1] / "catalog/incident-policy.json"
spec = importlib.util.spec_from_file_location("incident_loop_recovery", SOURCE)
assert spec and spec.loader
loop = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loop)


def _incident(name: str) -> dict:
    return {
        "id": loop.fingerprint("ci", "chidionyema/idp", name),
        "source": "ci",
        "repo": "chidionyema/idp",
        "severity": "critical",
        "blast": "main",
        "title": name,
        "url": f"https://example.invalid/{name}",
        "detail": {"run_id": name},
    }


def test_a_full_ledger_still_dispatches_an_existing_p0(monkeypatch, tmp_path):
    db = tmp_path / "incidents.db"
    policy = loop.load_policy(POLICY)
    policy["sense"] = {
        **policy["sense"],
        "max_open_incidents": 1,
        "verify_per_tick": 0,
        "recover_per_tick": 1,
    }
    conn = loop.open_ledger(db)
    old = _incident("older red run")
    loop.record_incident(conn, old, policy)
    conn.close()

    original_open = loop.open_ledger
    monkeypatch.setattr(loop, "open_ledger", lambda: original_open(db))
    monkeypatch.setattr(
        loop, "sense_ci", lambda repo, policy: [_incident("new red run")]
    )
    monkeypatch.setattr(loop, "sense_doors", lambda policy: [])
    monkeypatch.setattr(loop.clock_guard, "commit", lambda: {"state": "ok"})

    def ticket(conn, row_policy, row):
        loop.set_field(conn, row["id"], ticket=7581, event="test ticket")
        return 7581

    seen = []

    def dispatch(conn, row_policy, row):
        seen.append((row["id"], row["ticket"]))
        loop.set_field(conn, row["id"], dispatch_leg="worker", dispatch_ref="7")
        return "worker", "7"

    monkeypatch.setattr(loop, "raise_ticket", ticket)
    monkeypatch.setattr(loop, "dispatch_incident", dispatch)
    monkeypatch.setattr(loop, "verify_incident", lambda *args: False)
    result = loop.tick(policy, "chidionyema/idp")

    assert result["opened"] == 0
    assert result["dispatched"] == 1
    assert seen == [(old["id"], 7581)]
    conn = original_open(db)
    assert loop.get_incident(conn, old["id"])["ticket"] == 7581
    conn.close()


def test_recovery_verifies_an_old_red_run_before_ticketing(monkeypatch, tmp_path):
    db = tmp_path / "incidents.db"
    policy = loop.load_policy(POLICY)
    policy["sense"] = {
        **policy["sense"],
        "max_open_incidents": 1,
        "verify_per_tick": 0,
        "recover_per_tick": 1,
    }
    conn = loop.open_ledger(db)
    old = _incident("already green")
    loop.record_incident(conn, old, policy)
    conn.close()
    original_open = loop.open_ledger
    monkeypatch.setattr(loop, "open_ledger", lambda: original_open(db))
    monkeypatch.setattr(loop, "sense_ci", lambda repo, policy: [])
    monkeypatch.setattr(loop, "sense_doors", lambda policy: [])
    monkeypatch.setattr(loop.clock_guard, "commit", lambda: {"state": "ok"})

    def resolved(conn, policy, row):
        loop.set_field(conn, row["id"], state="closed", event="green")
        return True

    monkeypatch.setattr(loop, "verify_incident", resolved)
    monkeypatch.setattr(
        loop,
        "raise_ticket",
        lambda *args: (_ for _ in ()).throw(AssertionError("unneeded ticket")),
    )
    result = loop.tick(policy, "chidionyema/idp")
    assert result["verified"] == 1
    conn = original_open(db)
    assert loop.get_incident(conn, old["id"])["state"] == "closed"
    conn.close()


def test_report_dispatches_the_new_ticket_not_a_stale_row(monkeypatch, tmp_path):
    conn = loop.open_ledger(tmp_path / "incidents.db")
    monkeypatch.setattr(loop, "open_ledger", lambda: conn)
    original_load = loop.load_policy
    monkeypatch.setattr(loop, "load_policy", lambda: original_load(POLICY))

    def ticket(conn, policy, row):
        loop.set_field(conn, row["id"], ticket=7581)
        return 7581

    seen = []

    def dispatch(conn, policy, row):
        seen.append(row["ticket"])
        return "worker", "7"

    monkeypatch.setattr(loop, "raise_ticket", ticket)
    monkeypatch.setattr(loop, "dispatch_incident", dispatch)
    assert (
        loop.main(
            [
                "report",
                "--title",
                "door lost memory",
                "--severity",
                "critical",
                "--blast",
                "service",
            ]
        )
        == 0
    )
    assert seen == [7581]
    conn.close()


def test_github_ticket_calls_have_repo_context_from_the_one_policy(
    monkeypatch, tmp_path
):
    fake = tmp_path / "gh"
    fake.write_text(
        "#!/bin/sh\n[ \"$GH_REPO\" = 'chidionyema/idp' ] || exit 12\nprintf 'repo-bound\\n'\n"
    )
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}:{os.environ.get('PATH', '')}")
    monkeypatch.chdir(tmp_path)  # launchd has no repository cwd
    rc, out, err = loop.run_gh(["issue", "list"])
    assert (rc, out.strip(), err) == (0, "repo-bound", "")

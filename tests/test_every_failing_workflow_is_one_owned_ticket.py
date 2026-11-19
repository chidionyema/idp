"""idp#8301: anything that fails in the estate gets one response, laptop or no laptop.

Measured before this change: argon-sync's drive bridge 47/47 red, gemini-sync's AI Studio
recovery 12/12, argon's canonical IO 11/11 -- no ticket, no alert. The loop ran only from
launchd on the Mac, sensed one repo, and keyed a CI incident on the run id, so a red cron opened
a P0 per run. Each test below fails on the code before the change.
"""

from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
LIBEXEC = ROOT / "platform" / "estate" / "libexec" / "incident-loop.py"
POLICY = ROOT / "catalog" / "incident-policy.json"
WORKFLOW = ROOT / ".github" / "workflows" / "incident-loop.yml"


def _load():
    spec = importlib.util.spec_from_file_location("incident_loop_cloud", LIBEXEC)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


loop = _load()


@pytest.fixture()
def policy():
    return loop.load_policy(POLICY)


def _run(run_id: int, name: str = "Genesis drive bridge", branch: str = "main") -> dict:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "id": run_id,
        "name": name,
        "head_branch": branch,
        "conclusion": "failure",
        "event": "schedule",
        "created_at": now,
        "html_url": f"https://example.invalid/{run_id}",
        "run_attempt": 1,
    }


def test_one_failing_workflow_is_one_incident_not_one_per_run(monkeypatch, policy):
    runs = [_run(3), _run(2), _run(1), _run(9, name="ci")]
    monkeypatch.setattr(loop, "run_gh", lambda args: (0, json.dumps(runs), ""))
    incidents = loop.sense_ci("chidionyema/argon-sync", policy)
    drive = [i for i in incidents if i["detail"]["workflow"] == "Genesis drive bridge"]
    assert len(drive) == 1, drive
    assert drive[0]["detail"]["run_id"] == 3, "the newest run carries the class"
    assert drive[0]["title"].startswith("argon-sync: "), drive[0]["title"]
    assert len(incidents) == 2


def test_a_recurrence_of_a_closed_class_reopens_it(tmp_path, monkeypatch, policy):
    monkeypatch.setattr(loop, "LEDGER", tmp_path / "incidents.db")
    conn = loop.open_ledger()
    incident = {
        "id": loop.fingerprint(
            "ci", "chidionyema/argon-sync", "Genesis drive bridge@main"
        ),
        "source": "ci",
        "repo": "chidionyema/argon-sync",
        "severity": "critical",
        "blast": "main",
        "title": "argon-sync: Genesis drive bridge failed on main",
        "url": "u",
        "detail": {"run_id": 10, "workflow": "Genesis drive bridge", "branch": "main"},
    }
    loop.record_incident(conn, incident, policy)
    conn.execute(
        "UPDATE incidents SET state = 'closed', ticket = 77, closed_at = 'x' WHERE id = ?",
        (incident["id"],),
    )
    conn.commit()
    same = loop.record_incident(conn, incident, policy)
    assert same["state"] == "closed", "the same run seen again is not a recurrence"
    incident["detail"] = dict(incident["detail"], run_id=11)
    row = loop.record_incident(conn, incident, policy)
    assert row["state"] == "open", "a newer failing run of a closed class reopens it"
    assert row["ticket"] is None, "a recurrence gets a fresh ticket"


def test_cloud_mode_never_claims_a_dispatch_nothing_holds(monkeypatch, policy):
    monkeypatch.setenv("ESTATE_INCIDENT_DISPATCH", "0")
    called = []
    monkeypatch.setattr(
        loop, "push_worker_task", lambda *a, **k: called.append(a) or ("worker", "1")
    )
    monkeypatch.setattr(loop, "_sb_list", lambda *a, **k: called.append(a) or (1, []))
    assert loop.dispatch_incident(None, policy, {"repo": "r", "ticket": 1}) == ("", "")
    assert not called


def test_the_cloud_schedule_senses_every_estate_repo():
    policy = json.loads(POLICY.read_text())
    repos = set(policy["cloud_repos"])
    for repo in ("idp", "argon", "argon-sync", "gemini-sync", "geaistudio"):
        assert f"chidionyema/{repo}" in repos, repo
    flow = yaml.safe_load(WORKFLOW.read_text())
    on = flow.get("on", flow.get(True))
    assert on["schedule"], "the loop must run with no laptop and no person"
    job = flow["jobs"]["tick"]
    assert job["runs-on"] == "ubuntu-24.04", "cloud runner, not the Mac"
    assert job["env"]["ESTATE_INCIDENT_DISPATCH"] == "0"
    text = WORKFLOW.read_text()
    assert "refs/incidents/state" in text, "the ledger must outlive the runner"
    assert "cloud_repos" in text, "the repo list has one source"
    assert "api.telegram.org" in text, "a new ticket reaches the founder"

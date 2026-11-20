"""idp#8334: an agent acting under the founder's login is a critical incident, every tick.

QUAD law: agents never operate under the founder's account. Measured 2026-11-19: 37 of the last
100 commits on idp main and 10 agent-declared PRs carried his login. Each test fails on main,
where the loop has no identity sensor.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "incident_loop_identity", ROOT / "platform/estate/libexec/incident-loop.py"
)
loop = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loop)
POLICY = loop.load_policy(ROOT / "catalog/incident-policy.json")


def _gh(commits, pulls):
    def run_gh(args, timeout=45):
        path = args[1]
        if "/commits?" in path:
            return 0, json.dumps(commits), ""
        return 0, json.dumps(pulls), ""

    return run_gh


def test_each_agent_acting_as_the_founder_is_one_critical_incident(monkeypatch):
    now = "2099-01-01T00:00:00Z"
    commits = [
        {"sha": "a" * 40, "message": "x\n\nAgent: opencode\n", "at": now},
        {"sha": "b" * 40, "message": "y\n\nAgent: opencode\n", "at": now},
        {"sha": "c" * 40, "message": "founder's own work", "at": now},
    ]
    pulls = [
        {"number": 7, "login": "chidionyema", "body": "Agent: dsh-x", "at": now},
        {"number": 8, "login": "estate-agents[bot]", "body": "Agent: dsh-x", "at": now},
    ]
    monkeypatch.setattr(loop, "run_gh", _gh(commits, pulls))
    found = {
        i["detail"]["agent"]: i for i in loop.sense_identity("chidionyema/idp", POLICY)
    }
    assert set(found) == {"opencode", "dsh-x"}, (
        "the founder's own work is not an incident"
    )
    assert found["opencode"]["detail"]["count"] == 2
    assert found["dsh-x"]["detail"]["examples"] == ["#7"], (
        "the App's PR is not his login"
    )
    assert all(i["severity"] == "critical" for i in found.values())


def test_the_sensor_runs_on_every_tick():
    src = (ROOT / "platform/estate/libexec/incident-loop.py").read_text()
    tick = src.split("def tick(", 1)[1]
    assert "sense_identity(repo, policy)" in tick


def test_the_founder_login_is_policy_not_code():
    assert json.loads((ROOT / "catalog/incident-policy.json").read_text())["identity"][
        "founder_login"
    ]

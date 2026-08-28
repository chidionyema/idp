"""Binds features/drills/front-door-login-drill.feature (crew#307, crew#297): bin/idp-drill-heartbeat
runs for real against a fake gh, through the helper tests/test_incident_drill_never_scheduled.py
proves, and .github/workflows/drill-heartbeat.yml is read for its cron and its P0 title."""
import importlib.util
from pathlib import Path

import pytest
import yaml
from pytest_bdd import given, scenarios, then, when

scenarios("features/drills/front-door-login-drill.feature")

IDP = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location("incident_heartbeat", IDP / "tests/test_incident_drill_never_scheduled.py")
incident = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(incident)


@pytest.fixture
def state() -> dict:
    return {}


@given("the newest successful login-drill run is older than 20 minutes")
def _stale(state: dict) -> None:
    state["age"] = 41


@when("bin/idp-drill-heartbeat grades login-drill.yml")
def _grade(state: dict, tmp_path: Path) -> None:
    for d in ("stale", "none", "blind", "fresh"):
        (tmp_path / d).mkdir(exist_ok=True)
    state["stale"] = incident._run(tmp_path / "stale", state["age"])
    state["none"] = incident._run(tmp_path / "none", None)
    state["blind"] = incident._run(tmp_path / "blind", None, rc=1)
    state["fresh"] = incident._run(tmp_path / "fresh", 4)


@then("it prints FAIL with the age, the run id and the dispatch command")
def _fail(state: dict) -> None:
    r = state["stale"]
    assert r.returncode == 1, r.stdout + r.stderr
    assert "FAIL    heartbeat  login-drill.yml  last success 41 min ago > 20 (run 999)" in r.stdout, r.stdout
    assert "gh workflow run login-drill.yml -R o/r" in r.stdout, r.stdout


@then("a run with no successful run on record is FAIL, and an unreadable API is BLIND, never ok")
def _none_blind(state: dict) -> None:
    assert state["none"].returncode == 1 and "no successful run on record" in state["none"].stdout, state["none"].stdout
    assert state["blind"].returncode == 2 and state["blind"].stdout.startswith("BLIND   heartbeat"), state["blind"].stdout
    assert state["fresh"].returncode == 0 and state["fresh"].stdout.startswith("ok      heartbeat"), state["fresh"].stdout


@then('drill-heartbeat.yml runs every 15 minutes and opens or comments "P0: login drill failed" on FAIL')
def _workflow(state: dict) -> None:
    wf = yaml.safe_load((IDP / ".github/workflows/drill-heartbeat.yml").read_text())
    on = wf.get("on") or wf.get(True)
    crons = [s["cron"] for s in on["schedule"]]
    assert any(c.split()[0].endswith("/15") for c in crons), crons
    text = (IDP / ".github/workflows/drill-heartbeat.yml").read_text()
    assert 'gh issue create --title "P0: login drill failed"' in text and "gh issue comment" in text

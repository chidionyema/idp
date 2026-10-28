"""The critical-function spine: the detector, the incident, the alert and the invocation.

WHY THESE TESTS. 2026-10-28. The estate had no watcher for its critical functions: the disk
watcher was alive, ticking, and freeing nothing, and nothing in the estate could raise an
incident, alert a human, or wake an agent to fix a dead function. The spine is the estate-wide
answer, and it is only an answer if it can FAIL. So the tests below are mostly about failure:
a stale heartbeat must be a FAIL with a structured record, a probe that cannot be measured must be
a BLIND and not a quiet PASS, and a function that stays dead must not wake an agent every minute.

The detector takes its state directory, its registry and its invocation door from the
environment, so every test runs against a temporary estate and never touches the real one.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "platform"
    / "estate"
    / "libexec"
    / "critical-watch.py"
)


def _iso(offset_s: float = 0.0) -> str:
    return datetime.fromtimestamp(
        datetime.now(timezone.utc).timestamp() + offset_s, timezone.utc
    ).strftime("%Y-%m-%dT%H:%M:%SZ")


def _state(tmp_path: Path) -> Path:
    state = tmp_path / "estate"
    (state / "heartbeats").mkdir(parents=True, exist_ok=True)
    (state / "incidents").mkdir(parents=True, exist_ok=True)
    (state / "alerts").mkdir(parents=True, exist_ok=True)
    return state


def _registry(tmp_path: Path, body: dict) -> Path:
    path = tmp_path / "critical-functions.json"
    path.write_text(json.dumps(body))
    return path


def _invoke_stub(tmp_path: Path) -> Path:
    """A stand-in for the invocation door that records what it was asked to do."""
    calls = tmp_path / "invoke-calls.jsonl"
    stub = tmp_path / "agent-invoke.sh"
    stub.write_text(
        "#!/bin/bash\n"
        f'printf "%s\\n" "$2" >> {calls}\n'
        'echo \'{"invoked": true, "invoked_via": "stub"}\'\n'
    )
    stub.chmod(0o755)
    return stub


def _run(state: Path, registry: Path, stub: Path | None = None, *args: str):
    env = {
        **os.environ,
        "ESTATE_STATE_DIR": str(state),
        "CRITICAL_WATCH_INVOKE": str(stub) if stub else str(state / "no-invoke.sh"),
    }
    cmd = [sys.executable, str(SCRIPT), "--registry", str(registry), *args]
    return subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=60)


def _function(**over) -> dict:
    fn = {
        "id": "thing",
        "title": "the thing",
        "severity": "critical",
        "liveness": {
            "type": "heartbeat_file",
            "path": "~/.estate/heartbeats/thing.json",
            "max_age_s": 180,
        },
        "goal": {
            "type": "heartbeat_field_min",
            "path": "~/.estate/heartbeats/thing.json",
            "field": "count",
            "min": 1,
        },
        "remediation": {
            "runner": "claude",
            "repo": "/tmp",
            "budget": 5,
            "task": "bring the thing back",
        },
    }
    fn.update(over)
    return fn


def _write_heartbeat(state: Path, at: str | None = None, count: int = 1) -> Path:
    path = state / "heartbeats" / "thing.json"
    path.write_text(
        json.dumps({"at": at or _iso(), "state": "healthy", "count": count})
    )
    return path


def test_a_healthy_function_passes_and_raises_nothing(tmp_path):
    state = _state(tmp_path)
    _write_heartbeat(state)
    reg = _registry(tmp_path, {"functions": [_function()]})
    r = _run(state, reg)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PASS" in r.stdout, r.stdout
    assert not list((state / "incidents").glob("thing-*.json")), (
        "a healthy function must raise no incident"
    )


def test_a_stale_heartbeat_fails_and_raises_a_structured_incident(tmp_path):
    state = _state(tmp_path)
    _write_heartbeat(state, at=_iso(-3600))
    reg = _registry(tmp_path, {"functions": [_function()]})
    stub = _invoke_stub(tmp_path)
    r = _run(state, reg, stub)
    assert r.returncode == 1, r.stdout + r.stderr
    incidents = list((state / "incidents").glob("thing-*.json"))
    assert len(incidents) == 1, incidents
    incident = json.loads(incidents[0].read_text())
    assert incident["function"] == "thing"
    assert incident["verdict"] == "FAIL"
    assert incident["evidence"]["liveness"]["verdict"] == "FAIL"
    assert incident["evidence"]["liveness"]["evidence"]["age_s"] > 180
    # the ledger and the summary are the estate's record
    ledger = (state / "incidents" / "ledger.jsonl").read_text().strip().splitlines()
    assert len(ledger) == 1
    assert (
        json.loads((state / "incidents" / "latest.json").read_text())["function"]
        == "thing"
    )
    # the alert reached the inbox every surface reads
    inbox = (state / "alerts" / "inbox.jsonl").read_text().strip().splitlines()
    assert any(json.loads(line)["source"] == "critical-watch" for line in inbox)


def test_a_dead_function_wakes_an_agent_with_the_structured_data(tmp_path):
    state = _state(tmp_path)
    _write_heartbeat(state, at=_iso(-3600))
    reg = _registry(tmp_path, {"functions": [_function()]})
    calls = tmp_path / "invoke-calls.jsonl"
    stub = tmp_path / "agent-invoke.sh"
    stub.write_text(
        "#!/bin/bash\n"
        f'printf "%s\\n" "$2" >> {calls}\n'
        'echo \'{"invoked": true, "invoked_via": "stub"}\'\n'
    )
    stub.chmod(0o755)
    r = _run(state, reg, stub)
    assert r.returncode == 1, r.stdout + r.stderr
    assert calls.exists(), "the agent was never invoked"
    payload = json.loads(calls.read_text().strip())
    assert payload["task"], "the agent was invoked without a task"
    incident = payload["incident"]
    assert incident["function"] == "thing"
    assert incident["evidence"]["liveness"]["evidence"]["age_s"] > 180
    # the invocation is recorded in the incident, with the lane it used
    latest = json.loads((state / "incidents" / "latest.json").read_text())
    assert latest["invocation"]["invoked"] is True
    assert latest["invocation"]["invoked_via"] == "stub"


def test_an_unmeasurable_probe_is_blind_and_does_not_wake_an_agent(tmp_path):
    state = _state(tmp_path)
    # the heartbeat file exists but its 'at' is not a timestamp: the probe cannot be measured
    (state / "heartbeats" / "thing.json").write_text(
        json.dumps({"at": "not-a-time", "count": 1})
    )
    reg = _registry(tmp_path, {"functions": [_function()]})
    calls = tmp_path / "invoke-calls.jsonl"
    stub = tmp_path / "agent-invoke.sh"
    stub.write_text(f"#!/bin/bash\necho called >> {calls}\n")
    stub.chmod(0o755)
    r = _run(state, reg, stub)
    assert r.returncode == 2, r.stdout + r.stderr
    assert "BLIND" in r.stdout, r.stdout
    assert not calls.exists(), (
        "a BLIND probe must not wake an agent: the function may be well"
    )


def test_a_live_function_that_misses_its_goal_is_failing(tmp_path):
    """The case the old disk watcher was: alive, ticking, and not doing its job."""
    state = _state(tmp_path)
    _write_heartbeat(state, count=0)
    reg = _registry(tmp_path, {"functions": [_function()]})
    r = _run(state, reg, _invoke_stub(tmp_path))
    assert r.returncode == 1, r.stdout + r.stderr
    incident = json.loads(
        list((state / "incidents").glob("thing-*.json"))[0].read_text()
    )
    assert incident["verdict"] == "FAIL"
    assert incident["evidence"]["goal"]["verdict"] == "FAIL"
    assert incident["evidence"]["liveness"]["verdict"] == "PASS"


def test_a_function_that_stays_dead_does_not_wake_an_agent_storm(tmp_path):
    state = _state(tmp_path)
    _write_heartbeat(state, at=_iso(-3600))
    reg = _registry(tmp_path, {"functions": [_function()]})
    calls = tmp_path / "invoke-calls.jsonl"
    stub = tmp_path / "agent-invoke.sh"
    stub.write_text(
        f"#!/bin/bash\nprintf '%s\\n' \"$2\" >> {calls}\necho '{{\"invoked\": true}}'\n"
    )
    stub.chmod(0o755)
    first = _run(state, reg, stub)
    assert first.returncode == 1
    assert len(calls.read_text().strip().splitlines()) == 1
    # the second failure is inside the backoff: the incident is still recorded, nobody is woken
    second = _run(state, reg, stub)
    assert second.returncode == 1
    assert len(calls.read_text().strip().splitlines()) == 1, (
        "the agent was woken again inside the backoff"
    )
    assert len(list((state / "incidents").glob("thing-*.json"))) == 1


def test_a_recovered_function_clears_its_backoff(tmp_path):
    state = _state(tmp_path)
    _write_heartbeat(state, at=_iso(-3600))
    reg = _registry(tmp_path, {"functions": [_function()]})
    _run(state, reg, _invoke_stub(tmp_path))
    state_file = state / "incidents" / "state.json"
    assert json.loads(state_file.read_text())["thing"]["backoff_s"] > 300
    _write_heartbeat(state)  # it comes back
    _run(state, reg, _invoke_stub(tmp_path))
    assert "thing" not in json.loads(state_file.read_text())


def test_a_missing_registry_is_blind_rather_than_a_pass(tmp_path):
    state = _state(tmp_path)
    r = _run(state, tmp_path / "nope.json")
    assert r.returncode == 2, r.stdout + r.stderr
    assert "BLIND" in r.stdout


def test_the_spine_writes_its_own_heartbeat(tmp_path):
    state = _state(tmp_path)
    _write_heartbeat(state)
    reg = _registry(tmp_path, {"functions": [_function()]})
    _run(state, reg)
    hb = json.loads((state / "heartbeats" / "critical-watch.json").read_text())
    assert hb["state"] == "ok"
    assert hb["counts"]["PASS"] == 1

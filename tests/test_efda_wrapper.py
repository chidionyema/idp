"""The L1 wrapper: checkpoint, capture, resume, read-first."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time

import pytest

from efda.store import ArtifactStore, RedisClient

from efda_fake_redis import FakeRedisServer

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture()
def sink():
    server = FakeRedisServer()
    yield server
    server.stop()


def wrapper_env(sink, tmp_path, runner_id, **extra):
    env = dict(os.environ)
    env.update(
        {
            "EFDA_REDIS_HOST": sink.host if sink else "127.0.0.1",
            "EFDA_REDIS_PORT": str(sink.port) if sink else "1",
            "EFDA_RUNNER_ID": runner_id,
            "EFDA_COMPONENT_ID": "efda-test-agent",
            "EFDA_COMPONENT_CLASS": "efda-test-agent",
            "EFDA_COMPONENT_KIND": "agent",
            "EFDA_STATE_FILE": str(tmp_path / "state.json"),
            "EFDA_WAL_DIR": str(tmp_path / "wal"),
            "EFDA_CHECKPOINT_INTERVAL": "1",
            "EFDA_NAMESPACE": "default",
            "EFDA_CLUSTER": "oke",
            "PYTHONPATH": REPO,
        }
    )
    env.update(extra)
    return env


def start_wrapper(env, command=("sleep", "300")):
    return subprocess.Popen(  # noqa: S603 -- the command is the point
        [sys.executable, "-m", "efda", "wrapper", "--", *command],
        env=env,
        cwd=REPO,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def test_a_checkpoint_is_written_on_the_tick(sink, tmp_path):
    env = wrapper_env(sink, tmp_path, "efda-test-run-001")
    state = tmp_path / "state.json"
    state.write_text(json.dumps({"completed_steps": ["step_a"]}))
    process = start_wrapper(env, ("sleep", "30"))
    try:
        deadline = time.time() + 15
        key = "efda:ckpt:efda-test-run-001"
        while time.time() < deadline and key not in sink.data:
            time.sleep(0.2)
        assert key in sink.data
        checkpoint = json.loads(sink.data[key])
        assert checkpoint["completed_steps"] == ["step_a"]
        assert checkpoint["runner_id"] == "efda-test-run-001"
    finally:
        process.kill()
        process.wait(timeout=10)


def test_a_sigterm_writes_a_checkpoint_and_exits_143(sink, tmp_path):
    env = wrapper_env(sink, tmp_path, "efda-test-run-002")
    process = start_wrapper(env, ("sleep", "300"))
    time.sleep(1.5)
    process.send_signal(signal.SIGTERM)
    process.wait(timeout=15)
    assert process.returncode == 143
    assert "efda:ckpt:efda-test-run-002" in sink.data


def test_a_sigkill_leaves_a_hard_kill_artifact_and_the_checkpoint(sink, tmp_path):
    env = wrapper_env(sink, tmp_path, "efda-test-run-003")
    state = tmp_path / "state.json"
    state.write_text(json.dumps({"completed_steps": ["step_a", "step_b"]}))
    process = start_wrapper(env, ("sleep", "300"))
    deadline = time.time() + 15
    while time.time() < deadline and "efda:ckpt:efda-test-run-003" not in sink.data:
        time.sleep(0.2)
    assert "efda:ckpt:efda-test-run-003" in sink.data
    process.kill()
    process.wait(timeout=10)

    deadline = time.time() + 20
    artifact_key = None
    while time.time() < deadline:
        candidates = [
            key
            for key in sink.data
            if key.startswith("efda:evidence:") and key.endswith(":artifact")
        ]
        if candidates:
            artifact_key = candidates[0]
            break
        time.sleep(0.3)
    assert artifact_key, "the kill-observer wrote no artifact"
    artifact = json.loads(sink.data[artifact_key])
    assert artifact["failure_boundary"]["failure_class"] == "hard_kill"
    assert artifact["raw_evidence"]["capture_method"] == "supervisor_wrapper"
    assert artifact["identity"]["runner_id"] == "efda-test-run-003"
    checkpoint = json.loads(sink.data["efda:ckpt:efda-test-run-003"])
    assert checkpoint["completed_steps"] == ["step_a", "step_b"]


def test_an_unreachable_sink_falls_back_to_the_wal(tmp_path):
    env = wrapper_env(None, tmp_path, "efda-test-run-004")
    env["EFDA_REDIS_HOST"] = "127.0.0.1"
    env["EFDA_REDIS_PORT"] = "1"
    process = start_wrapper(env, ("sh", "-c", "exit 3"))
    process.wait(timeout=15)
    wal = tmp_path / "wal"
    assert wal.exists()
    names = list(wal.glob("*"))
    assert names, "the WAL holds no entry"


def test_the_read_first_gate_refuses_a_relaunch_without_an_artifact(sink, tmp_path):
    env = wrapper_env(sink, tmp_path, "efda-test-run-005", EFDA_RESUME="1")
    process = start_wrapper(env, ("sh", "-c", "echo should-not-run"))
    stdout, _stderr = process.communicate(timeout=15)
    assert process.returncode == 75
    assert "should-not-run" not in stdout
    artifacts = [key for key in sink.data if key.startswith("efda:evidence:")]
    assert artifacts
    violation = json.loads(sink.data[artifacts[0]])
    assert violation["failure_boundary"]["failure_class"] == "schema_violation"


def test_the_read_first_gate_lets_a_relaunch_proceed_after_an_artifact(sink, tmp_path):
    store = ArtifactStore(RedisClient(sink.host, sink.port))
    from efda.contract import build_artifact

    artifact = build_artifact(
        component_id="efda-test-agent",
        component_class="efda-test-agent",
        component_kind="agent",
        runner_id="efda-test-run-006",
        failure_class="exit_nonzero",
        attempted_operation="run_to_completion",
        invariant_broken="exit_zero",
        triggering_step="process_exit",
        capture_method="supervisor_wrapper",
        payloads=[{"kind": "checkpoint", "uri": "efda:ckpt:efda-test-run-006"}],
        cluster="oke",
        namespace="default",
    )
    store.write(artifact)
    env = wrapper_env(sink, tmp_path, "efda-test-run-006", EFDA_RESUME="1")
    process = start_wrapper(env, ("sh", "-c", "echo resumed"))
    stdout, _stderr = process.communicate(timeout=15)
    assert "artifact_read=true" in stdout
    assert "resumed" in stdout

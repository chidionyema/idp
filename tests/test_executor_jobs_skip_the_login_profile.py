"""A job runs in the login environment without re-reading the login profile (2026-10-02).

WHY. Every job ran `bash -lc`, so every job re-read ~/.bash_profile (nvm, a keychain lookup,
1,627 traced lines). Under load the profile outlived the 60 s ceiling and `echo hello` failed for
every agent. Measured with the CPU saturated: `bash -lc true` 15.5 s, `bash -c true` 0.08 s.
The first test fails on the old daemon: its argv carries `-lc`.
"""

import importlib.util
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "platform" / "executor"))
spec = importlib.util.spec_from_file_location(
    "executor_daemon", ROOT / "platform/executor/daemon.py"
)
daemon = importlib.util.module_from_spec(spec)
spec.loader.exec_module(daemon)


def test_a_job_does_not_start_a_login_shell(tmp_path):
    argv = daemon._runner_argv("exec-1-1", "echo hello", str(tmp_path), 60)
    assert argv[-3:] == ["bash", "-c", "echo hello"]
    assert "-lc" not in argv


def test_jobs_get_the_cached_login_environment_without_waiting_for_a_read(monkeypatch):
    reads = []
    monkeypatch.setattr(
        daemon,
        "_read_login_env",
        lambda: reads.append(1) or {"PATH": "/login/bin", "X": "1"},
    )
    monkeypatch.setattr(
        daemon,
        "_login_env_cache",
        {"env": {"PATH": "/cached/bin"}, "at": time.time(), "refreshing": False},
    )
    assert daemon._login_env()["PATH"] == "/cached/bin"
    assert reads == []  # fresh: no read


def test_a_stale_environment_is_refreshed_in_the_background(monkeypatch):
    monkeypatch.setattr(daemon, "_read_login_env", lambda: {"PATH": "/login/bin"})
    monkeypatch.setattr(
        daemon,
        "_login_env_cache",
        {"env": {"PATH": "/old/bin"}, "at": 0.0, "refreshing": False},
    )
    assert (
        daemon._login_env()["PATH"] == "/old/bin"
    )  # the caller is never blocked by the read
    for _ in range(50):
        if daemon._login_env_cache["env"]["PATH"] == "/login/bin":
            break
        time.sleep(0.02)
    assert daemon._login_env_cache["env"]["PATH"] == "/login/bin"


def test_an_unreadable_profile_falls_back_to_the_daemon_environment(monkeypatch):
    monkeypatch.setattr(
        daemon, "_login_env_cache", {"env": None, "at": 0.0, "refreshing": True}
    )
    assert daemon._login_env()["PATH"] == daemon.os.environ["PATH"]


def test_a_failed_profile_is_not_captured(monkeypatch):
    import subprocess

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a, 1, b"PATH=/half\0", b""),
    )
    assert daemon._read_login_env() is None


def test_a_refused_thread_does_not_freeze_refresh(monkeypatch):
    class NoThread:
        def __init__(self, *a, **k):
            pass

        def start(self):
            raise RuntimeError("can't start new thread")

    monkeypatch.setattr(daemon.threading, "Thread", NoThread)
    monkeypatch.setattr(
        daemon,
        "_login_env_cache",
        {"env": {"PATH": "/old/bin"}, "at": 0.0, "refreshing": False},
    )
    assert daemon._login_env()["PATH"] == "/old/bin"
    assert daemon._login_env_cache["refreshing"] is False


def test_the_job_is_spawned_with_the_login_environment(monkeypatch, tmp_path):
    import subprocess

    seen = {}
    monkeypatch.setattr(
        daemon, "_login_env", lambda: {"PATH": "/login/bin", "MARK": "1"}
    )
    monkeypatch.setattr(
        daemon,
        "execute_command",
        lambda *a, **k: {"accepted": True, "job_id": "exec-1-1", "ceiling_sec": 5},
    )
    monkeypatch.setattr(
        subprocess, "Popen", lambda argv, **k: seen.update(k) or object()
    )
    handler = object.__new__(daemon.Handler)
    out = daemon.Handler._execute(handler, {"command": "echo hi", "cwd": str(tmp_path)})
    assert out["ok"] is True
    assert seen["env"]["MARK"] == "1"

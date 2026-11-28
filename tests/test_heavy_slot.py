"""bin/heavy-slot: one admission point for heavy local work -- real processes, real locks."""

from __future__ import annotations

import os
import pathlib
import signal
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOOL = str(ROOT / "bin" / "heavy-slot")


def _env(tmp_path, **extra):
    return {
        **os.environ,
        "HEAVY_DIR": str(tmp_path / "heavy"),
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        **extra,
    }


def _start(tmp_path, *args, cwd=None, **extra):
    return subprocess.Popen(
        [sys.executable, TOOL, "--min-free-mb", "1", *args],
        cwd=cwd or tmp_path,
        env=_env(tmp_path, **extra),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )


def _held(tmp_path, seconds=30):
    """A running holder, started and confirmed to own the slot."""
    marker = tmp_path / "held"
    proc = _start(
        tmp_path, "--no-share", "--", "sh", "-c", f"touch {marker}; sleep {seconds}"
    )
    for _ in range(900):
        if marker.exists():
            return proc
        time.sleep(0.1)
    proc.kill()
    raise AssertionError("the holder never started")


def test_two_heavy_commands_take_turns_and_never_overlap(tmp_path):
    log = tmp_path / "log"
    script = f"echo start >> {log}; sleep 1; echo end >> {log}"
    a = _start(tmp_path, "--no-share", "--", "sh", "-c", script)
    b = _start(tmp_path, "--no-share", "--", "sh", "-c", script)
    assert a.wait(120) == 0 and b.wait(120) == 0
    assert log.read_text().split() == ["start", "end", "start", "end"]


def test_a_killed_holder_frees_the_slot_at_once(tmp_path):
    holder = _held(tmp_path)
    waiter = _start(tmp_path, "--no-share", "--", "sh", "-c", "echo ran")
    time.sleep(1)
    assert waiter.poll() is None  # it is waiting for its turn, not running
    os.killpg(holder.pid, signal.SIGKILL)  # the wrapper and its command both die
    out, _ = waiter.communicate(timeout=120)
    assert waiter.returncode == 0 and "ran" in out


def test_the_wait_is_bounded_and_says_so_without_running_anything(tmp_path):
    holder = _held(tmp_path)
    try:
        waiter = _start(
            tmp_path, "--no-share", "--wait", "1", "--", "sh", "-c", "touch ran"
        )
        _, err = waiter.communicate(timeout=120)
        assert waiter.returncode == 75 and "TIMED OUT" in err
        assert not (tmp_path / "ran").exists()
    finally:
        os.killpg(holder.pid, signal.SIGKILL)


def test_it_refuses_to_start_with_no_disk_and_says_why(tmp_path):
    proc = subprocess.run(
        [sys.executable, TOOL, "--min-free-mb", "999999999", "--", "true"],
        env=_env(tmp_path),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 75 and "REFUSED" in proc.stderr and "floor" in proc.stderr


def _repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    env = _env(tmp_path, GIT_AUTHOR_NAME="m", GIT_AUTHOR_EMAIL="m@e.test")
    env.update(GIT_COMMITTER_NAME="m", GIT_COMMITTER_EMAIL="m@e.test")
    for args in (["init", "-q"], ["commit", "-q", "--allow-empty", "-m", "seed"]):
        subprocess.run(["git", *args], cwd=repo, env=env, check=True)
    return repo


def test_a_passing_result_is_shared_and_not_run_twice(tmp_path):
    repo = _repo(tmp_path)
    count = tmp_path / "count"
    cmd = ["--", "sh", "-c", f"echo ran >> {count}; echo the-output"]
    first = _start(tmp_path, *cmd, cwd=repo)
    out1, _ = first.communicate(timeout=120)
    second = _start(tmp_path, *cmd, cwd=repo)
    out2, err2 = second.communicate(timeout=120)
    assert first.returncode == 0 and second.returncode == 0
    assert count.read_text().split() == ["ran"]  # run once
    assert "the-output" in out2 and "SHARED RESULT" in err2


def test_changed_code_is_not_served_a_stale_result(tmp_path):
    repo = _repo(tmp_path)
    count = tmp_path / "count"
    cmd = ["--", "sh", "-c", f"echo ran >> {count}"]
    _start(tmp_path, *cmd, cwd=repo).communicate(timeout=120)
    (repo / "new.txt").write_text("a change\n")
    _start(tmp_path, *cmd, cwd=repo).communicate(timeout=120)
    assert count.read_text().split() == ["ran", "ran"]


def test_a_failure_is_never_shared_so_it_retries(tmp_path):
    repo = _repo(tmp_path)
    count = tmp_path / "count"
    cmd = ["--", "sh", "-c", f"echo ran >> {count}; exit 3"]
    first = _start(tmp_path, *cmd, cwd=repo)
    first.communicate(timeout=120)
    second = _start(tmp_path, *cmd, cwd=repo)
    second.communicate(timeout=120)
    assert first.returncode == 3 and second.returncode == 3
    assert count.read_text().split() == ["ran", "ran"]


def test_a_waiter_behind_a_running_twin_is_handed_its_result(tmp_path):
    repo = _repo(tmp_path)
    count = tmp_path / "count"
    cmd = ["--", "sh", "-c", f"echo ran >> {count}; sleep 2"]
    a = _start(tmp_path, *cmd, cwd=repo)
    time.sleep(0.5)
    b = _start(tmp_path, *cmd, cwd=repo)  # the same work, asked for while a runs it
    _, _ = a.communicate(timeout=120)
    _, err = b.communicate(timeout=120)
    assert count.read_text().split() == ["ran"]
    assert b.returncode == 0 and "SHARED RESULT" in err


def test_status_shows_the_running_holder(tmp_path):
    holder = _held(tmp_path)
    try:
        proc = subprocess.run(
            [sys.executable, TOOL, "--status"],
            env=_env(tmp_path),
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert "RUNNING" in proc.stdout and "pid " in proc.stdout
    finally:
        os.killpg(holder.pid, signal.SIGKILL)

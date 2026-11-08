"""Regression: Git lane handover is a measured remote SHA, not a green local process.

Real bare origins and detached worktrees exercise the same shell from the
estate's existing lane-submit intent. No GitHub/Bitwarden key or live endpoint.
The intentionally short test observation window does not modify production.
"""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import time
from pathlib import Path

import pytest
import yaml

INTENT = Path(__file__).resolve().parents[1] / "platform/estate/intents/lane-submit.yaml"


def git(cwd: Path, *args: str) -> str:
    p = subprocess.run(["git", *args], cwd=cwd, text=True,
                       capture_output=True, timeout=20, check=True)
    return p.stdout.strip()


@pytest.fixture()
def checkout(tmp_path: Path) -> Path:
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "--bare", str(origin))
    work = tmp_path / "work"
    git(tmp_path, "clone", str(origin), str(work))
    git(work, "config", "user.name", "Test Agent")
    git(work, "config", "user.email", "agent@example.test")
    git(work, "checkout", "-b", "main")
    (work / "a.txt").write_text("base\n")
    git(work, "add", "a.txt")
    git(work, "commit", "-m", "base")
    git(work, "push", "origin", "main")
    git(work, "checkout", "--detach", "HEAD")
    (work / "a.txt").write_text("candidate\n")
    git(work, "add", "a.txt")
    git(work, "commit", "-m", "source-only candidate")
    assert subprocess.run(["git", "symbolic-ref", "-q", "--short", "HEAD"],
                          cwd=work, capture_output=True).returncode != 0
    return work


def push_command(lane: str = "", *, fast_window: bool = False) -> str:
    doc = yaml.safe_load(INTENT.read_text())
    step = next(s for s in doc["steps"] if s["name"] == "push the lane")
    # Only substitute known test values. The actual estate executor owns
    # production interpolation; this test exercises the resulting shell.
    cmd = step["cmd"].replace("{{cwd}}", ".").replace("{{lane}}", shlex.quote(lane))
    cmd = cmd.replace("sleep 2", "sleep 0.1")  # local fixture, not a cloud wait
    if fast_window:
        cmd = cmd.replace('while [ "$polls" -lt 18 ]; do',
                          'while [ "$polls" -lt 1 ]; do')
    return cmd


def invoke(work: Path, lane: str = "", *, fast_window: bool = False,
           env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", "-c", push_command(lane, fast_window=fast_window)],
                          cwd=work, capture_output=True, text=True,
                          timeout=25, env=env)


def test_detached_head_submission_needs_no_fake_local_branch(checkout: Path):
    expected_sha = git(checkout, "rev-parse", "HEAD")
    lane = "lane/estate-agent-" + expected_sha[:12]
    res = invoke(checkout)
    assert res.returncode == 0, res.stdout + res.stderr
    assert "ok      lane-submit" in res.stdout
    assert git(checkout, "ls-remote", "--heads", "origin",
               "refs/heads/" + lane).split()[0] == expected_sha
    assert subprocess.run(["git", "symbolic-ref", "-q", "--short", "HEAD"],
                          cwd=checkout, capture_output=True).returncode != 0


def test_explicit_lane_is_honoured_when_detached(checkout: Path):
    res = invoke(checkout, "lane/agent-pi-candidate")
    assert res.returncode == 0, res.stdout + res.stderr
    assert git(checkout, "ls-remote", "--heads", "origin",
               "refs/heads/lane/agent-pi-candidate").split()[0] == git(
                   checkout, "rev-parse", "HEAD")


def test_invalid_ambiguous_lane_does_not_push(checkout: Path):
    result = invoke(checkout, "HEAD")
    assert result.returncode == 2
    assert "REFUSED lane-submit" in result.stderr
    assert git(checkout, "ls-remote", "--heads", "origin",
               "refs/heads/lane/HEAD") == ""


def test_ongoing_push_is_not_reported_as_submitted(checkout: Path):
    hooks = checkout / ".git" / "hooks"
    script = hooks / "pre-push"
    script.write_text("#!/bin/sh\nsleep 3\nexit 1\n")
    script.chmod(0o700)
    result = invoke(checkout, fast_window=True)
    assert result.returncode == 3, result.stdout + result.stderr
    assert "IN-FLIGHT" in result.stderr
    assert "NOT SUBMITTED" in result.stderr
    assert "ok      lane-submit" not in result.stdout
    # Detached push is deliberately allowed to finish independently; the
    # failing hook must not create a branch after this early observation.
    time.sleep(3.3)
    assert git(checkout, "ls-remote", "--heads", "origin",
               "refs/heads/lane/estate-agent-" + git(
                   checkout, "rev-parse", "--short=12", "HEAD")) == ""


def test_push_exit_zero_without_remote_sha_is_unverified(checkout: Path,
                                                          tmp_path: Path):
    # Simulates a misleading local success with the remote visibility missing.
    # All other Git commands are the real executable.
    real_git = shutil.which("git")
    assert real_git
    fakebin = tmp_path / "fakebin"
    fakebin.mkdir()
    fakegit = fakebin / "git"
    fakegit.write_text("#!/bin/sh\n"
                       'case "$1" in\n'
                       '  push|ls-remote) exit 0 ;;\n'
                       "esac\n"
                       f"exec {shlex.quote(real_git)} \"$@\"\n")
    fakegit.chmod(0o700)
    env = dict(os.environ, PATH=str(fakebin) + os.pathsep + os.environ["PATH"])
    result = invoke(checkout, env=env)
    assert result.returncode == 3, result.stdout + result.stderr
    assert "SENT-UNVERIFIED" in result.stderr
    assert "NOT SUBMITTED" in result.stderr
    assert "ok      lane-submit" not in result.stdout


def test_no_unverified_success_paths_return_zero():
    step = yaml.safe_load(INTENT.read_text())["steps"][1]["cmd"]
    in_flight = step.split("if push_alive; then", 1)[1].split(
        'wait "$push_pid" 2>/dev/null; rc=$?', 1)[0]
    sent = step.split('if [ "$rc" -eq 0 ]; then', 1)[1].split(
        "if printf '%s'", 1
    )[0]
    assert "exit 3" in in_flight and "exit 0" not in in_flight
    assert "exit 3" in sent and "exit 0" not in sent
    assert 'git check-ref-format "refs/heads/$lane"' in step
    assert "--no-verify" not in step

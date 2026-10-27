"""The push `lane-submit` starts must outlive the step that starts it, and the step's observation
of the handover must not spend its budget on the network.

Measured 2026-10-27, twice, on this machine: the push step was SIGTERMed at its own 50s ceiling
while `git push` was still running (the pre-push guard alone reports `timing 32s total`), and the
push DIED WITH THE STEP. The lane ref never landed. That is the opposite of what the intent has
claimed since #5814 -- "the push is not killed with it" -- and it is why two hand-submissions of
this change failed to publish anything.

The step's other defect was the same shape: the observation window made EIGHT `git ls-remote`
round trips, at ~5s each on a slow link. Forty seconds of network inside a fifty-second step, so
the step was killed by the network before it could report anything, and the push it was watching
died with it.

So the two mechanisms this file pins down:

  1. the push is started in its OWN SESSION (`os.setsid()`), so nothing that kills the step --
     the step's ceiling, the door's ceiling, the agent's session -- can reach the handover;
  2. the observation window watches the push's OWN PROCESS (a local question, free) and reads
     the remote ref once, at the end.

The first is proved by BEHAVIOUR: the launch block is taken out of the intent file and run in a
sandbox where the step is killed exactly the way the executor kills a step (SIGTERM to the whole
process group). The handover must still complete afterwards. A text assertion cannot prove that;
a text assertion can only prove that the words are still there.
"""

from __future__ import annotations

import os
import re
import signal
import subprocess
import tempfile
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
INTENT = ROOT / "platform/estate/intents/lane-submit.yaml"


def _steps() -> list[dict]:
    return yaml.safe_load(INTENT.read_text())["steps"]


def _push_cmd() -> str:
    return next(s for s in _steps() if "push" in s["name"])["cmd"]


def _code(cmd: str) -> str:
    """The command without its comments. A comment that MENTIONS a thing it does not do is not
    the thing, and a test that cannot tell the difference reads prose as behaviour."""
    return "\n".join(l for l in cmd.splitlines() if not l.strip().startswith("#"))


def _launch_block(cmd: str) -> str:
    """The lines that start the push: the `python3 -c ...` launcher and the `push_pid=$!`."""
    lines = cmd.splitlines()
    start = next(i for i, l in enumerate(lines) if "python3 -c" in l)
    end = next(i for i, l in enumerate(lines) if "push_pid=$!" in l)
    return "\n".join(lines[start : end + 1])


def test_the_push_is_started_in_its_own_session():
    """`git push &` in the step's shell is a child of the step: a SIGTERM to the step's process
    group takes it down with it, and the handover dies with the observation (measured twice on
    2026-10-27 -- the lane ref never landed). `os.setsid()` puts the push in a session of its
    own, which no group kill reaches."""
    cmd = _push_cmd()
    assert "os.setsid()" in cmd, (
        "the push is not started in its own session, so a step killed at its ceiling kills the "
        "handover with it -- the exact failure measured on 2026-10-27"
    )
    assert "os.execvp" in cmd, (
        "the launcher does not exec git, so the step waits on a wrapper instead of on the push "
        "itself and can never read git's own exit code"
    )


def test_the_observation_window_does_not_spend_the_step_on_the_network():
    """The window used to make eight `git ls-remote` round trips at ~5s each -- 40s of network
    inside a 50s step, which is what the step was killed for. The window now watches the push's
    own process, which is free."""
    cmd = _code(_push_cmd())
    loop = re.search(r'while \[ "\$polls" -lt \d+ \]; do(.*?)\n\s*done', cmd, re.DOTALL)
    assert loop, "the push step no longer has an observation window at all"
    body = loop.group(1)
    assert "ls-remote" not in body, (
        "the observation window asks the network again and again; each round trip costs ~5s on a "
        "slow link and the window's budget is 50s (measured 2026-10-27)"
    )
    assert "push_alive" in body, (
        "the observation window does not watch the push's own process, so it has nothing cheap "
        "to observe"
    )


def test_liveness_is_not_measured_with_kill_zero():
    """`kill -0` cannot tell a running child from a ZOMBIE: a finished child that has not been
    waited for still answers kill -0, so a poll on it spins for the whole window on a push that
    had already finished. `ps -o stat=` can: gone means no stat, finished-but-unreaped means the
    stat starts with Z."""
    cmd = _code(_push_cmd())
    assert "kill -0" not in cmd, (
        "the push step polls with kill -0, which succeeds on a zombie: the window would spin "
        "for its whole budget on a push that had already finished"
    )
    assert "ps -p" in cmd and "Z*" in cmd, (
        "the push step has no zombie-aware liveness check"
    )


def test_the_repository_name_is_read_locally():
    """`gh repo view` cost 9.5s on a slow link (measured 2026-10-27) inside a 40s step whose
    claim-gate alone takes 28s. The repository's name is in this checkout's own remote."""
    cmds = "\n".join(s["cmd"] for s in _steps())
    assert "gh repo view" not in cmds, (
        "lane-submit asks the GitHub API for the repository's name it already has in its own "
        "remote: on a slow link that call is the difference between fitting the door and being "
        "killed by it (measured 9.5s, 2026-10-27)"
    )
    assert "remote.origin.url" in cmds, (
        "lane-submit no longer reads the repository's name from the local remote"
    )


def test_the_push_exit_code_is_still_read():
    """The step's verdict distinguishes a rejected push (non-fast-forward) from a sent one, and
    that verdict reads git's exit code. Exec'ing git keeps the same pid, so `wait` still has it."""
    cmd = _push_cmd()
    assert 'wait "$push_pid"' in cmd and "rc=$?" in cmd, (
        "the push step no longer reads git's exit code, so a rejected push and a sent one are "
        "indistinguishable"
    )


def test_a_push_started_by_the_intent_outlives_the_death_of_its_step():
    """The behavioural proof: take the launch block out of the intent file, run it in a sandbox
    where `git` is a stand-in that takes three seconds, and kill the STEP the way the executor
    kills one -- SIGTERM to its whole process group. The handover must still complete.

    Without `os.setsid()` the stand-in dies with the group and the marker never appears; that is
    the 2026-10-27 failure, reproduced."""
    cmd = _push_cmd()
    launch = _launch_block(cmd)
    assert launch, (
        "the intent no longer starts the push in a way this file can exercise"
    )

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        started, done = tmpdir / "started", tmpdir / "done"
        fake_git = tmpdir / "git"
        fake_git.write_text(f"#!/bin/sh\n: > {started}\nsleep 3\n: > {done}\nexit 0\n")
        fake_git.chmod(0o755)
        env = dict(os.environ, PATH=f"{tmpdir}:{os.environ['PATH']}")
        script = f"lane=lane/does-not-matter\npushlog=$(mktemp -t lane-push.XXXXXX)\n{launch}\nwhile :; do sleep 1; done\n"
        # The step gets a process group of its own, exactly as the executor gives a step one.
        step = subprocess.Popen(
            ["sh", "-c", script], env=env, cwd=tmpdir, start_new_session=True
        )

        deadline = time.time() + 20
        while not started.exists() and time.time() < deadline:
            time.sleep(0.05)
        assert started.exists(), (
            "the push never started: the intent's launch block does not run"
        )

        # The executor kills a step by signalling its whole process group. The push is in a
        # session of its own, so this cannot reach it.
        os.killpg(os.getpgid(step.pid), signal.SIGTERM)
        step.wait(timeout=20)

        deadline = time.time() + 20
        while not done.exists() and time.time() < deadline:
            time.sleep(0.1)
        assert done.exists(), (
            "the handover died with the step: killing the step's process group also killed the "
            "push, so the lane ref never lands (measured 2026-10-27)"
        )

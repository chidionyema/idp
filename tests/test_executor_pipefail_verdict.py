"""The executor door must not report a pipe's exit status as a command's verdict.

Measured 2026-11-08, twice in one session, on the same machine:

    git commit ... 2>&1 | tail -5      # pre-commit hook refused (exit 1)
    -> the door reported exit: 0, and the agent pushed an empty commit

    ./bin/idp-ci-guarded-paths ... | tail -3   # the gate printed FAIL and exited 1
    -> the door reported exit: 0, and the verdict was nearly filed as "the gate fails open"

Both times the agent's own `| tail` was what hid the verdict: bash reports the exit status of the
LAST stage of a pipeline, and `tail` exits 0 unconditionally. The door is the estate's promise
that "a door returns an exit code that IS the verdict (0 ok / 3 pending / 4 red / 5 gone)", so a
door that reports 0 for a refused command breaks that promise for every agent on every runtime.

This file is the falsifier for that promise, in both directions:

  * the known-bad shape -- an upstream stage that fails behind a truncating pipe -- must NOT
    come back as success;
  * the known-good shape -- a command that succeeds -- must still come back as success.

It grades the ARGV THE DOOR ACTUALLY BUILDS, by running it, rather than by asserting on a
string: a door that built the right argv but ran it differently would still be caught. The
module is loaded by path and `_runner_argv` is a pure function of its arguments, so nothing here
touches the daemon, a socket, or a shell the estate has not already agreed to run.
"""

from __future__ import annotations

import importlib.util
import pathlib
import subprocess
import sys

import pytest

DAEMON = (
    pathlib.Path(__file__).resolve().parents[1] / "platform" / "executor" / "daemon.py"
)


def _load():
    spec = importlib.util.spec_from_file_location("estate_executor_daemon", DAEMON)
    module = importlib.util.module_from_spec(spec)
    sys.modules["estate_executor_daemon"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def daemon():
    return _load()


def _run(daemon, command: str) -> int:
    """Run the command the way the door runs it, and return the status the door would report."""
    argv = daemon._runner_argv("job-test", command, None, 60)
    # The door runs `bash ... -c <command>`; run exactly that, and read its status.
    bash = argv[argv.index("bash") :]
    return subprocess.run(bash, capture_output=True, text=True, timeout=60).returncode


# The two shapes that hid the verdict, verbatim.
MASKED_FAILURES = [
    # A stage that fails, behind a stage that always succeeds.
    "false | tail -6",
    # The real case: a command refused by a hook, whose output the agent pipes to tail.
    "sh -c 'exit 3' | tail -5",
    # A pipeline whose FIRST stage fails but whose LAST stage succeeds -- the exact shape that
    # reported 0 while the upstream stage had failed.
    "sh -c 'exit 7' | cat",
]


@pytest.mark.parametrize("command", MASKED_FAILURES)
def test_a_masked_failure_is_not_reported_as_success(daemon, command):
    """The known-bad shape: the door must report the upstream failure, not 0."""
    status = _run(daemon, command)
    assert status != 0, (
        f"the door reported exit 0 for {command!r}: a piped command's status was reported as "
        "the verdict, so a refusal reads as a success"
    )


@pytest.mark.parametrize(
    "command, expected",
    [
        ("true | tail -3", 0),
        ("echo ok | tail -1", 0),
        # The last stage failing is unaffected: it already reported that stage's status.
        ("true | sh -c 'exit 4'", 4),
        # A plain command, no pipeline at all.
        ("true", 0),
        ("sh -c 'exit 2'", 2),
    ],
)
def test_a_real_verdict_is_still_reported(daemon, command, expected):
    """The known-good shape: the door must keep reporting the true status."""
    assert _run(daemon, command) == expected


def test_the_door_builds_bash_with_pipefail(daemon):
    """The property itself, stated on the argv: pipefail is a shell OPTION, not string surgery.

    Asserted separately from the behaviour above because the behaviour is what matters and the
    argv is the mechanism: a future change that achieves the right status by some other route
    should not fail this, and a future change that drops pipefail must fail the behaviour test
    first.
    """
    argv = daemon._runner_argv("job-test", "true", None, 60)
    bash = argv[argv.index("bash") :]
    assert bash[1:3] == ["-o", "pipefail"], (
        f"the door is not running bash with pipefail: {bash!r}"
    )


def test_the_command_the_agent_wrote_is_not_altered(daemon):
    """pipefail must not be achieved by rewriting the command string.

    String surgery is the obvious way to do this and it breaks real commands: a heredoc, a `#`
    comment on the first line, or a quoted pipe inside a string would all change meaning. The
    door must hand the agent's command to bash untouched, so the only thing between the agent and
    the truth is a shell option.
    """
    command = "cat <<'EOF'\nhello | world\nEOF"
    argv = daemon._runner_argv("job-test", command, None, 60)
    bash = argv[argv.index("bash") :]
    assert bash[-1] == command, f"the agent's command was rewritten: {bash[-1]!r}"

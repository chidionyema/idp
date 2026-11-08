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
RUN = pathlib.Path(__file__).resolve().parents[1] / "platform" / "executor" / "run.py"


def _load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _load_run():
    """`run.py` is the ONE place a process's termination becomes the door's exit code."""
    return _load_module(RUN, "estate_executor_run")


@pytest.fixture(scope="module")
def daemon():
    return _load_module(DAEMON, "estate_executor_daemon")


@pytest.fixture(scope="module")
def run():
    return _load_run()


def _run(daemon, command: str) -> int:
    """Run the command the way the door runs it, and return the status the door would report.

    The door's verdict is TWO things: the argv it builds, and the conversion of the process's
    termination into an exit code (`run.py::_exit_for`). Both are applied here, so this grades
    the verdict the door actually reports -- not a proxy for it.
    """
    argv = daemon._runner_argv("job-test", command, None, 60)
    # The door runs `bash ... -c <command>`; run exactly that, and read its status.
    bash = argv[argv.index("bash") :]
    raw = subprocess.run(bash, capture_output=True, text=True, timeout=60).returncode
    return _load_run()._exit_for(raw)


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


# The truncation the caller asked for. Under plain `pipefail` these exit 141 (SIGPIPE): the
# reader closed the pipe, so the writer was killed for doing what it was asked. This repo has
# 120 `| head` sites in bin/ alone, so treating that as a failure would trade one false verdict
# for another -- the guard taxing the estate's own scripts (R14).
TRUNCATIONS = [
    "seq 1 100000 | head -5",
    "seq 1 100000 | head -5 | tail -3",
    "seq 1 100000 | tail -5",
]


@pytest.mark.parametrize("command", TRUNCATIONS)
def test_a_truncation_the_caller_asked_for_is_not_a_failure(daemon, command):
    """The known-good shape: a deliberate `| head` is a success, not a 141."""
    assert _run(daemon, command) == 0, (
        f"the door reported a failure for {command!r}: a truncation the caller asked for was "
        "read as a failure, so the agent would chase a problem that does not exist"
    )


def test_sigpipe_is_masked_only_where_it_is_a_truncation(run):
    """The exception is narrow: 141 is a verdict only when nothing else failed.

    A genuine failure outranks the SIGPIPE -- pipefail reports the rightmost non-zero stage
    status, so `false | head -6` is 1 and never 141. This pins the boundary so the mask cannot
    widen by accident, and so the ceiling's own kills stay visible.
    """
    assert run._exit_for(141) == 0, "a SIGPIPE truncation must read as success"
    assert run._exit_for(1) == 1, "a real failure must stay a failure"
    assert run._exit_for(0) == 0
    assert run._exit_for(-13) == 0, "a process killed by SIGPIPE is the same truncation"
    # The ceiling's kills are NOT masked: a job killed at the ceiling must still say so.
    assert run._exit_for(-15) == 143, "SIGTERM must stay visible"
    assert run._exit_for(-9) == 137, "SIGKILL must stay visible"
    assert run._exit_for(124) == 124, "the ceiling's own exit code must stay visible"


def test_a_real_failure_behind_a_truncation_still_wins(run, daemon):
    """The mask must not swallow the failure hiding behind a `| head`.

    `false | head -6` exits 1, not 141, so the mask never sees it. This is the case that would
    be lost if the mask were applied to the pipeline's status instead of to a 141 alone.
    """
    assert _run(daemon, "false | head -6") == 1
    assert _run(daemon, "sh -c 'exit 9' | head -5") == 9


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

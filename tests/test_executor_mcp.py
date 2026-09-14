"""The executor door's edge cases, graded offline with no daemon and no shell.

Order (founder, 2026-09-13): "nake syre evry agennt sessionns is wre" -- make sure every agent
session is aware -- and "60 secsos is the nnax". So the grades here are the ceiling's own boundary
and the refusals that keep a command from parking an agent.

Every test injects an `Executor` stub (the plugin's `executor=` parameter). Nothing here spawns a
process, so the suite is fast and cannot itself block -- a test that can hang would be the defect
it grades (LAW 45).
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import tempfile

import pytest

PLUGIN = (
    pathlib.Path(__file__).resolve().parents[1]
    / "mcp"
    / "plugins"
    / "estate_executor.py"
)


def _load():
    """Load the plugin by file path, the way `workspace.yaml` loads a code location (LAW 45)."""
    spec = importlib.util.spec_from_file_location("estate_executor", PLUGIN)
    module = importlib.util.module_from_spec(spec)
    sys.modules["estate_executor"] = module
    spec.loader.exec_module(module)
    return module


ex = _load()


@pytest.fixture()
def executor():
    return ex.Executor()


# --- THE CEILING: 60 is the max, and it is not expressible above in any spelling ---


def test_a_plain_command_is_accepted_at_the_ceiling(executor):
    out = ex.execute_command("git status --short", executor=executor)
    assert out["accepted"] is True
    assert out["ceiling_sec"] == ex.CEILING_SEC == 60
    assert out["job_id"]


@pytest.mark.parametrize(
    "command",
    [
        "timeout 61 git push",
        "timeout 90 pytest -q",
        "timeout 150 bin/idp-ci",
        "timeout 2m bin/idp-ci",
        "timeout 150s bin/idp-ci",
        "timeout 1h bin/idp-ci",
        "gtimeout -k 5 150 bin/idp-ci",
        "timeout --kill-after=10 300 bin/idp-ci",
    ],
)
def test_a_ceiling_above_sixty_is_refused_in_every_spelling(command, executor):
    """The breach the founder watched six times: a number above the cap got through because the
    check read one spelling. Every spelling is now read, including the grace period that hid it."""
    out = ex.execute_command(command, executor=executor)
    assert out["accepted"] is False, f"{command!r} was accepted -- the cap is breached"
    assert "60" in out["error"]
    assert executor.get(out.get("job_id") or "none") is None  # nothing was queued


@pytest.mark.parametrize(
    "command",
    ["timeout 60 bin/idp-ci", "timeout 55 pytest -q", "gtimeout -k 5 60 make"],
)
def test_a_ceiling_at_or_below_sixty_is_allowed(command, executor):
    """R38: a guard that refuses correct work is an outage. 60 itself is correct work."""
    out = ex.execute_command(command, executor=executor)
    assert out["accepted"] is True


def test_a_requested_ceiling_above_the_cap_is_clamped_not_refused(executor):
    """The caller's parameter is trimmed; the command's own written ceiling is refused. The
    difference is deliberate: a caller asking for less is a preference, a command hard-coding
    150 is a claim about how long it needs."""
    out = ex.execute_command("pytest -q", ceiling_sec=900, executor=executor)
    assert out["accepted"] is True
    assert out["ceiling_sec"] == 60


def test_a_requested_ceiling_of_zero_is_lifted_to_the_floor(executor):
    """A command bounded to zero seconds never runs, which is a guard refusing correct work."""
    out = ex.execute_command("pytest -q", ceiling_sec=0, executor=executor)
    assert out["accepted"] is True
    assert out["ceiling_sec"] == ex.MIN_CEILING_SEC >= 1


# --- THE REFUSALS: what the executor will not do, and why it says so ---


@pytest.mark.parametrize(
    "command", ["sleep 900", "watch kubectl get pods", "gh run watch 12345"]
)
def test_a_command_with_no_return_path_is_refused(command, executor):
    """A detached run of a waiting command is a job nobody is waiting for."""
    out = ex.execute_command(command, executor=executor)
    assert out["accepted"] is False


def test_an_empty_command_is_refused_not_raised(executor):
    """A guard that crashes is worse than the defect it reports (R38)."""
    assert ex.execute_command("", executor=executor)["accepted"] is False
    assert ex.execute_command("   \n  ", executor=executor)["accepted"] is False
    assert ex.execute_command(None, executor=executor)["accepted"] is False  # type: ignore[arg-type]


def test_a_relative_cwd_is_refused(executor):
    """A relative path resolves against the executor's directory, not the caller's -- so the
    command would run somewhere the author never named."""
    out = ex.execute_command("pytest -q", cwd="sub/dir", executor=executor)
    assert out["accepted"] is False
    assert "absolute" in out["error"]


def test_an_absolute_cwd_is_carried_to_the_job(executor):
    # tempfile.gettempdir(), not a hardcoded "/tmp": the point is that an ABSOLUTE path is carried
    # through to the job unchanged, and naming the machine's own temp directory proves that without
    # writing where this machine lives into a test (LAW 46, and the estate's S108 rule).
    where = tempfile.gettempdir()
    out = ex.execute_command("pytest -q", cwd=where, executor=executor)
    assert out["accepted"] is True
    assert executor.get(out["job_id"]).cwd == where


def test_a_non_numeric_ceiling_is_refused_not_raised(executor):
    out = ex.execute_command("pytest -q", ceiling_sec="soon", executor=executor)  # type: ignore[arg-type]
    assert out["accepted"] is False


# --- READ: the door never waits ---


def test_read_job_reports_a_finished_job_and_its_log(executor):
    out = ex.execute_command("pytest -q", executor=executor)
    executor.finish(out["job_id"], exit_code=0, log="3 passed")
    read = ex.read_job(out["job_id"], executor=executor)
    assert read["found"] is True
    assert read["state"] == "finished"
    assert read["exit_code"] == 0
    assert "3 passed" in read["log"]


def test_read_job_on_a_missing_id_is_a_clean_answer(executor):
    read = ex.read_job("exec-does-not-exist", executor=executor)
    assert read["found"] is False
    assert read["error"]


def test_read_job_has_no_wait_path_in_its_signature():
    """The boundary is structural: a door that can wait is the thing this replaces."""
    import inspect

    params = set(inspect.signature(ex.read_job).parameters)
    assert not (params & {"wait", "timeout", "poll", "block"})


# --- THE PROPOSE TWIN (MUM-288: no execute verb without a simulate twin) ---


def test_the_execute_door_has_a_simulate_twin():
    """`bin/idp-simulate-gate` refuses a state-changing MCP tool with no propose twin."""
    assert callable(ex.simulate_command)


def test_the_twin_agrees_with_the_door_both_ways():
    """A proposal that says accepted while execute refuses is a door reporting something the
    world does not do."""
    for command in ["git status", "timeout 150 x", "sleep 900", "timeout 60 make"]:
        proposal = ex.simulate_command(command)
        executed = ex.execute_command(command, executor=ex.Executor())
        assert proposal["would_accept"] == executed["accepted"], (
            f"{command!r} disagrees"
        )


def test_the_twin_runs_nothing(executor):
    before = dict(executor._jobs)
    ex.simulate_command("rm -rf /tmp/definitely-not-real")
    assert executor._jobs == before


# --- THE CEILING PARSER ITSELF, graded on its own ---


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("echo hi", None),
        ("timeout 60 x", 60),
        ("timeout 2m x", 120),
        ("timeout 150s x", 150),
        ("timeout 1h x", 3600),
        ("gtimeout -k 5 150 x", 150),
        ("timeout --kill-after=10 300 x", 300),
        # The unit is attached or absent -- NEVER scavenged from the next word. Measured
        # 2026-09-13, caught by this suite: `gtimeout -k 5 60 make` parsed as 3600 because the
        # pattern read `make`'s `m` as minutes, silently turning a one-minute bound into an hour.
        ("gtimeout -k 5 60 make", 60),
        ("timeout 2m git commit", 120),
        ("timeout 30 python3 manage.py migrate", 30),
        # THE TIGHTEST BOUND WINS. Two nested timeouts: the outer one governs the command, and
        # the inner one applies to a process that is already bounded. `timeout 45 gtimeout 60 make`
        # is therefore a 45-second command. Reading it as 60 would take the LOOSER number, which is
        # the wrong direction: a bound must never be widened by the way it is written.
        ("timeout 45 gtimeout 60 make", 45),
    ],
)
def test_the_parser_reads_every_spelling(command, expected):
    assert ex.explicit_ceiling_sec(command) == expected


def test_a_word_after_the_number_never_becomes_the_unit():
    """The exact defect: a trailing word starting with s/m/h/d must not scale the number."""
    assert ex.explicit_ceiling_sec("timeout 60 make") == 60
    assert ex.explicit_ceiling_sec("timeout 60 sed -i s/x/y/") == 60
    assert ex.explicit_ceiling_sec("timeout 60 head -1 f") == 60
    assert ex.explicit_ceiling_sec("timeout 60 date") == 60

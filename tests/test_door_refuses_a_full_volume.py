"""The door refuses to start work on a full volume, and lets the cleaner through.

Measured 2026-10-23 on this laptop: 197 MB free of 113 GB, 8 GB of swap exhausted, load average
476, 17 pi sessions, and the door still accepting every job -- each one writing logs and state into
a volume with no room, so each job made the next one slower. Nothing in the estate refused for lack
of space. These tests pin the refusal, its units, and the single exception that keeps it satisfiable.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_MODULE = Path(__file__).resolve().parents[1] / "mcp" / "plugins" / "estate_executor.py"


class _StubExecutor:
    """Stands in for the detached daemon: records the accepted call, runs nothing."""

    def __init__(self):
        self.calls = []

    def submit(self, command, cwd=None, ceiling_sec=None):
        self.calls.append({"command": command, "cwd": cwd, "ceiling_sec": ceiling_sec})

        class _Job:
            job_id = "test-job"

        return _Job()


def _door(tmp_path, free_mb, floor_mb=1500):
    """The real door, with a temp ledger and a free space the test controls.

    The reclaim hook is stubbed here as well as `_free_mb`, and it MUST be: the hook runs the real
    cleaner, so a test that leaves it live deletes files on the machine running the suite and then
    blocks in fork() behind the real executor. A unit test may never reach the filesystem through
    a door it is pretending to run.
    """
    spec = importlib.util.spec_from_file_location(f"door_disk_{id(tmp_path)}", _MODULE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    mod.FRICTION_PATH = tmp_path / "events.jsonl"
    mod.friction_path = lambda: mod.FRICTION_PATH
    mod.MIN_FREE_MB = floor_mb
    mod._free_mb = lambda path="/": free_mb
    # This file grades the DISK FLOOR. The plan gate is a different gate that runs earlier and has
    # its own falsifiers (tests/test_plan_gate.py); leaving it live here would mean every assertion
    # below measured "no plan declared" instead of the floor it was written to measure.
    mod._plan_gate = lambda command, session_id="": None
    return mod, _StubExecutor()


def test_a_build_is_refused_on_a_full_volume_with_the_number_the_floor_and_the_way_out(
    tmp_path,
):
    # A build is what the floor exists to stop. `git status` is exempt by shape (it cannot fill a
    # disk), so the refusal has to be proved on a command that genuinely writes.
    door, ex = _door(tmp_path, free_mb=200)

    out = door.execute_command("python3 -m pytest tests/", cwd=str(tmp_path), executor=ex)

    assert out["accepted"] is False
    assert "200 MB free" in out["error"]
    assert "1500 MB floor" in out["error"]
    # The way out must be named, and it must be a thing that actually exists and actually frees
    # space. `disk-cleanup` was deleted 2026-11-11, so the refusal names the measurement and the
    # action instead of a door that is gone.
    assert "/bin/df" in out["detail"] or "rm" in out["detail"]
    assert out["free_mb"] == 200 and out["floor_mb"] == 1500, (
        f"the refusal must carry the numbers it decided on, got free_mb={out.get('free_mb')} "
        f"floor_mb={out.get('floor_mb')}"
    )
    assert ex.calls == []  # nothing was started on a full machine


def test_the_refusal_is_written_to_the_friction_ledger(tmp_path):
    # A command that BUILDS is what the floor is for: a test run on a full volume writes to it.
    # `git status` is deliberately exempt (it cannot fill a disk), so it cannot be the subject
    # of this test -- see _FLOOR_EXEMPT_RES.
    door, ex = _door(tmp_path, free_mb=200)

    door.execute_command("python3 -m pytest tests/", cwd=str(tmp_path), executor=ex)

    lines = [
        json.loads(l) for l in door.FRICTION_PATH.read_text().splitlines() if l.strip()
    ]
    disk = [l for l in lines if l["kind"] == "refuse-disk"]
    assert len(disk) == 1
    assert disk[0]["shape"] == "python3 -m pytest", (
        "the ledger records the command SHAPE, not the arguments: one row per kind of work, so a"
        " thousand test runs do not become a thousand distinct frictions"
    )
    assert "200 MB" in disk[0]["detail"]


def test_the_reclaim_door_is_never_refused_or_the_refusal_is_unsatisfiable(tmp_path):
    # A guard whose own instruction is refused by itself is the defect, not the remedy (R38).
    # `disk-cleanup` was deleted 2026-11-11; `disk-reclaim` is the door the refusal now names, so
    # it is the one that must never be refused while the floor is closed.
    door, ex = _door(tmp_path, free_mb=200)

    out = door.execute_command("estate-execute disk-reclaim", cwd=str(tmp_path), executor=ex)

    assert "MB free" not in out.get("error", "")
    assert len(ex.calls) == 1


def test_unloading_a_job_is_never_refused_or_the_floor_blocks_its_own_exit(tmp_path):
    """The circular case measured 2026-11-11: under the floor, `launchctl bootout` on the resident
    job holding the floor closed was itself refused. Unloading a job consumes no space, so the
    floor must never refuse it -- otherwise the floor is the only thing standing between the
    machine and the space it needs."""
    door, ex = _door(tmp_path, free_mb=200)

    out = door.execute_command(
        "launchctl bootout gui/501/ai.estate.disk-watch", cwd=str(tmp_path), executor=ex
    )

    assert "MB free" not in out.get("error", "")
    assert len(ex.calls) == 1


def test_above_the_floor_the_door_is_unchanged(tmp_path):
    door, ex = _door(tmp_path, free_mb=50_000)

    out = door.execute_command("git status", cwd=str(tmp_path), executor=ex)

    assert "MB free" not in out.get("error", "")
    assert (
        "free_mb" not in out
    )  # the floor never leaks into a reply that did not use it
    assert len(ex.calls) == 1


def test_an_unmeasurable_volume_does_not_invent_a_breach(tmp_path):
    # An unmeasurable grader is UNKNOWN, never a pass and never a fail: None is not zero.
    door, ex = _door(tmp_path, free_mb=None)

    out = door.execute_command("git status", cwd=str(tmp_path), executor=ex)

    assert "MB free" not in out.get("error", "")
    assert len(ex.calls) == 1


@pytest.mark.parametrize("floor", [0, 500, 10240])
def test_the_floor_is_configurable_and_read_from_the_environment(floor, monkeypatch):
    monkeypatch.setenv("ESTATE_MIN_FREE_MB", str(floor))
    spec = importlib.util.spec_from_file_location(f"door_env_{floor}", _MODULE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.MIN_FREE_MB == floor


# --------------------------------------------------------------------------------------------
# THE REFUSAL RUNS THE REMEDY IT NAMES (founder, 2026-11-10).
#
# The door named `estate-execute disk-cleanup` and stopped, so every agent paid the same two-step
# dance: refused, run the cleaner by hand, resend the original command. Worse, the cleaner the door
# told the caller to run was itself refused while the volume sat under the floor, so the one call
# the refusal pointed at could not be made. Advice that cannot be acted on in one call is friction
# by construction. These tests pin that the door RECLAIMS FIRST: it invokes the estate's own
# cleaner, re-measures, and only refuses if the space is still not there.
# --------------------------------------------------------------------------------------------


def _door_tracking_reclaim(tmp_path, free_readings, floor_mb=1500):
    """The real door, with free space that CHANGES when the cleaner runs.

    `free_readings` is consumed one value per `_free_mb()` call, so the test can model the real
    sequence: under the floor, the cleaner runs, the volume now has room. The reclaim hook is
    replaced with a recorder so no test ever deletes anything on the machine running it.
    """
    spec = importlib.util.spec_from_file_location(
        f"door_reclaim_{id(tmp_path)}", _MODULE
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    mod.FRICTION_PATH = tmp_path / "events.jsonl"
    mod.friction_path = lambda: mod.FRICTION_PATH
    mod.MIN_FREE_MB = floor_mb
    readings = list(free_readings)
    mod._free_mb = lambda path="/": readings.pop(0) if readings else free_readings[-1]
    mod._plan_gate = lambda command, session_id="": None
    calls = []

    def _record():
        calls.append(True)
        return 0

    mod._reclaim_before_refusing = _record
    mod.reclaim_calls = calls
    return mod, _StubExecutor(), calls


def test_the_door_refuses_and_names_the_measurement(tmp_path):
    # 200 MB free -> the door refuses a BUILD. It does NOT run a cleaner: the cleaner family was
    # deleted 2026-11-11 because it was the cause of the full disk, not the cure. The refusal has
    # to say what is true and name a command that frees space.
    door, ex, calls = _door_tracking_reclaim(tmp_path, free_readings=[200, 200])

    out = door.execute_command("python3 -m pytest tests/", cwd=str(tmp_path), executor=ex)

    assert out["accepted"] is False
    assert ex.calls == [], "a refused command must not run"
    assert "200 MB free" in out["error"]
    assert "1,500 MB floor" in out["error"] or "1500 MB floor" in out["error"]
    assert calls == [], "the deleted cleaner must not be invoked on the refusal path"
    assert out["floor_mb"] == 1500, "the refusal states the floor it applied"


def test_a_command_that_frees_space_runs_while_the_floor_is_closed(tmp_path):
    # The floor must never blockade its own exit: the command that frees the space has to run,
    # or the machine cannot recover and the guard has become the outage (R38, #7918).
    door, ex, calls = _door_tracking_reclaim(tmp_path, free_readings=[200, 200])

    door.execute_command("/bin/df -m /System/Volumes/Data", cwd=str(tmp_path), executor=ex)

    assert len(ex.calls) == 1, "df is how you find out what to free; refusing it is a catch-22"
    assert calls == []


def test_a_healthy_volume_is_not_refused(tmp_path):
    door, ex, calls = _door_tracking_reclaim(tmp_path, free_readings=[50_000])

    door.execute_command("git status", cwd=str(tmp_path), executor=ex)

    assert calls == [], "a healthy volume must not trigger a reclaim"
    assert len(ex.calls) == 1


def test_the_cleaner_is_not_run_when_the_volume_cannot_be_measured(tmp_path):
    # None is not zero: an unmeasurable volume must not invent a breach AND must not start deleting.
    door, ex, calls = _door_tracking_reclaim(tmp_path, free_readings=[None])

    door.execute_command("git status", cwd=str(tmp_path), executor=ex)

    assert calls == []
    assert len(ex.calls) == 1


def test_the_reclaim_hook_resurrects_nothing():
    # FALSIFIER for the founder's order, 2026-11-11: the disk guardian family is DELETED from
    # source, not retired. The floor used to shell out to the estate's cleaner from inside the
    # door. If that call ever comes back, the family has grown back and this fails.
    text = _MODULE.read_text()
    start = text.index("def _reclaim_before_refusing")
    end = text.index("\ndef ", start + 1)
    source = text[start:end]
    assert "disk-cleanup.sh" not in source, (
        "the door must not invoke the deleted cleaner: it was the cause of the full disk, not"
        " the cure (113 steps to do what one rm does)"
    )
    assert "return None" in source, "the hook is a named no-op so the floor block still runs"


def test_the_only_way_out_of_the_floor_is_a_command_that_frees_space():
    # The floor must never blockade its own exit. Each of these is a command that frees, measures
    # or stops the thing filling the disk, so the floor has to let it run while it is closed --
    # otherwise the machine cannot recover and the guard has become the outage (R38, #7918).
    # This grades the SHIPPED predicate, not a copy of its regex: a test that restates the list
    # can only ever agree with itself.
    spec = importlib.util.spec_from_file_location("door_floor_exit", _MODULE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for command in (
        "/bin/df -m /System/Volumes/Data",
        "du -sh ~/Documents/code",
        "rm -rf /tmp/scratch",
        "pkill -f runaway-build",
        "launchctl bootout gui/501/ai.estate.disk-watch",
    ):
        assert mod._floor_exempt(command), (
            f"{command!r} must stay exempt or the floor blocks its own way out"
        )
    # And the floor must still REFUSE the thing it exists for: a build on a full volume.
    for command in ("python3 -m pytest tests/", "npm run build", "cargo build"):
        assert not mod._floor_exempt(command), (
            f"{command!r} writes to the disk and must still wait for real space"
        )

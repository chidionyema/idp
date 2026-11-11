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
    mod._reclaim_before_refusing = lambda: 0
    return mod, _StubExecutor()


def test_a_full_volume_is_refused_with_the_number_the_floor_and_the_way_out(tmp_path):
    door, ex = _door(tmp_path, free_mb=200)

    out = door.execute_command("git status", cwd=str(tmp_path), executor=ex)

    assert out["accepted"] is False
    assert "200 MB free" in out["error"]
    assert "1500 MB floor" in out["error"]
    assert "disk-cleanup" in out["detail"]
    assert out["free_mb"] == 200 and out["floor_mb"] == 1500
    assert ex.calls == []  # nothing was started on a full machine


def test_the_refusal_is_written_to_the_friction_ledger(tmp_path):
    door, ex = _door(tmp_path, free_mb=200)

    door.execute_command("git status", cwd=str(tmp_path), executor=ex)

    lines = [
        json.loads(l) for l in door.FRICTION_PATH.read_text().splitlines() if l.strip()
    ]
    disk = [l for l in lines if l["kind"] == "refuse-disk"]
    assert len(disk) == 1
    assert disk[0]["shape"] == "git status"
    assert "200 MB" in disk[0]["detail"]


def test_the_cleaner_itself_is_never_refused_or_the_refusal_is_unsatisfiable(tmp_path):
    # A guard whose own instruction is refused by itself is the defect, not the remedy (R38).
    door, ex = _door(tmp_path, free_mb=200)

    out = door.execute_command(
        "estate-execute disk-cleanup apply=true", cwd=str(tmp_path), executor=ex
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
    calls = []

    def _record():
        calls.append(True)
        return 0

    mod._reclaim_before_refusing = _record
    mod.reclaim_calls = calls
    return mod, _StubExecutor(), calls


def test_the_refusal_runs_the_cleaner_and_then_lets_the_job_through(tmp_path):
    # 200 MB free -> cleaner runs -> 9000 MB free: the job the caller asked for now runs.
    door, ex, calls = _door_tracking_reclaim(tmp_path, free_readings=[200, 9000])

    out = door.execute_command("git status", cwd=str(tmp_path), executor=ex)

    assert calls == [True], "the door must run the cleaner, not just name it"
    assert len(ex.calls) == 1, "once the space is there the job runs on the same call"
    assert "MB free" not in out.get("error", "")


def test_when_reclaiming_does_not_free_enough_the_door_still_refuses_with_both_numbers(
    tmp_path,
):
    # 200 MB -> cleaner runs -> 300 MB: still under the 1500 MB floor, so the refusal is honest
    # and carries what was reclaimed, so the caller knows the cleaner ran and how much is owed.
    door, ex, calls = _door_tracking_reclaim(tmp_path, free_readings=[200, 300])

    out = door.execute_command("git status", cwd=str(tmp_path), executor=ex)

    assert calls == [True]
    assert out["accepted"] is False
    assert ex.calls == []
    assert "300 MB free" in out["error"]
    assert "reclaimed 200 -> 300 MB" in out["error"], (
        "the refusal must say the cleaner ran and what it freed, not re-issue the old advice"
    )
    assert out["free_mb"] == 300 and out["floor_mb"] == 1500


def test_the_cleaner_is_not_run_when_the_volume_is_already_above_the_floor(tmp_path):
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


def test_a_reclaim_that_cannot_run_still_refuses_honestly(tmp_path):
    # The cleaner is missing or crashed: the door must not pretend it freed space.
    door, ex, calls = _door_tracking_reclaim(tmp_path, free_readings=[200, 200])
    door._reclaim_before_refusing = lambda: None

    out = door.execute_command("git status", cwd=str(tmp_path), executor=ex)

    assert out["accepted"] is False
    assert "cleaner rc=None" in out["error"]
    assert ex.calls == []


def test_the_reclaim_is_off_unless_the_estate_opts_in(monkeypatch):
    # A refusal that DELETES files the caller never asked about is a worse defect than the two-step
    # dance it removes. Default OFF, and the refusal stays honest when it is off.
    monkeypatch.delenv("ESTATE_DISK_RECLAIM_ON_REFUSE", raising=False)
    spec = importlib.util.spec_from_file_location("door_optin_off", _MODULE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod._reclaim_before_refusing() is None, (
        "with no opt-in the hook must do nothing, so no refusal deletes anything unasked"
    )


def test_no_test_leaves_the_real_cleaner_live(tmp_path):
    # A door built for a test must not be able to spawn the real cleaner: that both deletes files
    # on the host and blocks in fork() behind the real executor (the hang this file shipped with).
    door, _ex = _door(tmp_path, free_mb=10)
    assert door._reclaim_before_refusing() == 0, (
        "the default test door must stub the reclaim hook, not run the real cleaner"
    )


def test_the_reclaim_is_recorded_in_the_friction_ledger(tmp_path):
    door, ex, calls = _door_tracking_reclaim(tmp_path, free_readings=[200, 9000])

    door.execute_command("git status", cwd=str(tmp_path), executor=ex)

    lines = [
        json.loads(l) for l in door.FRICTION_PATH.read_text().splitlines() if l.strip()
    ]
    kinds = [l["kind"] for l in lines]
    assert "reclaim-then-run" in kinds, (
        "a reclaim that unblocked work is the estate's evidence that the friction was real"
    )


def test_the_reclaim_hook_invokes_the_estate_cleaner_and_is_bounded():
    # The hook itself, un-stubbed, must call the one cleaner SCRIPT and bound its own runtime, or a
    # refusal could outlast the work it guards (the 100s ceiling is the door's, not its own).
    text = _MODULE.read_text()
    start = text.index("def _reclaim_before_refusing")
    end = text.index("\ndef ", start + 1)
    source = text[start:end]
    assert "disk-cleanup.sh" in source, (
        "must call the cleaner script, the layer that does the work"
    )
    assert "timeout=" in source, "a refusal must never outlast the work it guards"
    assert "target_mb=" in source or "DISK_CLEANUP_TARGET_MB" in source


def test_the_reclaim_never_calls_the_executor_door_from_inside_the_door():
    # Re-entrancy: spawning `estate-execute` from inside the door spawns a second door while the
    # first refuses. That is the fork storm this hook shipped with; the script is the layer.
    text = _MODULE.read_text()
    start = text.index("def _reclaim_before_refusing")
    end = text.index("\ndef ", start + 1)
    source = text[start:end]
    assert "bin/estate-execute" not in source, (
        "the hook must not invoke the door that is running it"
    )

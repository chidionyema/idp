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
    """The real door, with a temp ledger and a free space the test controls."""
    spec = importlib.util.spec_from_file_location(f"door_disk_{id(tmp_path)}", _MODULE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    mod.FRICTION_PATH = tmp_path / "events.jsonl"
    mod.friction_path = lambda: mod.FRICTION_PATH
    mod.MIN_FREE_MB = floor_mb
    mod._free_mb = lambda path="/": free_mb
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

"""The door's floor measures the volume the job writes to, not the system volume.

2026-11-15. `_free_mb(path="/")` documents itself as "free space on the volume that holds
`path`", but the execute door called it with no path, so it measured `/`. On this APFS layout `/`
is the sealed system volume and reported 783 MB while the Data volume holding every checkout,
worktree and log reported 1619 MB -- the door refused every command on the machine for a
shortage the work volume did not have, and told the caller to run a cleaner that frees nothing
there. A job writes where `cwd` points; that is the volume to judge.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "mcp" / "plugins" / "estate_executor.py"


class _Stub:
    def __init__(self):
        self.calls = []

    def submit(self, command, cwd=None, ceiling_sec=None):
        self.calls.append({"command": command, "cwd": cwd})

        class _Job:
            job_id = "test-job"

        return _Job()


def _door(tmp_path, recorded, free_mb=5000, floor_mb=1500):
    spec = importlib.util.spec_from_file_location(f"door_cwd_{id(tmp_path)}", MODULE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.FRICTION_PATH = tmp_path / "events.jsonl"
    mod.friction_path = lambda: mod.FRICTION_PATH
    mod.MIN_FREE_MB = floor_mb

    def _free(path="/"):
        recorded.append(path)
        return free_mb

    mod._free_mb = _free
    return mod, _Stub()


def test_the_floor_measures_the_volume_the_job_writes_to(tmp_path):
    recorded = []
    door, ex = _door(tmp_path, recorded)

    out = door.execute_command("python3 -c 'print(1)'", cwd=str(tmp_path), executor=ex)

    assert str(tmp_path) in recorded, (
        f"the floor measured {recorded}, not the job's own directory"
    )
    assert "/" not in recorded, "the system volume was measured for a job that writes elsewhere"
    assert out["accepted"] is True


def test_without_a_cwd_the_floor_still_measures_the_root_volume(tmp_path):
    recorded = []
    door, ex = _door(tmp_path, recorded)

    door.execute_command("python3 -c 'print(1)'", executor=ex)

    assert recorded == ["/"], f"no cwd must fall back to /, measured {recorded}"

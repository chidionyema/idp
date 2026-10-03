"""Tests for the run-record reaper in platform/executor/run.py.

WHY THESE EXIST. `~/.estate/runs/` had no pruning and grew to 13,125 files (51 MB) holding 5,141
finished jobs. The cost was not disk -- it was that `run --status` called 4,851 finished jobs
RUNNING, because `kill -0 <pid>` succeeds on whatever process now holds a recycled pid. An agent
reading that list was told days-old jobs were live. So the reaper has two jobs, and both are
tested here: reap finished runs, and NEVER touch one that has not recorded its exit.

The load-bearing test is `test_running_job_with_ancient_timestamps_is_never_reaped`. A prune that
deletes a running job's log deletes the only record of what that job was doing -- and the mtime
filter alone would delete it, because a long-running job's files are old by definition.
"""

from __future__ import annotations

import importlib.util
import os
import time
from pathlib import Path

import pytest


def _load_run_module(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Load run.py with RUNS pointed at a scratch directory.

    RUNS is read from ESTATE_RUNS at import time, so the env var is set before the module is
    loaded -- and the module is loaded per-test rather than once, so no test can see another's
    directory.
    """
    monkeypatch.setenv("ESTATE_RUNS", str(tmp_path))
    src = Path(__file__).resolve().parents[1] / "platform" / "executor" / "run.py"
    spec = importlib.util.spec_from_file_location("estate_run_under_test", src)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_job(runs: Path, name: str, *, finished: bool, age_secs: float) -> None:
    """Write one job's records, backdated. `finished` controls whether an exit file exists."""
    stamp = time.time() - age_secs
    for suffix, text in ((".log", "output\n"), (".pid", "99999")):
        path = runs / f"{name}{suffix}"
        path.write_text(text)
        os.utime(path, (stamp, stamp))
    if finished:
        path = runs / f"{name}.exit"
        path.write_text("0")
        os.utime(path, (stamp, stamp))


def test_finished_and_old_job_is_reaped(tmp_path, monkeypatch):
    run = _load_run_module(tmp_path, monkeypatch)
    _make_job(tmp_path, "old-done", finished=True, age_secs=30 * 86400)

    assert run.prune(keep_secs=7 * 86400) == 1
    assert not (tmp_path / "old-done.log").exists()
    assert not (tmp_path / "old-done.pid").exists()
    assert not (tmp_path / "old-done.exit").exists()


def test_finished_but_recent_job_is_kept(tmp_path, monkeypatch):
    """A finished job's log is how an agent finds out why it failed, so it is kept for a while."""
    run = _load_run_module(tmp_path, monkeypatch)
    _make_job(tmp_path, "just-done", finished=True, age_secs=60)

    assert run.prune(keep_secs=7 * 86400) == 0
    assert (tmp_path / "just-done.log").exists()


def test_running_job_with_ancient_timestamps_is_never_reaped(tmp_path, monkeypatch):
    """THE LOAD-BEARING CASE.

    A job that never wrote an exit file is not known to be over, and a long-running job's files
    are old by definition -- so an mtime-only reaper deletes exactly the records it must keep.
    No exit file, no reap, however old the files are.
    """
    run = _load_run_module(tmp_path, monkeypatch)
    _make_job(tmp_path, "still-running", finished=False, age_secs=365 * 86400)

    assert run.prune(keep_secs=7 * 86400) == 0
    assert (tmp_path / "still-running.log").exists()
    assert (tmp_path / "still-running.pid").exists()


def test_keep_secs_zero_keeps_everything(tmp_path, monkeypatch):
    """The escape hatch: an operator who wants nothing reaped says so and gets nothing reaped."""
    run = _load_run_module(tmp_path, monkeypatch)
    _make_job(tmp_path, "ancient", finished=True, age_secs=3650 * 86400)

    assert run.prune(keep_secs=0) == 0
    assert (tmp_path / "ancient.log").exists()


def test_prune_touches_only_the_runs_directory(tmp_path, monkeypatch):
    """A file outside RUNS that happens to match the glob's shape is not the reaper's business."""
    run = _load_run_module(tmp_path, monkeypatch)
    outside = tmp_path.parent / "not-a-run.exit"
    outside.write_text("0")
    os.utime(outside, (time.time() - 3650 * 86400,) * 2)

    run.prune(keep_secs=1)
    assert outside.exists()
    outside.unlink()


def test_start_reaps_without_being_asked(tmp_path, monkeypatch):
    """THE AUTOMATIC PATH. Nothing calls `--prune`; every start must be a chance to reap, or the
    directory grows without bound again. This drives `start()` and asserts the ancient job is gone.
    """
    import io
    from contextlib import redirect_stdout

    run = _load_run_module(tmp_path, monkeypatch)
    _make_job(tmp_path, "ancient-finished", finished=True, age_secs=30 * 86400)

    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = run.start("fresh-job", ["true"], None, 60)
    assert rc == 0
    assert not (tmp_path / "ancient-finished.exit").exists(), (
        "start() must reap finished runs automatically"
    )
    assert (tmp_path / "fresh-job.pid").exists(), "the new job still records itself"
    # Let the detached child finish so the test leaves no live process behind.
    for _ in range(50):
        if (tmp_path / "fresh-job.exit").exists():
            break
        time.sleep(0.1)


def test_status_reports_exit_not_recycled_pid(tmp_path, monkeypatch, capsys):
    """The lie that started this: a finished job whose pid was recycled reported RUNNING.

    A recorded exit means the job is over regardless of what the pid now names, so the exit file
    must be consulted first. This pid (1) is alive on every machine, which is the point -- the old
    ordering would have printed RUNNING.
    """
    run = _load_run_module(tmp_path, monkeypatch)
    (tmp_path / "finished-job.pid").write_text("1")
    (tmp_path / "finished-job.log").write_text("done\n")
    (tmp_path / "finished-job.exit").write_text("0")

    assert run.status(None) == 0
    out = capsys.readouterr().out
    assert "exited 0" in out
    assert "RUNNING" not in out

"""The disk doors fit inside one door.

Measured 2026-10-25, through the door: `disk-free` as invoked ran for 100s and came back exit 124
with no measurement in it -- the cleaner's `du` of HOME (T_SCAN 300s) was SIGTERMed by the door's
ceiling, so the caches, docker and tier phases never ran and nothing said so. A door whose work
cannot fit the door is not a slow door, it is a door that reports nothing.

These tests hold three things:
  1. both disk intents declare a bound under the ceiling (so the door cannot outlive itself);
  2. the cleaner, given a small budget, SKIPS phases by name, exits 4, and finishes in the time
     it was given -- a half-cleared disk is never reported as done;
  3. the cleaner still exits 0 with the budget off (no behaviour change for existing callers).
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CLEANER = ROOT / "platform/estate/libexec/disk-cleanup.sh"
CEILING = 100  # mcp/plugins/estate_executor.py CEILING_SEC


@pytest.mark.parametrize("intent", ["disk-free.yaml", "disk-cleanup.yaml"])
def test_the_door_declares_a_bound_under_the_ceiling(intent):
    spec = yaml.safe_load((ROOT / "platform/estate/intents" / intent).read_text())
    door_s = spec.get("door_s")
    assert isinstance(door_s, int), (
        f"{intent} declares no door_s, so it inherits the {CEILING}s ceiling"
    )
    assert door_s < CEILING, (
        f"{intent}: door_s {door_s} is not under the {CEILING}s ceiling"
    )


def test_the_disk_free_intent_budgets_the_work_it_hands_the_cleaner():
    spec = yaml.safe_load((ROOT / "platform/estate/intents/disk-free.yaml").read_text())
    door_s = spec["door_s"]
    budgets = []
    for step in spec["steps"]:
        if "disk-cleanup.sh" not in step["cmd"]:
            continue
        words = step["cmd"].split("disk-cleanup.sh", 1)[1].split()
        # the cleaner's fifth positional argument is its budget; four args means no bound at all
        assert len(words) >= 5 and words[4].isdigit(), (
            f"step {step['name']} must pass an integer budget as the cleaner's 5th argument, "
            f"not {words!r}"
        )
        budgets.append(int(words[4]))
        assert "DISK_CLEANUP_PHASES=" in step["cmd"], (
            f"step {step['name']} must name the phases it runs, or the split reclaims nothing"
        )
    assert budgets, "no cleaning step at all"
    assert sum(budgets) < door_s, (
        f"the cleaning calls total {sum(budgets)}s of a {door_s}s door: the df/verdict steps "
        "around them still need seconds of their own"
    )


def _run_cleaner(tmp_path: Path, secs: int) -> tuple[int, str, float]:
    """Dry-run the cleaner with a budget; return (rc, output, wall seconds)."""
    env = {
        **os.environ,
        "HOME": str(tmp_path),
        # A tiny scan target keeps this test about the budget, not about the laptop's home dir.
        "DISK_CLEANUP_SCAN_FILE": str(tmp_path / "scan.txt"),
        "TMPDIR": str(tmp_path),
    }
    t0 = time.time()
    r = subprocess.run(
        ["bash", str(CLEANER), "false", "false", "0", "false", str(secs)],
        env=env,
        capture_output=True,
        text=True,
        timeout=CEILING,
    )
    return r.returncode, r.stdout + r.stderr, time.time() - t0


@pytest.mark.parametrize("secs", [5, 12])
def test_a_small_budget_skips_phases_by_name_and_says_so(tmp_path, secs):
    rc, out, wall = _run_cleaner(tmp_path, secs)
    # 4: the budget ran out with phases still owed. Not 0 -- a caller that reads 0 would believe
    # the disk is clear. Not 3 -- nothing failed to delete.
    assert rc == 4, f"expected exit 4 (budget), got {rc}:\n{out}"
    assert "budget:" in out, out
    assert wall <= secs + 8, f"the cleaner took {wall:.0f}s on a {secs}s budget:\n{out}"


def test_a_phase_that_cannot_fit_is_named_with_the_seconds_it_was_denied(tmp_path):
    """The operator has to be able to read which phases are still owed, not just that some are."""
    rc, out, _ = _run_cleaner(tmp_path, 5)
    assert rc == 4, out
    assert "SKIP" in out, out
    # The line names the phase and the seconds it had left: `SKIP   <phase>   <n>s left of a 5s budget`
    skip_lines = [ln for ln in out.splitlines() if "SKIP" in ln and "budget" in ln]
    assert skip_lines, out
    assert any("s left of a 5s budget" in ln for ln in skip_lines), skip_lines


def test_with_no_budget_the_cleaner_is_unchanged(tmp_path):
    """Existing callers pass four args and expect the old contract (0, or 3, or 1)."""
    env = {
        **os.environ,
        "HOME": str(tmp_path),
        "DISK_CLEANUP_SCAN_FILE": str(tmp_path / "scan.txt"),
        "TMPDIR": str(tmp_path),
    }
    r = subprocess.run(
        ["bash", str(CLEANER), "false", "false", "0", "false"],
        env=env,
        capture_output=True,
        text=True,
        timeout=CEILING,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "budget:" not in r.stdout, (
        "an unbudgeted run must not report a budget it never had"
    )


def test_a_non_integer_budget_is_refused(tmp_path):
    env = {**os.environ, "HOME": str(tmp_path), "TMPDIR": str(tmp_path)}
    r = subprocess.run(
        ["bash", str(CLEANER), "false", "false", "0", "false", "soon"],
        env=env,
        capture_output=True,
        text=True,
        timeout=CEILING,
    )
    assert r.returncode == 1, r.stdout + r.stderr
    assert "budget" in (r.stdout + r.stderr).lower()


def test_the_scheduled_watcher_also_gives_the_cleaner_a_budget():
    """Measured 2026-10-25: bin/idp-disk-watch called the cleaner with four args (no budget), so a
    tick could run for minutes; every door call that wanted the disk then found the lock held and
    answered "nothing done" -- the agent that needed space could not get it."""
    src = (ROOT / "bin/idp-disk-watch").read_text()
    call = [ln for ln in src.splitlines() if 'bash "$CLEANUP"' in ln]
    assert call, (
        "the watcher no longer calls the cleaner: update this test, not the assertion"
    )
    assert all("$WATCH_BUDGET" in ln for ln in call), (
        "the scheduled call must pass a budget as the cleaner's fifth argument: "
        + repr(call)
    )
    assert 'case "$rc" in 0|4|5)' in src, (
        "a budgeted tick exits 4 (phases owed, the next tick continues) and 5 (another run held the "
        "lock): neither may raise the failure alert"
    )


def test_losing_the_lock_never_reports_a_clear_disk(tmp_path):
    """Measured 2026-10-25: a second call answered "nothing done" and exited 0, so the door's
    verdict printed "every phase ran" for a run that touched nothing. 0 must mean the disk is
    clear and nothing else."""
    env = {**os.environ, "HOME": str(tmp_path), "TMPDIR": str(tmp_path)}
    lock = tmp_path / ".estate/disk-cleanup.lock"
    lock.mkdir(parents=True)
    (lock / "pid").write_text(
        f"{os.getpid()}\n"
    )  # this test process: alive for the duration
    r = subprocess.run(
        ["bash", str(CLEANER), "true", "false", "0", "false", "30"],
        env=env,
        capture_output=True,
        text=True,
        timeout=CEILING,
    )
    assert r.returncode == 5, (
        f"expected 5 (another run holds it), got {r.returncode}:\n{r.stdout}"
    )
    assert "nothing done here" in r.stdout, r.stdout

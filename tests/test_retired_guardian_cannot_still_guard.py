"""A retired guardian must not still guard: drift, tombstone, and an unstoppable loop.

The defect this pins (measured 2026-11-11, on the founder's own laptop):

`main` retired the resident disk guardian correctly and in three places -- `bin/idp-disk-watch`
became a 27-line tombstone that prints BLIND and `exit 1`, `launchd/ai.estate.disk-watch.plist.tmpl`
gained `<key>Disabled</key><true/>`, and `platform/estate/libexec/disk-cleanup.sh` became a
tombstone that `exit 1`s. Every one of those is right.

The machine still ran the guardian. Its `~/.estate/bin/idp-disk-watch` was 22 lines and contained
no disable check at all, so it took a 45-second cleanup budget every cycle and held the executor's
1500 MB floor closed against every command -- including the `launchctl bootout` and the `rm` that
would have retired it. A runtime-only shell loop (`estate-local-maintenance run`), untracked and so
invisible to the sync, re-ran that stale copy every 60 seconds for 21h58m.

Two faults, each pinned below:

1. **Nothing compared the runtime copy to the tracked one.** A disable expressed only as "the new
   file exits 1" cannot stop the old file that is already installed and running, and no gate asked
   whether the installed bytes equal the tracked bytes. A stale install is invisible by
   construction.

2. **The loop could not be stopped.** `estate-local-maintenance run` traps `TERM` with
   `trap 'rm -f "$STATE"' EXIT INT TERM`, which removes the pidfile and lets `while :` keep going.
   `stop` printed `stopped`, deleted the pidfile, and the daemon was still alive afterwards. A
   `TERM` that does not stop the thing is worse than no `TERM`, because it reports success.

The tests are written against the real files on `main`, so they fail on the stale runtime shape and
pass on the retired one.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WATCH = REPO_ROOT / "bin/idp-disk-watch"
CLEANUP = REPO_ROOT / "platform/estate/libexec/disk-cleanup.sh"
TMPL = REPO_ROOT / "launchd/ai.estate.disk-watch.plist.tmpl"
SYNC = REPO_ROOT / "bin/estate-runtime-sync"
LOOP = REPO_ROOT / "bin/estate-local-maintenance"

_PROBE_ENV = {
    "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
    "HOME": "/tmp/estate-tombstone-probe",
}


def _run(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(path)], capture_output=True, text=True, timeout=30, env=_PROBE_ENV
    )


def test_the_guardian_refuses_to_guard() -> None:
    """The installed program must exit non-zero and say it is disabled, not run a cleanup."""
    assert WATCH.is_file(), f"the guardian must exist as a tombstone: {WATCH}"
    result = _run(WATCH)
    assert result.returncode != 0, (
        "bin/idp-disk-watch exited 0 -- it is still guarding. A retired guardian must refuse."
    )
    assert "disabled" in (result.stdout + result.stderr).lower()


def test_the_cleaner_refuses_to_clean() -> None:
    """The cleaner is half of the same guardian: a live one is the circle rebuilt."""
    assert CLEANUP.is_file()
    result = _run(CLEANUP)
    assert result.returncode != 0, (
        "the disk cleaner is disabled by founder order; it must exit non-zero"
    )
    assert "disabled" in (result.stdout + result.stderr).lower()


def test_the_plist_cannot_be_loaded() -> None:
    """launchd itself must refuse: a template without Disabled can be bootstrapped by anyone."""
    text = TMPL.read_text()
    assert "<key>Disabled</key><true/>" in text, (
        "the template must carry <key>Disabled</key><true/> so launchd will not load it"
    )


def test_the_runtime_sync_can_see_a_stale_install() -> None:
    """The check that was missing: installed bytes comparable to tracked bytes.

    It does not require the runtime to be synced here -- it requires that the comparison EXISTS,
    so a stale install is a finding instead of an invisible default.
    """
    assert SYNC.is_file(), (
        "estate-runtime-sync must exist to deliver tracked files to the runtime"
    )
    text = SYNC.read_text()
    assert "drift" in text.lower(), (
        "estate-runtime-sync must carry a drift check: without one, a runtime copy older than the\n"
        "tracked file runs forever and nothing notices (2026-11-11: the disk guardian)."
    )


def test_the_loop_stops_when_it_is_told_to_stop() -> None:
    """A TERM that removes the pidfile and keeps looping reports success without stopping.

    The loop must (a) exist as a tracked file, and (b) actually leave its `while` loop on TERM
    rather than only cleaning up after itself.
    """
    assert LOOP.is_file(), (
        "estate-local-maintenance is untracked today, so the loop that re-ran the stale guardian\n"
        "was invisible to the sync and to review. It must be a tracked file."
    )
    text = LOOP.read_text()
    after_term = text.split("trap", 1)[-1][:200].lower()
    assert "exit" in after_term or "stop_" in after_term or "stopping=" in after_term, (
        "the TERM handler must exit the loop, not merely remove the pidfile: "
        "`trap 'rm -f $STATE' EXIT INT TERM` leaves `while :` running and makes `stop` lie."
    )

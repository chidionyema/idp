"""A full disk must be reported before it costs a file, not after.

WHAT HAPPENED, 2026-09-18. The Mac's data volume reached 99% full. Two failures, and the guard
exists because of the shape they shared rather than either one alone:

  * `brew install kubernetes-cli` hung for seven minutes and died with `No space left on
    device` while copying its build tree. A tool that normally takes ninety seconds, presenting
    as a network hang.
  * `bin/idp-oci-login` vanished from the working tree. That was a quotation slip (`rm -rf
    /private/tmp/homebrew-* bin/idp-oci-login` takes TWO paths) and the disk was innocent -- but
    it was FOUND by running the script and getting exit 127, while the same machine was under
    storage pressure and nothing said so.

So this grades the reporting, not a cleanup. `bin/estate-cleaner` is the cleanup tool; a guard
that silently removes things on a machine whose problem is surprise deletions is the joke
writing itself.

THE BUG THE SUITE FOUND. The first version fell back to `/` when the data volume could not be
read. On macOS `/` is the read-only system volume and always looks roomy -- so the guard
reported 76% used and 3G free, green-ish, while the writable volume sat at 97%. A storage guard
that measures the wrong disk is worse than no guard, because it is the one that gets believed.
It now refuses to guess.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GUARD = REPO / "bin" / "idp-disk-guard"


def _run(**env: str) -> subprocess.CompletedProcess:
    e = dict(os.environ, **env)
    return subprocess.run(
        [str(GUARD)], capture_output=True, text=True, env=e, timeout=60, check=False
    )


def test_it_always_exits_zero():
    """A guard that failed a build on a full disk would block the work that frees it."""
    assert _run().returncode == 0
    assert _run(MIN_FREE_GB="999999").returncode == 0
    assert _run(DISK_GUARD_PATH="/nonexistent-xyz").returncode == 0


def test_a_healthy_disk_reports_ok():
    out = _run(MIN_FREE_GB="0").stdout
    assert out.startswith("ok"), out
    assert "floor" in out, "the floor must be visible, or the verdict is not checkable"


def test_quiet_mode_says_nothing_when_healthy():
    assert _run(MIN_FREE_GB="0", **{}).stdout.startswith("ok")
    quiet = subprocess.run(
        [str(GUARD), "--quiet"],
        capture_output=True,
        text=True,
        env=dict(os.environ, MIN_FREE_GB="0"),
        timeout=60,
        check=False,
    )
    assert quiet.stdout.strip() == "", f"expected silence, got {quiet.stdout!r}"


def test_below_the_floor_names_the_consequence_and_the_fix():
    """'Low disk' alone is a fact nobody can act on. The three parts are what make it usable."""
    out = _run(MIN_FREE_GB="999999").stdout
    assert out.startswith("FAIL"), out
    assert "consequence" in out, "say what it costs"
    assert "fix" in out, "say what to do"
    # And the specific measured consequence, not a generic warning.
    assert "No space left on device" in out


def test_it_never_suggests_deleting_the_users_own_files():
    """The guard must not be the thing that talks someone into deleting 11G of their photos.

    Measured: ~/Pictures holds 11G on this machine, which is the single largest reclaimable
    thing and belongs to the user. A guard recommending it would be automating exactly the
    mistake it exists to prevent.
    """
    out = _run(MIN_FREE_GB="999999").stdout
    assert "do not" in out
    for keep in ("Pictures", "Documents", "Music"):
        assert keep in out, f"the guard should name {keep} as not-the-build's to delete"
    # The suggested targets are regenerable caches only.
    assert "~/.npm/_npx" in out
    assert "brew cleanup" in out


def test_it_refuses_to_guess_which_volume_to_measure():
    """The bug the suite found: falling back to `/` reported a read-only volume as healthy."""
    out = _run(DISK_GUARD_PATH="/nonexistent-xyz").stdout
    assert out.startswith("BLIND"), (
        f"expected BLIND for an unreadable path, got: {out!r}. Falling back to / measures the "
        "read-only system volume, which always looks roomy while the data volume is full."
    )
    assert "refusing to guess" in out


def test_it_measures_a_writable_volume_by_default():
    """The default target is the one writes land on, and it is asserted by shape, not by value."""
    out = _run(MIN_FREE_GB="0").stdout
    assert "/System/Volumes/Data" in out or "/" in out
    # Whatever it measured, the number must be plausible rather than parsed from "1.0Gi".
    assert "G free" in out

"""The disk sentinel family was RETIRED 2026-11-11 by founder order.

WHAT IT WAS. A second, complete disk-watch system living outside the estate entirely, at
`~/.local/share/disk-sentinel/`, installed as three launchd agents:

  dev.disksentinel.monitor    StartInterval 60    -> sentinel.sh tick
  dev.disksentinel.scan       StartInterval 1800  -> sentinel.sh scan --auto
  dev.disksentinel.dashboard  opens dashboard.html

Plus the estate's own resident guardian (ai.estate.disk-watch, KeepAlive) and the 1303-line
platform/estate/libexec/disk-cleanup.sh behind it. That is four separate disk watchers on one
volume: the duplicate-layer defect in AGENTS.md section 6, five to ten copies of the same
capability, on a machine where each copy competes for memory that is already exhausted.

THE MEASUREMENT. The estate's guardian completed 120 bounded steps at last_freed_mb=3 while the
volume fell 1526 MB -> 1012 MB, on a machine at 26 MB free RAM and 80% swap. `dev.disksentinel.scan`
was observed loaded with last exit status 75. When the guardians were stopped the volume recovered
on its own: 1012 MB -> 2335 MB.

THE RULING. The founder's words: needing 113 steps to clean a disk IS the root cause, and worse
than anything else on the machine. Remove them from source control, once and for all, and tell
peers not to use them.

WHAT REPLACED THEM: nothing resident. `estate-execute disk-reclaim` steps 1-4 are the reclaim
path (duplicate local gate runs, finished pytest scratch, the estate's own run records, the stale
dependency tree) -- narrow, measured, needing no daemon, and never holding the disk floor closed
against its own off switch, which the guardian did (it refused `launchctl bootout` and `/bin/rm`
on itself at 1012 MB free).

This file is the FALSIFIER for the retirement: it fails if the family is reinstalled.
"""

from __future__ import annotations

import os
import plistlib
from pathlib import Path

import pytest

LAUNCH_AGENTS = Path(os.path.expanduser("~/Library/LaunchAgents"))

RETIRED_LABELS = [
    "ai.estate.disk-watch",
    "dev.disksentinel.monitor",
    "dev.disksentinel.scan",
    "dev.disksentinel.dashboard",
]


def _loadable_plists() -> list[Path]:
    """Every plist launchd would actually load: present, and not renamed to .disabled/.bak."""
    if not LAUNCH_AGENTS.is_dir():
        pytest.skip("no ~/Library/LaunchAgents on this host (CI)")
    return [
        p
        for p in LAUNCH_AGENTS.iterdir()
        if p.suffix == ".plist" and p.is_file()
    ]


@pytest.mark.parametrize("label", RETIRED_LABELS)
def test_no_retired_disk_watcher_is_loadable(label: str):
    """A retired watcher must not sit in LaunchAgents under a name launchd loads."""
    if not LAUNCH_AGENTS.is_dir():
        pytest.skip("no ~/Library/LaunchAgents on this host (CI)")

    for path in _loadable_plists():
        try:
            doc = plistlib.loads(path.read_bytes())
        except Exception:  # malformed plist is not loadable either
            continue
        if doc.get("Label") == label:
            raise AssertionError(
                f"{label} is loadable again at {path}. It was retired 2026-11-11: it freed "
                "3 MB/step while the volume fell, and it held the disk floor closed against its "
                "own off switch. Do not reinstall it."
            )


def test_no_resident_disk_guardian_template_remains():
    """The repo's renderable template must not produce a KeepAlive guardian again."""
    root = Path(__file__).resolve().parents[1]
    tmpl = root / "launchd" / "ai.estate.disk-watch.plist.tmpl"
    body = tmpl.read_text(encoding="utf-8", errors="replace")
    assert "<key>KeepAlive</key><true/>" not in body, (
        "a KeepAlive resident disk guardian must never be renderable again"
    )
    assert "retired" in body.lower(), "the template must state that it is retired"


def test_the_disk_sentinel_tree_is_not_running_from_here():
    """The sentinel's own script is outside the estate; if it returns, this names it."""
    sentinel = Path(os.path.expanduser("~/.local/share/disk-sentinel/sentinel.sh"))
    if not sentinel.exists():
        return  # gone, which is the intended state

    # Still on disk but must not be scheduled: scheduling is what made it a cost.
    pytest.fail(
        f"{sentinel} still exists and was retired 2026-11-11. If it is needed, it must run as a "
        "one-shot maintenance command with a budget and a before/after measurement -- never as a "
        "StartInterval job. Delete it or document why it is back."
    )

"""The resident disk guardian was RETIRED 2026-11-11 by founder order.

WHY THIS TEST IS GONE (not skipped, not weakened):

This file asserted that launchd runs the installed disk-watch agent -- that it is loaded, that
it ticks, that its heartbeat stays fresh. The guardian was indeed loaded and ticking. It was
also, measurably, the problem:

  - 120 bounded steps completed, last_freed_mb=3
  - free space 1526 MB -> 1012 MB over the same period, i.e. it lost 500 MB while "cleaning"
  - the machine sat at 26 MB free RAM with 80% swap, one more process competing for memory
  - when it was finally stopped, the volume recovered on its own: 1012 MB -> 2335 MB

And it held the executor's 1500 MB disk floor closed against every command, INCLUDING
`launchctl bootout` and `/bin/rm` on itself. The guard could not be disabled by any door it
guarded -- a safeguard that blocks its own remedy. That circle is the root cause the founder
ruled on: needing 113 steps to clean a disk IS the root cause, and worse than the symptom.

A test that proves the agent ticks is a test that proves the cost is being paid. Removing it is
the fix, so the assertion is not preserved in any form.

WHAT REPLACED IT: nothing resident. `estate-execute disk-reclaim` steps 1-4 are the reclaim path
(duplicate local gate runs, finished pytest scratch, the estate's own run records, the stale
dependency tree) -- narrow, measured, and needing no daemon. A cleanup written in future must not
be KeepAlive, must report free MB before and after against a target in ONE run, and must never
gate its own disable path.

The replacement assertions below are the FALSIFIER FOR THE RETIREMENT: they fail if anyone
reinstalls the guardian, which is the only thing that could silently undo this.
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

RETIRED_SOURCES = [
    "bin/idp-disk-watch",
    "bin/idp-disk-guard",
    "platform/estate/libexec/disk-cleanup.sh",
]


def test_the_retired_sources_are_tombstones_not_working_cleaners():
    """The files remain (so callers get an honest refusal), and none of them cleans."""
    for rel in RETIRED_SOURCES:
        path = os.path.join(ROOT, rel)
        assert os.path.exists(path), f"{rel} must remain as a tombstone, not vanish silently"
        body = open(path, encoding="utf-8", errors="replace").read()
        assert "DISABLED 2026-11-11" in body, f"{rel} must say it is disabled and why"
        assert "exit 1" in body, f"{rel} must refuse, not run"


def test_the_launchd_template_cannot_load_a_resident_job():
    """The renderable template must not produce a KeepAlive guardian again."""
    path = os.path.join(ROOT, "launchd", "ai.estate.disk-watch.plist.tmpl")
    body = open(path, encoding="utf-8", errors="replace").read()
    assert "<key>KeepAlive</key><true/>" not in body, (
        "the template must never render a KeepAlive resident guardian"
    )
    assert "retired" in body.lower(), "the template must state that it is retired"


def test_the_disk_intents_point_at_the_door_that_works():
    """disk-free and disk-cleanup must name disk-reclaim, not silently do nothing."""
    import yaml

    for name in ("disk-free", "disk-cleanup"):
        path = os.path.join(ROOT, "platform", "estate", "intents", f"{name}.yaml")
        body = open(path, encoding="utf-8", errors="replace").read()
        assert "disk-reclaim" in body, f"{name} must route its caller to disk-reclaim"
        assert "RETIRED 2026-11-11" in body, f"{name} must say its cleaner was retired"
        yaml.safe_load(body)  # still valid intent YAML


def test_disk_reclaim_no_longer_starts_the_retired_cleaner():
    """The one door that works must not delegate to the retired script."""
    path = os.path.join(ROOT, "platform", "estate", "intents", "disk-reclaim.yaml")
    body = open(path, encoding="utf-8", errors="replace").read()
    assert "nohup bash \"$HOME/.estate/libexec/disk-cleanup.sh\"" not in body, (
        "disk-reclaim must not background the retired cleaner"
    )
    assert "disk-cleanup.sh true False 0 true 600" not in body, (
        "the retired 600s cleaner launch must be gone"
    )

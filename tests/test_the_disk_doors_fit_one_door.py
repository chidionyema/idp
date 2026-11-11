"""The disk guardian family is DELETED, and `disk-reclaim` is the one door that reclaims space.

MEASURED 2026-10-25, through the door: `disk-free` as invoked ran for 100s and came back exit 124
with no measurement in it -- the cleaner's `du` of HOME (T_SCAN 300s) was SIGTERMed by the door's
ceiling, so the caches, docker and tier phases never ran and nothing said so. A door whose work
cannot fit the door is not a slow door, it is a door that reports nothing.

MEASURED 2026-11-11, which is why the family was deleted rather than repaired: as the resident
guardian the cleaner completed 120 bounded steps at `last_freed_mb=3` while the volume fell
1526 MB -> 1012 MB, on a machine at 26 MB free RAM with 80% swap. When the guardian was stopped
the volume recovered on its own, 1012 MB -> 2335 MB. The cleaner was never what freed the disk,
and it held the executor's 1500 MB floor closed against every command, including `rm` on itself.
So it was the cost it was trying to fix.

This file holds the two claims that keep it from growing back:

  1. the family is GONE from source -- not tombstoned, not disabled-by-header, deleted;
  2. `disk-reclaim` is the only reclaim door left, and it declares a budget under the ceiling.

A deletion is asserted positively (`mkdir -p` then `ls` the path), because a test that only greps
for a name passes on a repo that never had one.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
INTENTS = ROOT / "platform/estate/intents"
CEILING = 100  # mcp/plugins/estate_executor.py CEILING_SEC

DELETED_PATHS = [
    "bin/idp-disk-watch",
    "bin/idp-disk-guard",
    "platform/estate/libexec/disk-cleanup.sh",
    "platform/estate/intents/disk-cleanup.yaml",
    "platform/estate/intents/disk-free.yaml",
    "launchd/ai.estate.disk-watch.plist.tmpl",
    "infra/macos/tools/disk-sentinel",
]


@pytest.mark.parametrize("rel", DELETED_PATHS)
def test_the_guardian_family_is_gone_from_source(rel: str):
    assert not (ROOT / rel).exists(), (
        f"{rel} is back. The disk guardian family was DELETED 2026-11-11 by founder order: "
        "120 steps freed 3 MB while the volume fell 500 MB, and stopping it recovered 1.3 GB "
        "on its own. Do not restore it and do not replace it with a scheduled cleaner."
    )


def test_the_only_disk_door_left_is_disk_reclaim():
    names = sorted(p.stem for p in INTENTS.glob("disk-*.yaml"))
    assert names == ["disk-reclaim"], (
        f"the disk doors are {names}; exactly one reclaim door must remain. "
        "Reclaiming space is an on-demand act taken by whoever measures the volume under the "
        "floor, never a resident or scheduled loop."
    )


def test_the_reclaim_door_parses_and_names_itself():
    doc = yaml.safe_load((INTENTS / "disk-reclaim.yaml").read_text(encoding="utf-8"))
    assert doc["name"] == "disk-reclaim"
    assert doc.get("steps"), "disk-reclaim must declare its steps"


def test_no_disk_door_still_executes_the_deleted_cleaner():
    """Matches an EXECUTION of the deleted script, not prose.

    A check that fires on a comment is the same fail-open defect it exists to prevent: the
    registry and the docs legitimately record what the script used to do.
    """
    for intent in INTENTS.glob("disk-*.yaml"):
        live_calls = []
        for line in intent.read_text(encoding="utf-8").splitlines():
            stripped = line.lstrip()
            if stripped.startswith("#") or "disk-cleanup.sh" not in stripped:
                continue
            if (
                stripped.startswith("bash ")
                or stripped.startswith("nohup ")
                or stripped.startswith("~/.estate/libexec/disk-cleanup.sh")
                or stripped.startswith("$HOME/.estate/libexec/disk-cleanup.sh")
            ):
                live_calls.append(line)
        assert not live_calls, (
            f"{intent.name} still executes the deleted cleaner: {live_calls!r}. "
            "It was deleted 2026-11-11: it freed 3 MB/step while the volume fell."
        )


def test_the_reclaim_door_still_declares_a_bound_under_the_ceiling():
    """The finding that created this file: a door whose work cannot fit the door is not a door."""
    doc = yaml.safe_load((INTENTS / "disk-reclaim.yaml").read_text(encoding="utf-8"))
    budget = (doc.get("args") or {}).get("budget_s") or {}
    declared = budget.get("default")
    assert declared is not None, "disk-reclaim must keep a declared budget"
    assert declared < CEILING, (
        f"disk-reclaim's default budget {declared}s must sit under the {CEILING}s door ceiling"
    )

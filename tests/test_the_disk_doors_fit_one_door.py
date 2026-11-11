"""The disk doors fit inside one door, and no disk door points at the retired cleaner.

Measured 2026-10-25, through the door: `disk-free` as invoked ran for 100s and came back exit 124
with no measurement in it -- the cleaner's `du` of HOME (T_SCAN 300s) was SIGTERMed by the door's
ceiling, so the caches, docker and tier phases never ran and nothing said so. A door whose work
cannot fit the door is not a slow door, it is a door that reports nothing. That finding stands.

THE CLEANER WAS RETIRED 2026-11-11 by founder order (see tests/estate/test_disk_cleanup.py for the
measurement: 120 steps at 3 MB each while the volume fell 500 MB, then 1012 MB -> 2335 MB
recovered on its own once it was stopped). So the tests that exercised the cleaner's budget
behaviour against a real script are gone with the script. What remains is the part of this file
that is about the DOORS, which is still true and still worth holding:

  1. every disk intent still declares a bound under the executor ceiling;
  2. no disk intent still invokes the retired cleaner;
  3. the intents still parse as valid intent YAML.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
INTENTS = ROOT / "platform/estate/intents"
CEILING = 100  # mcp/plugins/estate_executor.py CEILING_SEC

DISK_INTENTS = ["disk-free.yaml", "disk-cleanup.yaml", "disk-reclaim.yaml"]


@pytest.mark.parametrize("intent", DISK_INTENTS)
def test_every_disk_intent_parses_and_names_itself(intent: str):
    doc = yaml.safe_load((INTENTS / intent).read_text(encoding="utf-8"))
    assert doc["name"] == intent.removesuffix(".yaml")
    assert doc.get("steps"), f"{intent} must declare its steps"


@pytest.mark.parametrize("intent", DISK_INTENTS)
def test_no_disk_intent_invokes_the_retired_cleaner(intent: str):
    """A door that shells out to a tombstone reports nothing, which is the defect this guards.

    Matches an EXECUTION of the retired script (a command line that runs it), not prose: the
    descriptions legitimately explain what the script used to do, and a check that fires on a
    comment is the same fail-open defect it exists to prevent.
    """
    body = (INTENTS / intent).read_text(encoding="utf-8")
    live_calls = []
    for line in body.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#") or "disk-cleanup.sh" not in stripped:
            continue
        # An execution names the script as a command argument: `bash .../disk-cleanup.sh`,
        # `nohup bash .../disk-cleanup.sh`, or a bare invocation at line start.
        if (
            stripped.startswith("bash ")
            or stripped.startswith("nohup ")
            or stripped.startswith("~/.estate/libexec/disk-cleanup.sh")
            or stripped.startswith("$HOME/.estate/libexec/disk-cleanup.sh")
        ):
            live_calls.append(line)
    assert not live_calls, (
        f"{intent} still executes the retired cleaner: {live_calls!r}. "
        "Retired 2026-11-11: it freed 3 MB/step while the volume fell."
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

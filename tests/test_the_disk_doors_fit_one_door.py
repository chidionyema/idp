"""Disk reclamation is ONE deterministic shell script. No guardian, no intent, no agent.

THE LAW (founder, 2026-11-11, "PIN 10"). Disk reclamation is 100 percent machine-owned. A short
POSIX shell script running via cron/launchd deletes caches, scratch and oversized logs
deterministically, and NEVER spawns an agent. The founder's instruction, verbatim: "DELETE EVERY
DISK CLEANUP CODE NOW".

MEASURED 2026-11-11, which is why the family was deleted rather than repaired: as the resident
guardian the 804-line `bin/idp-disk-watch` completed 225 bounded steps at `last_freed_mb=3` while
the volume fell 1526 MB -> 1012 MB, and on low disk it raised an incident and woke an LLM agent to
clean the disk -- while `estate-execute` simultaneously refused every agent command because free
space was under the 1500 MB floor. That is a self-DDoS: the cleaner blocked by the condition it
exists to fix. When the guardian was stopped the volume recovered on its own, 1012 MB -> 2335 MB.

So the family is GONE from source -- not tombstoned, not disabled behind a flag, deleted. What
replaced it is `bin/estate-cache-trim`: POSIX shell, bounded, deterministic, no agent.

This file holds the three claims that keep the family from growing back:

  1. every path of the guardian family is ABSENT from the tree;
  2. no disk intent survives -- reclamation is a script, not a door with steps and a budget;
  3. the one survivour is shell, is bounded, and names no agent/LLM/model anywhere.

A deletion is asserted POSITIVELY (stat the path), because a test that only greps for a name
passes just as happily on a repo that never had one.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
INTENTS = ROOT / "platform/estate/intents"

DELETED_PATHS = [
    # The guardian family, deleted 2026-11-11.
    "bin/idp-disk-watch",
    "bin/idp-disk-guard",
    "platform/estate/libexec/disk-cleanup.sh",
    "platform/estate/intents/disk-cleanup.yaml",
    "platform/estate/intents/disk-free.yaml",
    "platform/estate/intents/disk-reclaim.yaml",
    "launchd/ai.estate.disk-watch.plist.tmpl",
    "launchd/ai.estate.disk-cleanup.plist.tmpl",
    "infra/macos/tools/disk-sentinel",
    # Their tests went with them: a test for a deleted thing is a tombstone.
    "tests/estate/test_disk_cleanup.py",
    "tests/estate/test_disk_watch.py",
    "tests/test_disk_cleanup_keeps_a_claimed_worktree.py",
    "tests/test_disk_sentinel_retired.py",
    "tests/test_disk_watch_plist_runs.py",
]


@pytest.mark.parametrize("rel", DELETED_PATHS)
def test_the_guardian_family_is_gone_from_source(rel: str):
    assert not (ROOT / rel).exists(), (
        f"{rel} is back. The disk guardian family was DELETED 2026-11-11 by founder order "
        "('DELETE EVERY DISK CLEANUP CODE NOW'): 225 steps freed 3 MB while the volume fell "
        "500 MB, and stopping it recovered 1.3 GB on its own. Do not restore it, do not "
        "tombstone it, and do not replace it with a scheduled agent."
    )


def test_no_disk_intent_survives():
    """Reclamation is a shell script, not a door.

    A disk intent is the family's shape: steps, a budget, a place to add phase six. The founder's
    replacement is 20 lines of POSIX that a cron entry runs. If a `disk-*.yaml` appears here, the
    family has grown back through the door instead of through `bin/`.
    """
    stragglers = sorted(p.name for p in INTENTS.glob("disk-*.yaml"))
    assert stragglers == [], (
        f"disk intents are back: {stragglers!r}. Disk reclamation is machine-owned POSIX shell "
        "in bin/estate-cache-trim, never an intent with steps an agent can extend."
    )


def test_the_one_disk_script_is_posix_shell_and_bounded():
    """The surviving script must stay a script: shell, short, and with a hard target."""
    script = ROOT / "bin" / "estate-cache-trim"
    assert script.is_file(), (
        "bin/estate-cache-trim is the ONE surviving piece of disk reclamation; it must exist"
    )
    text = script.read_text(encoding="utf-8")
    first = text.splitlines()[0]
    assert first.startswith("#!") and ("sh" in first), (
        f"estate-cache-trim must be POSIX shell, got shebang {first!r}: a Python disk daemon is "
        "the family this replaced"
    )
    assert "set -eu" in text, "a disk script must fail loudly, never continue on error"
    assert "TARGET_MB" in text, (
        "a reclamation pass must declare the target it is reclaiming toward, or 'ran and freed "
        "nothing' reports success -- which is exactly how the guardian failed for weeks"
    )


def test_the_disk_script_never_spawns_an_agent():
    """Pin 10, in one assertion: the machine owns this, an LLM does not.

    The 804-line guardian raised an incident and woke an agent to clean the disk. That is the
    thing the founder ordered deleted. The replacement may run `rm`, `find` and `df`; the moment
    it can call a model, an agent or the estate's door, the defect is back.
    """
    text = (ROOT / "bin" / "estate-cache-trim").read_text(encoding="utf-8")
    # An INVOCATION of an agent or the door, never a path that happens to be named after one:
    # `/private/tmp/claude-501` is a cache directory the script deletes, and matching that name
    # would push a maintainer to rename the cache instead of keeping the law.
    forbidden = re.compile(
        r"(?:^|[|;&(]\s*)(?:/\S*/)?(?:claude|codex|minimax|gemini|llm|agent|"
        r"estate-execute|estate_invoke)\b",
        re.IGNORECASE,
    )
    # Only execution counts: the header comment may say why the guardian was wrong.
    live = [
        line
        for line in text.splitlines()
        if not line.lstrip().startswith("#") and forbidden.search(line)
    ]
    assert live == [], (
        f"estate-cache-trim can reach an agent/model: {live!r}. Disk reclamation is "
        "100 percent machine-owned (Pin 10)."
    )

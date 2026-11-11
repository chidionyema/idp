"""Falsifier: `bin/lane-where` must not call a landed lane GONE.

Measured 2026-11-10, the defect this pins down: `lane/disk-watch-plist` was handed to the
greenlane, landed on main as squash `166c9dc88`, and the greenlane then DELETED the lane ref --
which is what it does after a landing. `lane-where` answered

    GONE    lane-where  lane/disk-watch-plist  no such branch on origin (never pushed, or deleted)
    exit 5

for a branch whose two files were byte-identical to landed main. That is the worst shape an
answer can take: the work succeeded and the door reports failure, so an agent redoes it and
raises a second, conflicting change. The estate has already recorded that same class for
squash-landings ("make an agent redo work and raise a second, conflicting PR"), and this is its
sibling: a missing ref is a missing witness, not a verdict.

The rule: a deleted ref must be judged by whether the lane's CONTENT landed, and only a branch
this checkout never saw at all may be called GONE.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
DOOR = REPO / "bin" / "lane-where"


def _read() -> str:
    return DOOR.read_text(encoding="utf-8")


def test_door_exists_and_is_executable() -> None:
    assert DOOR.is_file(), f"{DOOR} is missing"
    assert DOOR.stat().st_mode & 0o111, "bin/lane-where is not executable"


def test_missing_ref_is_not_answered_before_the_land_question() -> None:
    """The defect itself: `if not head:` must not return a verdict before asking about content.

    This is the assertion that fails on the old door and passes on the fixed one. It reads the
    control flow rather than a message, because a message can be reworded while the early return
    stays: what matters is that the missing-ref branch consults the local head before answering.
    """
    src = _read()
    m = re.search(r"if not head:\n(.*?)\n    receipt\.update\(status=", src, re.S)
    assert m, "the `if not head:` branch is gone; this falsifier needs rewriting, not deleting"
    branch_src = m.group(1)
    assert "_local_head(" in branch_src, (
        "a branch missing from origin is answered without checking whether its content landed: "
        "a landed-then-deleted lane will read GONE"
    )
    assert "landed_by_content(" in branch_src, (
        "the missing-ref path must judge the lane by content, not by the absence of a ref"
    )


def test_local_head_falls_back_through_branch_tracking_ref_and_reflog() -> None:
    src = _read()
    m = re.search(r"def _local_head\(branch: str\).*?\n\ndef ", src, re.S)
    assert m, "_local_head is missing"
    body = m.group(0)
    for ref in ("refs/heads/", "refs/remotes/origin/", "reflog"):
        assert ref in body, f"_local_head does not consult {ref}; a deleted lane may be unrecoverable"


def test_never_pushed_branch_is_still_gone() -> None:
    """The other direction, against a real repository: a name no ref knows is GONE with exit 5."""
    proc = subprocess.run(
        [str(DOOR), "lane/never-pushed-2f4c1a9e-never-existed"],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode in (5, 2), (
        f"a branch nothing has ever seen must read GONE (5) or BLIND (2), got {proc.returncode}: "
        f"{proc.stdout}{proc.stderr}"
    )
    out = proc.stdout + proc.stderr
    assert "GONE" in out or "BLIND" in out
    assert "LANDED" not in out, f"an unknown branch was reported as landed: {out}"


def test_a_landed_lane_is_not_gone() -> None:
    """If a lane that landed is visible in this checkout, it must not read GONE.

    Skips when no such lane is present rather than passing vacuously: a test that executes
    nothing is not a test.
    """
    lane = "lane/disk-watch-plist"
    seen = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", lane],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    if seen.returncode != 0 or not seen.stdout.strip():
        pytest.skip(f"{lane} is not in this checkout; nothing to measure here")
    proc = subprocess.run(
        [str(DOOR), lane], cwd=REPO, capture_output=True, text=True, timeout=120
    )
    out = proc.stdout + proc.stderr
    assert "GONE" not in out, f"a lane whose content is in main was reported GONE: {out}"

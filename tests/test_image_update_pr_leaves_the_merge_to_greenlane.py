"""The flux/image-updates pull request is landed by greenlane, never by native auto-merge (2026-10-13).

flux/image-updates is greenlane's BOT_LANE: the engine batches it, rebases it, pushes the rebased
sha and squash-merges that exact sha. bin/idp-image-update-pr used to end with bin/idp-pr-arm, and
with allow_auto_merge true again every controller push armed GitHub's auto-merge on the same pull
request (#6107), which merges whatever head goes green first and races the engine for main.

These run the script itself against a fake `gh` and pin both directions: nothing arms, and an arm
left by an older run is taken off.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin/idp-image-update-pr"

FAKE_GH = """#!/usr/bin/env bash
echo "$*" >> "$LOG"
case "$*" in
  "pr list"*) echo 7 ;;
  *"--json body"*) echo 'Verify: `grep -rn imagepolicy platform/`' ;;
  *"--json mergeable"*) echo MERGEABLE ;;
  *"--json mergeStateStatus"*) echo BLOCKED ;;
  *"--json autoMergeRequest"*) echo "$ARMED" ;;
esac
"""


def _run(tmp_path: Path, armed: str) -> tuple[subprocess.CompletedProcess, list[str]]:
    (tmp_path / "gh").write_text(FAKE_GH)
    (tmp_path / "gh").chmod(0o755)
    log = tmp_path / "gh.log"
    log.touch()
    env = {
        **os.environ,
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        "LOG": str(log),
        "ARMED": armed,
        "GH_REPO": "o/r",
        "MERGEABLE_WAIT": "0",
    }
    run = subprocess.run(
        ["bash", str(SCRIPT)], capture_output=True, text=True, env=env, timeout=30
    )
    return run, log.read_text().splitlines()


def test_an_open_flux_pr_is_never_armed(tmp_path):
    run, calls = _run(tmp_path, armed="false")
    assert run.returncode == 0, run.stdout + run.stderr
    assert not [c for c in calls if c.startswith("pr merge")], calls
    assert run.stdout.strip().splitlines()[-1].startswith("ok"), run.stdout


def test_an_arm_left_by_an_older_run_is_taken_off(tmp_path):
    run, calls = _run(tmp_path, armed="true")
    assert run.returncode == 0, run.stdout + run.stderr
    merges = [c for c in calls if c.startswith("pr merge")]
    assert merges == ["pr merge 7 --disable-auto"], calls


def test_the_script_no_longer_reaches_for_pr_arm():
    src = "\n".join(
        line
        for line in SCRIPT.read_text().splitlines()
        if not line.lstrip().startswith("#")
    )
    assert "idp-pr-arm" not in src and "--auto" not in src.replace("--disable-auto", "")

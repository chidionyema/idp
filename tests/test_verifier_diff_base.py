"""The verifier's diff base, read from the real step in .github/workflows/verifier.yml.

Measured 2026-09-27: every flux/image-updates PR carried a red verifier because the push that
creates the branch has github.event.before = forty zeros, and `git diff 0000…...HEAD` is git exit
128. This runs the step's own base selection (everything before the diff) under bash for each
event, so the fix cannot drift from the file CI runs.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/verifier.yml"
ZEROS = "0" * 40


def _base(event: str, before: str) -> str:
    steps = yaml.safe_load(WORKFLOW.read_text())["jobs"]["verifier"]["steps"]
    run = next(s for s in steps if s.get("name") == "run verifier gauntlet")["run"]
    script = (
        run.split("diff_out=")[0]
        .replace("${{ github.event_name }}", event)
        .replace("${{ github.event.before }}", before)
        .replace("${{ github.base_ref }}", "main")
    )
    r = subprocess.run(
        ["bash", "-c", script + 'printf %s "$base"'],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert r.returncode == 0, r.stderr
    return r.stdout


@pytest.mark.parametrize(
    ("event", "before", "want"),
    [
        ("push", ZEROS, "origin/main"),
        ("push", "1a2b3c4d", "1a2b3c4d"),
        ("push", "1" + ZEROS, "1" + ZEROS),
        ("pull_request", "1a2b3c4d", "origin/main"),
        ("merge_group", "", "origin/main"),
    ],
)
def test_the_diff_base_for_each_event(event, before, want):
    assert _base(event, before) == want

"""The lifeboat node tests never touch the repository a git hook runs them from (idp#8602).

Under pre-push git exports GIT_DIR. seal-cli.test.mjs ran `git -C <tmp> init` and
`git config user.name ...`, which then wrote to the hook's repository: core.bare=true and a
synthetic identity in the shared .git/config, breaking every worktree on the machine. This
runs the real test file with GIT_DIR aimed at a victim repo and requires the victim unchanged.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEST = ROOT / "platform" / "lifeboat" / "test" / "seal-cli.test.mjs"


def _node22() -> bool:
    node = shutil.which("node")
    if not node:
        return False
    out = subprocess.run([node, "--version"], capture_output=True, text=True).stdout
    return out.startswith("v") and int(out[1:].split(".")[0]) >= 22


@pytest.mark.skipif(not _node22(), reason="Node.js 22+ not installed")
def test_seal_cli_test_cannot_reinit_the_hook_repo(tmp_path):
    victim = tmp_path / "victim"
    subprocess.run(["git", "init", "-q", str(victim)], check=True)
    cfg = victim / ".git" / "config"
    before = cfg.read_bytes()
    env = dict(os.environ, GIT_DIR=str(victim / ".git"), GIT_WORK_TREE=str(victim))
    subprocess.run(
        ["node", "--test", str(TEST)],
        cwd=TEST.parent.parent,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    after = cfg.read_bytes()
    assert b"bare = true" not in after
    assert b"Synthetic test" not in after
    assert after == before

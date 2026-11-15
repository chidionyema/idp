"""The integrity guard refuses when a hook exists but cannot run.

2026-11-15. `.githooks/pre-push` was tracked as mode 100644. The guard that delegates to it asked
`is_file() and X_OK`, and returned 0 for "exists but is not executable", so a one-character file
mode change switched off every gate in `.githooks/` silently. Eight lanes reached the merge queue
with no `Claim:` line before anyone saw it: the claim guard, Layer 0 and the fast gate had not run
on any push for hours.

The guard was untracked, living only in `.git/estate-test-integrity-hooks/guard`, so it had no
source, no review and no test. This file is the falsifier for the fail-closed half: a hook that
cannot run is a broken boundary, not an absent one.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GUARD = REPO / "bin" / "estate-test-integrity-guard"


def _repo(tmp_path: Path, executable: bool) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    hooks = tmp_path / ".githooks"
    hooks.mkdir()
    hook = hooks / "pre-commit"
    hook.write_text("#!/bin/sh\nexit 0\n")
    hook.chmod(0o755 if executable else 0o644)
    return tmp_path


def _guard(repo: Path) -> subprocess.CompletedProcess:
    # pre-commit exercises the same delegation without the pre-push merge-base preflight, so the
    # property under test is the delegation itself and nothing else.
    return subprocess.run(
        [sys.executable, str(GUARD), "pre-commit"],
        cwd=repo, input="", capture_output=True, text=True,
    )


def test_a_hook_that_exists_and_cannot_run_is_refused(tmp_path):
    out = _guard(_repo(tmp_path, executable=False))
    assert out.returncode == 1, f"the guard passed a hook it could not run: {out.stdout}"
    assert "not executable" in out.stderr and "chmod +x" in out.stderr


def test_an_executable_hook_is_delegated_to_and_its_verdict_is_kept(tmp_path):
    out = _guard(_repo(tmp_path, executable=True))
    assert out.returncode == 0, f"an executable hook that passes was refused: {out.stderr}"

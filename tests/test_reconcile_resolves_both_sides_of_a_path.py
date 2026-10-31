"""bin/idp-reconcile must compare a path the same way on BOTH sides of the comparison.

Measured 2026-10-27 on this laptop, with the checkout reached through a symlink -- on macOS
/tmp is a symlink to /private/tmp, and every agent's worktree lives under /tmp -- the tool
called the legitimate foreign project `prospector-edge` ROGUE:

    FAIL  reconcile rogue       prospector-edge: no compose file, foreign prefix or name prefix owns it
    FAIL  reconcile 3 projects, 1 drift

and the good fixture exited 1, so the estate's own gate rung ("a rogue container is a finding,
the clean fixture is not") failed on every worktree under /tmp, including the one the agents
work in. The cause is that the container's compose config path is compared AFTER
os.path.realpath() while the foreign project prefix is only expanded, never resolved: one side
of the comparison is resolved and the other is not, so a directory that is the same directory
however it is spelled reads as two different directories. With --fix that classification removes
a legitimate product container (`docker rm -f prospector-edge`).

The invariant this file pins down: a checkout reached through a symlink is still the same
checkout -- so the clean fixture is clean -- and the rogue fixture is STILL rogue, because a fix
that made the comparison blind would be worse than the defect it repairs.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "bin" / "idp-reconcile"
FIXTURES = ROOT / "tests" / "fixtures" / "reconcile"


def _symlinked_code(tmp_path) -> str:
    """A code directory that is reached through a symlink, which is how every agent's worktree
    on this laptop is reached. The link is the whole point: without it the two sides of the
    comparison are spelled the same way and the defect cannot be seen."""
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real)
    return str(link)


def _run(fixture: str, code: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, CODE=code, IDP=str(ROOT))
    return subprocess.run(
        [sys.executable, str(TOOL), "--ps", str(FIXTURES / fixture)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        check=False,
    )


def test_the_clean_fixture_is_clean_through_a_symlinked_checkout(tmp_path):
    result = _run("ps.good.jsonl", _symlinked_code(tmp_path))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "prospector-edge" not in result.stdout


def test_a_rogue_container_is_still_rogue_through_a_symlinked_checkout(tmp_path):
    result = _run("ps.rogue.jsonl", _symlinked_code(tmp_path))
    assert result.returncode != 0, result.stdout + result.stderr
    assert "rogue-redis" in result.stdout

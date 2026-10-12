"""A script under `bin/` that carries a shebang is a door somebody types.

`docs/runbooks/greenlane.md:40` tells whoever carries the lane to run `bin/idp-greenlane
status`. It was committed mode 100644 while 387 of the 394 files in `bin/` are 100755, so the
door the runbook names answered `Permission denied` -- which reads as a broken script rather
than a missing mode bit (idp#5946). Thirteen shebang'd scripts were in that state, not one:
every `estate-*-` renderer, the two gvisor gates, and `idp-greenlane` itself.

The invariant is exact and is read from the commit, so it needs no working tree and cannot be
satisfied by a `+x` that only exists in whoever's checkout ran last: a blob under `bin/` whose
first line is a shebang must be mode 100755. Files without one -- `bin/lib/*.py` (imported,
not run), `bin/*.txt`, the `.mjs` helpers, the Go tree -- are correctly 100644 and this rule
says nothing about them.

It is a real gate, not a ceremonial one: on the pre-fix tree it names all thirteen paths.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EXECUTABLE = "100755"


def _git(*args: str) -> str:
    done = subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True, timeout=60
    )
    assert done.returncode == 0, (
        f"git {' '.join(args)} failed: {done.stderr.strip()[:200]}"
    )
    return done.stdout


def _committed_modes() -> dict[str, str]:
    modes: dict[str, str] = {}
    for line in _git("ls-tree", "-r", "HEAD", "bin/").splitlines():
        meta, path = line.split("\t", 1)
        modes[path] = meta.split()[0]
    return modes


def _committed_shebangs() -> set[str]:
    # `git grep -l <tree>` prints `<tree>:<path>`; drop the tree back off.
    return {
        line.split(":", 1)[1]
        for line in _git("grep", "-l", "^#!", "HEAD", "--", "bin/").splitlines()
        if line.startswith("HEAD:")
    }


def test_the_rule_measured_something() -> None:
    """A rule that matches nothing is not a gate: both halves must find files."""
    assert len(_committed_modes()) > 50, "no bin/ files read from HEAD"
    assert len(_committed_shebangs()) > 20, "no shebang'd bin/ script found in HEAD"


def test_every_bin_script_with_a_shebang_is_executable() -> None:
    modes = _committed_modes()
    broken = sorted(
        path for path in _committed_shebangs() if modes.get(path) != EXECUTABLE
    )
    assert not broken, (
        "these bin/ scripts carry a shebang but are committed non-executable, so the command "
        "their runbook prints answers 'Permission denied': " + ", ".join(broken)
    )


def test_the_runbooks_own_door_is_executable() -> None:
    """The exact path and line the runbook prints (docs/runbooks/greenlane.md:40)."""
    runbook = (REPO / "docs/runbooks/greenlane.md").read_text()
    assert "bin/idp-greenlane status" in runbook, (
        "the runbook no longer prints this command"
    )
    assert _committed_modes().get("bin/idp-greenlane") == EXECUTABLE

"""Falsifier for the stale-OKE ghost scan in bin/verify_three_proofs.py.

A gate that cannot fail is not a gate (AGENTS.md 9 P1). These tests prove both
directions of PROOF_1's ghost scan, per idp#8519 (measured false positive of
2026-11-24):

  - known-good: a lane that touches a file carrying a ghost line INHERITED from
    main must PASS (the change introduces no ghost line);
  - known-bad: a lane whose diff INTRODUCES a ghost line must FAIL.

Both run against a real throwaway git repo so the git plumbing under
_introduced_lines is exercised, not mocked.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "bin"))

from verify_three_proofs import _introduced_lines  # noqa: E402

GHOST = "".join(
    ["oke", "-check"]
)  # built, not literal: this falsifier must not itself introduce a ghost line


def _init_repo(workdir: Path) -> Path:
    repo = workdir / "repo"
    repo.mkdir()
    run = lambda *argv: subprocess.run(  # noqa: E731
        ["git", *argv], cwd=repo, capture_output=True, text=True, check=True
    )
    run("init", "-q", "-b", "main")
    hooks = workdir / "empty-hooks"
    hooks.mkdir()
    run(
        "config", "core.hooksPath", str(hooks)
    )  # the throwaway repo runs no estate hooks
    run("config", "user.email", "falsifier@test")
    run("config", "user.name", "falsifier")
    run("config", "commit.gpgsign", "false")
    (repo / "surface.txt").write_text(f"kept: {GHOST} apply reads the token\n")
    run("add", ".")
    run("commit", "-q", "-m", "base: file already carries the inherited ghost")
    run("branch", "lane")
    bare = workdir / "origin.git"
    run("clone", "-q", "--bare", ".", str(bare))
    run("remote", "add", "origin", str(bare))
    run("push", "-q", "origin", "main")
    return repo


def test_inherited_ghost_passes(tmp_path=None):
    """known-good: editing around an inherited ghost line must not refuse."""
    workdir = Path(tempfile.mkdtemp(prefix="proof1-good-"))
    repo = _init_repo(workdir)
    run = lambda *argv: subprocess.run(  # noqa: E731
        ["git", *argv], cwd=repo, capture_output=True, text=True, check=True
    )
    run("checkout", "-q", "lane")
    (repo / "surface.txt").write_text(
        f"kept: {GHOST} apply reads the token\nclean new line\n"
    )
    run("add", ".")
    run("commit", "-q", "-m", "lane: add a clean line")
    introduced = _introduced_lines(str(repo), "surface.txt")
    assert "clean new line" in introduced
    assert GHOST not in introduced, (
        "PROOF_1 scanned history instead of the change: the inherited ghost "
        "line leaked into the introduced-lines sample and would false-fail"
    )


def test_introduced_ghost_fails(tmp_path=None):
    """known-bad: a diff that ADDS a ghost line must be caught."""
    workdir = Path(tempfile.mkdtemp(prefix="proof1-bad-"))
    repo = _init_repo(workdir)
    run = lambda *argv: subprocess.run(  # noqa: E731
        ["git", *argv], cwd=repo, capture_output=True, text=True, check=True
    )
    run("checkout", "-q", "lane")
    (repo / "surface.txt").write_text("resurrected: " + GHOST + " apply\n")
    run("add", ".")
    run("commit", "-q", "-m", "lane: wrongly re-introduce the ghost")
    introduced = _introduced_lines(str(repo), "surface.txt")
    assert GHOST in introduced, (
        "PROOF_1 missed a genuinely introduced ghost line: the gate would "
        "pass exactly the change it exists to refuse"
    )


if __name__ == "__main__":
    test_inherited_ghost_passes()
    test_introduced_ghost_fails()
    print("falsifier: known-good PASS, known-bad FAIL-as-required — 2/2")

"""The few git calls the engine makes, in one place (cp24, R7).

activities.run_step reads the repository HEAD before and after a runner
runs, so a receipt names the commit the step really produced and not the
one the runner claims (a runner is a vendor CLI, LAW 34). undo.py moves
HEAD back to that commit's parent. Both go through here so there is one
timeout (undo.git_timeout_s) and one parent spelling (undo.parent_suffix)
for every git call the engine makes.

Every function returns None or False on a repository that is missing or
not a git checkout rather than raising: a step in a scratch directory
with no .git is a normal case, not an error.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from sovereign import config


def _git(repo: str | Path, *args: str) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            timeout=config.UNDO_GIT_TIMEOUT_S,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def is_repo(repo: str | Path | None) -> bool:
    if not repo or not Path(str(repo)).is_dir():
        return False
    out = _git(repo, "rev-parse", "--is-inside-work-tree")
    return bool(out) and out.returncode == 0 and out.stdout.strip() == "true"


def rev_parse(repo: str | Path, rev: str) -> str | None:
    """The full hash `rev` names, or None when it names nothing here."""
    out = _git(repo, "rev-parse", "--verify", "--quiet", rev)
    if not out or out.returncode != 0:
        return None
    return out.stdout.strip() or None


def head(repo: str | Path) -> str | None:
    return rev_parse(repo, "HEAD")


def commit_exists(repo: str | Path, commit: str) -> bool:
    return rev_parse(repo, commit) is not None


def parent_of(repo: str | Path, commit: str) -> str | None:
    """The first parent of `commit`. None for a root commit, which has no
    parent to undo to."""
    return rev_parse(repo, f"{commit}{config.UNDO_PARENT_SUFFIX}")


def reset_hard(repo: str | Path, rev: str) -> bool:
    out = _git(repo, "reset", "--hard", "--quiet", rev)
    return bool(out) and out.returncode == 0

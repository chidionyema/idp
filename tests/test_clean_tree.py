"""bin/idp-clean-tree: the shared checkout is refused, and a standalone repository never is.

Why this is a test and not a fixture pair. The rule's own fixtures grade `--state`, which is a
JSON tree state and says nothing about how the gate decides WHICH tree it is looking at. That
decision is git semantics, and it was wrong in the version merged as #3339: the gate asked
`bin/idp-repo-root <dir>` and compared the answer to `<dir>`, so a throwaway repository in /tmp
answered with its own path, compared equal to itself, and was refused as the shared checkout.
Every ordinary dirty worktree was refused. LAW 38.

git answers it exactly, and these tests pin the three cases that distinguish the answers:

  * the primary checkout itself      -- relative `--git-common-dir` (".git")
  * an unrelated standalone repo     -- relative `--git-common-dir` (".git") too
  * a linked worktree of the primary -- ABSOLUTE `--git-common-dir` into the primary

Only the third separates them, so only a test that builds real git trees can grade this. A
fixture JSON cannot, which is exactly how the bug reached main.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GATE = ROOT / "bin" / "idp-clean-tree"


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(cwd), *args],
        check=True,
        capture_output=True,
        env={
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.com",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.com",
            "HOME": str(cwd),
        },
    )


def _repo(path: Path) -> Path:
    """A real repository with one commit and one uncommitted change."""
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-q", ".")
    (path / "f.txt").write_text("x\n")
    _git(path, "add", "f.txt")
    _git(path, "commit", "-qm", "init")
    (path / "f.txt").write_text("x\ny\n")
    return path


def _verdict(target: Path, primary: str | None = None) -> int:
    """The gate's exit code, run the way a person runs it."""
    env = {"PATH": "/usr/bin:/bin:/usr/local/bin"}
    if primary is not None:
        env["IDP_PRIMARY_CHECKOUT"] = primary
    p = subprocess.run(
        ["python3", str(GATE), "--path", str(target)],
        capture_output=True,
        text=True,
        env=env,
    )
    return p.returncode


def test_a_standalone_dirty_repository_is_not_the_shared_checkout(
    tmp_path: Path,
) -> None:
    """The regression. A throwaway repo in /tmp must pass; the merged version refused it."""
    scratch = _repo(tmp_path / "standalone")
    assert _verdict(scratch) == 0, (
        "a standalone repository is never the shared checkout (LAW 38)"
    )


def test_a_linked_worktree_is_not_the_shared_checkout(tmp_path: Path) -> None:
    """A worktree of the primary is where work is done, and must never be refused."""
    primary = _repo(tmp_path / "primary")
    linked = tmp_path / "linked"
    _git(primary, "worktree", "add", "-q", str(linked), "-b", "side")
    (linked / "f.txt").write_text("changed\n")
    assert _verdict(linked, primary=str(primary)) == 0


def test_the_primary_checkout_dirty_is_refused(tmp_path: Path) -> None:
    """The one tree the gate exists for."""
    primary = _repo(tmp_path / "primary")
    (primary / "bin").mkdir(exist_ok=True)
    # The gate requires the estate's own marker, so a random repository is never called shared.
    (primary / "bin" / "idp-rules").write_text("#!/bin/sh\n")
    assert _verdict(primary, primary=str(primary)) == 1


def test_a_repository_without_the_estate_marker_is_never_shared(tmp_path: Path) -> None:
    """Any repository can be dirty. Only this estate's primary checkout is ever refused.

    No override is passed: the gate must decide this from git and from the estate's marker alone.
    Setting IDP_PRIMARY_CHECKOUT to the repository under test would be asking the gate whether a
    tree is itself, which is the very question the merged version got wrong -- `bin/idp-repo-root`
    answers with the tree you hand it, so everything compared equal to itself.
    """
    plain = _repo(tmp_path / "plain")
    assert _verdict(plain) == 0


def test_the_override_does_not_refuse_a_stranger(tmp_path: Path) -> None:
    """IDP_PRIMARY_CHECKOUT names one tree; a different tree is not it."""
    a = _repo(tmp_path / "a")
    (a / "bin").mkdir(exist_ok=True)
    (a / "bin" / "idp-rules").write_text("#!/bin/sh\n")
    b = _repo(tmp_path / "b")
    assert _verdict(b, primary=str(a)) == 0


def test_a_mid_merge_worktree_is_refused(tmp_path: Path) -> None:
    """Mid-merge is refused in any tree: it is on nobody's branch, so nothing grades true there."""
    repo = _repo(tmp_path / "conflicted")
    _git(repo, "checkout", "-q", "-b", "one")
    (repo / "a.txt").write_text("one\n")
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-qm", "one")
    _git(repo, "checkout", "-q", "-")
    (repo / "a.txt").write_text("two\n")
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-qm", "two")
    merge = subprocess.run(
        ["git", "-C", str(repo), "merge", "one"],
        capture_output=True,
        text=True,
        env={
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.com",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.com",
            "HOME": str(repo),
        },
    )
    assert merge.returncode != 0, (
        "the merge must actually conflict for this test to mean anything"
    )
    assert _verdict(repo) == 1

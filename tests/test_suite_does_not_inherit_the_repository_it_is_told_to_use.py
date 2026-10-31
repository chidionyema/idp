"""The falsifier for the git-environment class defect (2026-10-31).

Measured failure: in a linked worktree, git exports GIT_DIR to the pre-push hook. Every test
that runs `git init` inherits it, so git re-initialises the inherited directory as a BARE
repository, writes `core.bare = true` into it, and never creates the repository the test asked
for. In /tmp/gitdirtest the shared repository's `core.bare` went false -> true and the
following `git commit --allow-empty` exited 128 with "not a git repository". That is how the
shared repository was corrupted and how the pre-push language gate failed.

The fix lives in the root conftest.py, the earliest layer every test passes through: it
removes the inherited repository-location variables before collection. These tests prove both
halves: that the hazard is real (so the fix is not cargo cult), and that the suite no longer
inherits the repository it is told to use.

Every repository here is a throwaway one created by the test. The estate's own repository is
never touched: the hazard is reproduced against a copy, never against the real thing.
"""

import os
import subprocess
from pathlib import Path

GIT = "git"
REPO_LOCATION_VARS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_COMMON_DIR",
    "GIT_PREFIX",
)


def _run(args, env=None, cwd=None):
    return subprocess.run(
        args, env=env, cwd=cwd, capture_output=True, text=True, check=False
    )


def _clean_env() -> dict:
    """The suite's environment with every repository-location variable removed.

    The fixture must be hermetic: it builds its own throwaway repository, so it may not be
    shaped by whatever repository the caller happened to inherit. The hazard is reproduced
    deliberately, in one test, by putting GIT_DIR back.
    """
    env = dict(os.environ)
    for name in REPO_LOCATION_VARS:
        env.pop(name, None)
    return env


def _throwaway_linked_worktree(root: Path) -> tuple[Path, str]:
    """A throwaway repository with a linked worktree, exactly the shape that exports GIT_DIR.

    A linked worktree's gitdir holds a `commondir` pointer, so a `git init` that inherits it
    writes into the SHARED repository's config. That is the measured corruption: `core.bare`
    false -> true on the repository every other worktree shares.

    Returns the shared repository and the linked gitdir to export as GIT_DIR.
    """
    repo = root / "shared"
    repo.mkdir(parents=True)
    env = _clean_env()
    init = _run([GIT, "init", "-q", str(repo)], env=env)
    assert init.returncode == 0, init.stderr
    _run(
        [GIT, "-C", str(repo), "config", "user.email", "suite@example.invalid"], env=env
    )
    _run([GIT, "-C", str(repo), "config", "user.name", "estate suite"], env=env)
    commit = _run(
        [GIT, "-C", str(repo), "commit", "--allow-empty", "-q", "-m", "base"], env=env
    )
    assert commit.returncode == 0, commit.stderr
    linked = root / "linked"
    add = _run(
        [
            GIT,
            "-C",
            str(repo),
            "worktree",
            "add",
            "-q",
            str(linked),
            "-b",
            "linked-branch",
        ],
        env=env,
    )
    assert add.returncode == 0, add.stderr
    git_dir = str(repo / ".git" / "worktrees" / "linked")
    assert Path(git_dir, "commondir").is_file(), (
        "the linked gitdir has no commondir pointer"
    )
    config = _run([GIT, "-C", str(repo), "config", "--get", "core.bare"], env=env)
    assert config.stdout.strip() in ("", "false"), config.stdout
    return repo, git_dir


def _core_bare(repo: Path) -> str:
    out = _run([GIT, "-C", str(repo), "config", "--get", "core.bare"], env=_clean_env())
    return out.stdout.strip() or "false"


def test_the_suite_does_not_inherit_a_repository_location():
    """The contract: the suite's own environment names no repository location."""
    inherited = [name for name in REPO_LOCATION_VARS if name in os.environ]
    assert inherited == [], (
        "the suite inherited repository-location variables %s; a test that runs `git init` "
        "would re-initialise that repository as bare" % inherited
    )


def test_the_hazard_is_real_so_the_fix_is_not_cargo_cult(tmp_path):
    """Without the sanitisation, an inherited GIT_DIR turns the target bare and eats the repo."""
    shared, git_dir = _throwaway_linked_worktree(tmp_path)
    target = tmp_path / "wanted"
    target.mkdir()

    env = _clean_env()
    env["GIT_DIR"] = git_dir

    init = _run([GIT, "init", "-q", str(target)], env=env, cwd=str(target))

    assert init.returncode == 0, init.stderr
    assert not (target / ".git").exists(), (
        "the inherited GIT_DIR swallowed the repository the test asked for"
    )
    assert _core_bare(shared) == "true", (
        "the inherited GIT_DIR did not flip the shared repository bare; the hazard this fix "
        "removes is not the hazard that was measured, and the fix needs re-measuring"
    )


def test_a_git_init_under_the_sanitised_environment_creates_the_repository(tmp_path):
    """With the location variables gone, `git init` creates the repository that was asked for."""
    shared, _git_dir = _throwaway_linked_worktree(tmp_path)
    target = tmp_path / "wanted"
    target.mkdir()

    env = _clean_env()

    init = _run([GIT, "init", "-q", str(target)], env=env, cwd=str(target))
    assert init.returncode == 0, init.stderr
    assert (target / ".git").is_dir(), "git init did not create the repository"

    _run(
        [GIT, "-C", str(target), "config", "user.email", "suite@example.invalid"],
        env=env,
    )
    _run([GIT, "-C", str(target), "config", "user.name", "estate suite"], env=env)
    commit = _run(
        [GIT, "-C", str(target), "commit", "--allow-empty", "-q", "-m", "base"], env=env
    )
    assert commit.returncode == 0, commit.stderr
    assert _core_bare(shared) == "false", "the surrounding repository was made bare"

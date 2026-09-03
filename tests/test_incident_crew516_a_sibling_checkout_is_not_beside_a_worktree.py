"""Every script that wants a sibling repository wrote "$IDP/..", and every one of them was wrong
for an agent session.

An agent session works in a linked git worktree under a temp directory. Nothing sits beside that
directory, so `bin/idp-kyverno-render` resolved its policy set to a path that does not exist, hit
its own BLIND branch and exited 2 on every local run -- which is how CI became the only thing in
this estate that has ever judged a render. `bin/scheduler-up` resolved crew's science facts the
same way and refused the estate-facts code location for the same reason.

The tests below drive `bin/idp-repo-root` from a real linked worktree of a real repository rather
than re-implementing its resolution, because a test that re-implements the thing it grades passes
on both the fixed and the broken script.
"""

import os
import pathlib
import subprocess

IDP = pathlib.Path(__file__).resolve().parents[1]
REPO_ROOT = IDP / "bin" / "idp-repo-root"


def _git(cwd, *args):
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        text=True,
        check=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t",
        },
    ).stdout.strip()


def _root_of(path):
    r = subprocess.run([str(REPO_ROOT), str(path)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout.strip()


def _repo_with_a_worktree(tmp_path):
    """A primary checkout at <tmp>/estate/primary and a linked worktree far away from it."""
    primary = tmp_path / "estate" / "primary"
    primary.mkdir(parents=True)
    _git(primary, "init", "-q", "-b", "main")
    (primary / "f").write_text("x\n")
    _git(primary, "add", "f")
    _git(primary, "commit", "-qm", "c")
    linked = tmp_path / "elsewhere" / "wt"
    linked.parent.mkdir(parents=True)
    _git(primary, "worktree", "add", "-q", str(linked), "-b", "side")
    return primary, linked


def test_from_a_linked_worktree_it_names_the_primary_checkout(tmp_path):
    primary, linked = _repo_with_a_worktree(tmp_path)
    assert _root_of(linked) == str(primary.resolve())


def test_the_sibling_of_a_worktree_is_not_the_sibling_of_the_repository(tmp_path):
    """The failure this closes: a sibling looked for beside the worktree is simply not there."""
    primary, linked = _repo_with_a_worktree(tmp_path)
    sibling = primary.parent / "prospector-main"
    sibling.mkdir()
    assert not (linked.parent / "prospector-main").exists()  # what "$IDP/.." asked for
    assert (pathlib.Path(_root_of(linked)).parent / "prospector-main").is_dir()


def test_from_the_primary_checkout_the_answer_is_unchanged(tmp_path):
    """The fix may not move the path for the case that already worked -- CI is a primary checkout."""
    primary, _ = _repo_with_a_worktree(tmp_path)
    assert _root_of(primary) == str(primary.resolve())


def test_a_directory_that_is_not_a_checkout_degrades_to_itself(tmp_path):
    plain = tmp_path / "tarball"
    plain.mkdir()
    assert _root_of(plain) == str(plain.resolve())

"""bin/claim-open must claim the tree you are standing in, not the tree it lives in.

2026-10-22. Every git call in `bin/claim-open` ran with `cwd=` the checkout the script lives in.
From a worktree that is a different tree, so the command reported and claimed the DEV checkout:

    $ cd ~/.estate/worktrees/epic-090 && bin/claim-open --issue 6859 --paths …
    claim-open  change touches 13 file(s): web/app/case-studies/page.tsx, web/app/consulting/page.tsx, …
    FAIL    claim-open  this commit already claims #6698 as estate-agent, not #6859 as pi-epic-090.

None of those files were in the branch, and #6698 was another agent's claim, read off the dev
tree's HEAD. No worktree lane could declare itself, so the workaround was to hand-post the CLAIM
comment and run bin/claim-gate with GITHUB_REPOSITORY exported — the escape hatch this file
outlaws by existing.

These tests execute the resolution rather than reading the source for `cwd=REPO`: a worktree made
for real with `git worktree add`, the override, and the fallback when the cwd is not a checkout.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
CLAIM_OPEN = ROOT / "bin" / "claim-open"


def _load() -> ModuleType:
    """Import bin/claim-open as a module (it has no .py suffix, so the loader is explicit --
    spec_from_file_location answers None for a file with no known suffix)."""
    loader = SourceFileLoader("claim_open_under_test", str(CLAIM_OPEN))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


@pytest.fixture()
def in_dir():
    """Run part of a test from another directory, and come back even when it fails."""
    old = os.getcwd()

    def _go(path: Path | str) -> None:
        os.chdir(path)

    yield _go
    os.chdir(old)


@pytest.fixture(scope="module")
def linked_worktree(tmp_path_factory) -> Path:
    """A real linked worktree of this repository, off HEAD, detached so no branch is claimed."""
    dest = tmp_path_factory.mktemp("wt") / "lane-probe"
    p = subprocess.run(  # noqa: S603, S607 -- fixed argv, no shell
        ["git", "worktree", "add", "--detach", str(dest), "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if p.returncode != 0:
        pytest.skip(f"cannot make a worktree here: {p.stderr.strip()[:200]}")
    try:
        yield dest
    finally:
        subprocess.run(  # noqa: S603, S607
            ["git", "worktree", "remove", "--force", str(dest)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )


def test_from_a_worktree_the_claim_is_about_the_worktree(
    linked_worktree: Path, in_dir
) -> None:
    in_dir(linked_worktree)
    mod = _load()
    assert Path(mod.REPO).resolve() == linked_worktree.resolve(), (
        "claim-open measured "
        f"{mod.REPO} while standing in {linked_worktree} — the defect this file was written for"
    )
    # And it must be a tree the claim can actually be gated in.
    assert (Path(mod.REPO) / "bin" / "claim-gate").exists()
    assert (Path(mod.REPO) / "bin" / "claim-open").exists()


def test_the_gate_it_runs_belongs_to_the_same_tree(
    linked_worktree: Path, in_dir
) -> None:
    in_dir(linked_worktree)
    mod = _load()
    gate = Path(mod.GATE).resolve()
    assert gate == (linked_worktree.resolve() / "bin" / "claim-gate"), (
        f"claim-open would judge {gate}, not the tree it just claimed"
    )


def test_the_override_wins_for_a_caller_that_is_not_in_a_tree(tmp_path, in_dir) -> None:
    in_dir(tmp_path)
    mod = _load()
    other = ROOT / "platform"
    os.environ["ESTATE_CLAIM_REPO"] = str(other)
    try:
        assert Path(mod.resolve_repo()).resolve() == other.resolve()
    finally:
        del os.environ["ESTATE_CLAIM_REPO"]


def test_a_directory_that_is_not_a_checkout_falls_back(tmp_path, in_dir) -> None:
    """Fail closed, not silent: a cwd with no repository (or one that cannot gate a claim) must
    land back on this script's own repo rather than claiming against a tree it cannot judge."""
    in_dir(tmp_path)
    mod = _load()
    assert Path(mod.REPO).resolve() == ROOT.resolve()


def test_the_dev_checkout_is_still_its_own_answer(in_dir) -> None:
    """The single-checkout case is what the script was written for; it must not regress."""
    in_dir(ROOT)
    mod = _load()
    assert Path(mod.REPO).resolve() == ROOT.resolve()


def test_python_can_still_syntax_check_it() -> None:
    p = subprocess.run(  # noqa: S603, S607 -- fixed argv, no shell
        [sys.executable, "-m", "py_compile", str(CLAIM_OPEN)],
        capture_output=True,
        text=True,
    )
    assert p.returncode == 0, p.stderr

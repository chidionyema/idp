"""The pre-commit hook APPLIES ruff format instead of refusing and printing the fix.

A check that failed with "fix: python3 -m ruff format ..." made every agent pay a failed commit
and a retry for a change the hook already knew how to make. A file staged whole now commits
formatted. A file with unstaged edits as well is still refused: formatting and re-staging it would
sweep those edits into the commit unseen.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
HOOK = REPO / ".githooks" / "pre-commit"
UGLY = "x = {  'a':1 }\n"
PRETTY = 'x = {"a": 1}\n'

pytestmark = pytest.mark.skipif(
    subprocess.run(
        ["python3", "-m", "ruff", "--version"], capture_output=True
    ).returncode
    != 0,
    reason="ruff not installed",
)


def git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q")
    (tmp_path / ".githooks").mkdir()
    shutil.copy(HOOK, tmp_path / ".githooks" / "pre-commit")
    return tmp_path


def run_hook(repo: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", ".githooks/pre-commit"], cwd=repo, capture_output=True, text=True
    )


def staged(repo: Path, name: str) -> str:
    return git(repo, "show", f":{name}").stdout


def test_a_wholly_staged_file_is_formatted_and_restaged(repo: Path) -> None:
    (repo / "a.py").write_text(UGLY)
    git(repo, "add", "a.py")
    r = run_hook(repo)
    assert r.returncode == 0, r.stderr
    assert staged(repo, "a.py") == PRETTY
    assert (repo / "a.py").read_text() == PRETTY


def test_a_partly_staged_file_is_refused_and_its_unstaged_edit_kept_out(
    repo: Path,
) -> None:
    (repo / "b.py").write_text(UGLY)
    git(repo, "add", "b.py")
    (repo / "b.py").write_text(UGLY + "y   = 2\n")
    r = run_hook(repo)
    assert r.returncode == 1
    assert "partly staged" in r.stderr
    assert staged(repo, "b.py") == UGLY
    assert (repo / "b.py").read_text() == UGLY + "y   = 2\n"

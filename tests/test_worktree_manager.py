"""The estate's worktree manager, tested.

The manager makes one worktree per task and cleans them up. The defects this module was
written for, measured on 2026-10-28:

  D5  `from platform.queue import dispatcher` raises ModuleNotFoundError in this
      repository (platform/ has no __init__.py: it collides with the stdlib `platform`
      module, idp#3564), so the sweep of orphaned worktrees caught the error, skipped
      every worktree and reported zero. The estate's orphans were never swept.
  D6  the sweep asked the queue for `load_task`, a function the queue did not have, so
      every task lookup raised and every worktree was skipped: the same no-op, from the
      other side.
  D7  removing a worktree used `git worktree remove --force`, which destroys uncommitted
      changes and untracked files with no record. The leftovers are archived first.
"""

from __future__ import annotations

import importlib.util
import sqlite3
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load(rel: str, dotted: str):
    """Load a module of platform/ by path (platform/ has no __init__.py: idp#3564)."""
    if dotted in sys.modules:
        return sys.modules[dotted]
    spec = importlib.util.spec_from_file_location(dotted, str(REPO_ROOT / rel))
    module = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = module
    spec.loader.exec_module(module)
    return module


_queue_package = _load("platform/queue/__init__.py", "platform.queue")
dispatcher = _queue_package.load_dispatcher()
manager_module = _load(
    "platform/execution/worktree_manager.py", "platform.execution.worktree_manager"
)
WorktreeManager = manager_module.WorktreeManager


@pytest.fixture
def repo(tmp_path):
    """A real git repository with one commit in it."""
    path = tmp_path / "repo"
    path.mkdir()
    for args in (
        ["init", "--quiet"],
        ["config", "user.email", "agent@estate"],
        ["config", "user.name", "agent"],
    ):
        subprocess.run(["git"] + args, cwd=str(path), check=True, capture_output=True)
    (path / "README.md").write_text("the estate\n")
    subprocess.run(["git", "add", "README.md"], cwd=str(path), check=True)
    subprocess.run(
        ["git", "commit", "--quiet", "-m", "the estate"],
        cwd=str(path),
        check=True,
        capture_output=True,
    )
    return path


@pytest.fixture
def queue(tmp_path, repo, monkeypatch):
    """A queue in a temp directory, with the environment the dispatcher reads."""
    monkeypatch.setenv("QUEUE_DB_PATH", str(tmp_path / "state" / "queue.db"))
    monkeypatch.setenv("WORKTREE_BASE", str(tmp_path / "wt"))
    monkeypatch.setenv("IDP_ROOT", str(repo))
    monkeypatch.setenv("WORKTREE_ARCHIVE_ROOT", str(tmp_path / "quarantine"))
    dispatcher.init_db()
    return dispatcher


@pytest.fixture
def manager(tmp_path, repo, monkeypatch):
    """A worktree manager that works in the temp repository.

    The environment matters: the manager asks the queue where the worktrees are and
    where a removed worktree's leftovers go, and without this the archive went to the
    estate's own quarantine instead of the temp directory.
    """
    monkeypatch.setenv("WORKTREE_BASE", str(tmp_path / "wt"))
    monkeypatch.setenv("IDP_ROOT", str(repo))
    monkeypatch.setenv("WORKTREE_ARCHIVE_ROOT", str(tmp_path / "quarantine"))
    return WorktreeManager(base_path=str(tmp_path / "wt"), repo_root=str(repo))


# ---------------------------------------------------------------------------
# making a worktree
# ---------------------------------------------------------------------------


def test_it_makes_a_worktree_that_is_a_worktree_of_the_repository(manager, repo):
    """The worktree is real: git knows about it and it holds the repository's files."""
    path = manager.create_worktree(1)

    assert Path(path).exists()
    assert (Path(path) / "README.md").exists()
    listed = subprocess.run(
        ["git", "worktree", "list"], cwd=str(repo), capture_output=True, text=True
    ).stdout
    assert path in listed


def test_building_a_manager_creates_no_directory(tmp_path):
    """A manager that makes a directory when it is built makes it in every checkout."""
    WorktreeManager(base_path=str(tmp_path / "wt"), repo_root=str(tmp_path))
    assert not (tmp_path / "wt").exists()


# ---------------------------------------------------------------------------
# D5/D6: the sweep of orphaned worktrees
# ---------------------------------------------------------------------------


def test_the_sweep_removes_the_worktree_of_a_task_that_is_gone(manager, queue):
    """A worktree whose task does not exist is an orphan, and it goes."""
    path = manager.create_worktree(7)
    assert Path(path).exists()

    removed = manager.sweep_orphaned()

    assert removed == 1, "the sweep removed nothing: the queue could not be reached"
    assert not Path(path).exists()


def test_the_sweep_keeps_the_worktree_of_a_running_task(manager, queue):
    """A task that is running has a worktree on purpose."""
    queue.push_task("prove the thing")
    task = queue.claim_task("agent-a")

    removed = manager.sweep_orphaned()

    assert removed == 0
    assert Path(task["worktree"]).exists()


def test_the_sweep_removes_the_worktree_of_a_finished_task(
    manager, queue, tmp_path, repo
):
    """The queue's terminal states are 'success' and 'failed'.

    The sweep used to look for 'done' and 'dead_letter', which the queue never writes, so
    the worktree of every finished task stayed on disk for ever.
    """
    queue.push_task("prove the thing")
    task = queue.claim_task("agent-a")
    worktree = Path(task["worktree"])
    # the task finished; the worktree was left behind
    with sqlite3.connect(queue.db_path()) as conn:
        conn.execute("UPDATE tasks SET status = 'success' WHERE id = ?", (task["id"],))
        conn.commit()

    removed = manager.sweep_orphaned()

    assert removed == 1, "the worktree of a finished task was never swept"
    assert not worktree.exists()


# ---------------------------------------------------------------------------
# D7: removal that keeps the work
# ---------------------------------------------------------------------------


def test_removing_a_worktree_archives_what_it_holds(manager, tmp_path):
    """The work is archived before the worktree is removed, and the archive holds it."""
    path = Path(manager.create_worktree(3))
    (path / "NOTES.md").write_text("the work\n")
    (path / "README.md").write_text("changed\n")

    manager.remove_worktree(3)

    assert not path.exists()
    archives = list((tmp_path / "quarantine").iterdir())
    assert len(archives) == 1, "the work was removed without an archive"
    archive = archives[0]
    assert "changed" in (archive / "work.patch").read_text()
    with tarfile.open(archive / "untracked.tgz") as tar:
        assert "NOTES.md" in tar.getnames()

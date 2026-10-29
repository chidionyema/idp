"""The estate's task queue, tested against the real thing.

Every test drives the real module: a real sqlite queue in a temp directory, a real git
repository, a real worktree. A queue that only works in a mock is a queue nobody runs.

The defects these tests were written for, all measured on 2026-10-28:

  D1  a claim did not stamp updated_at, so the sweep re-queued a task that was running
  D2  a failed 'git worktree add' was swallowed, so the task sat 'running' with no workspace
  D3  'git worktree remove --force' destroyed uncommitted and untracked work silently
  D4  the module created directories at import, and crashed when QUEUE_DB_PATH had no
      directory component
"""

from __future__ import annotations

import importlib.util
import os
import sqlite3
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load(rel: str, dotted: str):
    """Load a module of platform/ by path.

    platform/ has no __init__.py: it collides with the stdlib `platform` module the
    moment anything imports it bare (idp#3564), and pytest imports `platform` at
    startup. So `from platform.queue import dispatcher` cannot work in a test, and the
    modules are loaded by path under their real dotted names instead -- the pattern the
    estate already uses for platform.eval (tests/pareval/test_policy_validation.py).
    """
    if dotted in sys.modules:
        return sys.modules[dotted]
    spec = importlib.util.spec_from_file_location(dotted, str(REPO_ROOT / rel))
    module = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = module
    spec.loader.exec_module(module)
    return module


_queue_package = _load("platform/queue/__init__.py", "platform.queue")
dispatcher = _queue_package.load_dispatcher()

scenarios("../features/assurance/execution-substrate.feature")


def _git(repo: Path, args: list[str]):
    result = subprocess.run(
        ["git"] + args,
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


@pytest.fixture
def ctx():
    """The scenario's context: what the steps hand to each other."""
    return {}


@pytest.fixture
def repo(tmp_path):
    """A real git repository with one commit in it."""
    path = tmp_path / "repo"
    path.mkdir()
    _git(path, ["init", "--quiet"])
    _git(path, ["config", "user.email", "agent@estate"])
    _git(path, ["config", "user.name", "agent"])
    (path / "README.md").write_text("the estate\n")
    _git(path, ["add", "README.md"])
    _git(path, ["commit", "--quiet", "-m", "the estate"])
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


def _backdate(db: str, hours: int):
    """Make every task look as old as it is not."""
    with sqlite3.connect(db) as conn:
        conn.execute(
            "UPDATE tasks SET created_at = datetime('now', ?), updated_at = datetime('now', ?)",
            (f"-{hours} hours", f"-{hours} hours"),
        )
        conn.commit()


# ---------------------------------------------------------------------------
# the lifecycle
# ---------------------------------------------------------------------------


def test_a_task_is_claimed_given_a_worktree_and_completed(queue):
    """The shape of the whole thing: claim, work, complete."""
    queue.push_task("prove the thing")

    task = queue.claim_task("agent-a")
    assert task is not None
    assert task["goal"] == "prove the thing"
    assert Path(task["worktree"]).exists()

    queue.complete_task(task["id"], "success")

    row = queue.get_task_list()[0]
    assert row[2] == "success"
    assert row[3] == "agent-a"


def test_a_task_is_claimed_by_one_agent_only(queue):
    """Two agents, one task: the second one is given nothing."""
    queue.push_task("prove the thing")

    assert queue.claim_task("agent-a") is not None
    assert queue.claim_task("agent-b") is None


def test_a_task_can_be_asked_for_by_id(queue):
    """The worktree manager asks for a task by id; there is a function that answers."""
    queue.push_task("prove the thing")
    task = queue.claim_task("agent-a")

    loaded = dispatcher.load_task(task["id"])
    assert loaded is not None
    assert loaded["status"] == "running"
    assert loaded["agent_id"] == "agent-a"

    assert dispatcher.load_task(999999) is None


# ---------------------------------------------------------------------------
# D1: a claim that does not stamp the task
# ---------------------------------------------------------------------------


def test_a_claim_stamps_the_task_so_the_sweep_cannot_re_queue_it(queue):
    """The claim stamps updated_at.

    The sweep re-queues any task that is still 'running' after an hour. A task that was
    created two hours ago and claimed a moment ago was, before the fix, stamped with its
    CREATION time, so the sweep re-queued it while it was running: the task ran twice.
    """
    queue.push_task("prove the thing")
    _backdate(queue.db_path(), hours=2)

    task = queue.claim_task("agent-a")
    assert task is not None

    queue.sweep_zombies()

    row = queue.get_task_list()[0]
    assert row[2] == "running", "a running task was re-queued and would run twice"
    assert row[3] == "agent-a"


# ---------------------------------------------------------------------------
# D2: a claim that could not get a workspace
# ---------------------------------------------------------------------------


def test_a_claim_without_a_workspace_gives_the_task_back(queue, tmp_path, monkeypatch):
    """A claim that could not get a worktree is rolled back.

    `git worktree add` used to run with capture_output=True and its failure was
    swallowed, so the task stayed 'running' with no worktree: an agent held a task it
    could not work in, and the sweep re-queued it an hour later to fail the same way.
    """
    monkeypatch.setenv("IDP_ROOT", str(tmp_path / "not-a-repository"))
    queue.push_task("prove the thing")

    assert queue.claim_task("agent-a") is None

    row = queue.get_task_list()[0]
    assert row[2] == "pending"
    assert row[3] is None


# ---------------------------------------------------------------------------
# D3: work destroyed without a record
# ---------------------------------------------------------------------------


def test_completion_archives_the_work_before_it_removes_the_worktree(
    queue, tmp_path, capsys
):
    """The work is archived, and the archive's path is printed.

    `git worktree remove --force` throws away uncommitted changes and untracked files
    with no record of them. The leftovers are archived first, in the estate's own
    convention, and the path is printed so the archive can be found again.
    """
    queue.push_task("prove the thing")
    task = queue.claim_task("agent-a")
    worktree = Path(task["worktree"])
    (worktree / "NOTES.md").write_text("the work\n")
    (worktree / "README.md").write_text("changed\n")

    queue.complete_task(task["id"], "success")

    assert not worktree.exists()

    archives = list((tmp_path / "quarantine").iterdir())
    assert len(archives) == 1, "the work was removed without an archive"
    archive = archives[0]
    assert (archive / "origin").exists()
    assert (archive / "work.patch").exists()
    assert (archive / "untracked.tgz").exists()

    assert "changed" in (archive / "work.patch").read_text()
    with tarfile.open(archive / "untracked.tgz") as tar:
        assert "NOTES.md" in tar.getnames()

    assert str(archive) in capsys.readouterr().out


def test_an_archive_over_the_cap_keeps_the_worktree(queue, tmp_path, monkeypatch):
    """The work is worth more than the space: over the cap, nothing is removed."""
    monkeypatch.setenv("WORKTREE_ARCHIVE_MAX_BYTES", "1")
    queue.push_task("prove the thing")
    task = queue.claim_task("agent-a")
    worktree = Path(task["worktree"])
    (worktree / "NOTES.md").write_text("the work\n")

    queue.complete_task(task["id"], "success")

    assert worktree.exists(), (
        "the worktree was removed although the archive was refused"
    )
    assert not list((tmp_path / "quarantine").iterdir())


# ---------------------------------------------------------------------------
# D4: side effects at import, and the bare filename
# ---------------------------------------------------------------------------


def test_importing_the_queue_creates_nothing(tmp_path):
    """A module that makes a directory on import makes it in every process that reads it."""
    target = tmp_path / "state" / "queue.db"
    worktrees = tmp_path / "wt"
    env = dict(os.environ, QUEUE_DB_PATH=str(target), WORKTREE_BASE=str(worktrees))

    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            "import importlib.util; "
            f"s = importlib.util.spec_from_file_location('d', {str(REPO_ROOT / 'platform/queue/dispatcher.py')!r}); "
            "m = importlib.util.module_from_spec(s); s.loader.exec_module(m)",
        ],
        env=env,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr
    assert not target.parent.exists()
    assert not worktrees.exists()


def test_a_queue_path_with_no_directory_component_works(tmp_path, monkeypatch):
    """os.makedirs('') raises, so a bare filename used to crash the module at import."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("QUEUE_DB_PATH", "queue.db")

    dispatcher.init_db()
    dispatcher.push_task("prove the thing")

    assert (tmp_path / "queue.db").exists()
    assert dispatcher.get_task_list()[0][1] == "prove the thing"


# ---------------------------------------------------------------------------
# the scenarios of features/assurance/execution-substrate.feature
# ---------------------------------------------------------------------------


@given("a task that has been waiting in the queue for two hours")
def _waiting(ctx, queue):
    queue.push_task("prove the thing")
    _backdate(queue.db_path(), hours=2)


@when("an agent claims it")
def _claim(ctx, queue):
    ctx["task"] = queue.claim_task("agent-a")


@when("the zombie sweep runs")
def _sweep(ctx, queue):
    queue.sweep_zombies()


@then("the task is still running with the agent that claimed it")
def _still_running(ctx, queue):
    row = queue.get_task_list()[0]
    assert row[2] == "running"
    assert row[3] == "agent-a"


@given("a queue whose repository does not exist")
def _no_repository(ctx, queue, tmp_path, monkeypatch):
    monkeypatch.setenv("IDP_ROOT", str(tmp_path / "not-a-repository"))
    queue.push_task("prove the thing")


@when("an agent claims the oldest task")
def _claim_the_oldest(ctx, queue):
    ctx["task"] = queue.claim_task("agent-a")


@then("the task is pending again and no agent holds it")
def _pending_again(ctx, queue):
    row = queue.get_task_list()[0]
    assert row[2] == "pending"
    assert row[3] is None


@given("a claimed task with an uncommitted change and an untracked file")
def _claimed_with_work(ctx, queue):
    queue.push_task("prove the thing")
    task = queue.claim_task("agent-a")
    ctx["task"] = task
    worktree = Path(task["worktree"])
    (worktree / "NOTES.md").write_text("the work\n")
    (worktree / "README.md").write_text("changed\n")


@when("the task completes")
def _complete(ctx, queue):
    queue.complete_task(ctx["task"]["id"], "success")


@then("the worktree is gone")
def _worktree_gone(ctx):
    assert not Path(ctx["task"]["worktree"]).exists()


@then("the change and the file are in the archive")
def _work_archived(ctx, tmp_path):
    archives = list((tmp_path / "quarantine").iterdir())
    assert len(archives) == 1
    archive = archives[0]
    assert "changed" in (archive / "work.patch").read_text()
    with tarfile.open(archive / "untracked.tgz") as tar:
        assert "NOTES.md" in tar.getnames()

"""The estate's task queue.

A task is a goal with a status. An agent claims the oldest pending task, gets a git
worktree to work in, and completes the task when it is done.

The rules this module keeps, each of them a defect measured on 2026-10-28 and each of
them now a test (tests/test_queue_dispatcher.py):

  1. A claim that could not get a workspace is not a claim. ``git worktree add`` used to
     run with ``capture_output=True`` and its failure was swallowed, so the task sat in
     'running' with no worktree, and the sweep re-queued it an hour later to fail the
     same way. The claim is rolled back and the agent is given nothing.

  2. A running task is stamped. ``claim_task`` set 'running' without touching
     ``updated_at``, and ``sweep_zombies`` re-queues any running task whose stamp is
     older than an hour, so a task claimed a moment ago could be re-queued and run twice.

  3. Work is not destroyed silently. ``complete_task`` ran ``git worktree remove
     --force``, which throws away uncommitted changes and untracked files with no record
     of them. The leftovers are archived first, in the estate's own convention
     (~/.estate/quarantine/worktrees/<stamp>-<name>, work.patch + untracked.tgz), the
     archive path is printed, and only then is the worktree removed. An archive over the
     cap keeps the worktree: the work is worth more than the space.

The paths are read at call time, not at import time, and importing this module creates
nothing: a module that makes a directory on import makes it in every process that
merely reads it.
"""

import os
import re
import shutil
import sqlite3
import subprocess
import tarfile
from datetime import datetime, timezone

DEFAULT_DB_PATH = "state/queue.db"
DEFAULT_WORKTREE_BASE = ".wt-agents"

# The estate's own quarantine: the same place the estate's cleaner archives a worktree
# it removes (bin/disk-cleanup.sh), so there is ONE place a removed worktree's leftovers
# can be, and one convention for finding them again.
DEFAULT_ARCHIVE_ROOT = os.path.expanduser("~/.estate/quarantine/worktrees")
DEFAULT_ARCHIVE_MAX_BYTES = 64 * 1024 * 1024

# Build output is regenerable by definition: the estate's cleaner does not archive it
# either (the same REBUILDABLE list), and archiving it would put gigabytes in the
# quarantine for nothing.
REBUILDABLE = re.compile(
    r"(^|/)(node_modules|target|dist|dist-types|build|__pycache__|\.pytest_cache|"
    r"\.ruff_cache|\.mypy_cache|\.venv|venv|\.tox|coverage|\.coverage|\.turbo|"
    r"\.next|\.cache|htmlcov)(/|$)|\.pyc$|\.tsbuildinfo$"
)


def db_path() -> str:
    """Where the queue lives. Read at call time: an operator moves it with an env var."""
    return os.environ.get("QUEUE_DB_PATH", DEFAULT_DB_PATH)


def worktree_base() -> str:
    """Where the worktrees are made. Read at call time."""
    return os.environ.get("WORKTREE_BASE", DEFAULT_WORKTREE_BASE)


def archive_root() -> str:
    """Where a removed worktree's leftovers are kept."""
    return os.environ.get("WORKTREE_ARCHIVE_ROOT", DEFAULT_ARCHIVE_ROOT)


def archive_max_bytes() -> int:
    """How big an archive may be before the worktree is kept instead."""
    try:
        return int(
            os.environ.get("WORKTREE_ARCHIVE_MAX_BYTES", DEFAULT_ARCHIVE_MAX_BYTES)
        )
    except ValueError:
        return DEFAULT_ARCHIVE_MAX_BYTES


def repo_root() -> str:
    """The repository the worktrees are made from."""
    return os.environ.get("IDP_ROOT", ".")


def _ensure_parent(path: str) -> None:
    """Create the directory that holds the database, when it has one.

    os.makedirs('') raises FileNotFoundError, so a bare filename ('queue.db') used to
    crash the module at import. abspath gives the parent a name in every case.
    """
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)


def init_db():
    """Create the queue if it is not there."""
    _ensure_parent(db_path())
    with sqlite3.connect(db_path()) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                agent_id TEXT,
                worktree_path TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def push_task(goal: str):
    """Put a goal in the queue."""
    init_db()
    with sqlite3.connect(db_path()) as conn:
        conn.execute("INSERT INTO tasks (goal, status) VALUES (?, 'pending')", (goal,))
        conn.commit()
    print(f"[QUEUE] Task queued: {goal[:60]}...")


def load_task(task_id: int):
    """One task as a dict, or None when there is no such task.

    The worktree manager asks for a task by id to decide whether a worktree is
    orphaned. It used to ask for a function that did not exist.
    """
    with sqlite3.connect(db_path()) as conn:
        row = conn.execute(
            "SELECT id, goal, status, agent_id, worktree_path, created_at, updated_at "
            "FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()
    if row is None:
        return None
    keys = (
        "id",
        "goal",
        "status",
        "agent_id",
        "worktree_path",
        "created_at",
        "updated_at",
    )
    return dict(zip(keys, row, strict=True))


def claim_task(agent_id: str):
    """Claim the oldest pending task and give the agent a worktree to work in.

    The claim and the workspace are one thing: if the workspace cannot be created the
    claim is rolled back and the agent gets nothing, because a task in 'running' with no
    worktree is a task nobody can work on.
    """
    init_db()
    conn = sqlite3.connect(db_path(), isolation_level="IMMEDIATE")
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, goal FROM tasks WHERE status = 'pending' ORDER BY created_at ASC LIMIT 1"
        )
        row = cursor.fetchone()

        if not row:
            return None

        task_id, goal = row
        worktree = os.path.join(worktree_base(), f"task-{task_id}")
        os.makedirs(os.path.dirname(os.path.abspath(worktree)), exist_ok=True)
        # The stamp is the claim's heartbeat: sweep_zombies re-queues any running task
        # whose stamp is older than an hour, so a claim without a stamp is a task that
        # can be run twice.
        cursor.execute(
            "UPDATE tasks SET status = 'running', agent_id = ?, worktree_path = ?, "
            "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (agent_id, worktree, task_id),
        )
        conn.commit()

        result = _git(["worktree", "add", worktree, "--detach", "HEAD"], repo_root())
        if result.returncode != 0 and not _is_worktree(worktree):
            # No workspace: give the task back rather than leave it running with
            # nothing to work in.
            _release(task_id, agent_id)
            print(
                f"[QUEUE] Task {task_id} released: no workspace "
                f"({result.stderr.strip()[:200] or 'git worktree add failed'})"
            )
            return None

        return {"id": task_id, "goal": goal, "worktree": worktree}
    finally:
        conn.close()


def _release(task_id: int, agent_id: str):
    """Put a claimed task back in the queue."""
    with sqlite3.connect(db_path()) as conn:
        conn.execute(
            "UPDATE tasks SET status = 'pending', agent_id = NULL, worktree_path = NULL, "
            "updated_at = CURRENT_TIMESTAMP WHERE id = ? AND agent_id = ?",
            (task_id, agent_id),
        )
        conn.commit()


def complete_task(task_id: int, status: str):
    """Complete a task: the worktree is archived, then removed, then the task is marked."""
    with sqlite3.connect(db_path()) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT worktree_path FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()

        if row and row[0]:
            remove_worktree(row[0])

        cursor.execute(
            "UPDATE tasks SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, task_id),
        )
        conn.commit()


def sweep_zombies():
    """Re-queue the tasks that stopped moving.

    A task is a zombie when it is still marked 'running' and its stamp has not moved for
    an hour. The stamp is written when the task is claimed, so a task that is running
    right now is never re-queued.
    """
    with sqlite3.connect(db_path()) as conn:
        conn.execute("""
            UPDATE tasks
            SET status = 'pending', agent_id = NULL, worktree_path = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE status = 'running' AND updated_at < datetime('now', '-1 hour')
        """)
        conn.commit()


def get_task_list():
    """Every task, newest first."""
    with sqlite3.connect(db_path()) as conn:
        cursor = conn.execute(
            "SELECT id, goal, status, agent_id FROM tasks ORDER BY created_at DESC"
        )
        return cursor.fetchall()


# ---------------------------------------------------------------------------
# the worktree: archiving, then removing
# ---------------------------------------------------------------------------


def _git(args, cwd):
    """Run git and keep its output. Never raises: the caller decides what a failure means.

    A missing repository directory raised FileNotFoundError straight out of the claim, so
    the task stayed 'running' with no workspace and the agent got an exception instead of
    an answer. A failure is a return code, not a crash.
    """
    try:
        return subprocess.run(  # noqa: S603
            ["git"] + list(args),  # noqa: S607
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        return subprocess.CompletedProcess(
            args=["git"] + list(args), returncode=128, stdout="", stderr=str(exc)
        )


def _is_worktree(path: str) -> bool:
    """Is this path a worktree of a repository?"""
    if not os.path.isdir(path):
        return False
    return _git(["rev-parse", "--git-dir"], path).returncode == 0


def archive_worktree(worktree: str):
    """Archive what a worktree holds, in the estate's own convention.

    Returns the archive path, None when there is nothing worth keeping, or the string
    'refused' when the leftovers are over the cap: the worktree is kept then, because the
    work is worth more than the space.
    """
    if not os.path.isdir(worktree):
        return None

    status = _git(["status", "--porcelain", "--ignored=matching"], worktree)
    if status.returncode != 0:
        return None

    tracked = []
    untracked = []
    for line in status.stdout.splitlines():
        if not line:
            continue
        if line.startswith("??"):
            untracked.append(line[3:])
        elif line.startswith("!!"):
            continue  # ignored build output: regenerable, and not archived
        else:
            tracked.append(line)

    untracked = [name for name in untracked if not REBUILDABLE.search(name)]
    if not tracked and not untracked:
        return None

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = os.path.join(
        archive_root(), f"{stamp}-{os.path.basename(worktree.rstrip('/'))}"
    )
    try:
        os.makedirs(dest, exist_ok=True)
        os.chmod(dest, 0o700)
    except OSError as exc:
        print(f"[QUEUE] cannot create the archive {dest}: {exc}")
        return "refused"

    branch = _git(["branch", "--show-current"], worktree).stdout.strip()
    head = _git(["rev-parse", "HEAD"], worktree).stdout.strip()
    with open(os.path.join(dest, "origin"), "w") as fh:
        fh.write(f"{worktree}\n{branch}\n{head}\n")

    patch = _git(["diff", "--binary", "HEAD"], worktree).stdout
    with open(os.path.join(dest, "work.patch"), "w") as fh:
        fh.write(patch)

    if untracked:
        _tar_untracked(worktree, untracked, os.path.join(dest, "untracked.tgz"))

    size = 0
    for root, _dirs, names in os.walk(dest):
        for name in names:
            try:
                size += os.path.getsize(os.path.join(root, name))
            except OSError:
                pass
    if size > archive_max_bytes():
        shutil.rmtree(dest, ignore_errors=True)
        return "refused"
    return dest


def _tar_untracked(worktree: str, names, path: str):
    """Keep the untracked files as one tarball, at the paths they had."""
    with tarfile.open(path, "w:gz") as tar:
        for name in names:
            full = os.path.join(worktree, name)
            if os.path.exists(full):
                tar.add(full, arcname=name, recursive=True)


def remove_worktree(worktree: str):
    """Archive a worktree's leftovers, then remove the worktree.

    The order matters: the archive is what makes the removal safe. Nothing is destroyed
    without a record, and the record's path is printed.
    """
    archive = archive_worktree(worktree)
    if archive == "refused":
        print(f"[QUEUE] keeping {worktree}: its leftovers are over the archive cap")
        return None

    removed = _git(["worktree", "remove", worktree, "--force"], repo_root())
    if removed.returncode != 0:
        print(
            f"[QUEUE] git worktree remove failed for {worktree}: "
            f"{removed.stderr.strip()[:200]}"
        )
        return None

    if archive:
        print(f"[QUEUE] archived {worktree} to {archive}")
    return archive

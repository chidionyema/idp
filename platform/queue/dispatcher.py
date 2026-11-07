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


class QueueLeaseRefused(RuntimeError):
    """Stale or unproven task owner. Never perform task completion side effects."""

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
    """Idempotently migrate the existing queue to monotonic claim epochs.

    The tasks row remains the single owner authority. We keep prior worktree
    locations for forensic recovery when a zombie is reassigned; no automatic
    deletion or untrusted patch application occurs during takeover.
    """
    _ensure_parent(db_path())
    with sqlite3.connect(db_path(), timeout=15, isolation_level=None) as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                agent_id TEXT,
                worktree_path TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                lease_epoch INTEGER NOT NULL DEFAULT 0
            )
        """)
        columns = {row[1] for row in conn.execute("PRAGMA table_info(tasks)")}
        if "lease_epoch" not in columns:
            conn.execute("ALTER TABLE tasks ADD COLUMN lease_epoch INTEGER NOT NULL DEFAULT 0")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS task_recovery_worktrees (
                task_id INTEGER NOT NULL,
                lease_epoch INTEGER NOT NULL,
                worktree_path TEXT NOT NULL,
                recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(task_id, lease_epoch, worktree_path)
            )
        """)
        conn.execute("COMMIT")



def push_task(goal: str):
    """Put a goal in the queue."""
    init_db()
    with sqlite3.connect(db_path()) as conn:
        conn.execute("INSERT INTO tasks (goal, status) VALUES (?, 'pending')", (goal,))
        conn.commit()
    print(f"[QUEUE] Task queued: {goal[:60]}...")


def load_task(task_id: int):
    """Return state and ownership epoch, plus paths needed to recover a takeover."""
    with sqlite3.connect(db_path()) as conn:
        row = conn.execute(
            "SELECT id, goal, status, agent_id, worktree_path, created_at, updated_at, lease_epoch "
            "FROM tasks WHERE id = ?", (task_id,),
        ).fetchone()
        if row is None:
            return None
        recovery = [
            item[0] for item in conn.execute(
                "SELECT worktree_path FROM task_recovery_worktrees "
                "WHERE task_id=? ORDER BY recorded_at, lease_epoch", (task_id,)
            )
        ]
    keys = ("id", "goal", "status", "agent_id", "worktree_path", "created_at",
            "updated_at", "lease_epoch")
    return {**dict(zip(keys, row, strict=True)), "recovery_worktrees": recovery}



def claim_task(agent_id: str):
    """Claim one pending task with a unique epoch and a fresh worktree.

    BEGIN IMMEDIATE precedes the SELECT: otherwise concurrent callers can both
    select the same pending row and allocate the same workspace. Reassignment
    preserves previous worktrees for explicit recovery rather than reusing the
    still-running zombie's directory.
    """
    if not agent_id:
        raise QueueLeaseRefused("MISSING_AGENT_ID")
    init_db()
    conn = sqlite3.connect(db_path(), timeout=15, isolation_level=None)
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT id,goal,lease_epoch,worktree_path FROM tasks "
            "WHERE status='pending' ORDER BY created_at,id LIMIT 1"
        ).fetchone()
        if row is None:
            conn.execute("COMMIT")
            return None
        task_id, goal, last_epoch, previous_worktree = row
        epoch = last_epoch + 1
        worktree = os.path.join(worktree_base(), f"task-{task_id}-epoch-{epoch}")
        os.makedirs(os.path.dirname(os.path.abspath(worktree)), exist_ok=True)
        if previous_worktree and previous_worktree != worktree:
            conn.execute(
                "INSERT OR IGNORE INTO task_recovery_worktrees "
                "(task_id,lease_epoch,worktree_path) VALUES(?,?,?)",
                (task_id, last_epoch, previous_worktree),
            )
        conn.execute(
            "UPDATE tasks SET status='running',agent_id=?,worktree_path=?, "
            "lease_epoch=?,updated_at=CURRENT_TIMESTAMP WHERE id=? AND status='pending'",
            (agent_id, worktree, epoch, task_id),
        )
        conn.execute("COMMIT")
    finally:
        conn.close()

    result = _git(["worktree", "add", worktree, "--detach", "HEAD"], repo_root())
    if result.returncode != 0 and not _is_worktree(worktree):
        _release(task_id, agent_id, epoch)
        print(f"[QUEUE] Task {task_id} released: no workspace "
              f"({result.stderr.strip()[:200] or 'git worktree add failed'})")
        return None

    recovery = load_task(task_id)["recovery_worktrees"]
    return {"id": task_id, "goal": goal, "worktree": worktree,
            "agent_id": agent_id, "lease_epoch": epoch,
            "recovery_worktrees": recovery}



def _release(task_id: int, agent_id: str, lease_epoch: int):
    """Release only the exact attempt whose workspace failed."""
    with sqlite3.connect(db_path()) as conn:
        conn.execute(
            "UPDATE tasks SET status='pending',agent_id=NULL,worktree_path=NULL, "
            "updated_at=CURRENT_TIMESTAMP WHERE id=? AND agent_id=? "
            "AND lease_epoch=? AND status='running'",
            (task_id, agent_id, lease_epoch),
        )
        conn.commit()


def heartbeat_task(task_id: int, agent_id: str, lease_epoch: int):
    """Keep the real owner alive; a stale worker cannot extend another's task."""
    if not agent_id or not isinstance(lease_epoch, int) or lease_epoch < 1:
        raise QueueLeaseRefused("MISSING_OWNERSHIP_PROOF")
    with sqlite3.connect(db_path()) as conn:
        result = conn.execute(
            "UPDATE tasks SET updated_at=CURRENT_TIMESTAMP "
            "WHERE id=? AND agent_id=? AND lease_epoch=? AND status='running'",
            (task_id, agent_id, lease_epoch),
        )
        if result.rowcount != 1:
            raise QueueLeaseRefused("STALE_FENCING_LEASE")
        conn.commit()



def complete_task(task_id: int, status: str, *, agent_id: str | None = None,
                  lease_epoch: int | None = None):
    """Commit a terminal outcome ONLY for the current owner and epoch.

    The status transition is serialized before worktree cleanup; no stale
    attempt is allowed to archive or delete the next worker's files. External
    GitHub/Cloud side effects still require their own broker-side fencing.
    Legacy callers without an epoch are deliberately refused instead of
    silently defeating takeover safety.
    """
    if not agent_id or not isinstance(lease_epoch, int) or lease_epoch < 1:
        raise QueueLeaseRefused("MISSING_OWNERSHIP_PROOF")
    if status not in ("success", "failed", "error", "cancelled"):
        raise QueueLeaseRefused("INVALID_TERMINAL_STATUS")
    with sqlite3.connect(db_path(), timeout=15, isolation_level=None) as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT status,agent_id,lease_epoch,worktree_path FROM tasks WHERE id=?",
            (task_id,),
        ).fetchone()
        if row is None or row[0] != "running" or row[1] != agent_id or row[2] != lease_epoch:
            raise QueueLeaseRefused("STALE_FENCING_LEASE")
        worktree = row[3]
        conn.execute(
            "UPDATE tasks SET status=?,updated_at=CURRENT_TIMESTAMP "
            "WHERE id=? AND agent_id=? AND lease_epoch=? AND status='running'",
            (status, task_id, agent_id, lease_epoch),
        )
        conn.execute("COMMIT")
    if worktree:
        remove_worktree(worktree)
    return True



def sweep_zombies():
    """Invalidate stale ownership, retaining worktree custody for takeover.

    The next claim increments the epoch again and gets its own directory.
    Preserve the previous location until the new worker can checkpoint,
    inspect and explicitly recover any uncommitted data.
    """
    init_db()
    with sqlite3.connect(db_path(), timeout=15, isolation_level=None) as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("""
            UPDATE tasks
            SET status='pending', agent_id=NULL, lease_epoch=lease_epoch+1,
                updated_at=CURRENT_TIMESTAMP
            WHERE status='running' AND updated_at < datetime('now', '-1 hour')
        """)
        conn.execute("COMMIT")



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

import sqlite3
import os
import subprocess

DB_PATH = os.environ.get("QUEUE_DB_PATH", "state/queue.db")
WORKTREE_BASE = os.environ.get("WORKTREE_BASE", ".wt-agents")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(WORKTREE_BASE, exist_ok=True)


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
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
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT INTO tasks (goal, status) VALUES (?, 'pending')", (goal,))
        conn.commit()
    print(f"[QUEUE] Task queued: {goal[:60]}...")


def claim_task(agent_id: str):
    conn = sqlite3.connect(DB_PATH, isolation_level="IMMEDIATE")
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, goal FROM tasks WHERE status = 'pending' ORDER BY created_at ASC LIMIT 1"
        )
        row = cursor.fetchone()

        if row:
            task_id, goal = row
            worktree = os.path.join(WORKTREE_BASE, f"task-{task_id}")
            cursor.execute(
                "UPDATE tasks SET status = 'running', agent_id = ?, worktree_path = ? WHERE id = ?",
                (agent_id, worktree, task_id),
            )
            conn.commit()

            repo_root = os.environ.get("IDP_ROOT", ".")
            subprocess.run(  # noqa: S603
                [  # noqa: S607
                    "git",
                    "worktree",
                    "add",
                    worktree,
                    "--detach",
                    "HEAD",
                ],
                cwd=repo_root,
                capture_output=True,
            )

            return {"id": task_id, "goal": goal, "worktree": worktree}
        return None
    finally:
        conn.close()


def complete_task(task_id: int, status: str):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT worktree_path FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()

        if row and row[0]:
            subprocess.run(  # noqa: S603
                [  # noqa: S607
                    "git",
                    "worktree",
                    "remove",
                    row[0],
                    "--force",
                ],
                capture_output=True,
            )

        cursor.execute(
            "UPDATE tasks SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, task_id),
        )
        conn.commit()


def sweep_zombies():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            UPDATE tasks
            SET status = 'pending', agent_id = NULL, worktree_path = NULL
            WHERE status = 'running' AND updated_at < datetime('now', '-1 hour')
        """)
        conn.commit()


def get_task_list():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "SELECT id, goal, status, agent_id FROM tasks ORDER BY created_at DESC"
        )
        return cursor.fetchall()

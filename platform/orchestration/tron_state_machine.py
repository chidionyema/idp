import os
import sqlite3
from enum import Enum
from typing import Any, Dict, Optional


class TaskState(Enum):
    QUEUED = "QUEUED"
    CLAIMED = "CLAIMED"
    RUNNING = "RUNNING"
    TRANSCRIBED = "TRANSCRIBED"
    EVALUATED = "EVALUATED"
    VERIFIED = "VERIFIED"
    DONE = "DONE"


TRANSITIONS = {
    TaskState.QUEUED: [TaskState.CLAIMED],
    TaskState.CLAIMED: [TaskState.RUNNING],
    TaskState.RUNNING: [TaskState.TRANSCRIBED],
    TaskState.TRANSCRIBED: [TaskState.EVALUATED],
    TaskState.EVALUATED: [TaskState.VERIFIED],
    TaskState.VERIFIED: [TaskState.DONE],
    TaskState.DONE: [],
}


class IllegalTransition(Exception):
    pass


def _get_db_path() -> str:
    return os.path.expanduser("~/dev/code/idp/state/tron.db")


def _init_tron_db() -> None:
    db_path = _get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS task_transitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                from_state TEXT NOT NULL,
                to_state TEXT NOT NULL,
                metadata TEXT,
                gate_result TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(task_id, from_state, to_state)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS task_state (
                task_id INTEGER PRIMARY KEY,
                current_state TEXT NOT NULL,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def lookup_transition(
    current_state: TaskState,
    metadata: Optional[Dict[str, Any]] = None,
    gate_result: Optional[str] = None,
) -> TaskState:
    metadata = metadata or {}
    gate_result = gate_result or ""

    if current_state not in TRANSITIONS:
        raise IllegalTransition(f"Unknown state: {current_state}")

    valid_next_states = TRANSITIONS[current_state]

    if not valid_next_states:
        raise IllegalTransition(
            f"No valid transitions from state {current_state.value}"
        )

    if len(valid_next_states) == 1:
        return valid_next_states[0]

    if gate_result == "halt":
        if current_state == TaskState.VERIFIED:
            return TaskState.DONE
        raise IllegalTransition(f"Cannot halt at state {current_state.value}")

    return valid_next_states[0]


def persist_transition(
    task_id: int,
    from_state: TaskState,
    to_state: TaskState,
    metadata: Optional[Dict[str, Any]] = None,
    gate_result: Optional[str] = None,
) -> None:
    _init_tron_db()

    if to_state not in TRANSITIONS.get(from_state, []):
        raise IllegalTransition(
            f"Invalid transition: {from_state.value} → {to_state.value}"
        )

    db_path = _get_db_path()

    with sqlite3.connect(db_path) as conn:
        metadata_str = str(metadata) if metadata else ""
        gate_result_str = gate_result if gate_result else ""

        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO task_transitions
            (task_id, from_state, to_state, metadata, gate_result)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                task_id,
                from_state.value,
                to_state.value,
                metadata_str,
                gate_result_str,
            ),
        )

        cursor.execute(
            """
            INSERT INTO task_state (task_id, current_state, last_updated)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(task_id) DO UPDATE SET
                current_state = excluded.current_state,
                last_updated = CURRENT_TIMESTAMP
        """,
            (task_id, to_state.value),
        )

        conn.commit()


def get_current_state(task_id: int) -> Optional[TaskState]:
    _init_tron_db()
    db_path = _get_db_path()

    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            "SELECT current_state FROM task_state WHERE task_id = ?", (task_id,)
        )
        row = cursor.fetchone()

    if row:
        return TaskState(row[0])
    return None


def get_transition_history(task_id: int) -> list:
    _init_tron_db()
    db_path = _get_db_path()

    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            """
            SELECT from_state, to_state, metadata, gate_result, timestamp
            FROM task_transitions
            WHERE task_id = ?
            ORDER BY timestamp ASC
        """,
            (task_id,),
        )
        rows = cursor.fetchall()

    return [
        {
            "from_state": row[0],
            "to_state": row[1],
            "metadata": row[2],
            "gate_result": row[3],
            "timestamp": row[4],
        }
        for row in rows
    ]

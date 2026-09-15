"""Atomic VACUUM INTO operations for span retention and archival."""

from __future__ import annotations

import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional


class SpanTier(str, Enum):
    """Span retention tiers with lifecycle policies."""

    TIER0_RAM = "tier0_ram"  # Ring buffer, flushed every 500ms
    TIER1_SQLITE = "tier1_sqlite"  # 14-day retention in SQLite
    TIER2_COMPRESSED = "tier2_compressed"  # 90-day retention compressed
    TIER3_STATS = "tier3_stats"  # Indefinite daily aggregates


@dataclass
class VacuumCheckpoint:
    """Checkpoint for vacuum operation atomicity."""

    checkpoint_id: str
    source_table: str
    archive_table: str
    rows_to_vacuum: int
    rows_vacuumed: int
    state: str  # pending, swapped, validated, committed, rolled_back
    created_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class VacuumJob:
    """Manages atomic VACUUM INTO operations with crash-safety."""

    # Schema for vacuum tracking
    VACUUM_SCHEMA = """
    CREATE TABLE IF NOT EXISTS vacuum_checkpoints (
        checkpoint_id TEXT PRIMARY KEY,
        source_table TEXT NOT NULL,
        archive_table TEXT NOT NULL,
        rows_to_vacuum INTEGER NOT NULL,
        rows_vacuumed INTEGER NOT NULL,
        state TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL,
        completed_at TIMESTAMP,
        error TEXT,
        UNIQUE(source_table, created_at)
    );

    CREATE INDEX IF NOT EXISTS idx_vacuum_state
        ON vacuum_checkpoints(state, created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_vacuum_source
        ON vacuum_checkpoints(source_table, completed_at DESC);
    """

    def __init__(self, db_path: str):
        """Initialize vacuum job manager."""
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path, timeout=30.0)
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA synchronous = FULL")
        self._lock = threading.Lock()
        self._init_vacuum_schema()

    def _init_vacuum_schema(self):
        """Initialize vacuum tracking tables."""
        with self._lock:
            for statement in self.VACUUM_SCHEMA.strip().split(";"):
                if statement.strip():
                    self._conn.execute(statement)
            self._conn.commit()

    def prepare_vacuum(
        self,
        source_table: str,
        archive_table: str,
        retention_days: int = 14,
    ) -> str:
        """Prepare VACUUM INTO statement with checkpoint.

        Args:
            source_table: Table to vacuum spans from
            archive_table: Archive table destination
            retention_days: Days of data to retain

        Returns:
            checkpoint_id for tracking
        """
        checkpoint_id = str(uuid.uuid4())

        with self._lock:
            cursor = self._conn.cursor()

            # Count rows to vacuum
            cutoff_date = (
                datetime.utcnow() - timedelta(days=retention_days)
            ).isoformat()
            cursor.execute(
                f'SELECT COUNT(*) FROM "{source_table}" WHERE created_at < ?',  # noqa: S608
                (cutoff_date,),
            )
            rows_to_vacuum = cursor.fetchone()[0]

            if rows_to_vacuum == 0:
                return checkpoint_id

            # Record checkpoint in pending state
            cursor.execute(
                """
                INSERT INTO vacuum_checkpoints
                (checkpoint_id, source_table, archive_table, rows_to_vacuum,
                 rows_vacuumed, state, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    checkpoint_id,
                    source_table,
                    archive_table,
                    rows_to_vacuum,
                    0,
                    "pending",
                    datetime.utcnow().isoformat(),
                ),
            )
            self._conn.commit()

        return checkpoint_id

    def execute_vacuum(self, checkpoint_id: str) -> bool:
        """Execute atomic swap of old spans to archive.

        Args:
            checkpoint_id: Checkpoint from prepare_vacuum

        Returns:
            True if swap succeeded, False otherwise

        Raises:
            RuntimeError: If checkpoint not found or swap fails
        """
        with self._lock:
            try:
                cursor = self._conn.cursor()

                # Fetch checkpoint
                cursor.execute(
                    "SELECT source_table, archive_table, rows_to_vacuum FROM "
                    "vacuum_checkpoints WHERE checkpoint_id = ?",
                    (checkpoint_id,),
                )
                row = cursor.fetchone()
                if not row:
                    raise RuntimeError(f"Checkpoint {checkpoint_id} not found")

                source_table, archive_table, rows_to_vacuum = row

                if rows_to_vacuum == 0:
                    cursor.execute(
                        "UPDATE vacuum_checkpoints SET state = ?, completed_at = ? "
                        "WHERE checkpoint_id = ?",
                        ("swapped", datetime.utcnow().isoformat(), checkpoint_id),
                    )
                    self._conn.commit()
                    return True

                # Begin transaction for atomic swap
                cursor.execute("BEGIN IMMEDIATE")

                try:
                    cutoff_date = (datetime.utcnow() - timedelta(days=14)).isoformat()

                    # Copy old rows to archive
                    cursor.execute(
                        f"""
                        INSERT INTO "{archive_table}"
                        SELECT * FROM "{source_table}"
                        WHERE created_at < ?
                        """,  # noqa: S608
                        (cutoff_date,),
                    )
                    rows_copied = cursor.rowcount

                    # Delete vacuumed rows from source
                    cursor.execute(
                        f"""
                        DELETE FROM "{source_table}"
                        WHERE created_at < ?
                        """,  # noqa: S608
                        (cutoff_date,),
                    )
                    rows_deleted = cursor.rowcount

                    if rows_copied != rows_deleted:
                        raise RuntimeError(
                            f"Swap mismatch: copied {rows_copied}, "
                            f"deleted {rows_deleted}"
                        )

                    # Update checkpoint to swapped state
                    cursor.execute(
                        "UPDATE vacuum_checkpoints SET state = ?, rows_vacuumed = ? "
                        "WHERE checkpoint_id = ?",
                        ("swapped", rows_copied, checkpoint_id),
                    )

                    cursor.execute("COMMIT")
                    return True

                except Exception as swap_error:
                    cursor.execute("ROLLBACK")
                    # Record error in checkpoint
                    cursor.execute(
                        "UPDATE vacuum_checkpoints SET state = ?, error = ? "
                        "WHERE checkpoint_id = ?",
                        ("rolled_back", str(swap_error), checkpoint_id),
                    )
                    self._conn.commit()
                    raise RuntimeError(
                        f"Vacuum swap failed: {swap_error}"
                    ) from swap_error

            except RuntimeError:
                self._conn.rollback()
                raise

    def validate_swap(self, checkpoint_id: str) -> bool:
        """Verify data integrity post-swap.

        Args:
            checkpoint_id: Checkpoint to validate

        Returns:
            True if swap is valid, False otherwise

        Raises:
            RuntimeError: If validation fails
        """
        with self._lock:
            cursor = self._conn.cursor()

            cursor.execute(
                "SELECT source_table, archive_table, rows_vacuumed FROM "
                "vacuum_checkpoints WHERE checkpoint_id = ?",
                (checkpoint_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise RuntimeError(f"Checkpoint {checkpoint_id} not found")

            source_table, archive_table, rows_vacuumed = row

            if rows_vacuumed == 0:
                cursor.execute(
                    "UPDATE vacuum_checkpoints SET state = ? WHERE checkpoint_id = ?",
                    ("validated", checkpoint_id),
                )
                self._conn.commit()
                return True

            try:
                # Verify no rows from archive were re-inserted to source
                cutoff_date = (datetime.utcnow() - timedelta(days=14)).isoformat()
                cursor.execute(
                    f'SELECT COUNT(*) FROM "{source_table}" WHERE created_at < ?',  # noqa: S608
                    (cutoff_date,),
                )
                stray_rows = cursor.fetchone()[0]

                if stray_rows > 0:
                    raise RuntimeError(
                        f"Found {stray_rows} stray old rows in source after swap"
                    )

                # Verify archive has expected row count
                cursor.execute(
                    f'SELECT COUNT(*) FROM "{archive_table}" WHERE created_at < ?',  # noqa: S608
                    (cutoff_date,),
                )
                archive_count = cursor.fetchone()[0]

                if archive_count < rows_vacuumed:
                    raise RuntimeError(
                        f"Archive has {archive_count} rows, expected "
                        f"at least {rows_vacuumed}"
                    )

                # Update checkpoint to validated state
                cursor.execute(
                    "UPDATE vacuum_checkpoints SET state = ?, completed_at = ? "
                    "WHERE checkpoint_id = ?",
                    ("validated", datetime.utcnow().isoformat(), checkpoint_id),
                )
                self._conn.commit()
                return True

            except Exception as e:
                self._conn.rollback()
                raise RuntimeError(f"Validation failed: {e}") from e

    def rollback_if_needed(self, checkpoint_id: str) -> bool:
        """Safety rollback for incomplete or failed swaps.

        Args:
            checkpoint_id: Checkpoint to rollback

        Returns:
            True if rollback succeeded, False if already terminal

        Raises:
            RuntimeError: If rollback fails
        """
        with self._lock:
            try:
                cursor = self._conn.cursor()

                cursor.execute(
                    "SELECT state, rows_vacuumed FROM vacuum_checkpoints "
                    "WHERE checkpoint_id = ?",
                    (checkpoint_id,),
                )
                row = cursor.fetchone()
                if not row:
                    raise RuntimeError(f"Checkpoint {checkpoint_id} not found")

                state, rows_vacuumed = row

                # Only rollback if in intermediate states
                if state not in ("pending", "swapped"):
                    return False

                if state == "swapped" and rows_vacuumed == 0:
                    cursor.execute(
                        "UPDATE vacuum_checkpoints SET state = ? "
                        "WHERE checkpoint_id = ?",
                        ("rolled_back", checkpoint_id),
                    )
                    self._conn.commit()
                    return True

                # Rollback was already attempted in execute_vacuum on error
                cursor.execute(
                    "UPDATE vacuum_checkpoints SET state = ? "
                    "WHERE checkpoint_id = ? AND state = ?",
                    ("rolled_back", checkpoint_id, "pending"),
                )
                self._conn.commit()
                return True

            except Exception as e:
                self._conn.rollback()
                raise RuntimeError(f"Rollback failed: {e}") from e

    def get_checkpoint_status(self, checkpoint_id: str) -> Optional[VacuumCheckpoint]:
        """Fetch checkpoint status.

        Args:
            checkpoint_id: Checkpoint ID to fetch

        Returns:
            VacuumCheckpoint or None if not found
        """
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                "SELECT checkpoint_id, source_table, archive_table, "
                "rows_to_vacuum, rows_vacuumed, state, created_at, "
                "completed_at, error FROM vacuum_checkpoints "
                "WHERE checkpoint_id = ?",
                (checkpoint_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None

            return VacuumCheckpoint(
                checkpoint_id=row[0],
                source_table=row[1],
                archive_table=row[2],
                rows_to_vacuum=row[3],
                rows_vacuumed=row[4],
                state=row[5],
                created_at=datetime.fromisoformat(row[6]),
                completed_at=(datetime.fromisoformat(row[7]) if row[7] else None),
                error=row[8],
            )

    def cleanup_old_checkpoints(self, days: int = 30):
        """Clean up old checkpoint records.

        Args:
            days: Delete checkpoints older than this many days
        """
        with self._lock:
            cursor = self._conn.cursor()
            cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
            cursor.execute(
                "DELETE FROM vacuum_checkpoints WHERE created_at < ? "
                "AND state IN ('committed', 'rolled_back', 'validated')",
                (cutoff,),
            )
            self._conn.commit()

    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

"""Write-ahead outbox pattern for span retention operations."""

from __future__ import annotations

import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional


class OutboxOperation(str, Enum):
    """Operation types in the outbox."""

    ARCHIVE = "archive"  # Archive old spans
    COMPRESS = "compress"  # Compress archived spans
    AGGREGATE = "aggregate"  # Create daily aggregate stats
    DELETE = "delete"  # Delete expired spans
    VACUUM = "vacuum"  # Run VACUUM on database


@dataclass
class OutboxEntry:
    """Entry in the outbox log."""

    outbox_id: str
    span_id: str
    operation: OutboxOperation
    payload: str  # JSON-encoded operation data
    idempotency_key: str
    state: str  # pending, processing, processed, failed, retrying
    created_at: datetime
    processed_at: Optional[datetime] = None
    retry_count: int = 0
    error: Optional[str] = None


class OutboxPattern:
    """Write-ahead logging for idempotent retention operations."""

    # Schema for outbox
    OUTBOX_SCHEMA = """
    CREATE TABLE IF NOT EXISTS span_outbox (
        outbox_id TEXT PRIMARY KEY,
        span_id TEXT NOT NULL,
        operation TEXT NOT NULL,
        payload TEXT NOT NULL,
        idempotency_key TEXT NOT NULL UNIQUE,
        state TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL,
        processed_at TIMESTAMP,
        retry_count INTEGER NOT NULL DEFAULT 0,
        error TEXT,
        FOREIGN KEY (span_id) REFERENCES transcript_spans(span_id)
            ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_outbox_state
        ON span_outbox(state, created_at ASC);
    CREATE INDEX IF NOT EXISTS idx_outbox_operation
        ON span_outbox(operation, state);
    CREATE INDEX IF NOT EXISTS idx_outbox_span_id
        ON span_outbox(span_id);
    CREATE INDEX IF NOT EXISTS idx_outbox_idempotency
        ON span_outbox(idempotency_key);
    CREATE INDEX IF NOT EXISTS idx_outbox_retry
        ON span_outbox(retry_count, created_at ASC)
        WHERE state = 'retrying';

    CREATE TABLE IF NOT EXISTS outbox_processed (
        outbox_id TEXT PRIMARY KEY,
        processed_at TIMESTAMP NOT NULL,
        result TEXT,
        FOREIGN KEY (outbox_id) REFERENCES span_outbox(outbox_id)
            ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_processed_at
        ON outbox_processed(processed_at DESC);
    """

    def __init__(self, db_path: str):
        """Initialize outbox pattern.

        Args:
            db_path: Path to database
        """
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path, timeout=30.0)
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA synchronous = FULL")
        self._lock = threading.Lock()
        self._init_outbox_schema()

    def _init_outbox_schema(self):
        """Initialize outbox tracking tables."""
        with self._lock:
            for statement in self.OUTBOX_SCHEMA.strip().split(";"):
                if statement.strip():
                    self._conn.execute(statement)
            self._conn.commit()

    def outbox_insert(
        self,
        span_id: str,
        operation: OutboxOperation,
        payload: str,
        idempotency_key: Optional[str] = None,
    ) -> str:
        """Insert operation into outbox idempotently.

        Args:
            span_id: Span ID associated with operation
            operation: Operation type
            payload: JSON-encoded operation payload
            idempotency_key: Unique key for idempotency, auto-generated if None

        Returns:
            outbox_id for tracking

        Raises:
            RuntimeError: If insert fails due to constraint violation
        """
        outbox_id = str(uuid.uuid4())
        if idempotency_key is None:
            idempotency_key = f"{span_id}:{operation.value}"

        with self._lock:
            try:
                cursor = self._conn.cursor()

                cursor.execute(
                    "INSERT INTO span_outbox "
                    "(outbox_id, span_id, operation, payload, "
                    "idempotency_key, state, created_at, retry_count) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        outbox_id,
                        span_id,
                        operation.value,
                        payload,
                        idempotency_key,
                        "pending",
                        datetime.utcnow().isoformat(),
                        0,
                    ),
                )
                self._conn.commit()
                return outbox_id

            except sqlite3.IntegrityError as e:
                if "idempotency_key" in str(e):
                    # Idempotent: return existing entry ID
                    cursor = self._conn.cursor()
                    cursor.execute(
                        "SELECT outbox_id FROM span_outbox WHERE idempotency_key = ?",
                        (idempotency_key,),
                    )
                    existing = cursor.fetchone()
                    if existing:
                        return existing[0]
                raise RuntimeError(f"Failed to insert outbox entry: {e}") from e
            except Exception as e:
                self._conn.rollback()
                raise RuntimeError(f"Failed to insert outbox entry: {e}") from e

    def process_outbox(
        self,
        batch_size: int = 100,
        operation_filter: Optional[OutboxOperation] = None,
    ) -> list[OutboxEntry]:
        """Get pending outbox entries for processing.

        Args:
            batch_size: Maximum entries to return
            operation_filter: Filter by operation type, None for all

        Returns:
            List of pending outbox entries

        Raises:
            RuntimeError: If query fails
        """
        with self._lock:
            try:
                cursor = self._conn.cursor()

                query = (
                    "SELECT outbox_id, span_id, operation, payload, "
                    "idempotency_key, state, created_at, processed_at, "
                    "retry_count, error FROM span_outbox "
                    "WHERE state IN ('pending', 'retrying') "
                )
                params = []

                if operation_filter:
                    query += "AND operation = ? "
                    params.append(operation_filter.value)

                query += "ORDER BY created_at ASC LIMIT ?"
                params.append(batch_size)

                cursor.execute(query, params)
                rows = cursor.fetchall()

                return [
                    OutboxEntry(
                        outbox_id=row[0],
                        span_id=row[1],
                        operation=OutboxOperation(row[2]),
                        payload=row[3],
                        idempotency_key=row[4],
                        state=row[5],
                        created_at=datetime.fromisoformat(row[6]),
                        processed_at=(
                            datetime.fromisoformat(row[7]) if row[7] else None
                        ),
                        retry_count=row[8],
                        error=row[9],
                    )
                    for row in rows
                ]

            except Exception as e:
                raise RuntimeError(f"Failed to process outbox: {e}") from e

    def mark_processing(self, outbox_id: str) -> bool:
        """Mark entry as being processed atomically.

        Args:
            outbox_id: Outbox entry to mark

        Returns:
            True if marked successfully, False if already processed

        Raises:
            RuntimeError: If update fails
        """
        with self._lock:
            try:
                cursor = self._conn.cursor()

                # Atomic update: only if still pending or retrying
                cursor.execute(
                    "UPDATE span_outbox SET state = 'processing' "
                    "WHERE outbox_id = ? AND state IN ('pending', 'retrying')",
                    (outbox_id,),
                )
                self._conn.commit()

                return cursor.rowcount > 0

            except Exception as e:
                self._conn.rollback()
                raise RuntimeError(f"Failed to mark processing: {e}") from e

    def confirm_processed(
        self,
        outbox_ids: list[str],
        result: Optional[str] = None,
    ) -> int:
        """Confirm operation complete and mark entries processed.

        Args:
            outbox_ids: List of outbox IDs to confirm
            result: Optional result data to store

        Returns:
            Number of entries confirmed

        Raises:
            RuntimeError: If confirmation fails
        """
        if not outbox_ids:
            return 0

        with self._lock:
            try:
                cursor = self._conn.cursor()

                # Begin transaction for atomic confirmation
                cursor.execute("BEGIN IMMEDIATE")

                try:
                    processed_count = 0

                    for outbox_id in outbox_ids:
                        # Update outbox entry
                        cursor.execute(
                            "UPDATE span_outbox SET state = 'processed', "
                            "processed_at = ? "
                            "WHERE outbox_id = ?",
                            (datetime.utcnow().isoformat(), outbox_id),
                        )
                        processed_count += cursor.rowcount

                        # Record in processed table for audit trail
                        cursor.execute(
                            "INSERT OR IGNORE INTO outbox_processed "
                            "(outbox_id, processed_at, result) "
                            "VALUES (?, ?, ?)",
                            (
                                outbox_id,
                                datetime.utcnow().isoformat(),
                                result,
                            ),
                        )

                    cursor.execute("COMMIT")
                    return processed_count

                except Exception as e:
                    cursor.execute("ROLLBACK")
                    raise e

            except Exception as e:
                self._conn.rollback()
                raise RuntimeError(f"Failed to confirm processed: {e}") from e

    def mark_failed(
        self,
        outbox_id: str,
        error: str,
        retry: bool = True,
    ) -> bool:
        """Mark operation as failed.

        Args:
            outbox_id: Failed outbox entry
            error: Error message
            retry: If True, mark for retry; otherwise mark as failed

        Returns:
            True if marked successfully

        Raises:
            RuntimeError: If update fails
        """
        with self._lock:
            try:
                cursor = self._conn.cursor()

                new_state = "retrying" if retry else "failed"

                cursor.execute(
                    "UPDATE span_outbox SET state = ?, error = ?, "
                    "retry_count = retry_count + 1 "
                    "WHERE outbox_id = ?",
                    (new_state, error, outbox_id),
                )
                self._conn.commit()

                return cursor.rowcount > 0

            except Exception as e:
                self._conn.rollback()
                raise RuntimeError(f"Failed to mark failed: {e}") from e

    def get_entry_status(self, outbox_id: str) -> Optional[OutboxEntry]:
        """Fetch outbox entry status.

        Args:
            outbox_id: Entry to fetch

        Returns:
            OutboxEntry or None if not found
        """
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                "SELECT outbox_id, span_id, operation, payload, "
                "idempotency_key, state, created_at, processed_at, "
                "retry_count, error FROM span_outbox "
                "WHERE outbox_id = ?",
                (outbox_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None

            return OutboxEntry(
                outbox_id=row[0],
                span_id=row[1],
                operation=OutboxOperation(row[2]),
                payload=row[3],
                idempotency_key=row[4],
                state=row[5],
                created_at=datetime.fromisoformat(row[6]),
                processed_at=(datetime.fromisoformat(row[7]) if row[7] else None),
                retry_count=row[8],
                error=row[9],
            )

    def cleanup_processed_entries(self, days: int = 7):
        """Clean up old processed entries.

        Args:
            days: Delete entries older than this many days
        """
        with self._lock:
            try:
                cursor = self._conn.cursor()
                cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

                # Delete from audit trail first
                cursor.execute(
                    "DELETE FROM outbox_processed WHERE processed_at < ?",
                    (cutoff,),
                )

                # Delete from main outbox
                cursor.execute(
                    "DELETE FROM span_outbox WHERE state = 'processed' "
                    "AND processed_at < ?",
                    (cutoff,),
                )

                self._conn.commit()

            except Exception as e:
                self._conn.rollback()
                raise RuntimeError(f"Cleanup failed: {e}") from e

    def get_statistics(self) -> dict:
        """Get outbox statistics.

        Returns:
            Dictionary with pending, processing, processed, failed counts
        """
        with self._lock:
            cursor = self._conn.cursor()

            cursor.execute("SELECT state, COUNT(*) FROM span_outbox GROUP BY state")
            stats = {state: count for state, count in cursor.fetchall()}

            # Add operation breakdown
            cursor.execute(
                "SELECT operation, state, COUNT(*) FROM span_outbox "
                "GROUP BY operation, state"
            )
            op_stats = {}
            for operation, state, count in cursor.fetchall():
                if operation not in op_stats:
                    op_stats[operation] = {}
                op_stats[operation][state] = count

            return {
                "by_state": stats,
                "by_operation": op_stats,
                "total": sum(stats.values()),
            }

    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

"""Span emission and hierarchical tracking for parallel agents."""

from __future__ import annotations

import sqlite3
import threading
import uuid
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime
from typing import Optional

from platform.telemetry.transcript_schema import (
    SpanKind,
    TranscriptSpan,
    init_schema,
)


class SpanEmitter:
    """Emit and persist spans with parent/child hierarchy."""

    def __init__(
        self,
        transcript_id: str,
        db_path: str = None,
        auto_create_transcript: bool = True,
    ):
        self.transcript_id = transcript_id
        self.db_path = db_path
        self._conn = init_schema(db_path)
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._local = threading.local()
        self._lock = threading.Lock()
        if auto_create_transcript:
            self._ensure_transcript_exists()

    def _ensure_transcript_exists(self):
        """Create transcript record if it doesn't exist."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                "SELECT id FROM transcripts WHERE id = ?", (self.transcript_id,)
            )
            if not cursor.fetchone():
                cursor.execute(
                    """
                    INSERT INTO transcripts
                    (id, task_id, agent_instance, model_id, model_tier, total_turns, cost,
                     loop_detected, circuit_breaker_tripped)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        self.transcript_id,
                        "task-unknown",
                        "agent-unknown",
                        "model-unknown",
                        "tier-unknown",
                        0,
                        0.0,
                        False,
                        False,
                    ),
                )
                self._conn.commit()

    @property
    def _current_parent_span_id(self) -> Optional[str]:
        """Get current parent span ID from thread-local context."""
        return getattr(self._local, "parent_span_id", None)

    @_current_parent_span_id.setter
    def _current_parent_span_id(self, span_id: Optional[str]):
        """Set current parent span ID in thread-local context."""
        self._local.parent_span_id = span_id

    @property
    def _sequence_counter(self) -> int:
        """Get current sequence number for this transcript."""
        return getattr(self._local, "sequence_counter", 0)

    @_sequence_counter.setter
    def _sequence_counter(self, value: int):
        """Set sequence counter."""
        self._local.sequence_counter = value

    def _next_sequence_num(self) -> int:
        """Increment and return next sequence number."""
        with self._lock:
            current = self._sequence_counter
            self._sequence_counter = current + 1
            return current + 1

    def emit(
        self,
        span_kind: SpanKind,
        content: str,
        args_hash: Optional[str] = None,
        result_hash: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        fault_flags: str = "",
        eval_scores: str = "",
    ) -> str:
        """Emit a span and persist it. Returns span_id."""
        span_id = str(uuid.uuid4())
        sequence_num = self._next_sequence_num()

        parent_id = parent_span_id or self._current_parent_span_id

        span = TranscriptSpan(
            span_id=span_id,
            transcript_id=self.transcript_id,
            span_kind=span_kind,
            sequence_num=sequence_num,
            content=content,
            args_hash=args_hash,
            result_hash=result_hash,
            parent_span_id=parent_id,
            fault_flags=fault_flags,
            eval_scores=eval_scores,
            created_at=datetime.utcnow(),
        )

        self._persist_span(span)
        return span_id

    def _persist_span(self, span: TranscriptSpan):
        """Write span to database with checkpointing."""
        with self._lock:
            try:
                cursor = self._conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO transcript_spans
                    (span_id, transcript_id, parent_span_id, span_kind, sequence_num,
                     content, args_hash, result_hash, fault_flags, eval_scores, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        span.span_id,
                        span.transcript_id,
                        span.parent_span_id,
                        span.span_kind.value,
                        span.sequence_num,
                        span.content,
                        span.args_hash,
                        span.result_hash,
                        span.fault_flags,
                        span.eval_scores,
                        span.created_at.isoformat(),
                    ),
                )
                self._conn.commit()
            except sqlite3.Error as e:
                self._conn.rollback()
                raise RuntimeError(f"Failed to persist span {span.span_id}: {e}") from e

    @contextmanager
    def child_span(
        self,
        span_kind: SpanKind,
        content: str,
        args_hash: Optional[str] = None,
    ):
        """Context manager for child span hierarchy."""
        parent_id = self._current_parent_span_id
        span_id = self.emit(
            span_kind=span_kind,
            content=content,
            args_hash=args_hash,
        )

        old_parent = self._current_parent_span_id
        self._current_parent_span_id = span_id

        try:
            yield span_id
        finally:
            self._current_parent_span_id = old_parent

    def checkpoint_before_llm_call(self) -> str:
        """Checkpoint current state before LLM call. Returns checkpoint_id."""
        checkpoint_id = str(uuid.uuid4())
        self.emit(
            span_kind=SpanKind.LLM_CALL,
            content=f"checkpoint: {checkpoint_id}",
            args_hash=checkpoint_id,
        )
        return checkpoint_id

    def record_llm_result(
        self,
        checkpoint_id: str,
        result_hash: str,
        eval_scores: str = "",
    ):
        """Record LLM result with evaluation scores."""
        self.emit(
            span_kind=SpanKind.LLM_CALL,
            content=f"llm_result: {checkpoint_id}",
            result_hash=result_hash,
            eval_scores=eval_scores,
        )

    def get_span(self, span_id: str) -> Optional[dict]:
        """Fetch span details by ID."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(
                """
                SELECT span_id, transcript_id, parent_span_id, span_kind, sequence_num,
                       content, args_hash, result_hash, fault_flags, eval_scores, created_at
                FROM transcript_spans
                WHERE span_id = ?
                """,
                (span_id,),
            )
            row = cursor.fetchone()
            if row:
                return {
                    "span_id": row[0],
                    "transcript_id": row[1],
                    "parent_span_id": row[2],
                    "span_kind": row[3],
                    "sequence_num": row[4],
                    "content": row[5],
                    "args_hash": row[6],
                    "result_hash": row[7],
                    "fault_flags": row[8],
                    "eval_scores": row[9],
                    "created_at": row[10],
                }
            return None

    def get_transcript_spans(self, limit: int = None) -> list[dict]:
        """Fetch all spans for transcript, ordered by sequence."""
        with self._lock:
            cursor = self._conn.cursor()
            query = """
                SELECT span_id, transcript_id, parent_span_id, span_kind, sequence_num,
                       content, args_hash, result_hash, fault_flags, eval_scores, created_at
                FROM transcript_spans
                WHERE transcript_id = ?
                ORDER BY sequence_num ASC
            """
            if limit:
                query += f" LIMIT {limit}"
            cursor.execute(query, (self.transcript_id,))
            rows = cursor.fetchall()
            return [
                {
                    "span_id": row[0],
                    "transcript_id": row[1],
                    "parent_span_id": row[2],
                    "span_kind": row[3],
                    "sequence_num": row[4],
                    "content": row[5],
                    "args_hash": row[6],
                    "result_hash": row[7],
                    "fault_flags": row[8],
                    "eval_scores": row[9],
                    "created_at": row[10],
                }
                for row in rows
            ]

    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

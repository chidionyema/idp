#!/usr/bin/env python3
"""Span storage retention manager: four-tier architecture.

Tier 0 (RAM): In-memory ring buffer
Tier 1 (SQLite): Export buffer, 14-day retention
Tier 2 (Compressed): Parquet archive, 90-day retention
Tier 3 (Stats): Daily aggregates, indefinite retention
"""

import sqlite3
import threading
import time
from collections import deque
from datetime import datetime, timedelta
from typing import Optional


class HotSpanBuffer:
    """
    In-memory ring buffer. Background writer flushes to SQLite in batches.
    Agent execution never touches disk directly.
    """

    def __init__(self, maxlen: int = 10000, flush_interval_ms: float = 500):
        self.buffer = deque(maxlen=maxlen)
        self.lock = threading.Lock()
        self.flush_interval = flush_interval_ms / 1000
        self.db_path: Optional[str] = None
        self._flush_thread: Optional[threading.Thread] = None
        self.running = False

    def start(self, db_path: str):
        """Start the background flush worker."""
        self.db_path = db_path
        self.running = True
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()

    def append(self, span: dict):
        """Add span to buffer. Non-blocking."""
        with self.lock:
            self.buffer.append(span)

    def stop(self):
        """Stop background worker and flush remaining spans."""
        self.running = False
        if self._flush_thread:
            self._flush_thread.join(timeout=5)
        # Final flush
        self._flush_batch(list(self.buffer))

    def _flush_loop(self):
        """Background worker: flush buffer at regular intervals."""
        while self.running:
            time.sleep(self.flush_interval)
            with self.lock:
                batch = list(self.buffer)
                self.buffer.clear()
            if batch:
                self._flush_batch(batch)

    def _flush_batch(self, batch: list[dict]):
        """Write batch to SQLite."""
        if not self.db_path or not batch:
            return
        try:
            with sqlite3.connect(self.db_path) as conn:
                for span in batch:
                    conn.execute(
                        """
                        INSERT INTO spans_buffer
                        (span_id, transcript_id, span_kind, payload, created_at, exported)
                        VALUES (?, ?, ?, ?, ?, FALSE)
                        """,
                        (
                            span.get("id"),
                            span.get("transcript_id"),
                            span.get("kind"),
                            span.get("payload"),
                            datetime.now(),
                        ),
                    )
                conn.commit()
        except Exception as e:
            print(f"[SpanBuffer] Flush failed: {e}")


class SpanExporter:
    """
    Exports spans from SQLite buffer to compressed archive.
    Runs on a schedule or when buffer exceeds size threshold.
    """

    def __init__(self, db_path: str, archive_dir: str, batch_size: int = 10000):
        self.db_path = db_path
        self.archive_dir = archive_dir
        self.batch_size = batch_size

    def export_batch(self) -> dict:
        """
        Export unexported spans from buffer. Write to archive. Mark exported.
        Returns summary: {exported: N, archived_to: path, error: None|str}
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT span_id, payload FROM spans_buffer
                WHERE exported = FALSE
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (self.batch_size,),
            )
            rows = cursor.fetchall()

        if not rows:
            return {"exported": 0, "archived_to": None}

        # Write to archive (Parquet would go here; simplified to JSON for now)
        archive_file = f"{self.archive_dir}/spans_{datetime.now().isoformat()}.jsonl"
        try:
            with open(archive_file, "w") as f:
                for row in rows:
                    f.write(f"{row[1]}\n")
        except Exception as e:
            return {"exported": 0, "error": str(e)}

        # Mark as exported
        span_ids = [row[0] for row in rows]
        placeholders = ",".join("?" * len(span_ids))
        with sqlite3.connect(self.db_path) as conn:
            query = f"UPDATE spans_buffer SET exported = TRUE, exported_at = CURRENT_TIMESTAMP WHERE span_id IN ({placeholders})"  # noqa: S608
            conn.execute(query, span_ids)
            conn.commit()

        return {"exported": len(rows), "archived_to": archive_file}


class SpanRetentionManager:
    """
    Enforces retention policy across all tiers.
    Runs on schedule (e.g., daily). Prunes old spans, compacts SQLite.
    """

    RETENTION_POLICY = {
        "sqlite_spans": timedelta(days=14),  # Tier 1
        "compressed_archive": timedelta(days=90),  # Tier 2
        "daily_stats": None,  # Tier 3: indefinite
    }

    def __init__(self, db_path: str, archive_dir: str):
        self.db_path = db_path
        self.archive_dir = archive_dir

    def run_retention_cycle(self) -> dict:
        """Run full retention enforcement cycle. Returns summary."""
        summary = {
            "timestamp": datetime.now().isoformat(),
            "tier1_pruned": 0,
            "tier2_pruned": 0,
            "vacuum_size_before": 0,
            "vacuum_size_after": 0,
            "errors": [],
        }

        # Tier 1: Delete exported spans older than 14 days
        try:
            cutoff = datetime.now() - self.RETENTION_POLICY["sqlite_spans"]
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    DELETE FROM spans_buffer
                    WHERE exported = TRUE
                      AND exported_at < ?
                    """,
                    (cutoff,),
                )
                summary["tier1_pruned"] = cursor.rowcount
                conn.commit()
        except Exception as e:
            summary["errors"].append(f"Tier 1 prune failed: {e}")

        # Tier 2: Remove compressed archives older than 90 days
        try:
            import os
            import glob

            cutoff = datetime.now() - self.RETENTION_POLICY["compressed_archive"]
            for archive in glob.glob(f"{self.archive_dir}/spans_*.jsonl"):
                try:
                    stat = os.stat(archive)
                    mtime = datetime.fromtimestamp(stat.st_mtime)
                    if mtime < cutoff:
                        os.remove(archive)
                        summary["tier2_pruned"] += 1
                except Exception as e:
                    summary["errors"].append(f"Archive removal failed: {archive}: {e}")
        except Exception as e:
            summary["errors"].append(f"Tier 2 prune failed: {e}")

        # VACUUM: Compact SQLite
        try:
            # Get size before
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size()"
                )
                before = cursor.fetchone()[0]
                summary["vacuum_size_before"] = before

            # VACUUM INTO + atomic swap
            tmp_db = self.db_path + ".vacuumed"
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(f"VACUUM INTO '{tmp_db}'")

                import os

                os.replace(tmp_db, self.db_path)

                # Get size after
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute(
                        "SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size()"
                    )
                    after = cursor.fetchone()[0]
                    summary["vacuum_size_after"] = after
            except Exception as e:
                summary["errors"].append(f"VACUUM failed: {e}")
                if os.path.exists(tmp_db):
                    os.remove(tmp_db)

        except Exception as e:
            summary["errors"].append(f"VACUUM setup failed: {e}")

        # Tier 3: Aggregate daily stats (additive, no pruning)
        try:
            self._aggregate_daily_stats()
        except Exception as e:
            summary["errors"].append(f"Daily stats aggregation failed: {e}")

        return summary

    def _aggregate_daily_stats(self):
        """
        Compute daily aggregate statistics from raw spans.
        Store in daily_span_stats table for long-term trend analysis.
        """
        today = datetime.now().date()
        with sqlite3.connect(self.db_path) as conn:
            # Count spans by kind
            cursor = conn.execute(
                """
                SELECT span_kind, COUNT(*) FROM spans_buffer
                WHERE DATE(created_at) = ?
                GROUP BY span_kind
                """,
                (today,),
            )
            spans_by_kind = {row[0]: row[1] for row in cursor.fetchall()}

            # Count faults
            cursor = conn.execute(
                """
                SELECT COUNT(*) FROM spans_buffer
                WHERE DATE(created_at) = ? AND fault_flags IS NOT NULL
                """,
                (today,),
            )
            fault_count = cursor.fetchone()[0]

            # Upsert daily stats
            conn.execute(
                """
                INSERT OR REPLACE INTO daily_span_stats
                (date, total_spans, spans_by_kind, fault_counts)
                VALUES (?, ?, ?, ?)
                """,
                (
                    today,
                    len(spans_by_kind),
                    __import__("json").dumps(spans_by_kind),
                    fault_count,
                ),
            )
            conn.commit()

    def get_retention_status(self) -> dict:
        """Fetch current storage usage and retention status."""
        import os

        status = {}

        # Tier 1: SQLite size
        if os.path.exists(self.db_path):
            status["tier1_size_mb"] = os.path.getsize(self.db_path) / (1024 * 1024)

        # Tier 2: Compressed archives
        try:
            import glob

            archives = glob.glob(f"{self.archive_dir}/spans_*.jsonl")
            total_size = sum(os.path.getsize(a) for a in archives)
            status["tier2_size_mb"] = total_size / (1024 * 1024)
            status["tier2_count"] = len(archives)
        except Exception:
            status["tier2_size_mb"] = 0

        # Tier 3: Daily stats row count
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM daily_span_stats")
                status["tier3_rows"] = cursor.fetchone()[0]
        except Exception:
            status["tier3_rows"] = 0

        return status

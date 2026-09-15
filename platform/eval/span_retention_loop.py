#!/usr/bin/env python3
"""SpanRetention control loop: four-tier storage lifecycle.

Implements ControlLoop protocol.
Periodic job: runs daily, sweeps old spans, compacts SQLite, aggregates stats.
Out of request path entirely.
"""

from platform.eval.protocol import ControlLoop, GateDecision, LoopHealth
from platform.eval.span_retention import (
    HotSpanBuffer,
    SpanExporter,
    SpanRetentionManager,
)
from datetime import datetime
import os


class SpanRetentionLoop(ControlLoop):
    """
    SpanRetention as a ControlLoop.
    Manages four-tier storage: RAM → SQLite → Compressed → Stats.
    Runs periodically, out of request path.
    """

    name = "span_retention"

    def __init__(
        self,
        db_path: str = None,
        archive_dir: str = None,
    ):
        self.db_path = db_path or "/Users/chidionyema/dev/code/idp/state/queue.db"
        self.archive_dir = (
            archive_dir or "/Users/chidionyema/dev/code/idp/state/archives"
        )

        # Ensure archive dir exists
        os.makedirs(self.archive_dir, exist_ok=True)

        self.hot_buffer = HotSpanBuffer(maxlen=10000, flush_interval_ms=500)
        self.exporter = SpanExporter(
            db_path=self.db_path, archive_dir=self.archive_dir, batch_size=10000
        )
        self.retention_manager = SpanRetentionManager(
            db_path=self.db_path, archive_dir=self.archive_dir
        )

        self.last_run_at = None
        self.last_error = None
        self.mode = "off"  # Default off; enable via config

    def pre_llm(self, state: dict) -> GateDecision:
        """SpanRetention doesn't gate on pre_llm. Return allow."""
        return GateDecision(action="allow")

    def post_verdict(self, state: dict, verdict: dict) -> None:
        """
        SpanRetention doesn't listen to post_verdict.
        Out of request path; only periodic() runs.
        """
        pass

    def periodic(self) -> None:
        """
        Daily retention cycle:
        1. Export spans from buffer to archive
        2. Prune old spans and archives
        3. Compact SQLite (VACUUM INTO)
        4. Aggregate daily stats
        """
        self.last_run_at = datetime.now().isoformat()

        try:
            # Step 1: Export buffer to archive
            self.exporter.export_batch()

            # Step 2: Prune old spans, run retention policy
            self.retention_manager.run_retention_cycle()

            # Step 3: Report final storage status
            self.retention_manager.get_retention_status()

            # Success
            self.last_error = None

        except Exception as e:
            self.last_error = str(e)
            # Don't raise; periodic jobs never block

    def health(self) -> LoopHealth:
        """Report loop health and storage status."""
        storage_status = self.retention_manager.get_retention_status()
        health_msg = f"Tier1: {storage_status.get('tier1_size_mb', 0):.1f}MB, Tier2: {storage_status.get('tier2_size_mb', 0):.1f}MB"

        return LoopHealth(
            name=self.name,
            mode=self.mode,
            last_run_at=self.last_run_at or "never",
            last_error=self.last_error or f"Storage: {health_msg}",
            is_healthy=self.last_error is None or "Storage" in (self.last_error or ""),
        )

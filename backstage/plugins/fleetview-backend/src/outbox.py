"""SQLite WAL outbox for reliable NATS publish — events persist even when NATS is unreachable.

THE OUTBOX PATTERN. Every steer intent lands in SQLite first, returns 200 instantly, and a
background worker publishes to NATS when the bus is reachable. The intent is DURABLE: a process
restart, a NATS outage, a network blip — none of them lose an intent that made it into the buffer.

WHY NOT JUST PUBLISH? `nats_adapter.publish` is synchronous in the request path. If NATS is down
or slow, every request blocks. The outbox decouples the two: the endpoint writes to a local
SQLite database (WAL mode, so writes never block reads), returns instantly, and a background
asyncio task drains the buffer. The intent is in SQLite before the 200 leaves the wire.

BOUNDED RETRY WITH BACKOFF AND JITTER. A failed publish retries up to `MAX_RETRIES` times with
exponential backoff (capped at `MAX_BACKOFF_S`) plus random jitter (up to 25% of the delay).
After the cap, the row is marked `failed` and stays in the table for forensics. A 15-minute TTL
on JetStream means an intent older than that is not worth publishing anyway — but we keep the
row to know it existed.

CONFIG (LAW 46): OUTBOX_DB_PATH (default: ~/.estate/outbox.db), OUTBOX_POLL_INTERVAL_S (default:
0.5), NATS_URL (the bus itself).
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import random
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

from . import tracing

# Max retries before giving up on a row.
MAX_RETRIES = 5

# Backoff parameters.
BASE_BACKOFF_S = 0.5
MAX_BACKOFF_S = 30.0

# The 15-minute TTL on JetStream. An intent older than this is stale.
TTL_S = 15 * 60

# Poll interval for the background worker.
DEFAULT_POLL_INTERVAL_S = 0.5

_NATS_ADAPTER_MODULE = Path(__file__).resolve().parent / "nats_adapter.py"
_KAFKA_ADAPTER_MODULE = Path(__file__).resolve().parent / "kafka_adapter.py"


def _nats():
    """Load the NATS adapter module the same way voice_media.py does."""
    spec = importlib.util.spec_from_file_location(
        "fleetview_nats_adapter_impl", _NATS_ADAPTER_MODULE
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module at {_NATS_ADAPTER_MODULE}")
    cached = sys.modules.get("fleetview_nats_adapter_impl")
    if cached is not None:
        return cached
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _kafka():
    """Load the Kafka adapter module."""
    spec = importlib.util.spec_from_file_location(
        "fleetview_kafka_adapter_impl", _KAFKA_ADAPTER_MODULE
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module at {_KAFKA_ADAPTER_MODULE}")
    cached = sys.modules.get("fleetview_kafka_adapter_impl")
    if cached is not None:
        return cached
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _use_kafka() -> bool:
    """Check if Kafka is configured. KAFKA_BROKERS set means use Kafka, else NATS."""
    return bool(os.environ.get("KAFKA_BROKERS"))


def _db_path() -> Path:
    """The outbox database path. Defaults to ~/.estate/outbox.db."""
    path = os.environ.get("OUTBOX_DB_PATH")
    if path:
        return Path(path)
    home = Path.home() / ".estate"
    home.mkdir(parents=True, exist_ok=True)
    return home / "outbox.db"


def _init_db(con: sqlite3.Connection) -> None:
    """Create the outbox table if it does not exist."""
    con.execute("""
        CREATE TABLE IF NOT EXISTS outbox (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at REAL NOT NULL,
            session_id TEXT NOT NULL,
            runtime TEXT NOT NULL,
            kind TEXT NOT NULL,
            phase TEXT NOT NULL,
            payload TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            retries INTEGER NOT NULL DEFAULT 0,
            last_attempt_at REAL,
            next_attempt_at REAL,
            error TEXT
        )
    """)
    con.execute("""
        CREATE INDEX IF NOT EXISTS idx_outbox_status_next
        ON outbox(status, next_attempt_at)
    """)
    con.commit()


def _get_connection() -> sqlite3.Connection:
    """Get a connection to the outbox database with WAL mode enabled."""
    path = _db_path()
    con = sqlite3.connect(str(path), timeout=5.0)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.row_factory = sqlite3.Row
    _init_db(con)
    return con


def enqueue(
    session_id: str,
    runtime: str,
    kind: str,
    phase: str,
    payload: dict[str, Any],
) -> int:
    """Write an intent to the outbox. Returns the row id. Never blocks on NATS."""
    now = time.time()
    con = _get_connection()
    try:
        cursor = con.execute(
            """
            INSERT INTO outbox (created_at, session_id, runtime, kind, phase, payload, next_attempt_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (now, session_id, runtime, kind, phase, json.dumps(payload), now),
        )
        con.commit()
        return cursor.lastrowid or 0
    finally:
        con.close()


def _calculate_backoff(retries: int) -> float:
    """Exponential backoff with jitter. Returns seconds until next attempt."""
    delay = min(BASE_BACKOFF_S * (2**retries), MAX_BACKOFF_S)
    jitter = delay * random.uniform(0, 0.25)  # noqa: S311 — non-crypto jitter for backoff
    return delay + jitter


async def _publish_row(row: sqlite3.Row, nats_url: str) -> tuple[bool, str]:
    """Attempt to publish a single row to NATS or Kafka. Returns (success, error_message).

    Auto-detects which adapter to use based on KAFKA_BROKERS env var.
    Continues the trace from the original request if _trace_context was stored in the payload.
    """
    payload = json.loads(row["payload"])

    # Extract and continue the trace context from the original request.
    trace_ctx = payload.pop("_trace_context", None)
    ctx = tracing.extract_context(trace_ctx) if trace_ctx else None

    session_id = row["session_id"]
    runtime = row["runtime"]
    kind = row["kind"]
    subject = f"estate.agent.{runtime}.{session_id}.{kind}"

    with tracing.with_context(ctx):
        bus_type = "kafka" if _use_kafka() else "nats"
        with tracing.producer_span(
            f"voice.publish.{bus_type}",
            {
                "voice.session_id": session_id,
                "voice.kind": kind,
                "messaging.system": bus_type,
                "messaging.destination": subject,
            },
        ) as publish_span:
            try:
                if _use_kafka():
                    # Use Kafka adapter.
                    kafka_adapter = _kafka()
                    kafka_brokers = os.environ.get("KAFKA_BROKERS", "").split(",")
                    kafka_topic = os.environ.get(
                        "KAFKA_TOPIC", "fleetview.voice.events"
                    )

                    # Inject trace context into message headers for downstream consumers.
                    message_headers = tracing.get_current_trace_context()
                    payload["_trace_headers"] = message_headers

                    await kafka_adapter.publish(
                        kafka_brokers,
                        kafka_topic,
                        session_id=session_id,
                        runtime=runtime,
                        kind=kind,
                        phase=row["phase"],
                        **payload,
                    )
                else:
                    # Use NATS adapter.
                    nats_adapter = _nats()

                    # Inject trace context into message headers for downstream consumers.
                    message_headers = tracing.get_current_trace_context()
                    payload["_trace_headers"] = message_headers

                    await nats_adapter.publish(
                        nats_url,
                        session_id=session_id,
                        runtime=runtime,
                        kind=kind,
                        phase=row["phase"],
                        **payload,
                    )

                if publish_span:
                    publish_span.set_attribute("voice.publish.success", True)
                return True, ""
            except Exception as exc:  # noqa: BLE001 — error is recorded, not swallowed
                error_msg = f"{exc.__class__.__name__}: {exc}"
                if publish_span:
                    publish_span.set_attribute("voice.publish.success", False)
                    publish_span.set_attribute("voice.publish.error", error_msg)
                return False, error_msg


def _mark_published(con: sqlite3.Connection, row_id: int) -> None:
    """Mark a row as successfully published."""
    con.execute(
        "UPDATE outbox SET status = 'published', last_attempt_at = ? WHERE id = ?",
        (time.time(), row_id),
    )
    con.commit()


def _mark_failed(con: sqlite3.Connection, row_id: int, error: str) -> None:
    """Mark a row as permanently failed (max retries exceeded)."""
    con.execute(
        "UPDATE outbox SET status = 'failed', last_attempt_at = ?, error = ? WHERE id = ?",
        (time.time(), error, row_id),
    )
    con.commit()


def _mark_retry(con: sqlite3.Connection, row_id: int, retries: int, error: str) -> None:
    """Schedule a row for retry with exponential backoff."""
    now = time.time()
    next_attempt = now + _calculate_backoff(retries)
    con.execute(
        """
        UPDATE outbox
        SET retries = ?, last_attempt_at = ?, next_attempt_at = ?, error = ?
        WHERE id = ?
        """,
        (retries, now, next_attempt, error, row_id),
    )
    con.commit()


async def drain_once(nats_url: str) -> int:
    """Process all pending rows that are due. Returns the number of rows processed."""
    now = time.time()
    con = _get_connection()
    processed = 0

    with tracing.span(
        "voice.outbox.drain",
        {"voice.outbox.poll_time": now},
    ) as drain_span:
        try:
            rows = con.execute(
                """
                SELECT * FROM outbox
                WHERE status = 'pending' AND next_attempt_at <= ?
                ORDER BY created_at ASC
                LIMIT 100
                """,
                (now,),
            ).fetchall()

            if drain_span:
                drain_span.set_attribute("voice.outbox.pending_count", len(rows))

            for row in rows:
                row_id = row["id"]
                created_at = row["created_at"]
                retries = row["retries"]

                # Check TTL — an intent older than 15 minutes is stale.
                if now - created_at > TTL_S:
                    _mark_failed(con, row_id, "TTL exceeded: intent too old to publish")
                    processed += 1
                    continue

                success, error = await _publish_row(row, nats_url)
                if success:
                    _mark_published(con, row_id)
                elif retries + 1 >= MAX_RETRIES:
                    _mark_failed(con, row_id, f"max retries exceeded: {error}")
                else:
                    _mark_retry(con, row_id, retries + 1, error)
                processed += 1

            if drain_span:
                drain_span.set_attribute("voice.outbox.processed_count", processed)

            return processed
        finally:
            con.close()


class OutboxWorker:
    """Background worker that drains the outbox to NATS.

    Usage:
        worker = OutboxWorker()
        await worker.start()  # runs until stop() is called
        await worker.stop()
    """

    def __init__(self, nats_url: str | None = None):
        self._nats_url = nats_url or os.environ.get("NATS_URL", "")
        self._poll_interval = float(
            os.environ.get("OUTBOX_POLL_INTERVAL_S", DEFAULT_POLL_INTERVAL_S)
        )
        self._running = False
        self._task: asyncio.Task | None = None

    async def _run(self) -> None:
        """The drain loop. Runs until _running is False."""
        while self._running:
            if self._nats_url:
                try:
                    await drain_once(self._nats_url)
                except Exception:  # noqa: BLE001, S110 — loop must not die on transient errors
                    pass
            await asyncio.sleep(self._poll_interval)

    async def start(self) -> None:
        """Start the background drain loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        """Stop the background drain loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None


# Module-level worker instance for the FastAPI lifespan.
_worker: OutboxWorker | None = None


async def start_worker(nats_url: str | None = None) -> None:
    """Start the global outbox worker. Call from FastAPI startup."""
    global _worker
    if _worker is None:
        _worker = OutboxWorker(nats_url)
    await _worker.start()


async def stop_worker() -> None:
    """Stop the global outbox worker. Call from FastAPI shutdown."""
    global _worker
    if _worker:
        await _worker.stop()
        _worker = None


def pending_count() -> int:
    """Return the number of pending rows in the outbox."""
    con = _get_connection()
    try:
        row = con.execute(
            "SELECT COUNT(*) FROM outbox WHERE status = 'pending'"
        ).fetchone()
        return row[0] if row else 0
    finally:
        con.close()


def recent(limit: int = 50) -> list[dict[str, Any]]:
    """Return the most recent outbox entries for debugging."""
    con = _get_connection()
    try:
        rows = con.execute(
            """
            SELECT id, created_at, session_id, runtime, kind, phase, status, retries, error
            FROM outbox
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        con.close()

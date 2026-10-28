"""The Postgres store: the same contract as the SQLite store, on the estate's own database.

WHY A SECOND STORE IMPLEMENTATION, AND WHY IT IS NOT A SECOND LAYER. The delivered reference build
ships SQLite because it had to run with the standard library alone. The estate already runs
Postgres (estate-db) and the placement decision (0034) says a small database that belongs to the
estate goes on estate-db rather than on the node as a new stateful workload with its own volume.
This module is the SAME store contract -- append / events / runs / evaluate -- over Postgres, so
the collector in OKE keeps one canonical long-term backend instead of a SQLite file on a node
volume that a restart would lose. The SQLite store remains the laptop's offline spool.

The contract that must not drift: an event_id is written once. A repeat append with the same
event_id and the same payload is a no-op; the same event_id with a DIFFERENT payload is an error.
That is what makes the ledger append-only and idempotent, and it is enforced here exactly as the
SQLite store enforces it.
"""

from __future__ import annotations

import hashlib
import json
import threading
import uuid
from typing import Any

from .core import utc_now, validate

SCHEMA = """
CREATE TABLE IF NOT EXISTS aei_events (
    seq BIGSERIAL PRIMARY KEY,
    event_id TEXT UNIQUE NOT NULL,
    run_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    trace_id TEXT NOT NULL,
    event_time TIMESTAMPTZ NOT NULL,
    event_type TEXT NOT NULL,
    payload TEXT NOT NULL,
    digest TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_aei_events_run ON aei_events(run_id, seq);
CREATE INDEX IF NOT EXISTS idx_aei_events_task ON aei_events(task_id, seq);
CREATE TABLE IF NOT EXISTS aei_evaluations (
    evaluation_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    evaluator_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    payload TEXT NOT NULL
);
"""


class PostgresStore:
    """The estate's Postgres store for AEI. Same surface as core.Store."""

    def __init__(self, dsn: str):
        import psycopg  # imported here so the SQLite path needs no driver

        self.dsn = dsn
        self.lock = threading.RLock()
        self.db = psycopg.connect(dsn, autocommit=True)
        with self.db.cursor() as cur:
            cur.execute(SCHEMA)

    def append(self, event: dict[str, Any]) -> dict[str, Any]:
        validate(event)
        body = json.dumps(
            event, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        digest = hashlib.sha256(body.encode()).hexdigest()
        with self.lock:
            with self.db.cursor() as cur:
                cur.execute(
                    "INSERT INTO aei_events(event_id,run_id,task_id,trace_id,event_time,event_type,payload,digest)"
                    " VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (event_id) DO NOTHING RETURNING seq",
                    (
                        event["event_id"],
                        event["run_id"],
                        event["task_id"],
                        event["trace_id"],
                        event["timestamp"],
                        event["type"],
                        body,
                        digest,
                    ),
                )
                row = cur.fetchone()
                if row is not None:
                    return {"accepted": True, "seq": row[0], "digest": digest}
                cur.execute(
                    "SELECT seq,digest FROM aei_events WHERE event_id=%s",
                    (event["event_id"],),
                )
                existing = cur.fetchone()
        if existing is None:
            raise ValueError("event_id reused with different payload")
        if existing[1] != digest:
            raise ValueError("event_id reused with different payload")
        return {
            "accepted": False,
            "seq": existing[0],
            "digest": digest,
            "duplicate": True,
        }

    def events(self, run_id: str, limit: int = 10000) -> list[dict[str, Any]]:
        with self.lock:
            with self.db.cursor() as cur:
                cur.execute(
                    "SELECT seq,payload,digest FROM aei_events WHERE run_id=%s ORDER BY seq LIMIT %s",
                    (run_id, min(max(int(limit), 1), 10000)),
                )
                rows = cur.fetchall()
        return [
            dict(json.loads(payload), seq=seq, digest=digest)
            for seq, payload, digest in rows
        ]

    def runs(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.lock:
            with self.db.cursor() as cur:
                cur.execute(
                    "SELECT run_id,MIN(event_time),MAX(event_time),COUNT(*),MAX(task_id)"
                    " FROM aei_events GROUP BY run_id ORDER BY MAX(seq) DESC LIMIT %s",
                    (min(max(int(limit), 1), 500),),
                )
                rows = cur.fetchall()
        return [
            dict(
                run_id=r[0],
                first_seen=r[1].isoformat(),
                last_seen=r[2].isoformat(),
                events=r[3],
                task_id=r[4],
            )
            for r in rows
        ]

    def evaluate(
        self, run_id: str, evaluator_version: str, payload: dict[str, Any]
    ) -> str:
        eid = str(uuid.uuid4())
        with self.lock:
            with self.db.cursor() as cur:
                cur.execute(
                    "INSERT INTO aei_evaluations(evaluation_id,run_id,evaluator_version,created_at,payload)"
                    " VALUES (%s,%s,%s,%s,%s)",
                    (
                        eid,
                        run_id,
                        evaluator_version,
                        utc_now(),
                        json.dumps(payload, sort_keys=True),
                    ),
                )
        return eid

    def close(self) -> None:
        self.db.close()

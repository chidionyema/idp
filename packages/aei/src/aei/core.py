"""Schema, privacy boundaries, and append-only SQLite evidence storage."""

from __future__ import annotations
import hashlib
import json
import re
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = "aei.event.v1"
FAMILIES = frozenset(
    """task.created task.started task.completed task.failed context.assembled context.retrieved context.compacted decision.proposed decision.selected decision.revised model.requested model.first_token model.completed model.failed tool.started tool.completed tool.failed hypothesis.registered hypothesis.tested hypothesis.rejected retry.started recovery.completed verification.started verification.passed verification.failed human.intervention approval.requested approval.received""".split()
)
SECRET = re.compile(
    r"(?i)(?:sk-[a-z0-9_-]{12,}|gh[pousr]_[a-z0-9]{12,}|bearer\s+[^\s]+|(?:password|api[_-]?key|token|secret)\s*[=:]\s*[^\s,;}]+)"
)
SAFE_ATTRS = frozenset(
    "model provider lane tool_name tool_kind status outcome reason_code artifact_class tier verifier result_code retry_reason queue_ms latency_ms duration_ms input_tokens output_tokens cache_read_tokens cost_usd bytes_in bytes_out source_path source_line source_sha source_revision http_status attempts error_type metric_unit evidence_grade config_id phase target_component model_group deployment_model total_tokens".split()
)
IDENTIFIERS = ("run_id", "task_id", "agent_id", "harness_id", "trace_id", "revision")
TERMINAL = frozenset(("task.completed", "task.failed"))


def utc_now():
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def scrub(value):
    """Only allowlisted scalar attributes are retained; strings are secret-redacted."""
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return SECRET.sub("[REDACTED]", value[:512])
    return None


def validate(event):
    if not isinstance(event, dict) or event.get("schema") != SCHEMA_VERSION:
        raise ValueError("unsupported event schema")
    if event.get("type") not in FAMILIES:
        raise ValueError("unknown event type")
    for key in IDENTIFIERS:
        if (
            not isinstance(event.get(key), str)
            or not event[key].strip()
            or len(event[key]) > 200
        ):
            raise ValueError(f"missing/invalid {key}")
    if not isinstance(event.get("event_id"), str) or not event["event_id"]:
        raise ValueError("event_id required")
    if not isinstance(event.get("timestamp"), str) or not event["timestamp"].endswith(
        "Z"
    ):
        raise ValueError("UTC timestamp required")
    try:
        datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid timestamp") from exc
    if not isinstance(event.get("attempt"), int) or event["attempt"] < 1:
        raise ValueError("attempt must be positive")
    if event.get("parent_id") is not None and not isinstance(event["parent_id"], str):
        raise ValueError("invalid parent_id")
    attrs = event.get("attributes", {})
    if not isinstance(attrs, dict) or len(attrs) > 64:
        raise ValueError("attributes must be a bounded object")
    if set(attrs) - SAFE_ATTRS:
        raise ValueError("unclassified attributes are prohibited")
    for k, v in attrs.items():
        if not (v is None or isinstance(v, (str, int, float, bool))):
            raise ValueError(f"non-scalar attribute {k}")
        if isinstance(v, str) and (len(v) > 512 or SECRET.search(v)):
            raise ValueError("unredacted secret or oversized attribute")
    return event


def make_event(
    event_type,
    *,
    run_id,
    task_id,
    agent_id,
    harness_id,
    trace_id,
    revision,
    parent_id=None,
    attempt=1,
    attributes=None,
    timestamp=None,
    event_id=None,
):
    attrs = {k: scrub(v) for k, v in (attributes or {}).items() if k in SAFE_ATTRS}
    event = dict(
        schema=SCHEMA_VERSION,
        event_id=event_id or str(uuid.uuid4()),
        type=event_type,
        timestamp=timestamp or utc_now(),
        run_id=run_id,
        task_id=task_id,
        agent_id=agent_id,
        harness_id=harness_id,
        trace_id=trace_id,
        revision=revision,
        parent_id=parent_id,
        attempt=attempt,
        attributes=attrs,
    )
    return validate(event)


class Store:
    def __init__(self, path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(self.path, check_same_thread=False, timeout=5)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA busy_timeout=5000")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT UNIQUE NOT NULL,
              run_id TEXT NOT NULL, task_id TEXT NOT NULL, trace_id TEXT NOT NULL, timestamp TEXT NOT NULL,
              event_type TEXT NOT NULL, payload TEXT NOT NULL, digest TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_events_run ON events(run_id,seq);
            CREATE INDEX IF NOT EXISTS idx_events_task ON events(task_id,seq);
            CREATE TABLE IF NOT EXISTS evaluations (evaluation_id TEXT PRIMARY KEY, run_id TEXT NOT NULL,
              evaluator_version TEXT NOT NULL, created_at TEXT NOT NULL, payload TEXT NOT NULL);
        """)
        self.db.commit()

    def append(self, event):
        validate(event)
        body = json.dumps(
            event, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        digest = hashlib.sha256(body.encode()).hexdigest()
        with self.lock:
            try:
                cur = self.db.execute(
                    "INSERT INTO events(event_id,run_id,task_id,trace_id,timestamp,event_type,payload,digest) VALUES (?,?,?,?,?,?,?,?)",
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
                self.db.commit()
                return {"accepted": True, "seq": cur.lastrowid, "digest": digest}
            except sqlite3.IntegrityError:
                row = self.db.execute(
                    "SELECT seq,digest FROM events WHERE event_id=?",
                    (event["event_id"],),
                ).fetchone()
                if row[1] != digest:
                    raise ValueError("event_id reused with different payload") from None
                return {
                    "accepted": False,
                    "seq": row[0],
                    "digest": digest,
                    "duplicate": True,
                }

    def events(self, run_id, limit=10000):
        with self.lock:
            rows = self.db.execute(
                "SELECT seq,payload,digest FROM events WHERE run_id=? ORDER BY seq LIMIT ?",
                (run_id, min(max(int(limit), 1), 10000)),
            ).fetchall()
        return [
            dict(json.loads(payload), seq=seq, digest=digest)
            for seq, payload, digest in rows
        ]

    def runs(self, limit=100):
        with self.lock:
            rows = self.db.execute(
                "SELECT run_id,MIN(timestamp),MAX(timestamp),COUNT(*),MAX(task_id) FROM events GROUP BY run_id ORDER BY MAX(seq) DESC LIMIT ?",
                (min(max(int(limit), 1), 500),),
            ).fetchall()
        return [
            dict(
                run_id=r[0], first_seen=r[1], last_seen=r[2], events=r[3], task_id=r[4]
            )
            for r in rows
        ]

    def evaluate(self, run_id, evaluator_version, payload):
        eid = str(uuid.uuid4())
        with self.lock:
            self.db.execute(
                "INSERT INTO evaluations VALUES (?,?,?,?,?)",
                (
                    eid,
                    run_id,
                    evaluator_version,
                    utc_now(),
                    json.dumps(payload, sort_keys=True),
                ),
            )
            self.db.commit()
        return eid

    def close(self):
        self.db.close()

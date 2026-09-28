"""Transcript and span schema for parallel agent layer telemetry."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import sqlite3
import os


class SpanKind(str, Enum):
    AGENT = "agent"
    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"
    PLANNING = "planning"
    REASONING = "reasoning"
    RETRIEVAL = "retrieval"
    GUARD_RAIL = "guard_rail"
    DELEGATION = "delegation"
    MEMORY = "memory"


@dataclass
class Transcript:
    id: str
    task_id: str
    agent_instance: str
    model_id: str
    model_tier: str
    total_turns: int
    cost: float
    loop_detected: bool
    circuit_breaker_tripped: bool
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TranscriptSpan:
    span_id: str
    transcript_id: str
    span_kind: SpanKind
    sequence_num: int
    content: str
    args_hash: Optional[str] = None
    result_hash: Optional[str] = None
    parent_span_id: Optional[str] = None
    fault_flags: str = ""
    eval_scores: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)


TRANSCRIPT_SCHEMA = """
CREATE TABLE IF NOT EXISTS transcripts (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    agent_instance TEXT NOT NULL,
    model_id TEXT NOT NULL,
    model_tier TEXT NOT NULL,
    total_turns INTEGER NOT NULL,
    cost REAL NOT NULL,
    loop_detected BOOLEAN NOT NULL DEFAULT 0,
    circuit_breaker_tripped BOOLEAN NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_transcripts_task_id ON transcripts(task_id);
CREATE INDEX IF NOT EXISTS idx_transcripts_agent_instance ON transcripts(agent_instance);
CREATE INDEX IF NOT EXISTS idx_transcripts_created_at ON transcripts(created_at);
"""

TRANSCRIPT_SPANS_SCHEMA = """
CREATE TABLE IF NOT EXISTS transcript_spans (
    span_id TEXT PRIMARY KEY,
    transcript_id TEXT NOT NULL,
    parent_span_id TEXT,
    span_kind TEXT NOT NULL,
    sequence_num INTEGER NOT NULL,
    content TEXT NOT NULL,
    args_hash TEXT,
    result_hash TEXT,
    fault_flags TEXT DEFAULT '',
    eval_scores TEXT DEFAULT '',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (transcript_id) REFERENCES transcripts(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_span_id) REFERENCES transcript_spans(span_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_spans_transcript_id ON transcript_spans(transcript_id);
CREATE INDEX IF NOT EXISTS idx_spans_parent_span_id ON transcript_spans(parent_span_id);
CREATE INDEX IF NOT EXISTS idx_spans_span_kind ON transcript_spans(span_kind);
CREATE INDEX IF NOT EXISTS idx_spans_sequence ON transcript_spans(transcript_id, sequence_num);
"""


def init_schema(db_path: str = None) -> sqlite3.Connection:
    """Initialize transcript schema. Returns connection."""
    if db_path is None:
        db_path = os.path.expanduser("~/.pi/agent/telemetry/transcripts.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")

    for statement in TRANSCRIPT_SCHEMA.strip().split(";"):
        if statement.strip():
            conn.execute(statement)

    for statement in TRANSCRIPT_SPANS_SCHEMA.strip().split(";"):
        if statement.strip():
            conn.execute(statement)

    conn.commit()
    return conn

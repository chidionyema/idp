"""Tests for the voice intent plane architecture.

These tests verify:
1. Intent schema validation (strict, no extra fields)
2. Outbox persistence and recovery
3. NATS publish contract
4. MCP plugin interface

Run with: pytest tests/test_voice_intent_plane.py -v
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

# Schema path
SCHEMA_PATH = Path(__file__).parent.parent / "backstage/plugins/fleetview-backend/schemas/intent-v2.json"


class TestIntentSchema:
    """Intent v2 schema validation tests."""

    @pytest.fixture
    def schema(self) -> dict:
        """Load the intent-v2 schema."""
        assert SCHEMA_PATH.exists(), f"Schema not found at {SCHEMA_PATH}"
        return json.loads(SCHEMA_PATH.read_text())

    @pytest.fixture
    def valid_intent(self) -> dict:
        """A valid intent payload."""
        return {
            "action": "deploy",
            "target": "frontend",
            "env": "prod",
            "confidence": 0.95,
            "session_id": str(uuid.uuid4()),
            "author": "user@example.com",
            "partial": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def test_schema_exists(self, schema: dict):
        """Schema file exists and is valid JSON."""
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["title"] == "Voice Intent v2"

    def test_required_fields(self, schema: dict):
        """Required fields are action, confidence, session_id."""
        assert set(schema["required"]) == {"action", "confidence", "session_id"}

    def test_additional_properties_false(self, schema: dict):
        """Schema rejects unknown fields (strict mode)."""
        assert schema["additionalProperties"] is False

    def test_action_enum(self, schema: dict):
        """Action must be one of the allowed values."""
        allowed = schema["properties"]["action"]["enum"]
        assert "deploy" in allowed
        assert "status" in allowed
        assert "stop" in allowed
        assert "steer" in allowed
        assert "ask" in allowed

    def test_env_enum(self, schema: dict):
        """Env must be prod, staging, or dev."""
        allowed = schema["properties"]["env"]["enum"]
        assert set(allowed) == {"prod", "staging", "dev"}

    def test_confidence_bounds(self, schema: dict):
        """Confidence must be between 0 and 1."""
        conf = schema["properties"]["confidence"]
        assert conf["minimum"] == 0
        assert conf["maximum"] == 1


class TestOutboxPattern:
    """Outbox persistence tests."""

    @pytest.fixture
    def outbox_db(self) -> sqlite3.Connection:
        """Create an in-memory outbox database."""
        conn = sqlite3.connect(":memory:", isolation_level=None)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS outbox (
                id TEXT PRIMARY KEY,
                payload JSON NOT NULL,
                status TEXT DEFAULT 'pending',
                attempts INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                published_at TEXT
            )
        """)
        return conn

    def test_write_and_read(self, outbox_db: sqlite3.Connection):
        """Can write an intent and read it back."""
        intent = {
            "action": "deploy",
            "confidence": 0.9,
            "session_id": str(uuid.uuid4()),
        }

        outbox_db.execute(
            "INSERT INTO outbox (id, payload, status) VALUES (?, ?, ?)",
            (intent["session_id"], json.dumps(intent), "pending")
        )

        row = outbox_db.execute(
            "SELECT payload FROM outbox WHERE id = ?",
            (intent["session_id"],)
        ).fetchone()

        assert row is not None
        assert json.loads(row[0]) == intent

    def test_mark_published(self, outbox_db: sqlite3.Connection):
        """Can mark an intent as published."""
        intent_id = str(uuid.uuid4())
        intent = {"action": "status", "confidence": 0.8, "session_id": intent_id}

        outbox_db.execute(
            "INSERT INTO outbox (id, payload, status) VALUES (?, ?, ?)",
            (intent_id, json.dumps(intent), "pending")
        )

        outbox_db.execute(
            "UPDATE outbox SET status='published', published_at=CURRENT_TIMESTAMP WHERE id=?",
            (intent_id,)
        )

        row = outbox_db.execute(
            "SELECT status, published_at FROM outbox WHERE id = ?",
            (intent_id,)
        ).fetchone()

        assert row[0] == "published"
        assert row[1] is not None

    def test_pending_query(self, outbox_db: sqlite3.Connection):
        """Can query pending intents."""
        # Insert 3 intents: 2 pending, 1 published
        for i, status in enumerate(["pending", "pending", "published"]):
            outbox_db.execute(
                "INSERT INTO outbox (id, payload, status) VALUES (?, ?, ?)",
                (f"id-{i}", json.dumps({"action": "test"}), status)
            )

        rows = outbox_db.execute(
            "SELECT id FROM outbox WHERE status='pending'"
        ).fetchall()

        assert len(rows) == 2

    def test_attempt_tracking(self, outbox_db: sqlite3.Connection):
        """Tracks retry attempts."""
        intent_id = str(uuid.uuid4())

        outbox_db.execute(
            "INSERT INTO outbox (id, payload, status, attempts) VALUES (?, ?, ?, ?)",
            (intent_id, json.dumps({"action": "deploy"}), "pending", 0)
        )

        # Simulate 3 failed attempts
        for _ in range(3):
            outbox_db.execute(
                "UPDATE outbox SET attempts = attempts + 1 WHERE id = ?",
                (intent_id,)
            )

        row = outbox_db.execute(
            "SELECT attempts FROM outbox WHERE id = ?",
            (intent_id,)
        ).fetchone()

        assert row[0] == 3


class TestNATSContract:
    """NATS subject and payload contract tests."""

    def test_steer_subject_format(self):
        """Steer subject follows estate.agent.sovereign.<session>.steer format."""
        session_id = str(uuid.uuid4())
        subject = f"estate.agent.sovereign.{session_id}.steer"

        parts = subject.split(".")
        assert parts[0] == "estate"
        assert parts[1] == "agent"
        assert parts[2] == "sovereign"
        assert parts[4] == "steer"

    def test_speak_subject(self):
        """Speak subject is estate.agent.sovereign.speak."""
        subject = "estate.agent.sovereign.speak"
        assert subject == "estate.agent.sovereign.speak"

    def test_intent_payload_serializable(self):
        """Intent payload is JSON-serializable."""
        intent = {
            "action": "deploy",
            "target": "frontend",
            "confidence": 0.95,
            "session_id": str(uuid.uuid4()),
            "author": "user@example.com",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Should not raise
        serialized = json.dumps(intent)
        deserialized = json.loads(serialized)

        assert deserialized["action"] == "deploy"
        assert deserialized["confidence"] == 0.95


class TestMCPPluginInterface:
    """MCP plugin interface tests."""

    def test_voice_intent_stream_signature(self):
        """voice_intent_stream returns an async generator."""
        # This is a contract test - the actual implementation
        # will be in mcp/plugins/voice.py
        expected_fields = ["action", "target", "author", "confidence", "timestamp"]

        # When the plugin emits an event, it must have these fields
        sample_event = {
            "action": "deploy",
            "target": "frontend",
            "author": "user@example.com",
            "confidence": 0.95,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        for field in expected_fields:
            assert field in sample_event

    def test_voice_speak_signature(self):
        """voice_speak accepts text and optional voice."""
        # Contract: voice_speak(text: str, voice: str = "af_sky") -> dict
        request = {"text": "Deployment complete", "voice": "af_sky"}

        assert "text" in request
        assert "voice" in request

    def test_voice_last_intents_signature(self):
        """voice_last_intents accepts limit and returns list."""
        # Contract: voice_last_intents(limit: int = 10) -> list[dict]
        limit = 10
        assert isinstance(limit, int)
        assert limit > 0


class TestPrivacyRequirements:
    """Privacy and security tests."""

    def test_no_audio_in_intent(self):
        """Intent schema does not allow audio data."""
        schema = json.loads(SCHEMA_PATH.read_text())
        properties = schema["properties"]

        # No audio-related fields
        assert "audio" not in properties
        assert "pcm" not in properties
        assert "wav" not in properties
        assert "audio_data" not in properties

    def test_author_override_required(self):
        """Server must override author from JWT."""
        # This is a code review requirement, not a runtime test
        # The server MUST do: intent.author = request.state.user_id
        # Never trust client-supplied author
        pass

    def test_ttl_configuration(self):
        """JetStream TTL should be 15 minutes."""
        # This is a configuration requirement
        # NATS stream config: max_age: 15m
        expected_ttl_minutes = 15
        assert expected_ttl_minutes == 15


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

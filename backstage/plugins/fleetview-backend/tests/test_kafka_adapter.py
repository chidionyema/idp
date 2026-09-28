"""FleetView CP6: Kafka adapter unit tests.

Uses mock aiokafka (no live Kafka required) following the same pattern as
test_trace.py uses for its stub Langfuse client.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

REPO = Path(__file__).resolve().parents[4]
KAFKA_MODULE = (
    REPO / "backstage" / "plugins" / "fleetview-backend" / "src" / "kafka_adapter.py"
)


def _load(path: Path, name: str):
    """Load module from path, avoiding caching issues in tests."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def kafka_module(monkeypatch):
    """Load kafka_adapter with env vars set."""
    monkeypatch.setenv("KAFKA_BROKERS", "kafka1:9092,kafka2:9092")
    monkeypatch.setenv("KAFKA_TOPIC", "test.events")
    monkeypatch.setenv("KAFKA_ENABLE_IDEMPOTENCE", "true")
    return _load(KAFKA_MODULE, "kafka_adapter_under_test")


def _make_mock_aiokafka():
    """Create a mock aiokafka module with AIOKafkaProducer."""
    mock_producer_instance = AsyncMock()

    # Mock send_and_wait to return a RecordMetadata-like object.
    mock_result = MagicMock()
    mock_result.topic = "test.events"
    mock_result.partition = 0
    mock_result.offset = 42
    mock_result.timestamp = 1695312000000
    mock_producer_instance.send_and_wait = AsyncMock(return_value=mock_result)
    mock_producer_instance.start = AsyncMock()
    mock_producer_instance.stop = AsyncMock()

    mock_producer_class = MagicMock(return_value=mock_producer_instance)

    mock_module = MagicMock()
    mock_module.AIOKafkaProducer = mock_producer_class

    return mock_module, mock_producer_class, mock_producer_instance


# ---------------------------------------------------------------------------
# Config guard tests
# ---------------------------------------------------------------------------


def test_no_aiokafka_raises_runtime_error(monkeypatch):
    """Fail loudly when aiokafka is not installed."""
    monkeypatch.setenv("KAFKA_BROKERS", "kafka:9092")
    # Remove aiokafka from sys.modules if present.
    monkeypatch.delitem(sys.modules, "aiokafka", raising=False)

    mod = _load(KAFKA_MODULE, "kafka_adapter_no_aiokafka")

    # Patch import to fail.
    original_import = (
        __builtins__["__import__"]
        if isinstance(__builtins__, dict)
        else __builtins__.__import__
    )

    def mock_import(name, *args, **kwargs):
        if name == "aiokafka":
            raise ImportError("No module named 'aiokafka'")
        return original_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=mock_import):
        with pytest.raises(RuntimeError, match="aiokafka not installed"):
            mod._require_aiokafka()


def test_is_kafka_configured_true_when_brokers_set(monkeypatch):
    """is_kafka_configured returns True when KAFKA_BROKERS is set."""
    monkeypatch.setenv("KAFKA_BROKERS", "kafka:9092")
    mod = _load(KAFKA_MODULE, "kafka_adapter_configured")
    assert mod.is_kafka_configured() is True


def test_is_kafka_configured_false_when_brokers_empty(monkeypatch):
    """is_kafka_configured returns False when KAFKA_BROKERS is not set."""
    monkeypatch.delenv("KAFKA_BROKERS", raising=False)
    mod = _load(KAFKA_MODULE, "kafka_adapter_not_configured")
    assert mod.is_kafka_configured() is False


# ---------------------------------------------------------------------------
# Publish tests
# ---------------------------------------------------------------------------


def test_publish_sends_event_to_kafka(kafka_module, monkeypatch):
    """publish() sends JSON event to Kafka with correct key and value."""
    mock_module, mock_producer_class, mock_producer = _make_mock_aiokafka()

    # Inject mock aiokafka.
    monkeypatch.setitem(sys.modules, "aiokafka", mock_module)

    # Reset the module's producer pool.
    kafka_module._producer = None
    kafka_module._producer_brokers = []

    async def run_test():
        result = await kafka_module.publish(
            kafka_brokers=["kafka1:9092", "kafka2:9092"],
            topic="test.events",
            session_id="sess-123",
            runtime="voice",
            kind="phase",
            phase="hearing",
            transcript="Hello world",
        )
        return result

    result = asyncio.get_event_loop().run_until_complete(run_test())

    # Verify producer was created with correct config.
    assert mock_producer_class.called
    call_kwargs = mock_producer_class.call_args[1]
    assert call_kwargs["bootstrap_servers"] == "kafka1:9092,kafka2:9092"
    assert call_kwargs["enable_idempotence"] is True

    # Verify send_and_wait was called.
    assert mock_producer.send_and_wait.called
    call_args = mock_producer.send_and_wait.call_args
    assert call_args[0][0] == "test.events"  # topic
    assert call_args[1]["key"] == b"sess-123"  # session_id as key

    # Verify the value is valid JSON with expected fields.
    value = call_args[1]["value"]
    event = json.loads(value)
    assert event["session_id"] == "sess-123"
    assert event["runtime"] == "voice"
    assert event["kind"] == "phase"
    assert event["phase"] == "hearing"
    assert event["transcript"] == "Hello world"
    assert "at" in event  # timestamp

    # Verify return value.
    assert result["topic"] == "test.events"
    assert result["partition"] == 0
    assert result["offset"] == 42
    assert result["published"] is True


def test_publish_empty_brokers_raises_value_error(kafka_module, monkeypatch):
    """publish() raises ValueError when kafka_brokers is empty."""

    async def run_test():
        await kafka_module.publish(
            kafka_brokers=[],
            topic="test.events",
            session_id="sess-123",
            runtime="voice",
            kind="phase",
            phase="hearing",
        )

    with pytest.raises(ValueError, match="kafka_brokers cannot be empty"):
        asyncio.get_event_loop().run_until_complete(run_test())


def test_producer_reused_across_calls(kafka_module, monkeypatch):
    """Producer is reused (connection pooling) across publish calls."""
    mock_module, mock_producer_class, mock_producer = _make_mock_aiokafka()
    monkeypatch.setitem(sys.modules, "aiokafka", mock_module)

    # Reset the module's producer pool.
    kafka_module._producer = None
    kafka_module._producer_brokers = []

    async def run_test():
        # First publish.
        await kafka_module.publish(
            kafka_brokers=["kafka:9092"],
            topic="test.events",
            session_id="sess-1",
            runtime="voice",
            kind="phase",
            phase="hearing",
        )

        first_call_count = mock_producer_class.call_count

        # Second publish with same brokers.
        await kafka_module.publish(
            kafka_brokers=["kafka:9092"],
            topic="test.events",
            session_id="sess-2",
            runtime="voice",
            kind="phase",
            phase="hearing",
        )

        return first_call_count

    first_call_count = asyncio.get_event_loop().run_until_complete(run_test())

    # Producer should not be recreated.
    assert mock_producer_class.call_count == first_call_count


def test_producer_recreated_when_brokers_change(kafka_module, monkeypatch):
    """Producer is recreated when brokers change."""
    mock_module, mock_producer_class, mock_producer = _make_mock_aiokafka()
    monkeypatch.setitem(sys.modules, "aiokafka", mock_module)

    # Reset the module's producer pool.
    kafka_module._producer = None
    kafka_module._producer_brokers = []

    async def run_test():
        # First publish with brokers A.
        await kafka_module.publish(
            kafka_brokers=["kafka-a:9092"],
            topic="test.events",
            session_id="sess-1",
            runtime="voice",
            kind="phase",
            phase="hearing",
        )

        first_call_count = mock_producer_class.call_count

        # Second publish with different brokers.
        await kafka_module.publish(
            kafka_brokers=["kafka-b:9092"],
            topic="test.events",
            session_id="sess-2",
            runtime="voice",
            kind="phase",
            phase="hearing",
        )

        return first_call_count

    first_call_count = asyncio.get_event_loop().run_until_complete(run_test())

    # Producer should be recreated.
    assert mock_producer_class.call_count == first_call_count + 1
    # Old producer should be stopped.
    assert mock_producer.stop.called


# ---------------------------------------------------------------------------
# Batch publish tests
# ---------------------------------------------------------------------------


def test_publish_batch_sends_multiple_events(kafka_module, monkeypatch):
    """publish_batch() sends multiple events in sequence."""
    mock_module, mock_producer_class, mock_producer = _make_mock_aiokafka()
    monkeypatch.setitem(sys.modules, "aiokafka", mock_module)

    # Reset the module's producer pool.
    kafka_module._producer = None
    kafka_module._producer_brokers = []

    events = [
        {
            "session_id": "sess-1",
            "runtime": "voice",
            "kind": "phase",
            "phase": "hearing",
        },
        {
            "session_id": "sess-2",
            "runtime": "voice",
            "kind": "done",
            "phase": "complete",
        },
    ]

    async def run_test():
        return await kafka_module.publish_batch(
            kafka_brokers=["kafka:9092"],
            topic="test.events",
            events=events,
        )

    results = asyncio.get_event_loop().run_until_complete(run_test())

    assert len(results) == 2
    assert mock_producer.send_and_wait.call_count == 2
    for result in results:
        assert result["published"] is True


# ---------------------------------------------------------------------------
# Close producer tests
# ---------------------------------------------------------------------------


def test_close_producer_stops_and_clears(kafka_module, monkeypatch):
    """close_producer() stops the producer and clears the pool."""
    mock_module, mock_producer_class, mock_producer = _make_mock_aiokafka()
    monkeypatch.setitem(sys.modules, "aiokafka", mock_module)

    # Reset the module's producer pool.
    kafka_module._producer = None
    kafka_module._producer_brokers = []

    async def run_test():
        await kafka_module.publish(
            kafka_brokers=["kafka:9092"],
            topic="test.events",
            session_id="sess-1",
            runtime="voice",
            kind="phase",
            phase="hearing",
        )

        assert kafka_module._producer is not None

        # Close it.
        await kafka_module.close_producer()

    asyncio.get_event_loop().run_until_complete(run_test())

    assert kafka_module._producer is None
    assert kafka_module._producer_brokers == []


# ---------------------------------------------------------------------------
# SASL auth tests
# ---------------------------------------------------------------------------


def test_sasl_auth_config_passed_to_producer(monkeypatch):
    """SASL credentials are passed to producer when configured."""
    monkeypatch.setenv("KAFKA_BROKERS", "kafka:9092")
    monkeypatch.setenv("KAFKA_SASL_USERNAME", "admin")
    monkeypatch.setenv("KAFKA_SASL_PASSWORD", "secret123")
    monkeypatch.setenv("KAFKA_SECURITY_PROTOCOL", "SASL_SSL")

    mock_module, mock_producer_class, mock_producer = _make_mock_aiokafka()
    monkeypatch.setitem(sys.modules, "aiokafka", mock_module)

    # Load module with SASL env vars.
    mod = _load(KAFKA_MODULE, "kafka_adapter_sasl")
    mod._producer = None
    mod._producer_brokers = []

    async def run_test():
        await mod.publish(
            kafka_brokers=["kafka:9092"],
            topic="test.events",
            session_id="sess-1",
            runtime="voice",
            kind="phase",
            phase="hearing",
        )

    asyncio.get_event_loop().run_until_complete(run_test())

    call_kwargs = mock_producer_class.call_args[1]
    assert call_kwargs["security_protocol"] == "SASL_SSL"
    assert call_kwargs["sasl_mechanism"] == "PLAIN"
    assert call_kwargs["sasl_plain_username"] == "admin"
    assert call_kwargs["sasl_plain_password"] == "secret123"  # noqa: S105 — test fixture literal

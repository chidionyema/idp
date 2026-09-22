"""FleetView CP6: Kafka adapter — publish agent events to Kafka for enterprise deployments.

Mirrors the NATS adapter interface for enterprises with existing Kafka infrastructure (Confluent
Cloud, AWS MSK, self-hosted). The outbox worker auto-detects which adapter to use based on
KAFKA_BROKERS being set.

Topics follow the estate convention: `fleetview.voice.events` by default, with the full event
payload matching the same schema as NATS (platform/event-bus/contract/estate.agent.event.json).

CONFIG (LAW 46): All from env, no hardcodes.
- KAFKA_BROKERS: comma-separated broker list (required to enable Kafka)
- KAFKA_TOPIC: topic name (default: fleetview.voice.events)
- KAFKA_SCHEMA_REGISTRY_URL: optional schema registry for Avro/JSON validation
- KAFKA_ENABLE_IDEMPOTENCE: enable idempotent producer (default: true)
- KAFKA_SASL_USERNAME / KAFKA_SASL_PASSWORD: optional SASL auth
- KAFKA_SECURITY_PROTOCOL: PLAINTEXT, SASL_PLAINTEXT, SSL, SASL_SSL (default: PLAINTEXT)
"""

from __future__ import annotations

import datetime as dt
import json
import os
from typing import Any

# Connection budget — same as NATS adapter (2s timeout, 1 attempt, 0.1s retry between).
# These are measured values from the NATS adapter; see nats_adapter.py for the receipts.
_REQUEST_TIMEOUT_MS = int(os.environ.get("KAFKA_REQUEST_TIMEOUT_MS", "2000"))
_RETRY_BACKOFF_MS = int(os.environ.get("KAFKA_RETRY_BACKOFF_MS", "100"))
_RETRIES = int(os.environ.get("KAFKA_RETRIES", "1"))

# Configuration (LAW 46: env, never hardcode).
KAFKA_BROKERS = os.environ.get("KAFKA_BROKERS", "").split(",") if os.environ.get("KAFKA_BROKERS") else []
KAFKA_TOPIC = os.environ.get("KAFKA_TOPIC", "fleetview.voice.events")
KAFKA_SCHEMA_REGISTRY_URL = os.environ.get("KAFKA_SCHEMA_REGISTRY_URL", "")
KAFKA_ENABLE_IDEMPOTENCE = os.environ.get("KAFKA_ENABLE_IDEMPOTENCE", "true").lower() == "true"

# Optional SASL auth for Confluent Cloud / AWS MSK.
KAFKA_SASL_USERNAME = os.environ.get("KAFKA_SASL_USERNAME", "")
KAFKA_SASL_PASSWORD = os.environ.get("KAFKA_SASL_PASSWORD", "")
KAFKA_SECURITY_PROTOCOL = os.environ.get("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT")

# Connection pool — one producer per process, not per publish.
_producer = None
_producer_brokers: list[str] = []


def _require_aiokafka():
    """Fail loudly if aiokafka is not installed — estate rule: missing service raises."""
    try:
        import aiokafka  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("aiokafka not installed: pip install aiokafka") from exc


async def _get_producer(brokers: list[str]):
    """Get or create a pooled producer for the given brokers.

    One producer per process, reused across publishes. The producer is created lazily
    on first publish and kept alive. This matches how production Kafka clients work —
    creating a producer per request is expensive and unnecessary.
    """
    global _producer, _producer_brokers
    _require_aiokafka()
    from aiokafka import AIOKafkaProducer

    # Reuse if brokers match.
    if _producer is not None and _producer_brokers == brokers:
        return _producer

    # Close old producer if brokers changed.
    if _producer is not None:
        try:
            await _producer.stop()
        except Exception:  # noqa: BLE001 — best effort cleanup
            pass

    # Build producer config.
    config: dict[str, Any] = {
        "bootstrap_servers": ",".join(brokers),
        "request_timeout_ms": _REQUEST_TIMEOUT_MS,
        "retry_backoff_ms": _RETRY_BACKOFF_MS,
        "enable_idempotence": KAFKA_ENABLE_IDEMPOTENCE,
        "acks": "all" if KAFKA_ENABLE_IDEMPOTENCE else 1,
    }

    # SASL auth for Confluent Cloud / AWS MSK.
    if KAFKA_SASL_USERNAME and KAFKA_SASL_PASSWORD:
        config["security_protocol"] = KAFKA_SECURITY_PROTOCOL
        config["sasl_mechanism"] = os.environ.get("KAFKA_SASL_MECHANISM", "PLAIN")
        config["sasl_plain_username"] = KAFKA_SASL_USERNAME
        config["sasl_plain_password"] = KAFKA_SASL_PASSWORD

    _producer = AIOKafkaProducer(**config)
    await _producer.start()
    _producer_brokers = brokers
    return _producer


async def close_producer() -> None:
    """Close the pooled producer. Call from app shutdown."""
    global _producer, _producer_brokers
    if _producer is not None:
        try:
            await _producer.stop()
        except Exception:  # noqa: BLE001 — best effort
            pass
        _producer = None
        _producer_brokers = []


async def publish(
    kafka_brokers: list[str],
    topic: str,
    *,
    session_id: str,
    runtime: str,
    kind: str,
    phase: str,
    **payload,
) -> dict[str, Any]:
    """Publish an event to Kafka. Returns ack metadata.

    Interface matches nats_adapter.publish for seamless switching.

    Args:
        kafka_brokers: List of broker addresses (e.g., ["kafka:9092"]).
        topic: Kafka topic name.
        session_id: The voice session id.
        runtime: Runtime identifier (e.g., "voice").
        kind: Event kind (phase|tool|wait|done|steer).
        phase: Current phase of the session.
        **payload: Additional event fields (tool, trace_id, needs, steer, etc.).

    Returns:
        Ack metadata with topic, partition, offset, and timestamp.

    Raises:
        RuntimeError: If aiokafka is not installed.
        KafkaError: On publish failure after retries.
    """
    if not kafka_brokers:
        raise ValueError("kafka_brokers cannot be empty")

    _require_aiokafka()

    # Build the event payload — same schema as NATS.
    event: dict[str, Any] = {
        "session_id": session_id,
        "runtime": runtime,
        "kind": kind,
        "at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "phase": phase,
    }
    event.update(payload)

    # Use session_id as the key for partition affinity — all events for a session
    # land on the same partition, preserving order.
    key = session_id.encode("utf-8")
    value = json.dumps(event).encode("utf-8")

    producer = await _get_producer(kafka_brokers)

    # Send with bounded retry. aiokafka handles retries internally based on config.
    result = await producer.send_and_wait(topic, value=value, key=key)

    return {
        "topic": result.topic,
        "partition": result.partition,
        "offset": result.offset,
        "timestamp": result.timestamp,
        "published": True,
    }


async def publish_batch(
    kafka_brokers: list[str],
    topic: str,
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Publish multiple events in a batch. Returns list of ack metadata.

    Useful for draining the outbox in bulk when Kafka is reachable.
    """
    _require_aiokafka()

    if not kafka_brokers:
        raise ValueError("kafka_brokers cannot be empty")

    producer = await _get_producer(kafka_brokers)
    results = []

    for event in events:
        key = event.get("session_id", "").encode("utf-8")
        value = json.dumps(event).encode("utf-8")
        result = await producer.send_and_wait(topic, value=value, key=key)
        results.append({
            "topic": result.topic,
            "partition": result.partition,
            "offset": result.offset,
            "timestamp": result.timestamp,
            "published": True,
        })

    return results


def is_kafka_configured() -> bool:
    """Check if Kafka is configured via environment variables."""
    return bool(os.environ.get("KAFKA_BROKERS"))

"""Telemetry subsystem: real-time observability, circuit breaking, fault detection."""

from platform.telemetry.span_emitter import SpanEmitter
from platform.telemetry.transcript_schema import (
    SpanKind,
    Transcript,
    TranscriptSpan,
    init_schema,
)

__all__ = [
    "SpanEmitter",
    "SpanKind",
    "Transcript",
    "TranscriptSpan",
    "init_schema",
]

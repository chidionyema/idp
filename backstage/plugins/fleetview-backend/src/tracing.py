"""OpenTelemetry tracing for the FleetView voice pipeline.

Full distributed tracing from browser -> FastAPI -> outbox -> NATS/Kafka -> agent response.

THE PIPELINE:
  Browser (client):
    - voice.vad          — VAD processing time
    - voice.asr          — Whisper transcription time
    - voice.intent       — SmolLM2 intent compilation time
    - voice.send         — HTTP POST to /voice/steer

  FastAPI (server):
    - voice.receive      — Total endpoint time
    - voice.validate     — Schema validation
    - voice.outbox.write — SQLite WAL write

  Outbox Worker:
    - voice.outbox.drain — Polling and processing
    - voice.publish.nats — NATS bus publish (or voice.publish.kafka)

  Agent (via SDK):
    - voice.handle       — Event handler execution
    - voice.speak        — Response speech trigger

TRACE CONTEXT PROPAGATION:
  The browser passes `traceparent` header to FastAPI, which passes it through the outbox
  to NATS/Kafka message headers, so agents can continue the trace.

CONFIG (LAW 46):
  OTEL_EXPORTER_OTLP_ENDPOINT  — The OTLP endpoint (e.g., http://tempo:4317)
  OTEL_SERVICE_NAME            — Service name (default: fleetview-voice)
  OTEL_TRACE_SAMPLE_RATE       — Sample rate 0.0-1.0 (default: 1.0)
  OTEL_ENABLED                 — Set to "false" to disable tracing entirely

DESIGN:
  - All tracing functions are no-ops when OpenTelemetry SDK is not installed or OTEL_ENABLED=false
  - This keeps the voice pipeline functional on machines without the OTEL stack
  - Trace context is propagated via W3C traceparent/tracestate headers
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Generator

if TYPE_CHECKING:
    from opentelemetry.trace import Span, Tracer

# ---------------------------------------------------------------------------
# Configuration (LAW 46: all from env vars)
# ---------------------------------------------------------------------------

OTEL_EXPORTER_OTLP_ENDPOINT = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "")
OTEL_SERVICE_NAME = os.environ.get("OTEL_SERVICE_NAME", "fleetview-voice")
OTEL_TRACE_SAMPLE_RATE = float(os.environ.get("OTEL_TRACE_SAMPLE_RATE", "1.0"))
OTEL_ENABLED = os.environ.get("OTEL_ENABLED", "true").lower() not in (
    "false",
    "0",
    "no",
)

# ---------------------------------------------------------------------------
# Lazy initialization — tracer is created once on first use
# ---------------------------------------------------------------------------

_tracer: "Tracer | None" = None
_initialized = False


def _is_otel_available() -> bool:
    """Check if OpenTelemetry SDK is installed."""
    try:
        from opentelemetry import trace  # noqa: F401

        return True
    except ImportError:
        return False


def _initialize_tracer() -> "Tracer | None":
    """Initialize the OpenTelemetry tracer with OTLP exporter.

    Returns None if:
      - OTEL_ENABLED is false
      - OTEL_EXPORTER_OTLP_ENDPOINT is not set
      - OpenTelemetry SDK is not installed
    """
    global _tracer, _initialized

    if _initialized:
        return _tracer

    _initialized = True

    if not OTEL_ENABLED:
        return None

    if not _is_otel_available():
        return None

    if not OTEL_EXPORTER_OTLP_ENDPOINT:
        # No endpoint configured — tracing is off but not an error
        return None

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

        # Build resource with service name
        resource = Resource.create({"service.name": OTEL_SERVICE_NAME})

        # Sampler: respect parent trace's sampling decision, or sample based on rate
        sampler = ParentBased(root=TraceIdRatioBased(OTEL_TRACE_SAMPLE_RATE))

        # Create tracer provider
        provider = TracerProvider(resource=resource, sampler=sampler)

        # Add OTLP exporter
        exporter = OTLPSpanExporter(endpoint=OTEL_EXPORTER_OTLP_ENDPOINT)
        provider.add_span_processor(BatchSpanProcessor(exporter))

        # Register as global tracer provider
        trace.set_tracer_provider(provider)

        _tracer = trace.get_tracer(OTEL_SERVICE_NAME)
        return _tracer

    except Exception as exc:
        # Tracing setup failed — log and continue without tracing
        print(f"[tracing] OTEL setup failed, tracing disabled: {exc}", flush=True)
        return None


def get_tracer() -> "Tracer | None":
    """Get the tracer instance, initializing on first call."""
    global _tracer, _initialized
    if not _initialized:
        return _initialize_tracer()
    return _tracer


# ---------------------------------------------------------------------------
# Span creation helpers
# ---------------------------------------------------------------------------


@contextmanager
def span(
    name: str, attributes: dict[str, Any] | None = None
) -> Generator["Span | None", None, None]:
    """Create a span for the given operation.

    Usage:
        with span("voice.validate", {"schema": "intent-v2"}) as s:
            # do work
            if s:
                s.set_attribute("result", "ok")

    Returns None if tracing is disabled — callers must check before using.
    """
    tracer = get_tracer()
    if tracer is None:
        yield None
        return

    from opentelemetry import trace

    with tracer.start_as_current_span(name, kind=trace.SpanKind.INTERNAL) as s:
        if attributes:
            for k, v in attributes.items():
                s.set_attribute(k, v)
        yield s


@contextmanager
def server_span(
    name: str, attributes: dict[str, Any] | None = None
) -> Generator["Span | None", None, None]:
    """Create a SERVER span — for incoming requests."""
    tracer = get_tracer()
    if tracer is None:
        yield None
        return

    from opentelemetry import trace

    with tracer.start_as_current_span(name, kind=trace.SpanKind.SERVER) as s:
        if attributes:
            for k, v in attributes.items():
                s.set_attribute(k, v)
        yield s


@contextmanager
def producer_span(
    name: str, attributes: dict[str, Any] | None = None
) -> Generator["Span | None", None, None]:
    """Create a PRODUCER span — for publishing to message bus."""
    tracer = get_tracer()
    if tracer is None:
        yield None
        return

    from opentelemetry import trace

    with tracer.start_as_current_span(name, kind=trace.SpanKind.PRODUCER) as s:
        if attributes:
            for k, v in attributes.items():
                s.set_attribute(k, v)
        yield s


# ---------------------------------------------------------------------------
# Trace context propagation
# ---------------------------------------------------------------------------


def extract_context(headers: dict[str, str]) -> Any:
    """Extract trace context from incoming HTTP headers.

    Returns the OpenTelemetry context object, or None if tracing is disabled.
    The returned context should be passed to `with_context()` to continue the trace.
    """
    if not OTEL_ENABLED or not _is_otel_available():
        return None

    try:
        from opentelemetry.propagate import extract

        return extract(headers)
    except Exception:
        return None


def inject_context(headers: dict[str, str]) -> dict[str, str]:
    """Inject current trace context into outgoing headers.

    Modifies headers in place and returns them for convenience.
    Returns unchanged headers if tracing is disabled.
    """
    if not OTEL_ENABLED or not _is_otel_available():
        return headers

    try:
        from opentelemetry.propagate import inject

        inject(headers)
    except Exception:  # noqa: BLE001, S110 — tracing must never fail the call path
        pass

    return headers


def get_current_trace_context() -> dict[str, str]:
    """Get the current trace context as a dict suitable for message headers.

    Returns empty dict if tracing is disabled.
    """
    headers: dict[str, str] = {}
    return inject_context(headers)


@contextmanager
def with_context(context: Any) -> Generator[None, None, None]:
    """Execute code within the given trace context.

    Usage:
        ctx = extract_context(request.headers)
        with with_context(ctx):
            # spans created here are children of the incoming trace
            with span("voice.receive") as s:
                ...
    """
    if context is None:
        yield
        return

    try:
        from opentelemetry import context as otel_context

        token = otel_context.attach(context)
        try:
            yield
        finally:
            otel_context.detach(token)
    except Exception:
        yield


# ---------------------------------------------------------------------------
# Convenience functions for voice pipeline spans
# ---------------------------------------------------------------------------


def record_validation(
    duration_ms: float, success: bool, error: str | None = None
) -> None:
    """Record schema validation metrics on the current span."""
    tracer = get_tracer()
    if tracer is None:
        return

    try:
        from opentelemetry import trace

        current_span = trace.get_current_span()
        current_span.set_attribute("voice.validation.duration_ms", duration_ms)
        current_span.set_attribute("voice.validation.success", success)
        if error:
            current_span.set_attribute("voice.validation.error", error)
    except Exception:  # noqa: BLE001, S110 — tracing must never fail the call path
        pass


def record_outbox_write(
    row_id: int, session_id: str, action: str | None = None
) -> None:
    """Record outbox write metrics on the current span."""
    tracer = get_tracer()
    if tracer is None:
        return

    try:
        from opentelemetry import trace

        current_span = trace.get_current_span()
        current_span.set_attribute("voice.outbox.row_id", row_id)
        current_span.set_attribute("voice.session_id", session_id)
        if action:
            current_span.set_attribute("voice.action", action)
    except Exception:  # noqa: BLE001, S110 — tracing must never fail the call path
        pass


def record_publish(subject: str, success: bool, error: str | None = None) -> None:
    """Record NATS/Kafka publish metrics on the current span."""
    tracer = get_tracer()
    if tracer is None:
        return

    try:
        from opentelemetry import trace

        current_span = trace.get_current_span()
        current_span.set_attribute("voice.publish.subject", subject)
        current_span.set_attribute("voice.publish.success", success)
        if error:
            current_span.set_attribute("voice.publish.error", error)
    except Exception:  # noqa: BLE001, S110 — tracing must never fail the call path
        pass


# ---------------------------------------------------------------------------
# FastAPI middleware for automatic trace context extraction
# ---------------------------------------------------------------------------


def get_trace_middleware():
    """Return FastAPI middleware for automatic trace context extraction.

    Usage in serve.py:
        middleware = get_trace_middleware()
        if middleware:
            app.add_middleware(middleware)
    """
    if not OTEL_ENABLED or not _is_otel_available():
        return None

    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        return FastAPIInstrumentor
    except ImportError:
        return None


def instrument_fastapi(app: Any) -> None:
    """Instrument a FastAPI app with OpenTelemetry tracing.

    No-op if OTEL is disabled or SDK not installed.
    """
    if not OTEL_ENABLED:
        return

    # Ensure tracer is initialized
    get_tracer()

    if not _is_otel_available():
        return

    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
    except ImportError:
        # Instrumentation package not installed — not fatal
        pass
    except Exception as exc:
        print(f"[tracing] FastAPI instrumentation failed: {exc}", flush=True)

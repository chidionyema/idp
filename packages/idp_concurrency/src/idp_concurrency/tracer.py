"""Phase C — Traced HTTP client.

The only HTTP client any repo is allowed to use (Forcing F3: no untraced I/O).
Every call emits an OTel span *before* the bytes leave the process. Each
response carries a `Receipt` whose fields are derived from the live span
context — `Receipt = f(Trace)` is structural, not asserted.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any, Mapping, Optional
from dataclasses import dataclass
from typing import Any, Mapping, Optional

from opentelemetry import context as otel_context
from opentelemetry import trace
from opentelemetry.trace import SpanKind, Status, StatusCode


@dataclass(frozen=True)
class Receipt:
    """Immutable trace pointer. Receipt = f(Trace)."""

    trace_id: str
    span_id: str
    request_sha256: str


class _NoopSpan:
    def __enter__(self) -> "_NoopSpan":
        return self

    def __exit__(self, *exc: Any) -> None:
        return None

    def set_attribute(self, key: str, value: Any) -> None:
        return None

    def set_status(self, status: Status) -> None:
        return None

    def record_exception(self, exc: BaseException) -> None:
        return None

    def get_span_context(self) -> Any:
        return _ZeroSpanContext()


class _ZeroSpanContext:
    trace_id = 0
    span_id = 0
    is_valid = False


class _NoopTracer:
    def start_as_current_span(self, name: str, **_: Any) -> _NoopSpan:
        return _NoopSpan()


def build_tracer(env: Optional[Mapping[str, str]] = None) -> Any:
    """Build a tracer from the environment.

    Real SDK when `OTEL_EXPORTER_OTLP_ENDPOINT` is set AND the SDK is importable;
    no-op otherwise. Telemetry never breaks the call.
    """
    env = os.environ if env is None else env
    endpoint = (env.get("OTEL_EXPORTER_OTLP_ENDPOINT") or "").strip()
    if not endpoint:
        return _NoopTracer()
    try:
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
    except Exception:
        return _NoopTracer()

    try:
        resource = Resource.create(
            {
                "service.name": env.get("OTEL_SERVICE_NAME", "idp-concurrency"),
                "service.version": env.get("IDP_CONCURRENCY_VERSION", "0.1.0"),
            }
        )
        provider = TracerProvider(resource=resource)
        url = endpoint.rstrip("/")
        if not url.endswith("/v1/traces"):
            url = f"{url}/v1/traces"
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=url)))
        trace.set_tracer_provider(provider)
        return trace.get_tracer("idp-concurrency")
    except Exception:
        return _NoopTracer()


def _format_id(value: int, width: int) -> str:
    return format(value, f"0{width}x")


class TracedClient:
    """Wraps `httpx.AsyncClient`. Span per call. Receipt on response."""

    def __init__(self, inner: Any, tracer: Any) -> None:
        self._inner = inner
        self._tracer = tracer

    async def post(
        self,
        url: str,
        *,
        body: dict | None = None,
        headers: dict | None = None,
        **kw: Any,
    ) -> Any:
        payload = body or {}
        body_sha = hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode()
        ).hexdigest()

        with self._tracer.start_as_current_span("http.post", kind=SpanKind.CLIENT) as sp:
            sp.set_attribute("http.url", url)
            sp.set_attribute("http.body_sha256", body_sha)
            sp.set_attribute("http.method", "POST")
            try:
                response = await self._inner.post(url, json=payload, headers=headers, **kw)
            except Exception as exc:
                sp.record_exception(exc)
                sp.set_status(Status(StatusCode.ERROR, str(exc)))
                raise

            sp.set_attribute("http.status_code", response.status_code)
            ctx = sp.get_span_context()
            response._receipt = Receipt(
                trace_id=_format_id(ctx.trace_id, 32),
                span_id=_format_id(ctx.span_id, 16),
                request_sha256=body_sha,
            )
            return response


__all__ = ["Receipt", "TracedClient", "build_tracer"]

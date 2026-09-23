"""Real tests for tracer.TracedClient.

We exercise both the no-op path (no SDK / no endpoint) and the traced path
(real OTel SDK with an in-memory exporter), and verify the Receipt contract.
"""

from __future__ import annotations

from typing import Any

import pytest

from idp_concurrency.tracer import Receipt, TracedClient, build_tracer


def _isolated_tracer():
    """Build a TracerProvider directly, without touching the global.

    OTel's `set_tracer_provider` is one-shot and refuses overrides, so tests
    that need a real tracer must obtain one from a fresh provider.
    """
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    provider = TracerProvider(resource=Resource.create({"service.name": "test"}))
    exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return provider.get_tracer("test"), exporter


class _FakeResponse:
    status_code = 200
    _receipt: Receipt


class _FakeAsyncClient:
    """Mimics httpx.AsyncClient. Records the URL hit."""

    def __init__(self, status_code: int = 200) -> None:
        self.status_code = status_code
        self.calls: list[dict[str, Any]] = []

    async def post(self, url: str, *, json: Any = None, headers: Any = None, **kw: Any):
        self.calls.append({"url": url, "json": json})
        r = _FakeResponse()
        r.status_code = self.status_code
        return r


# ---------------------------------------------------------------------------
# No-op path: no OTel SDK or no endpoint configured.


def test_noop_tracer_returns_traced_client_with_receipt():
    inner = _FakeAsyncClient()
    tracer = build_tracer(env={"OTEL_EXPORTER_OTLP_ENDPOINT": ""})
    client = TracedClient(inner, tracer)

    import asyncio

    response = asyncio.run(client.post("https://example.test/v1", body={"a": 1}))

    assert response.status_code == 200
    assert isinstance(response._receipt, Receipt)
    assert len(response._receipt.trace_id) == 32
    assert len(response._receipt.span_id) == 16
    assert len(response._receipt.request_sha256) == 64


def test_noop_tracer_does_not_break_on_missing_sdk(monkeypatch):
    """`build_tracer` must never raise — even if the SDK is absent."""
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:65535")
    tracer = build_tracer()
    assert tracer is not None


# ---------------------------------------------------------------------------
# Real SDK path: install the SDK and an in-memory exporter.


def test_real_sdk_emits_span_with_receipt():
    tracer, exporter = _isolated_tracer()

    inner = _FakeAsyncClient(status_code=201)
    client = TracedClient(inner, tracer)

    import asyncio

    response = asyncio.run(client.post("https://example.test/v1/chat", body={"model": "x"}))

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    sp = spans[0]
    assert sp.name == "http.post"
    assert sp.attributes["http.url"] == "https://example.test/v1/chat"
    assert sp.attributes["http.status_code"] == 201
    assert sp.attributes["http.body_sha256"] == response._receipt.request_sha256
    assert response._receipt.trace_id == format(sp.context.trace_id, "032x")
    assert response._receipt.span_id == format(sp.context.span_id, "016x")


def test_receipt_is_stable_for_identical_bodies():
    """Two posts with the same body must produce the same request_sha256."""
    inner = _FakeAsyncClient()
    tracer = build_tracer(env={"OTEL_EXPORTER_OTLP_ENDPOINT": ""})
    client = TracedClient(inner, tracer)

    import asyncio

    r1 = asyncio.run(client.post("https://x", body={"a": 1, "b": 2}))
    r2 = asyncio.run(client.post("https://x", body={"b": 2, "a": 1}))
    assert r1._receipt.request_sha256 == r2._receipt.request_sha256


def test_request_failure_records_exception_and_raises():
    tracer, exporter = _isolated_tracer()

    class _Boom:
        async def post(self, *_a: Any, **_kw: Any):
            raise ConnectionError("no route")

    import asyncio

    client = TracedClient(_Boom(), tracer)
    with pytest.raises(ConnectionError):
        asyncio.run(client.post("https://x", body={"q": 1}))

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].status.status_code.name == "ERROR"

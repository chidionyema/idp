"""Tracing to the estate collector. Mandatory in every service (founder decision 1, crew#627).

Reads OTEL_EXPORTER_OTLP_ENDPOINT, set by the deployment to the one SigNoz collector
(LAW 50: every workload emits to the central collector). With no endpoint set, spans go nowhere
and the service still runs, so a laptop can start it without the cluster.
"""
import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

SERVICE = "${{ values.name }}"


def configure() -> TracerProvider:
    provider = TracerProvider(resource=Resource.create({"service.name": SERVICE}))
    if os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
    return provider

"""Agent-level OTel metrics, guarded exactly like sovereign/engine/tracing.py:
if OTEL_EXPORTER_OTLP_ENDPOINT is absent the whole module is a no-op that
warns once to stderr and never raises. A missing metrics backend must never
take a session down, same reasoning as R33 for Langfuse.

Emits only what this engine actually observes today. It does NOT emit
agent_tokens_input_total / agent_tokens_output_total / agent_tokens_cached_total
(runners.py returns one undifferentiated `tokens` estimate, never a real
provider-reported input/output/cached split), agent_tool_call_total /
agent_tool_call_duration_seconds (an individual tool call happens inside the
vendor CLI subprocess a runner shells out to -- LAW 34 keeps the vendor
opaque past that boundary, so this engine cannot see one), or
agent_repair_loops_total (fsm.py's cycle counter lives inside the Temporal
workflow sandbox, which may take no side effect -- counting it here would
require moving the count into an activity, not yet done). Those names are
declared, with the reason they are unmet, in observability/agent-metrics.yaml
so the gap is visible rather than silently faked.
"""

from __future__ import annotations

import sys
import threading
from typing import Any

from sovereign import config

_warned = False
_warn_lock = threading.Lock()
_meter = None
_meter_lock = threading.Lock()
_instruments: dict[str, Any] = {}


def _warn_once(msg: str) -> None:
    global _warned
    with _warn_lock:
        if _warned:
            return
        _warned = True
        print(f"[sovereign.metrics] {msg}", file=sys.stderr)


def configured() -> bool:
    return bool(config.OTEL_EXPORTER_OTLP_ENDPOINT)


def _get_meter():
    global _meter
    if not configured():
        _warn_once("OTEL_EXPORTER_OTLP_ENDPOINT not configured; metrics are a no-op")
        return None
    with _meter_lock:
        if _meter is not None:
            return _meter
        try:
            from opentelemetry import metrics as otel_metrics
            from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
                OTLPMetricExporter,
            )
            from opentelemetry.sdk.metrics import MeterProvider
            from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

            exporter = OTLPMetricExporter(endpoint=config.OTEL_EXPORTER_OTLP_ENDPOINT)
            reader = PeriodicExportingMetricReader(exporter)
            provider = MeterProvider(metric_readers=[reader])
            otel_metrics.set_meter_provider(provider)
            _meter = otel_metrics.get_meter("sovereign.engine")
        except Exception as exc:  # pragma: no cover - defensive, never fatal
            _warn_once(f"opentelemetry unavailable ({exc}); metrics are a no-op")
            _meter = None
        return _meter


def _instrument(name: str, kind: str, unit: str, description: str):
    key = f"{kind}:{name}"
    if key in _instruments:
        return _instruments[key]
    meter = _get_meter()
    if meter is None:
        return None
    factory = meter.create_counter if kind == "counter" else meter.create_histogram
    inst = factory(name, unit=unit, description=description)
    _instruments[key] = inst
    return inst


def turn(runner: str, status: str) -> None:
    """agent_turn_total: one call site, activities.notify_change, on every
    session state change notify_change already reports (real signal:
    workflow.py drives one notify_change per FSM transition)."""
    try:
        inst = _instrument(
            "agent_turn_total",
            "counter",
            "1",
            "count of agent turns by runner and terminal status",
        )
        if inst is not None:
            inst.add(1, {"runner": runner or "unknown", "status": status or "unknown"})
    except Exception as exc:  # pragma: no cover - defensive, never fatal
        _warn_once(f"turn() failed: {exc}")


def turn_duration(runner: str, seconds: float) -> None:
    """agent_turn_duration_seconds: wall time of one run_step activity call
    (subprocess launch through result), measured in activities.py where the
    side effect already lives."""
    try:
        inst = _instrument(
            "agent_turn_duration_seconds",
            "histogram",
            "s",
            "wall time of one run_step activity call",
        )
        if inst is not None:
            inst.record(max(seconds, 0.0), {"runner": runner or "unknown"})
    except Exception as exc:  # pragma: no cover - defensive, never fatal
        _warn_once(f"turn_duration() failed: {exc}")


def wall_clock(runner: str, seconds: float) -> None:
    """agent_wall_clock_seconds: cumulative real time spent, same
    measurement as turn_duration but a running total rather than a
    distribution -- the spec names both, and both are cheap from one
    timer."""
    try:
        inst = _instrument(
            "agent_wall_clock_seconds",
            "counter",
            "s",
            "cumulative wall-clock time spent in run_step",
        )
        if inst is not None:
            inst.add(max(seconds, 0.0), {"runner": runner or "unknown"})
    except Exception as exc:  # pragma: no cover - defensive, never fatal
        _warn_once(f"wall_clock() failed: {exc}")


def tokens(runner: str, count: int) -> None:
    """agent_tokens_total: the one undifferentiated figure runners.py
    reports (real usage from a real runner, or len(output)//divisor from
    the estimate fallback -- runners.py's own docstring names the
    fallback). Not split into input/output/cached; see module docstring."""
    try:
        inst = _instrument(
            "agent_tokens_total",
            "counter",
            "1",
            "tokens spent per step, undifferentiated",
        )
        if inst is not None:
            inst.add(max(int(count), 0), {"runner": runner or "unknown"})
    except Exception as exc:  # pragma: no cover - defensive, never fatal
        _warn_once(f"tokens() failed: {exc}")

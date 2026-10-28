"""The estate router's AEI observer: every routed call becomes one execution-evidence event.

WHY THIS FILE EXISTS. The estate's default model route is the cloud router (AGENTS.md 7a), so
the router is the ONE place every agent's model call passes. That makes it the honest place to
observe from: an agent that never calls the router is an agent that never cost money, and an
agent that does is observed without the agent having to know it is watched.

WHAT IT RECORDS, AND WHAT IT MUST NEVER RECORD. The AEI schema is metadata only: the model that
answered, the tokens it used, the latency, the status. Never the prompt, never the answer, never
the arguments. There is no attribute class for content in the schema, so there is nowhere to put
it -- that is the design, not a promise.

THE RULE THAT MATTERS MOST: a telemetry failure may never fail a request (LAW 38). Every write
here is on a background thread with its own queue; if the collector is down, the evidence is
lost and the call still answers. The queue is bounded and overflow DROPS the event rather than
growing without limit.

THE DRIFT GUARD. This module is mounted into the router pod, where the `aei` package is not
importable, so it builds the event itself. That is a second copy of the schema, and a second
copy is a stitch -- so packages/aei/tests/test_router_callback.py imports BOTH this module and
the library and proves they agree: the event this file builds passes the library's validator,
with the same schema version, the same identifiers and the same attribute names. If the library
changes and this file does not, the test fails.

Registered as: aei_observer.proxy_handler_instance in litellm_settings.callbacks.
Mounted at: /etc/litellm/callbacks/aei_observer.py (the litellm-callbacks ConfigMap).
Configured by: AEI_COLLECTOR_URL (where the collector is) and AEI_API_TOKEN_FILE (the token,
as a FILE -- Kyverno's secrets-not-from-env-vars forbids a secret in an env var).
"""

from __future__ import annotations

import json
import os
import queue
import threading
import urllib.request
import uuid
from typing import Any

SCHEMA_VERSION = "aei.event.v1"

# The same allowlist the library enforces (packages/aei/src/aei/core.py SAFE_ATTRS). The drift
# test compares them, so a name added to one and not the other fails CI rather than producing
# events the collector refuses.
SAFE_ATTRS = frozenset(
    "model provider lane tool_name tool_kind status outcome reason_code artifact_class tier "
    "verifier result_code retry_reason queue_ms latency_ms duration_ms input_tokens "
    "output_tokens cache_read_tokens cost_usd bytes_in bytes_out source_path source_line "
    "source_sha source_revision http_status attempts error_type metric_unit evidence_grade "
    "config_id phase target_component model_group deployment_model total_tokens".split()
)

IDENTIFIERS = ("run_id", "task_id", "agent_id", "harness_id", "trace_id", "revision")

_COLLECTOR_URL = os.environ.get("AEI_COLLECTOR_URL", "").rstrip("/")
_TOKEN_FILE = os.environ.get("AEI_API_TOKEN_FILE", "/run/secrets/aei/api-token")
_QUEUE: "queue.Queue[dict[str, Any]]" = queue.Queue(maxsize=1024)
_DROPPED = 0
_STATS = {"sent": 0, "errors": 0, "dropped": 0}


def _token() -> str:
    """The API token, read from the mounted file. Never from an env var, never printed."""
    try:
        with open(_TOKEN_FILE, "r", encoding="utf-8") as handle:
            return handle.read().strip()
    except OSError:
        return ""


def _now() -> str:
    from datetime import datetime, timezone

    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def _metadata(kwargs: dict) -> dict:
    meta = kwargs.get("litellm_params") or {}
    if isinstance(meta, dict):
        found = meta.get("metadata")
        if isinstance(found, dict):
            return found
    found = kwargs.get("metadata")
    return found if isinstance(found, dict) else {}


def _identity(kwargs: dict, call_id: str) -> dict:
    """The six identifiers. A caller that does not say who it is is recorded as unattributed,
    which is a fact; it is never given a name nobody declared."""
    meta = _metadata(kwargs)
    return {
        "run_id": str(meta.get("run_id") or meta.get("task_id") or call_id),
        "task_id": str(meta.get("task_id") or call_id),
        "agent_id": str(meta.get("agent_id") or "unattributed"),
        "harness_id": str(meta.get("harness_id") or "estate-router"),
        "trace_id": str(meta.get("trace_id") or call_id),
        "revision": str(os.environ.get("ESTATE_REVISION") or "unknown"),
    }


def _event(event_type: str, ident: dict, attributes: dict) -> dict:
    safe = {k: v for k, v in (attributes or {}).items() if k in SAFE_ATTRS}
    return {
        "schema": SCHEMA_VERSION,
        "event_id": str(uuid.uuid4()),
        "type": event_type,
        "timestamp": _now(),
        "parent_id": None,
        "attempt": 1,
        "attributes": safe,
        **ident,
    }


def _post(event: dict) -> None:
    body = json.dumps(event).encode()
    request = urllib.request.Request(  # noqa: S310 - http to the estate's own collector, configured by the environment
        f"{_COLLECTOR_URL}/api/events",
        data=body,
        headers={
            "Authorization": f"Bearer {_token()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )  # noqa: S310 - http to the estate's own collector, configured by the environment
    with urllib.request.urlopen(request, timeout=2.0) as response:  # noqa: S310 - same endpoint, http scheme only
        response.read(512)


def _worker() -> None:
    while True:
        event = _QUEUE.get()
        try:
            _post(event)
            _STATS["sent"] += 1
        except Exception:  # noqa: BLE001 - a collector that is down loses evidence, not calls
            _STATS["errors"] += 1
        finally:
            _QUEUE.task_done()


def _enqueue(event: dict) -> None:
    global _DROPPED
    try:
        _QUEUE.put_nowait(event)
    except queue.Full:
        _DROPPED += 1
        _STATS["dropped"] = _DROPPED


def _usage_numbers(response_obj: Any) -> dict:
    usage = getattr(response_obj, "usage", None)
    if usage is None and isinstance(response_obj, dict):
        usage = response_obj.get("usage")
    if usage is None:
        return {}
    if isinstance(usage, dict):
        return {
            "input_tokens": int(usage.get("prompt_tokens") or 0),
            "output_tokens": int(usage.get("completion_tokens") or 0),
            "total_tokens": int(usage.get("total_tokens") or 0),
        }
    return {
        "input_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
        "output_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
        "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
    }


def _status_code(kwargs: dict) -> int | None:
    """The HTTP status of a failed call, when the router knows it. None means unknown."""
    exception = kwargs.get("exception")
    for source in (exception, kwargs.get("response")):
        if source is None:
            continue
        value = getattr(source, "status_code", None)
        if value is None and isinstance(source, dict):
            value = source.get("status_code")
        try:
            if value is not None:
                return int(value)
        except (TypeError, ValueError):
            continue
    return None


class EstateAeiObserver:
    """LiteLLM callback that turns each routed call into one AEI event."""

    def __init__(self) -> None:
        self._thread = threading.Thread(target=_worker, daemon=True)
        self._thread.start()

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        self._observe(kwargs, response_obj, start_time, end_time, failed=False)

    async def async_log_failure_event(self, kwargs, response_obj, start_time, end_time):
        self._observe(kwargs, response_obj, start_time, end_time, failed=True)

    def _observe(
        self, kwargs, response_obj, start_time, end_time, failed: bool
    ) -> None:
        if not _COLLECTOR_URL:
            # Not configured means not installed in this router. Nothing to do, nothing to fail.
            return
        try:
            call_id = str(kwargs.get("litellm_call_id") or uuid.uuid4())
            ident = _identity(kwargs, call_id)
            usage = _usage_numbers(response_obj)
            model = str(kwargs.get("model") or "unknown")
            latency_ms = round(max(0.0, float(end_time) - float(start_time)) * 1000, 3)
            attributes: dict[str, Any] = {
                "model": model,
                "provider": "estate-router",
                "latency_ms": latency_ms,
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            }
            # The alias is what the caller asked for; the deployment is what actually answered.
            # "default" is several deployments with different prices, so the cost of a call is
            # not knowable from the alias -- it is knowable from the deployment.
            deployment = None
            if not isinstance(response_obj, dict):
                deployment = getattr(response_obj, "model", None)
            if deployment and str(deployment) != model:
                attributes["deployment_model"] = str(deployment)
            status_code = _status_code(kwargs)
            if status_code is not None:
                attributes["http_status"] = status_code
            response_cost = kwargs.get("response_cost")
            if isinstance(response_cost, (int, float)) and response_cost > 0:
                # The router's own figure. Recorded because it is the estate's accounting, and
                # labelled observed because the router computed it.
                attributes["cost_usd"] = round(float(response_cost), 10)
                attributes["evidence_grade"] = "observed"
            elif usage.get("input_tokens") or usage.get("output_tokens"):
                # A zero cost with real tokens is the shape the estate already called a hole
                # (176M tokens recorded at $0.0000 on an unpriced lane). UNKNOWN, not zero.
                attributes["evidence_grade"] = "unknown"
            else:
                attributes["evidence_grade"] = "observed"
            event_type = "model.failed" if failed else "model.completed"
            _enqueue(_event(event_type, ident, attributes))
        except Exception:  # noqa: BLE001 - LAW 38: telemetry may never fail a request
            _STATS["errors"] += 1


proxy_handler_instance = EstateAeiObserver()

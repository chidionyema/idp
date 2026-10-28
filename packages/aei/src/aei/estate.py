"""The estate's adapter to AEI: observe a real task without changing what it does.

WHY THIS FILE EXISTS. The delivered reference build (packages/aei/docs/README.reference-build.md)
proves the evidence contract in isolation: a schema, a store, an emitter, an evaluator. What the
estate needs is the seam where its OWN work happens -- the router every model call passes through,
the tools an agent calls, the verification that closes a task -- expressed so that the work cannot
tell it is being watched. Two rules from the delivered build are load-bearing here and are the
reason this module is thin:

  1. A telemetry failure may never block or alter the work it observes. Every call below is
     best effort: a collector that is down loses evidence, never the task.
  2. A missing measurement is UNKNOWN, not zero. Tokens and latency are observed from the
     response; money is DERIVED from the estate's own router price table and is marked as
     derived in `evidence_grade`. When no price row exists, cost stays absent -- the evaluator
     reports null and says so.

The identifiers are the six the contract requires: run, task, agent, harness, trace, revision.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .client import Emitter
from .core import utc_now

# The estate's default model route is the cloud router (AGENTS.md 7a). It is the one place every
# agent's model call passes, so it is the one place the evidence has to come from.
ROUTER_URL = os.environ.get("ESTATE_ROUTER_URL", "https://llm.mumchimp.com").rstrip("/")
COLLECTOR_URL = os.environ.get("AEI_COLLECTOR_URL", "http://127.0.0.1:8766").rstrip("/")
IDP_ROOT = Path(__file__).resolve().parents[4]


def identity(
    *,
    run_id: str,
    task_id: str,
    agent_id: str,
    harness_id: str,
    revision: str,
    trace_id: str | None = None,
) -> dict[str, str]:
    """The six identifiers every AEI event must carry."""
    return {
        "run_id": run_id,
        "task_id": task_id,
        "agent_id": agent_id,
        "harness_id": harness_id,
        "trace_id": trace_id or run_id,
        "revision": revision,
    }


def emitter(
    ident: dict[str, str],
    *,
    endpoint: str | None = None,
    token: str | None = None,
) -> Emitter:
    """An emitter pointed at the collector. The token is a NAME in the environment, never a value."""
    return Emitter(
        endpoint or COLLECTOR_URL,
        token if token is not None else os.environ.get("AEI_API_TOKEN", ""),
        ident,
    )


def _price_rows() -> dict[str, dict[str, float]]:
    """The estate's own per-token prices, read from the router's config.

    platform/llm/config.yaml is the router's model_cost map, so it is the one place the estate
    already declares what a token costs. Cost derived from it is DERIVED, not observed, and the
    event says so in `evidence_grade`.

    The parse is deliberately shallow -- this is a price lookup, not a YAML library. The shape
    it walks is the one the router config has: a `- model_name:` opens a lane, `model:` names
    the deployment inside it, and `input_cost_per_token` / `output_cost_per_token` price that
    deployment. A deployment with no price row is UNPRICED, which is NOT zero: the estate's own
    comment on the free lanes says an absent price is why the router recorded $0.0000 for a
    call that cost money, so an absent row yields an unknown cost, never a zero.
    """
    path = IDP_ROOT / "platform" / "llm" / "config.yaml"
    try:
        text = path.read_text()
    except OSError:
        return {}
    rows: dict[str, dict[str, float]] = {}
    deployment: str | None = None
    in_params = False
    params_indent = 0
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        if stripped.startswith("- "):
            in_params = False
            deployment = None
            continue
        if stripped == "litellm_params:":
            in_params = True
            params_indent = indent
            deployment = None
            continue
        if not in_params:
            continue
        if indent <= params_indent:
            in_params = False
            deployment = None
            continue
        if stripped.startswith("model:") and deployment is None:
            deployment = stripped.split(":", 1)[1].strip().strip('"')
            continue
        if deployment and stripped.startswith(
            ("input_cost_per_token:", "output_cost_per_token:")
        ):
            key, _, value = stripped.partition(":")
            try:
                rows.setdefault(deployment, {})[key.strip()] = float(value.strip())
            except ValueError:
                continue
    return rows


def derived_cost(
    deployment: str | None, input_tokens: int, output_tokens: int
) -> tuple[float | None, str]:
    """(cost_usd, evidence_grade) for a call, or (None, 'unknown') when no price row exists.

    The deployment is what the ROUTER says answered (`x-litellm-model-name`), not the alias the
    caller asked for: `default` is four deployments with four different prices, so the alias
    cannot price a call and only the deployment can.
    """
    if not deployment:
        return None, "unknown"
    rows = _price_rows()
    row = rows.get(deployment)
    if not row:
        return None, "unknown"
    cost = (
        row.get("input_cost_per_token", 0.0) * input_tokens
        + row.get("output_cost_per_token", 0.0) * output_tokens
    )
    return round(cost, 10), "derived"


def router_call(
    emitter: Emitter,
    ident: dict[str, str],
    messages: list[dict[str, str]],
    *,
    model: str = "default",
    router_url: str | None = None,
    api_key: str | None = None,
    timeout: float = 120.0,
    metadata: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Make a REAL call to the estate router and record what came back.

    Observed: the model that answered, the tokens it used, the wall-clock it took, the HTTP
    status. Derived: the money (from the estate's own price table). Never recorded: the prompt,
    the answer, the arguments -- the ledger is metadata only.
    """
    base = (router_url or ROUTER_URL).rstrip("/")
    key = api_key if api_key is not None else os.environ.get("LITELLM_API_KEY", "")
    body: dict[str, Any] = {"model": model, "messages": messages}
    if metadata:
        body["metadata"] = metadata
    payload = json.dumps(body).encode()
    request = urllib.request.Request(  # noqa: S310 - http to the estate's own router, configured by the caller
        f"{base}/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )  # noqa: S310 - http to the estate's own router, configured by the caller
    started = time.monotonic()
    emitter.emit(
        "model.requested", attributes={"model": model, "provider": "estate-router"}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - the estate's router, http scheme only
            raw = response.read()
            status = response.status
            headers = {k.lower(): v for k, v in response.headers.items()}
    except urllib.error.HTTPError as exc:
        elapsed = round((time.monotonic() - started) * 1000, 3)
        emitter.emit(
            "model.failed",
            attributes={
                "model": model,
                "http_status": exc.code,
                "latency_ms": elapsed,
                "error_type": type(exc).__name__,
            },
        )
        raise
    except Exception as exc:  # noqa: BLE001 - the failure is recorded, then re-raised unchanged
        elapsed = round((time.monotonic() - started) * 1000, 3)
        emitter.emit(
            "model.failed",
            attributes={
                "model": model,
                "latency_ms": elapsed,
                "error_type": type(exc).__name__,
            },
        )
        raise
    elapsed = round((time.monotonic() - started) * 1000, 3)
    data = json.loads(raw)
    usage = data.get("usage") or {}
    answer_model = data.get("model") or model
    # The router tells us which deployment actually answered. Without it, `default` is four
    # deployments with four prices and no call can be priced honestly.
    deployment = headers.get("x-litellm-model-name")
    input_tokens = int(usage.get("prompt_tokens") or 0)
    output_tokens = int(usage.get("completion_tokens") or 0)
    cost, grade = derived_cost(deployment, input_tokens, output_tokens)
    attributes: dict[str, Any] = {
        "model": answer_model,
        "provider": "estate-router",
        "latency_ms": elapsed,
        "http_status": status,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": int(
            usage.get("total_tokens") or (input_tokens + output_tokens)
        ),
        "evidence_grade": grade,
    }
    if deployment:
        attributes["deployment_model"] = deployment
        attributes["model_group"] = headers.get("x-litellm-model-group", answer_model)
    cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens")
    if cached:
        attributes["cache_read_tokens"] = cached
    if cost is not None:
        attributes["cost_usd"] = cost
    emitter.emit("model.completed", attributes=attributes)
    return {
        "model": answer_model,
        "deployment_model": deployment,
        "usage": usage,
        "latency_ms": elapsed,
        "cost_usd": cost,
        "cost_grade": grade,
        "http_status": status,
        "response": data,
    }


@contextmanager
def tool(
    emitter: Emitter,
    ident: dict[str, str],
    tool_name: str,
    *,
    source_path: str | None = None,
    tool_kind: str | None = None,
    attributes: dict[str, Any] | None = None,
) -> Iterator[dict[str, Any]]:
    """Record one tool invocation around the real call.

    `attributes` carries what the tool MEASURED (bytes in, a digest, a status) -- never what it
    was given: the arguments of a tool call are the thing the schema exists to keep out.
    """
    started = time.monotonic()
    attrs: dict[str, Any] = {"tool_name": tool_name}
    if source_path:
        attrs["source_path"] = source_path
    if tool_kind:
        attrs["tool_kind"] = tool_kind
    if attributes:
        attrs.update(attributes)
    emitter.emit("tool.started", attributes=attrs)
    state: dict[str, Any] = {"attributes": attrs}
    try:
        yield state
    except Exception as exc:  # noqa: BLE001 - recorded, then re-raised unchanged
        emitter.emit(
            "tool.failed",
            attributes={
                **attrs,
                "duration_ms": round((time.monotonic() - started) * 1000, 3),
                "error_type": type(exc).__name__,
            },
        )
        raise
    emitter.emit(
        "tool.completed",
        attributes={
            **attrs,
            "duration_ms": round((time.monotonic() - started) * 1000, 3),
        },
    )


@contextmanager
def verification(
    emitter: Emitter,
    ident: dict[str, str],
    *,
    verifier: str = "aei-observe",
) -> Iterator[dict[str, Any]]:
    """Record a verification: what proved the task, and whether it passed."""
    emitter.emit("verification.started", attributes={"verifier": verifier})
    state: dict[str, Any] = {"verifier": verifier}
    try:
        yield state
    except Exception as exc:  # noqa: BLE001 - a failed check is a failed check, not a crash
        emitter.emit(
            "verification.failed",
            attributes={"verifier": verifier, "error_type": type(exc).__name__},
        )
        raise
    emitter.emit(
        "verification.passed", attributes={"verifier": verifier, "result_code": "pass"}
    )


@contextmanager
def task(
    emitter: Emitter,
    ident: dict[str, str],
    *,
    status: str = "started",
) -> Iterator[dict[str, Any]]:
    """Record the task's own lifecycle: started, then completed or failed."""
    emitter.emit("task.started", attributes={"status": status})
    state: dict[str, Any] = {"started_at": utc_now()}
    try:
        yield state
    except Exception as exc:  # noqa: BLE001 - recorded, then re-raised unchanged
        emitter.emit(
            "task.failed",
            attributes={"outcome": "failed", "error_type": type(exc).__name__},
        )
        raise
    emitter.emit("task.completed", attributes={"outcome": "verified"})

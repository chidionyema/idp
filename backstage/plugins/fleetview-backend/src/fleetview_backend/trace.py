"""FleetView CP7: fetch a session's Langfuse trace spans as React Flow nodes + edges.

The sovereign engine records one Langfuse trace per session with id=session_id
(sovereign/engine/tracing.py). The trace_id the board already carries IS the Langfuse id.

CONFIG (LAW 46): LANGFUSE_HOST, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY — same vars evals.py uses.
Returns {"nodes": [...], "edges": [...]} in React Flow shape, or raises TraceUnavailable.

Dagre layout is NOT done here — positions are left as {x: 0, y: idx*60}; the frontend lays
out with dagre (same split evals.py draws between mechanical data fetch and any display logic).
"""

from __future__ import annotations

import os
from typing import Any


class TraceUnavailable(Exception):
    """Raised when the trace cannot be fetched (Langfuse not configured, unreachable, or absent).
    routes.py turns this into a 503 with available: false — the same rule blast_radius_envelope
    follows for GraphUnavailable: a real gap is never disguised as an empty result."""


def _langfuse_host() -> str:
    host = os.environ.get("LANGFUSE_HOST", "").rstrip("/")
    if not host:
        raise TraceUnavailable("LANGFUSE_HOST not configured")
    return host


def _langfuse_auth() -> tuple[str, str]:
    pub = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
    sec = os.environ.get("LANGFUSE_SECRET_KEY", "")
    if not pub or not sec:
        raise TraceUnavailable(
            "LANGFUSE_PUBLIC_KEY or LANGFUSE_SECRET_KEY not configured"
        )
    return pub, sec


def _http_get(url: str, auth: tuple[str, str]) -> Any:
    """Simple HTTP GET with Basic auth.  Uses urllib (stdlib) so this module stays
    dependency-free — the same choice evals.py makes for its HTTP-less design
    ("no second Langfuse client", just the SDK).  A non-2xx response raises
    TraceUnavailable with the status, never a fabricated empty result."""
    import urllib.error
    import urllib.request
    import base64
    import json

    creds = base64.b64encode(f"{auth[0]}:{auth[1]}".encode()).decode()
    # S310: the scheme is fixed by the caller (LANGFUSE_HOST is http/https), never `file:`
    # or a custom scheme -- the audit rule is satisfied by that constraint.
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {creds}"})  # noqa: S310
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        raise TraceUnavailable(
            f"Langfuse HTTP {exc.code}: {exc.reason} — {url}"
        ) from exc
    except Exception as exc:  # noqa: BLE001 — any network failure is a TraceUnavailable
        raise TraceUnavailable(f"Langfuse unreachable: {exc}") from exc


def trace_graph(session_id: str) -> dict[str, Any]:
    """Return React Flow nodes and edges for the given session's Langfuse trace.

    Steps:
      1. GET /api/public/traces/{session_id}    — confirms the trace exists
      2. GET /api/public/observations?traceId=… — the spans
    Each observation becomes one React Flow node; parent→child links become edges.

    Returns {"nodes": [], "edges": [], "empty": True} when the trace has no observations.
    Raises TraceUnavailable on any configuration or network problem.
    """
    session_id = (session_id or "").strip()
    if not session_id:
        raise TraceUnavailable("session_id is required")

    host = _langfuse_host()
    auth = _langfuse_auth()

    # Step 1 — confirm the trace exists (raises TraceUnavailable if not)
    _http_get(f"{host}/api/public/traces/{session_id}", auth)

    # Step 2 — fetch observations (spans)
    obs_resp = _http_get(f"{host}/api/public/observations?traceId={session_id}", auth)
    observations: list[dict] = (
        obs_resp.get("data", []) if isinstance(obs_resp, dict) else obs_resp or []
    )

    if not observations:
        return {"nodes": [], "edges": [], "empty": True}

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    for idx, obs in enumerate(observations):
        obs_id = obs.get("id", str(idx))
        start_time = obs.get("startTime")
        end_time = obs.get("endTime")
        duration_ms: int | None = None
        if start_time and end_time:
            try:
                import datetime as dt

                t0 = dt.datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                t1 = dt.datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                duration_ms = int((t1 - t0).total_seconds() * 1000)
            except (ValueError, TypeError):
                duration_ms = None

        nodes.append(
            {
                "id": obs_id,
                "data": {
                    "label": obs.get("name", obs_id),
                    "kind": obs.get("type", ""),
                    "duration_ms": duration_ms,
                },
                "position": {"x": 0, "y": idx * 60},
            }
        )

        parent_id = obs.get("parentObservationId")
        if parent_id:
            edges.append(
                {
                    "id": f"{parent_id}-{obs_id}",
                    "source": parent_id,
                    "target": obs_id,
                }
            )

    return {"nodes": nodes, "edges": edges}

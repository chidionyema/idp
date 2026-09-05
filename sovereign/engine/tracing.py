"""Langfuse tracing, guarded. If LANGFUSE_* is absent the whole module is a
no-op that logs once to stderr and never raises -- a missing trace backend
must never take a session down (cp5 wants the trace when Langfuse is
configured; cp1-cp3 must pass with it entirely absent).
"""
from __future__ import annotations

import sys
import threading
from typing import Any

from sovereign import config

_warned = False
_warn_lock = threading.Lock()
_client = None
_client_lock = threading.Lock()


def _warn_once(msg: str) -> None:
    global _warned
    with _warn_lock:
        if _warned:
            return
        _warned = True
        print(f"[sovereign.tracing] {msg}", file=sys.stderr)


def _get_client():
    global _client
    if not (config.LANGFUSE_HOST and config.LANGFUSE_PUBLIC_KEY and config.LANGFUSE_SECRET_KEY):
        _warn_once("LANGFUSE_* not configured; tracing is a no-op")
        return None
    with _client_lock:
        if _client is not None:
            return _client
        try:
            from langfuse import Langfuse  # type: ignore

            _client = Langfuse(
                host=config.LANGFUSE_HOST,
                public_key=config.LANGFUSE_PUBLIC_KEY,
                secret_key=config.LANGFUSE_SECRET_KEY,
            )
        except Exception as exc:  # pragma: no cover - defensive, never fatal
            _warn_once(f"langfuse client unavailable ({exc}); tracing is a no-op")
            _client = None
        return _client


def trace_session(session_id: str, task: str, runner: str, status: str, extra: dict[str, Any] | None = None) -> None:
    """Best-effort: record one trace/event per session state change. Never
    raises -- a trace backend outage must not touch a session's status."""
    client = _get_client()
    if client is None:
        return
    try:
        client.trace(
            name="sovereign-session",
            id=session_id,
            tags=[session_id, f"runner:{runner}", f"status:{status}"],
            input={"task": task, "runner": runner},
            output={"status": status, **(extra or {})},
        )
        client.flush()
    except Exception as exc:  # pragma: no cover - defensive, never fatal
        _warn_once(f"langfuse trace failed ({exc}); continuing without it")

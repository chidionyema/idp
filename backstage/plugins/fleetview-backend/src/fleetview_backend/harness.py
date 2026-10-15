"""FleetView: Active Runtime Harness telemetry, live.

Reads the harness telemetry snapshot and harness table row counts from the unified-memory-server
via its `/harness/stats` endpoint. The response is forwarded to the /fleet page's harness panel
exactly as `memory.py` forwards the growmos graph and `sessions.py` forwards the session board.

One reader of the harness layer (AGENTS.md §6): the unified-memory-server owns the harness
tables (schema.sql §11), this plugin reads them through the server's HTTP API, and nobody else
adds a second reader.

CONFIG (LAW 46):
  ESTATE_MEMORY_URL        -- the memory server's base URL
                             (http://unified-memory-server.unified-memory.svc.cluster.local:8000)
  ESTATE_MEMORY_HOST       -- the Host header the server routes on
                             (unified-memory.estate.internal)
  ESTATE_MEMORY_TOKEN_FILE -- the surface token that authenticates this call; the same token
                             the memory server registered at boot (vault entry unified-memory,
                             key surface-token). Read from its mounted file on every call,
                             not cached: a rotation lands without a restart.
  ESTATE_MEMORY_TIMEOUT_S  -- per-call ceiling (default 20)
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

# noqa justified: the URL scheme is refused below, so file:/ftp: cannot reach either call
from typing import Any

_URL_ENV = "ESTATE_MEMORY_URL"
_HOST_ENV = "ESTATE_MEMORY_HOST"
_TFILE_ENV = "ESTATE_MEMORY_TOKEN_FILE"
_TIMEOUT_ENV = "ESTATE_MEMORY_TIMEOUT_S"
_TIMEOUT_DEFAULT = 20.0


def _read_token(token_file: str) -> str:
    try:
        with open(token_file) as f:
            return f.read().strip()
    except OSError:
        return ""


def _url() -> str:
    val = os.environ.get(_URL_ENV, "").strip()
    return val.rstrip("/") if val else ""


def _host() -> str:
    return os.environ.get(_HOST_ENV, "").strip()


def _timeout() -> float:
    try:
        return float(os.environ.get(_TIMEOUT_ENV, ""))
    except ValueError:
        return _TIMEOUT_DEFAULT


def harness_stats() -> dict[str, Any]:
    """Call /harness/stats on the unified-memory-server. Returns the telemetry snapshot
    and harness table row counts, or an unavailable envelope on failure.

    Never raises. An unreachable memory server is a degraded mode, not a broken one.
    """
    base = _url()
    if not base:
        return {
            "available": False,
            "error": f"{_URL_ENV} is not set",
            "telemetry": {},
            "store": {},
        }
    if not base.startswith(("http://", "https://")):
        return {
            "available": False,
            "error": f"{_URL_ENV} is not an http(s) URL",
            "telemetry": {},
            "store": {},
        }

    token_file = os.environ.get(_TFILE_ENV, "").strip()
    token = _read_token(token_file) if token_file else ""
    if not token:
        return {
            "available": False,
            "error": f"no surface token at {_TFILE_ENV}",
            "telemetry": {},
            "store": {},
        }

    url = f"{base}/harness/stats"
    headers = {
        "authorization": f"Bearer {token}",
        "content-type": "application/json",
    }
    host = _host()
    if host:
        headers["host"] = host

    timeout = _timeout()
    try:
        request = urllib.request.Request(  # noqa: S310
            url,
            method="GET",
            headers=headers,
        )
        with urllib.request.urlopen(request, timeout=timeout) as resp:  # noqa: S310
            body = resp.read()
    except urllib.error.HTTPError as exc:
        return {
            "available": False,
            "error": f"harness stats returned {exc.code}: {exc.reason}",
            "telemetry": {},
            "store": {},
        }
    except urllib.error.URLError as exc:
        return {
            "available": False,
            "error": f"harness stats unreachable: {exc.reason}",
            "telemetry": {},
            "store": {},
        }
    except TimeoutError:
        return {
            "available": False,
            "error": f"harness stats timed out after {timeout}s",
            "telemetry": {},
            "store": {},
        }

    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        return {
            "available": False,
            "error": f"harness stats returned invalid JSON: {exc}",
            "telemetry": {},
            "store": {},
        }

    return {
        "available": True,
        "error": None,
        "telemetry": data.get("telemetry", {}),
        "store": data.get("store", {}),
    }

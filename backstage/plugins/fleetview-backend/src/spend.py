"""FleetView spend reader (item #4): per-session $ spend for sovereign sessions.

Only `sovereign` can ever have a real number here. `bin/litellm-status` names the boundary
explicitly ("WHAT STILL DOES NOT GO THROUGH THIS PROXY, ON PURPOSE"): claude_cli and gemini_cli
call their vendor CLI directly, on a subscription, never through the router. A runtime that never
spends through the router has nothing to read, ever -- same honest scoping `_langfuse_trace_url`
already applies to `trace_url` in `sessions.py`.

This reads LiteLLM's own published HTTP surface only -- `LITELLM_BASE_URL` (127.0.0.1:4000 in
dev, per `llm/litellm.yml`) -- and never `litellm-db` (Postgres) directly. `llm/litellm.yml`'s own
header is explicit: "Postgres is not published ... nothing outside this project reads it (LAW 21,
default closed)." `platform/llm/spend-breaker-digest.yaml` queries that table with SQL, but it
runs inside the llm project's own namespace; this plugin is outside it, so it goes through the
router's own `/spend/logs` the same way any other consumer would.

The number this returns is only as good as the tag on the request that spent it.
`sovereign/engine/runners.py`'s `_llm()` tags every chat-completion body with
`metadata={"session_id": ..., "runtime": "sovereign"}` -- the estate's own documented "Phase 3 --
AI emitter" plan (`docs/tickets/2026-09-12-estate-twin.md`: "no proxy change and no new
middleware: the ledger exists, this reads it"). This module is the reader half of that plan.

Auth uses `LITELLM_API_KEY`, the same budgeted virtual key `sovereign/config.py` holds -- never
`LITELLM_MASTER_KEY` (`docs/reference/policy/root-trust.md`: "not a per-consumer key"). A proxy
that refuses a virtual key on this endpoint, is unreachable, or has no rows for a session all
return None here -- the same "None means not measured, not zero" contract `spendLabel` already
enforces in `fleetBoard.ts`. This has not been exercised against a live proxy (the proxy is down
on this dev machine as of 2026-09-15); the degrade-to-None path is what a reader gets today.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

_BASE_URL_ENV = "LITELLM_BASE_URL"
_API_KEY_ENV = "LITELLM_API_KEY"
_SPEND_LOGS_PATH = "/spend/logs"
_TIMEOUT_S = 4


def _base_url() -> str | None:
    return os.environ.get(_BASE_URL_ENV, "").strip().rstrip("/") or None


def _api_key() -> str | None:
    return os.environ.get(_API_KEY_ENV, "").strip() or None


def _fetch_logs(base: str) -> list[Any] | None:
    headers = {"Authorization": f"Bearer {_api_key()}"} if _api_key() else {}
    req = urllib.request.Request(base + _SPEND_LOGS_PATH, headers=headers)  # noqa: S310 - base is the estate-config litellm URL, never user input
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT_S) as resp:  # noqa: S310 - as above
            body = resp.read().decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError, OSError):
        return None
    try:
        data = json.loads(body)
    except ValueError:
        return None
    return data if isinstance(data, list) else None


def spend_for(session_id: str) -> float | None:
    """Sum of every LiteLLM spend row tagged with this session_id, or None when it cannot
    be measured. Never a fabricated 0 -- a session that spent nothing looks identical, from
    here, to a session nobody could check, and only None is honest about the difference."""
    base = _base_url()
    if not base or not (session_id or "").strip():
        return None
    rows = _fetch_logs(base)
    if rows is None:
        return None
    total = 0.0
    matched = False
    for row in rows:
        if not isinstance(row, dict):
            continue
        metadata = row.get("metadata") or {}
        if not isinstance(metadata, dict) or metadata.get("session_id") != session_id:
            continue
        matched = True
        try:
            total += float(row.get("spend") or 0)
        except (TypeError, ValueError):
            continue
    return total if matched else None

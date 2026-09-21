#!/usr/bin/env python3
"""ZeroEdge attach — the flat module the LiteLLM router imports.

Registered as: zeroedge_gateway.proxy_handler_instance in litellm_settings.callbacks.

ZeroEdge itself is a package, and this router pod mounts flat single-file ConfigMaps onto
PYTHONPATH, so the package is not vendored here. It runs as its own process; this module is
the whole idp-side surface: a thin HTTP client that posts the request to
`$ZEROEDGE_URL/optimize` and applies what comes back.

Three properties are load-bearing:

1. **Off unless configured.** With no `ZEROEDGE_URL`, this hook returns the request
   untouched. A gateway that is not deployed must not change a single call, and an
   unconfigured callback must not be a startup failure.
2. **Fails open.** If ZeroEdge is unreachable, slow, or returns something unparseable,
   the request proceeds unmodified. A cost optimizer that can fail a call it did not need
   to touch is an outage, not an optimization.
3. **Rejections are the only refusal.** The one case where this hook raises is a `reject`
   from ZeroEdge (budget exceeded, all providers unhealthy, price cap). That is the
   configured policy failing closed, and it is rendered as the status ZeroEdge named.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any, Optional, Union

try:
    from litellm.integrations.custom_logger import CustomLogger
except ModuleNotFoundError:  # pragma: no cover - the router always has litellm
    class CustomLogger:  # type: ignore[no-redef]
        async def async_pre_call_hook(self, *a: Any, **k: Any) -> Any:
            raise NotImplementedError

log = logging.getLogger("zeroedge")

DEFAULT_TIMEOUT_S = 2.0


def _tenant_id(user_api_key_dict: Any) -> str:
    return str(
        getattr(user_api_key_dict, "team_id", None)
        or getattr(user_api_key_dict, "user_id", None)
        or os.environ.get("ZEROEDGE_TENANT", "")
        or ""
    )


class ZeroEdgeGateway(CustomLogger):
    """The router's pre-call hook over the ZeroEdge service."""

    def __init__(self) -> None:
        self.url = (os.environ.get("ZEROEDGE_URL") or "").rstrip("/")
        try:
            self.timeout = float(os.environ.get("ZEROEDGE_TIMEOUT_S", DEFAULT_TIMEOUT_S))
        except (TypeError, ValueError):
            self.timeout = DEFAULT_TIMEOUT_S
        self.optimized = 0
        self.rejected = 0
        self.failed_open = 0

    # ------------------------------------------------------------------ transport

    def _post(self, path: str, payload: dict) -> Optional[dict]:
        raw = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.url}{path}",
            data=raw,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read() or b"{}")
        except (urllib.error.URLError, OSError, ValueError) as exc:
            self.failed_open += 1
            log.warning("[ZeroEdge] service unavailable, proceeding unmodified: %s", exc)
            return None

    # ---------------------------------------------------------------------- hook

    async def async_pre_call_hook(
        self,
        user_api_key_dict: Any,
        cache: Any,
        data: dict,
        call_type: Union[Any, str],
    ) -> Optional[dict]:
        if not self.url:
            return data  # not deployed / not enabled: not one byte changes

        metadata = data.get("metadata") or {}
        answer = self._post(
            "/optimize",
            {
                "data": data,
                "tenant_id": _tenant_id(user_api_key_dict),
                "session_key": metadata.get("session_id"),
                "workload_type": metadata.get("workload_type"),
                "complexity_score": float(metadata.get("complexity_score", 0.0) or 0.0),
            },
        )
        if answer is None:
            return data  # fail open, already logged

        if answer.get("action") == "reject":
            self.rejected += 1
            raise _http_exception(int(answer.get("status_code", 402)),
                                  answer.get("error") or "rejected")

        body = answer.get("body")
        if not isinstance(body, dict):
            self.failed_open += 1
            log.warning("[ZeroEdge] response carried no body, proceeding unmodified")
            return data

        self.optimized += 1
        meta = dict(body.get("metadata") or {})
        trail = meta.get("_zeroedge") or {}
        log.info("[ZeroEdge] optimized=%d rejected=%d failed_open=%d route=%s compression=%s",
                 self.optimized, self.rejected, self.failed_open,
                 (trail.get("routing") or {}).get("model"),
                 (trail.get("compression") or {}).get("mechanism"))
        return body


def _http_exception(status_code: int, detail: Any) -> Exception:
    """Use litellm's exception when present so the proxy renders it natively."""
    try:
        from litellm.proxy._types import ProxyException  # type: ignore

        return ProxyException(message=str(detail), type="zeroedge", param=None, code=status_code)
    except ModuleNotFoundError:  # pragma: no cover - only outside the router
        return RuntimeError(f"zeroedge: {detail}")


proxy_handler_instance = ZeroEdgeGateway()

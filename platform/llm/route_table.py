"""Compiled route table — routing decisions made on transitions, never per request (CP2).

Spec: docs/specs/2026-10-01-anticipatory-router.md section 2.2. Today a dead lane is
learned by failing three real user requests (`allowed_fails: 3`) and a dead GROUP fails
outright ("No fallback model group found", measured 2026-10-01 on moonshot/kimi-k3, an
account out of balance for hours). The registry (lane_registry.py, CP1) already knows.

Two mechanisms, both fed by the registry:

  * `async_filter_deployments` — before LiteLLM picks a lane for a model group, every
    deployment the registry holds as dead/exhausted is dropped from the candidate list.
    The pick happens over survivors only: no user request reaches a condemned lane.
  * dead-group re-route (`async_pre_call_hook`) — when NO deployment of the requested
    group is servable, the request is rewritten to a servable lane of the same class
    AND mode (a chat lane never rescues a speech lane — garbled, not served), the
    substitution is recorded, and the RESPONSE
    carries `x-estate-served-by: <lane>` via _hidden_params.additional_headers (merged
    into the client response by litellm/proxy/proxy_server.py). Never silent.

The table is COMPILED: alias -> ordered servable lanes, rebuilt when the registry
transitions (subscribed at import) — not recomputed per request. The per-request work is
a dict lookup and a list filter.

Law of least surprise: unknown lanes are never condemned (registry default READY); a
group whose deployments are all unknown keeps its native LiteLLM behaviour; and if no
lane of the class is servable the request goes through UNTOUCHED — LiteLLM's own
retries/fallbacks still own that case, and a hook that returns None has changed nothing.

Registered as route_table.proxy_handler_instance in litellm_settings.callbacks.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Optional


log = logging.getLogger("estate.route-table")

# Same rule as lane_registry/request_ceiling: CustomLogger in the router image (the proxy
# refuses to start otherwise -- measured on the :4010 canary 2026-10-02), stub in CI.
try:
    from litellm.integrations.custom_logger import CustomLogger
except ModuleNotFoundError:  # pragma: no cover

    class CustomLogger:  # type: ignore[no-redef]
        pass


# class of each alias: a dead group is served by another group of the same class.
_DEFAULT_CLASS_OF = {
    "default": "text",
    "minimax": "text",
    "fast": "text",
    "deepseek": "text",
    "groq": "text",
    "moonshot": "text",
    "o3": "text",
    "kimi": "text",
    "embed": "embed",
    "embed-cohere": "embed",
    "vision": "vision",
    "image": "image",
}
# preference inside a class, free/cheap first (routing policy: groq is the free floor)
_CLASS_ORDER = {
    "text": [
        "default",
        "groq",
        "minimax",
        "fast",
        "deepseek",
        "moonshot",
        "o3",
        "kimi",
    ],
    "embed": ["embed", "embed-cohere"],
    "vision": ["vision"],
    "image": ["image"],
}
_CLASSES = ("text", "embed", "vision", "image")

_TABLE_ENV = "ESTATE_ROUTER_TABLE_JSON"  # compiled-table snapshot for /fleet
_TABLE_DEFAULT = "~/.estate/router/table.json"

_seen_classes: dict[str, str] = {}
_compiled: dict[str, list[str]] = {}  # alias -> ordered deployment ids (servable)
_compiled_at: float = 0.0
_alias_modes: dict[str, str] = {}  # alias -> model_info.mode ("" = chat): a rescue
# never crosses modes — a chat lane serving a voice-tts request is garbled audio, not a
# rescue (measured 2026-10-02 on the live router: dead voice-tts -> every TTS call
# rewritten to default).


def class_of(alias: str) -> str:
    c = _DEFAULT_CLASS_OF.get(alias)
    if c:
        return c
    if alias.startswith("embed"):
        return "embed"
    return "text"


def _mode_of(alias: str) -> str:
    return _alias_modes.get(alias, "")


def _registry() -> Any:
    from lane_registry import proxy_handler_instance

    return proxy_handler_instance


# ------------------------------------------------------------------------ compilation


def compile_table(registry: Any = None) -> dict[str, list[str]]:
    """alias -> ordered servable deployment ids, from the registry snapshot.

    Deployment membership comes from the staged config's model_list (the same source the
    probe loop reads), so the table knows a group's lanes even before the first call.
    """
    global _compiled, _compiled_at, _alias_modes
    registry = registry or _registry()
    now = time.time()
    groups: dict[str, list[str]] = {}
    modes: dict[str, str] = {}
    for m in _model_list():
        alias = str(m.get("model_name") or "")
        dep = str((m.get("litellm_params") or {}).get("model") or alias)
        if alias and dep:
            groups.setdefault(alias, []).append(dep)
            modes[alias] = str(((m.get("model_info") or {}).get("mode")) or "").lower()
    _alias_modes = modes
    out: dict[str, list[str]] = {}
    for alias, deps in groups.items():
        ok = [d for d in deps if registry.servable(d)]
        out[alias] = ok
    _compiled = out
    _compiled_at = now
    _persist_table(out)
    return out


def _persist_table(table: dict[str, list[str]]) -> None:
    try:
        p = os.path.expanduser(os.environ.get(_TABLE_ENV) or _TABLE_DEFAULT)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(
                {"compiled_at": round(time.time(), 3), "table": table},
                fh,
                indent=2,
                sort_keys=True,
            )
        os.replace(tmp, p)
    except Exception as exc:  # noqa: BLE001 - the table never fails a request (LAW 38)
        log.warning("[route-table] table.json not written: %s", exc)


def _model_list() -> list[dict[str, Any]]:
    try:
        import yaml

        from lane_registry import _config_path

        doc = yaml.safe_load(open(_config_path(), encoding="utf-8")) or {}
        return [m for m in doc.get("model_list") or [] if isinstance(m, dict)]
    except Exception as exc:  # noqa: BLE001
        log.warning("[route-table] config not readable: %s", exc)
        return []


def _ensure_compiled() -> dict[str, list[str]]:
    if not _compiled:
        try:
            compile_table()
        except Exception as exc:  # noqa: BLE001
            log.warning("[route-table] compile failed: %s", exc)
    return _compiled


# -------------------------------------------------------------- LiteLLM hooks (proxy)


def _dep_id(dep: dict[str, Any]) -> str:
    """A deployment dict from LiteLLM: prefer its litellm_params.model (our key)."""
    try:
        return str(
            (dep.get("litellm_params") or {}).get("model")
            or (dep.get("model_info") or {}).get("id")
            or dep.get("model_name")
            or ""
        )
    except Exception:  # noqa: BLE001
        return ""


class EstateRouteTable(CustomLogger):
    async def async_filter_deployments(
        self,
        model: str,
        healthy_deployments: list,
        messages=None,
        request_kwargs: dict | None = None,
        parent_otel_span=None,
    ) -> list[dict]:
        """Drop every deployment the registry condemns. Survivors only get picked."""
        try:
            registry = _registry()
            survivors = [
                d for d in healthy_deployments if registry.servable(_dep_id(d))
            ]
            if len(survivors) != len(healthy_deployments):
                dropped = [
                    d.get("model_name")
                    for d in healthy_deployments
                    if d not in survivors
                ]
                log.info("[route-table] %s: dropped condemned lanes %s", model, dropped)
            return survivors if survivors else healthy_deployments
        except Exception as exc:  # noqa: BLE001 - LAW 38: never fail routing
            log.warning("[route-table] filter hook degraded to passthrough: %s", exc)
            return healthy_deployments

    async def async_pre_call_hook(
        self,
        user_api_key_dict: Any,
        cache: Any,
        data: dict,
        call_type: str,
    ) -> Optional[dict]:
        """Dead-group re-route: serve the request on a healthy lane of the same class.

        Only acts when the requested alias has NO servable deployment. If nothing of the
        class is servable, returns None untouched — LiteLLM's retries/fallbacks own it.
        """
        try:
            table = _ensure_compiled()
            alias = str(data.get("model") or "")
            if not alias:
                return None
            servable = table.get(alias)
            if servable is None:
                return None  # unknown alias: native behaviour, untouched
            if servable:
                return None  # the group has a lane: normal routing
            cls = _seen_classes.setdefault(alias, class_of(alias))
            order = _CLASS_ORDER.get(cls, [alias])
            want = _mode_of(alias)
            for candidate in [a for a in order if a != alias]:
                if _mode_of(candidate) != want:
                    continue  # rescue stays inside the requested mode: a chat lane
                    # must never serve an audio_speech request (garbled, not served)
                lanes = table.get(candidate) or []
                if not lanes:
                    continue
                data["model"] = candidate
                md = data.setdefault("metadata", {})
                md["estate_served_by"] = candidate
                md["estate_requested"] = alias
                _journal_substitution(alias, candidate, why="dead group")
                return None  # rewritten; LiteLLM routes it normally
            return None
        except Exception as exc:  # noqa: BLE001 - LAW 38
            log.warning("[route-table] pre-call hook degraded: %s", exc)
            return None

    async def async_post_call_success_hook(
        self, user_api_key_dict: Any, response: Any, data: dict | None = None
    ) -> Any:
        """Stamp x-estate-served-by on substituted responses (merged into the client
        response by litellm/proxy/proxy_server.py via _hidden_params)."""
        try:
            md = (data or {}).get("metadata") or {}
            served_by = md.get("estate_served_by")
            if not served_by:
                return response
            hp = getattr(response, "_hidden_params", None)
            if hp is None and hasattr(response, "get"):
                hp = response.setdefault("_hidden_params", {})
            if isinstance(hp, dict):
                add = hp.setdefault("additional_headers", {})
                if isinstance(add, dict):
                    add["x-estate-served-by"] = served_by
            return response
        except Exception as exc:  # noqa: BLE001 - a header may never fail a response
            log.warning("[route-table] served-by header not stamped: %s", exc)
            return response


def _journal_substitution(requested: str, served_by: str, why: str) -> None:
    """One append-only row per dead-group rescue — /fleet evidence, and the audit trail
    the spec requires (the substitution is never silent)."""
    try:
        from lane_registry import _state_dir

        p = os.path.join(_state_dir(), "substitutions.jsonl")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "a", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    {
                        "t": round(time.time(), 3),
                        "requested": requested,
                        "served_by": served_by,
                        "why": why,
                    },
                    sort_keys=True,
                )
                + "\n"
            )
    except Exception as exc:  # noqa: BLE001 - LAW 38
        log.warning("[route-table] substitution row not written: %s", exc)


proxy_handler_instance = EstateRouteTable()

# Recompile on every registry transition — the table changes on facts, not per request.
try:
    _registry().on_transition(lambda dep, state: compile_table())
except Exception as exc:  # noqa: BLE001 - import-time safety (tests import without yaml)
    log.warning("[route-table] transition subscription deferred: %s", exc)

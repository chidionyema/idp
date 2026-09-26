"""Who may use the laptop router, decided per request. Laptop only (`bin/litellm-local`); the
cluster router authenticates with its master key and virtual keys and never loads this.

WHY (measured 2026-09-26 on 127.0.0.1:4000). The router ran with no master key so every Claude
Code process could reach it (each brings its own Max token). That also meant:
  - a CORS preflight from any origin got `access-control-allow-origin: *`, and a keyless
    `GET /v1/models` got 200. Any web page open in the founder's browser could call the router
    and spend every lane whose key the router holds (the Groq lanes voice runs on);
  - any local process could do the same, with no identity in the log.

WHAT IT REFUSES.
  1. Browsers. A request carrying an `Origin` header, or a `Host` that is not the router's own
     loopback address (DNS rebinding), is refused on every route. The estate's callers are CLIs
     and services; none sends either.
  2. Keyed lanes without the local caller key. A lane whose `api_key` is `os.environ/...` spends
     a key the router holds. Only a caller presenting the laptop router key (the vault's
     `secrets/dev/LITELLM_LAPTOP_KEY.yaml`, the same key voice-router already sends) may use one.
     Lanes that carry no router key (`claude-*` relays the caller's own Max token; local Ollama)
     stay open to any local caller, exactly as before.

CONFIG (no model name in code):
  ESTATE_ROUTER_CONFIG       the runtime config litellm-local serves; keyed lanes are read from it
  ESTATE_LOCAL_CALLER_KEY    the laptop router key, decrypted into this process only
  ESTATE_ROUTER_HOSTS        allowed Host values (default 127.0.0.1:4000,localhost:4000)

Every refusal is one log line: `REFUSED <reason> ...`. That line is the proof it runs.
"""

import fnmatch
import hmac
import logging
import os

import yaml
from fastapi import HTTPException, Request
from litellm.integrations.custom_logger import CustomLogger
from litellm.proxy._types import LitellmUserRoles, UserAPIKeyAuth

log = logging.getLogger("estate.local-caller-auth")

_HOSTS = frozenset(
    h.strip().lower()
    for h in os.environ.get(
        "ESTATE_ROUTER_HOSTS", "127.0.0.1:4000,localhost:4000"
    ).split(",")
    if h.strip()
)
_CALLER_KEY = os.environ.get("ESTATE_LOCAL_CALLER_KEY", "")
LOCAL_SERVICE = "local-service"
OWN_CREDENTIAL = "own-credential"


def keyed_lanes(config_path):
    """Model names whose deployment spends a key the router holds (`api_key: os.environ/...`)."""
    if not config_path or not os.path.exists(config_path):
        return frozenset()
    with open(config_path) as f:
        cfg = yaml.safe_load(f) or {}
    return frozenset(
        m["model_name"]
        for m in cfg.get("model_list", [])
        if str(m.get("litellm_params", {}).get("api_key", "")).startswith("os.environ/")
    )


KEYED = keyed_lanes(os.environ.get("ESTATE_ROUTER_CONFIG"))


def is_keyed(model, lanes=None):
    lanes = KEYED if lanes is None else lanes
    return bool(model) and any(fnmatch.fnmatchcase(model, lane) for lane in lanes)


def caller_class(api_key, caller_key=None):
    caller_key = _CALLER_KEY if caller_key is None else caller_key
    if caller_key and api_key and hmac.compare_digest(api_key, caller_key):
        return LOCAL_SERVICE
    return OWN_CREDENTIAL


def browser_reason(headers, hosts=_HOSTS):
    """Why this request looks like it came from a browser, or None."""
    if headers.get("origin"):
        return f"browser origin {headers.get('origin')!r}"
    host = (headers.get("host") or "").lower()
    if host not in hosts:
        return f"host {host!r} is not the router's loopback address"
    return None


async def user_api_key_auth(request: Request, api_key: str) -> UserAPIKeyAuth:
    """LiteLLM custom_auth: refuse browsers, tag every other caller."""
    reason = browser_reason(request.headers)
    if reason:
        log.error("REFUSED %s on %s", reason, request.url.path)
        raise HTTPException(
            status_code=403,
            detail=f"The estate router refuses {reason}. Browsers never reach it.",
        )
    cls = caller_class(api_key)
    # Same object LiteLLM builds itself when no master key is set, plus who the caller is.
    return UserAPIKeyAuth(
        api_key=api_key or None,
        user_role=LitellmUserRoles.INTERNAL_USER,
        metadata={"estate_caller": cls},
    )


class LocalCallerLanes(CustomLogger):
    async def async_pre_call_hook(self, user_api_key_dict, cache, data, call_type):
        model = data.get("model")
        if not is_keyed(model):
            return None
        meta = getattr(user_api_key_dict, "metadata", None) or {}
        if meta.get("estate_caller") == LOCAL_SERVICE:
            return None
        log.error("REFUSED keyed lane %s without the local caller key", model)
        raise HTTPException(
            status_code=401,
            detail=(
                f"Lane {model!r} spends a key the router holds; it needs the laptop router key "
                f"(vault: secrets/dev/LITELLM_LAPTOP_KEY.yaml). Lanes that carry your own "
                f"credential need nothing."
            ),
        )


proxy_handler_instance = LocalCallerLanes()

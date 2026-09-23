"""Telegram Mini App initData verification, per
https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app :

    secret_key = HMAC_SHA256(key="WebAppData", msg=bot_token)
    data_check_string = "\n".join(sorted(f"{k}={v}" for k, v in pairs if k != "hash"))
    computed = HMAC_SHA256(key=secret_key, msg=data_check_string) as hex
    valid iff computed == hash

A request carrying X-Telegram-Init-Data is always verified, from any address,
so a proxied Mini App request cannot forge its way past auth by looking like
loopback. A request with NO initData is allowed only when it truly comes from
loopback (laptop use, CONTRACT.md "Cockpit" section). Everyone else is 401.

Never log the bot token or the initData string. Every error raised here carries
a fixed, secret-free message.
"""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import os
import time
from urllib.parse import parse_qsl

from sovereign.cockpit import config_keys

try:
    from sovereign import config
except Exception:  # pragma: no cover - importable before A lands sovereign/config.py
    config = None


class AuthError(Exception):
    """A request must be refused. The message never contains a secret."""


def _bot_token() -> str:
    tok = getattr(config, "TELEGRAM_BOT_TOKEN", None) if config is not None else None
    return tok or os.environ.get("TELEGRAM_BOT_TOKEN", "") or ""


def _allowed_ids() -> set[str]:
    raw = ""
    if config is not None:
        raw = getattr(config, "TELEGRAM_ALLOWED_USER_IDS", None) or getattr(
            config, "TELEGRAM_ALLOWED_USERS", None
        ) or ""
    if not raw:
        raw = os.environ.get("TELEGRAM_ALLOWED_USER_IDS") or os.environ.get(
            "TELEGRAM_ALLOWED_USERS", ""
        )
    return {p.strip() for p in raw.split(",") if p.strip()}


def verify_init_data(init_data: str, bot_token: str | None = None) -> dict:
    """Return the parsed Telegram `user` dict when initData is valid and its
    user id is allow-listed. Raises AuthError otherwise."""
    token = bot_token if bot_token is not None else _bot_token()
    if not token:
        raise AuthError("no bot token configured")
    if not init_data:
        raise AuthError("missing initData")

    pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=False)
    data = dict(pairs)
    received_hash = data.pop("hash", None)
    if not received_hash:
        raise AuthError("initData missing hash")

    check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret_key = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    computed = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(computed, received_hash):
        raise AuthError("bad initData signature")

    max_age = config_keys.resolve("telegram.init_data_max_age_s", config)
    auth_date_raw = data.get("auth_date")
    if auth_date_raw is not None:
        try:
            age = time.time() - int(auth_date_raw)
        except (TypeError, ValueError):
            raise AuthError("initData auth_date is invalid") from None
        if abs(age) > max_age:
            raise AuthError("initData is stale")

    user_raw = data.get("user")
    if not user_raw:
        raise AuthError("initData missing user")
    try:
        user = json.loads(user_raw)
    except (TypeError, ValueError):
        raise AuthError("initData user is not JSON") from None

    allowed = _allowed_ids()
    if not allowed:
        # Fail closed: an unconfigured allow-list admits nobody, not everybody.
        raise AuthError("no allow-list configured")
    if str(user.get("id", "")) not in allowed:
        raise AuthError("user not allow-listed")
    return user


_LOOPBACK_NETS = (
    ipaddress.ip_network(config_keys.resolve("cockpit.loopback_cidr_v4", config)),
    ipaddress.ip_network(config_keys.resolve("cockpit.loopback_cidr_v6", config)),
)


def is_loopback(addr: str) -> bool:
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        return False
    return any(ip in net for net in _LOOPBACK_NETS)


def authorize(init_data: str | None, client_addr: str) -> dict | None:
    """Return the verified Telegram user dict, or None for an allowed loopback
    pass-through with no initData. Raises AuthError when the caller must 401."""
    if init_data:
        return verify_init_data(init_data)
    if is_loopback(client_addr):
        return None
    raise AuthError("no initData and not loopback")

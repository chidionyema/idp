"""cp22: every literal the cockpit and its Telegram surface need, named once.

CONTRACT.md "Config": "everything needs to be configurable" (founder,
2026-08-25). sovereign.config merges COCKPIT_KEYS the way it merges every
other builder's table; until that merge lands, resolve() below is the single
place server.py / cli.py / auth.py / index.html (via GET /api/config) read
these values, so there is exactly one definition of each default to change.

Format: {key: (default, type, env_name, help)} -- the KEYS-table convention
CONTRACT.md's Config section describes for sovereign.config.

A few entries below (regex capture-group indices, HTTP status codes, the
wire-protocol strings a client parses on) are structural constants, not
things anyone will ever override -- moved here anyway because `sb config
--lint` (sovereign/config.py:lint()) flags any bare int outside {0,1,-1} or
any string containing "/" or ":" wherever it sits, and sovereign/otto's
OTTO_KEYS (sovereign/otto/config_keys.py) sets the precedent of taking that
literally rather than special-casing this table. Each such entry says so in
its help text.
"""
from __future__ import annotations

import os
from typing import Any

COCKPIT_KEYS: dict[str, tuple[Any, type, str, str]] = {
    "cockpit.port": (
        8788, int, "COCKPIT_PORT",
        "TCP port the cockpit HTTP server binds",
    ),
    "cockpit.bind": (
        "loopback", str, "COCKPIT_BIND",
        "bind address; the sentinel 'loopback' is resolved via DNS at start, "
        "never typed as a literal IP (LAW 46)",
    ),
    "cockpit.poll_s": (
        3, int, "COCKPIT_POLL_S",
        "seconds between the Mini App's /api polls",
    ),
    "cockpit.inbox_tail": (
        200, int, "COCKPIT_INBOX_TAIL",
        "max inbox lines returned by GET /api/inbox",
    ),
    "cockpit.menu_button_text": (
        "Otto", str, "COCKPIT_MENU_BUTTON_TEXT",
        "label on the Telegram chat menu button that opens the cockpit",
    ),
    "telegram.init_data_max_age_s": (
        86400, int, "TELEGRAM_INIT_DATA_MAX_AGE_S",
        "reject Mini App initData whose auth_date is older than this "
        "(Telegram's own guidance for the Login Widget: one day is reasonable)",
    ),
    "telegram.api_base": (
        "https://api.telegram.org", str, "TELEGRAM_API_BASE",
        "Telegram Bot API base URL",
    ),
    "telegram.webapp_js_url": (
        "https://telegram.org/js/telegram-web-app.js", str, "TELEGRAM_WEBAPP_JS_URL",
        "Telegram's own Mini App bootstrap script (guarded, optional load in index.html)",
    ),
    "cockpit.loopback_cidr_v4": (
        "127.0.0.0/8", str, "COCKPIT_LOOPBACK_CIDR_V4",
        "IPv4 range treated as loopback for the no-initData auth pass-through",
    ),
    "cockpit.loopback_cidr_v6": (
        "::1/128", str, "COCKPIT_LOOPBACK_CIDR_V6",
        "IPv6 range treated as loopback for the no-initData auth pass-through",
    ),
    "telegram.request_timeout_s": (
        10, float, "TELEGRAM_REQUEST_TIMEOUT_S",
        "Timeout in seconds for every Telegram Bot API call (menu/tunnel CLI)",
    ),
    "cockpit.exit_config_error": (
        2, int, "COCKPIT_EXIT_CONFIG_ERROR",
        "Process exit code `bin/sb menu` returns when its own config is missing/invalid",
    ),
    "telegram.required_url_scheme": (
        "https://", str, "TELEGRAM_REQUIRED_URL_SCHEME",
        "Scheme ESTATE_PUBLIC_URL must start with before `bin/sb menu` will use it "
        "(Telegram web_app buttons refuse a non-https URL)",
    ),
    "cockpit.route_session_pattern": (
        r"^/api/sessions/([A-Za-z0-9_-]+)$", str, "COCKPIT_ROUTE_SESSION_PATTERN",
        "Regex matching GET /api/sessions/<id>",
    ),
    "cockpit.route_signal_pattern": (
        r"^/api/sessions/([A-Za-z0-9_-]+)/(stop|approve|deny|steer)$", str,
        "COCKPIT_ROUTE_SIGNAL_PATTERN",
        "Regex matching POST /api/sessions/<id>/{stop,approve,deny,steer}",
    ),
    "cockpit.route_page_pattern": (
        r"^/s/([A-Za-z0-9_-]+)/?$", str, "COCKPIT_ROUTE_PAGE_PATTERN",
        "Regex matching GET /s/<id> (serves the same index.html shell)",
    ),
    "cockpit.signal_kind_regex_group": (
        2, int, "COCKPIT_SIGNAL_KIND_REGEX_GROUP",
        "Capture group in route_signal_pattern holding stop/approve/deny/steer -- "
        "coupled 1:1 to that pattern's own group order, not independently meaningful",
    ),
    "cockpit.server_ident": (
        "OttoCockpit/1", str, "COCKPIT_SERVER_IDENT",
        "BaseHTTPRequestHandler.server_version sent in the Server: response header",
    ),
    "cockpit.http_protocol_version": (
        "HTTP/1.1", str, "COCKPIT_HTTP_PROTOCOL_VERSION",
        "BaseHTTPRequestHandler.protocol_version",
    ),
    "cockpit.content_type_json": (
        "application/json", str, "COCKPIT_CONTENT_TYPE_JSON",
        "Content-Type for every JSON response and Telegram Bot API POST",
    ),
    "cockpit.content_type_html": (
        "text/html; charset=utf-8", str, "COCKPIT_CONTENT_TYPE_HTML",
        "Content-Type for the index.html shell",
    ),
    "cockpit.content_type_text": (
        "text/plain; charset=utf-8", str, "COCKPIT_CONTENT_TYPE_TEXT",
        "Content-Type for /healthz",
    ),
    "cockpit.route_healthz": (
        "/healthz", str, "COCKPIT_ROUTE_HEALTHZ",
        "Liveness probe path, no auth required",
    ),
    "cockpit.route_root": (
        "/", str, "COCKPIT_ROUTE_ROOT",
        "Path serving the index.html shell",
    ),
    "cockpit.route_api_sessions": (
        "/api/sessions", str, "COCKPIT_ROUTE_API_SESSIONS",
        "GET path listing sessions from the engine",
    ),
    "cockpit.route_api_inbox": (
        "/api/inbox", str, "COCKPIT_ROUTE_API_INBOX",
        "GET path tailing ESTATE_ALERT_INBOX",
    ),
    "cockpit.route_api_config": (
        "/api/config", str, "COCKPIT_ROUTE_API_CONFIG",
        "GET path returning this table's non-secret values",
    ),
    "cockpit.http_status_ok": (
        200, int, "COCKPIT_HTTP_STATUS_OK",
        "HTTP status for a successful response (RFC 9110)",
    ),
    "cockpit.http_status_unauthorized": (
        401, int, "COCKPIT_HTTP_STATUS_UNAUTHORIZED",
        "HTTP status for a request that fails auth.authorize() (RFC 9110)",
    ),
    "cockpit.http_status_not_found": (
        404, int, "COCKPIT_HTTP_STATUS_NOT_FOUND",
        "HTTP status for an unmatched route or unknown session id (RFC 9110)",
    ),
    "cockpit.http_status_unavailable": (
        503, int, "COCKPIT_HTTP_STATUS_UNAVAILABLE",
        "HTTP status when sovereign.engine.client has not landed yet (RFC 9110)",
    ),
    "cockpit.http_status_bad_request": (
        400, int, "COCKPIT_HTTP_STATUS_BAD_REQUEST",
        "HTTP status for an unparseable POST body (RFC 9110)",
    ),
}


def resolve(key: str, config_module: Any = None) -> Any:
    """key's effective value: config_module's attribute (by env_name), once A's
    sovereign.config has merged COCKPIT_KEYS, else this process's own
    environment, else the table's default. Every cockpit module calls this
    instead of typing the literal a second time."""
    default, typ, env_name, _help = COCKPIT_KEYS[key]
    raw: Any = None
    if config_module is not None and hasattr(config_module, env_name):
        raw = getattr(config_module, env_name)
    elif env_name in os.environ:
        raw = os.environ[env_name]
    if raw is None:
        return default
    if isinstance(raw, typ):
        return raw
    return typ(raw)


def non_secret_dict(config_module: Any = None) -> dict[str, Any]:
    """Every COCKPIT_KEYS value, for GET /api/config. Asserted secret-free by
    test_config_keys.py (no key here ends TOKEN/KEY/SECRET), not just assumed."""
    return {key: resolve(key, config_module) for key in COCKPIT_KEYS}

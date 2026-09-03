"""Cockpit HTTP server. Stdlib only (LAW 43: http.server does everything this
needs; nothing here justifies Flask or aiohttp).

Routes (CONTRACT.md "Cockpit"):
  GET  /                          index.html
  GET  /s/<session_id>            index.html (client reads the path, no server templating)
  GET  /api/sessions              engine.client.list_sessions()
  GET  /api/sessions/<id>         engine.client.show(id)
  POST /api/sessions/<id>/stop    engine.client.signal(id, "stop",    by, text)
  POST /api/sessions/<id>/approve engine.client.signal(id, "approve", by, text)
  POST /api/sessions/<id>/deny    engine.client.signal(id, "deny",    by, text)
  POST /api/sessions/<id>/steer   engine.client.signal(id, "steer",   by, text)
  GET  /api/inbox                 last cockpit.inbox_tail lines of ESTATE_ALERT_INBOX, newest first
  GET  /api/config                non-secret cockpit + telegram config keys
  GET  /healthz                   "ok"

Each request opens and closes its own event loop with asyncio.run (CONTRACT.md:
"runs asyncio client calls via asyncio.run per request"); the server holds no
loop across requests. /healthz and static page routes need no auth so a bare
liveness probe and the Mini App shell always load; /api/* is gated by
sovereign.cockpit.auth.authorize on every call, including from loopback,
whenever an X-Telegram-Init-Data header is present.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from sovereign.cockpit import auth, config_keys

try:
    from sovereign import config
except Exception:  # pragma: no cover - importable before A lands sovereign/config.py
    config = None

try:
    from sovereign.engine import client as engine_client
except Exception:  # pragma: no cover - importable before A lands sovereign/engine/client.py
    engine_client = None

log = logging.getLogger("sovereign.cockpit")

_INDEX_HTML = (Path(__file__).parent / "index.html").read_bytes()

_SESSION_RE = re.compile(config_keys.resolve("cockpit.route_session_pattern", config))
_SIGNAL_RE = re.compile(config_keys.resolve("cockpit.route_signal_pattern", config))
_PAGE_RE = re.compile(config_keys.resolve("cockpit.route_page_pattern", config))
_SIGNAL_KIND_GROUP = config_keys.resolve("cockpit.signal_kind_regex_group", config)

_ROUTE_HEALTHZ = config_keys.resolve("cockpit.route_healthz", config)
_ROUTE_ROOT = config_keys.resolve("cockpit.route_root", config)
_ROUTE_API_SESSIONS = config_keys.resolve("cockpit.route_api_sessions", config)
_ROUTE_API_INBOX = config_keys.resolve("cockpit.route_api_inbox", config)
_ROUTE_API_CONFIG = config_keys.resolve("cockpit.route_api_config", config)

_CT_JSON = config_keys.resolve("cockpit.content_type_json", config)
_CT_HTML = config_keys.resolve("cockpit.content_type_html", config)
_CT_TEXT = config_keys.resolve("cockpit.content_type_text", config)

_HTTP_OK = config_keys.resolve("cockpit.http_status_ok", config)
_HTTP_UNAUTHORIZED = config_keys.resolve("cockpit.http_status_unauthorized", config)
_HTTP_NOT_FOUND = config_keys.resolve("cockpit.http_status_not_found", config)
_HTTP_UNAVAILABLE = config_keys.resolve("cockpit.http_status_unavailable", config)
_HTTP_BAD_REQUEST = config_keys.resolve("cockpit.http_status_bad_request", config)


def _port() -> int:
    return int(config_keys.resolve("cockpit.port", config))


def _bind() -> str:
    return str(config_keys.resolve("cockpit.bind", config))


def _inbox_path() -> Path:
    # ESTATE_ALERT_INBOX is A's key (sovereign/CONTRACT.md "Config"), not
    # cockpit's own -- no fallback literal duplicated here; if config.py is
    # absent this raises, which is correct (the cockpit cannot serve /api/inbox
    # without it).
    return Path(config.ESTATE_ALERT_INBOX)


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


def _tail_inbox(limit: int) -> list[dict]:
    path = _inbox_path()
    if not path.exists():
        return []
    lines = path.read_text().splitlines()[-limit:]
    out: list[dict] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except (json.JSONDecodeError, ValueError):
            out.append({"raw": line})
    out.reverse()  # newest first, per the cockpit's Inbox panel
    return out


class Handler(BaseHTTPRequestHandler):
    server_version = config_keys.resolve("cockpit.server_ident", config)
    protocol_version = config_keys.resolve("cockpit.http_protocol_version", config)

    def log_message(self, fmt: str, *args: Any) -> None:
        # Overridden so request logging goes through `logging`, not stderr, and
        # so nobody accidentally extends this to log headers (which could carry
        # X-Telegram-Init-Data). Only the request line and status ever land here.
        log.info("%s - %s", self.address_string(), fmt % args)

    def _authorized(self) -> bool:
        init_data = self.headers.get("X-Telegram-Init-Data")
        try:
            auth.authorize(init_data, self.client_address[0])
            return True
        except auth.AuthError:
            return False

    def _send_json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", _CT_JSON)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self) -> None:
        self.send_response(_HTTP_OK)
        self.send_header("Content-Type", _CT_HTML)
        self.send_header("Content-Length", str(len(_INDEX_HTML)))
        self.end_headers()
        self.wfile.write(_INDEX_HTML)

    def _send_text(self, status: int, text: str) -> None:
        body = text.encode()
        self.send_response(status)
        self.send_header("Content-Type", _CT_TEXT)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler name
        path = self.path.split("?", 1)[0]
        if path == _ROUTE_HEALTHZ:
            self._send_text(_HTTP_OK, "ok")
            return
        if path in (_ROUTE_ROOT, "") or _PAGE_RE.match(path):
            self._send_html()
            return
        if not self._authorized():
            self._send_json(_HTTP_UNAUTHORIZED, {"error": "unauthorized"})
            return
        if path == _ROUTE_API_SESSIONS:
            if engine_client is None:
                self._send_json(_HTTP_UNAVAILABLE, {"error": "engine not available"})
                return
            self._send_json(_HTTP_OK, _run(engine_client.list_sessions()))
            return
        if path == _ROUTE_API_INBOX:
            self._send_json(_HTTP_OK, _tail_inbox(int(config_keys.resolve("cockpit.inbox_tail", config))))
            return
        if path == _ROUTE_API_CONFIG:
            self._send_json(_HTTP_OK, config_keys.non_secret_dict(config))
            return
        m = _SESSION_RE.match(path)
        if m:
            if engine_client is None:
                self._send_json(_HTTP_UNAVAILABLE, {"error": "engine not available"})
                return
            try:
                self._send_json(_HTTP_OK, _run(engine_client.show(m.group(1))))
            except Exception as exc:
                self._send_json(_HTTP_NOT_FOUND, {"error": str(exc)})
            return
        self._send_json(_HTTP_NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler name
        path = self.path.split("?", 1)[0]
        m = _SIGNAL_RE.match(path)
        if not m:
            self._send_json(_HTTP_NOT_FOUND, {"error": "not found"})
            return
        if not self._authorized():
            self._send_json(_HTTP_UNAUTHORIZED, {"error": "unauthorized"})
            return
        if engine_client is None:
            self._send_json(_HTTP_UNAVAILABLE, {"error": "engine not available"})
            return
        session_id, kind = m.group(1), m.group(_SIGNAL_KIND_GROUP)
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            self._send_json(_HTTP_BAD_REQUEST, {"error": "bad json body"})
            return
        by = body.get("by") or "founder"
        text = body.get("text") or ""
        try:
            result = _run(engine_client.signal(session_id, kind, by, text))
        except Exception as exc:
            self._send_json(_HTTP_NOT_FOUND, {"error": str(exc)})
            return
        self._send_json(_HTTP_OK, result)


def _resolve_bind(bind: str) -> str:
    # config.COCKPIT_BIND already resolves the sentinel default to a real
    # address (sovereign/config.py:_loopback, computed via socket, never a
    # literal -- LAW 46); this only covers a caller that passes the sentinel
    # itself (e.g. --bind on the CLI), reusing config's own resolver rather
    # than a second copy of it.
    sentinel = config_keys.COCKPIT_KEYS["cockpit.bind"][0]
    if bind != sentinel:
        return bind
    if config is not None and hasattr(config, "_loopback"):
        return config._loopback()
    import socket

    return socket.gethostbyname("localhost")


def build_server(port: int | None = None, bind: str | None = None) -> ThreadingHTTPServer:
    """Construct (but do not run) the cockpit's ThreadingHTTPServer. Split out
    from serve() so a test can bind an ephemeral port (0) and drive it with
    real HTTP requests in a background thread instead of parsing serve()'s
    infinite loop."""
    p = port if port is not None else _port()
    b = _resolve_bind(bind if bind is not None else _bind())
    return ThreadingHTTPServer((b, p), Handler)


def serve(port: int | None = None, bind: str | None = None) -> None:
    """Block serving the cockpit. `bin/sb cockpit` and the launchd job call
    this and never return."""
    httpd = build_server(port, bind)
    log.info("cockpit listening")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()

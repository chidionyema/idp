"""Otto's card: one pinned Telegram message, edited in place, plus one line
message per live session, collapsed when the session ends.

Entry point: on_change(state) — called (sync) from the engine's
notify_change activity every time a session's state changes. state is the
dict shape returned by sovereign.engine.client.list_sessions()/show() for
ONE session: session_id, repo, task, step, status, runner, asking,
started_at, updated_at, last_output, line_message_id.

Never raises: every Telegram call and every engine call is wrapped, because
the caller (notify_change) must not fail a workflow activity over a chat
hiccup (CONTRACT.md, "Otto card (B)").

Config resolution is defensive on purpose: sovereign/config.py is owned by
builder A and may not exist yet. This module prefers it when importable and
falls back to reading env / $ESTATE_ENV directly otherwise, using the exact
names CONTRACT.md gives (TELEGRAM_BOT_TOKEN, TELEGRAM_HOME_CHANNEL,
ESTATE_HOME, ESTATE_PUBLIC_URL). Once sovereign/config.py lands, this
module picks it up with no code change on either side.

The phase-1 configurability gate: every other literal (templates, truncation
lengths, timeouts, the Telegram API base URL, ...) lives in
sovereign/otto/config_keys.py's OTTO_KEYS table, resolved through
config_keys.get(). See that module's docstring for the merge story with
sovereign/config.py's KEYS table.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import httpx

from sovereign.otto import config_keys as ck

logger = logging.getLogger("sovereign.otto.card")

# LAW 21: httpx logs "HTTP Request: POST https://.../bot<TOKEN>/..." at INFO.
# Never let that reach a handler -- this module never logs a URL itself either.
logging.getLogger("httpx").setLevel(logging.WARNING)

ACTIVE_STATUSES = ("running", "waiting")
TERMINAL_STATUSES = ("done", "stopped", "denied", "failed")


# --------------------------------------------------------------------------
# Config resolution (see module docstring)
# --------------------------------------------------------------------------

def _config():
    """Return sovereign.config module if importable, else None."""
    try:
        from sovereign import config  # type: ignore
        return config
    except Exception:
        return None


def _parse_env_file(path: Path) -> dict:
    out: dict[str, str] = {}
    try:
        text = path.read_text()
    except OSError:
        return out
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def _estate_home() -> Path:
    cfg = _config()
    if cfg is not None and getattr(cfg, "ESTATE_HOME", None):
        return Path(cfg.ESTATE_HOME)
    env = os.environ.get("ESTATE_HOME")
    if env:
        return Path(env)
    return Path.home() / ck.get("otto.default_estate_home_dirname")


def _telegram_creds() -> tuple[Optional[str], Optional[str]]:
    cfg = _config()
    if cfg is not None and getattr(cfg, "TELEGRAM_BOT_TOKEN", None):
        return cfg.TELEGRAM_BOT_TOKEN, getattr(cfg, "TELEGRAM_HOME_CHANNEL", None)
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_HOME_CHANNEL")
    if token and chat:
        return token, chat
    env_path = Path(os.environ.get(
        "ESTATE_ENV", str(Path.home() / ck.get("otto.estate_env_relpath"))))
    parsed = _parse_env_file(env_path)
    return token or parsed.get("TELEGRAM_BOT_TOKEN"), chat or parsed.get("TELEGRAM_HOME_CHANNEL")


def _public_url() -> Optional[str]:
    cfg = _config()
    if cfg is not None and getattr(cfg, "ESTATE_PUBLIC_URL", None):
        return cfg.ESTATE_PUBLIC_URL
    return os.environ.get("ESTATE_PUBLIC_URL") or None


def _otto_path() -> Path:
    d = _estate_home() / "sovereign"
    d.mkdir(parents=True, exist_ok=True)
    return d / "otto.json"


# --------------------------------------------------------------------------
# otto.json state
# --------------------------------------------------------------------------

def _load_otto() -> dict:
    path = _otto_path()
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            logger.warning("otto.json unreadable, reinitializing")
    otto = {"card_message_id": None, "sends": 0, "edits": 0, "lines": {}, "sessions_cache": {}}
    adopt = os.environ.get("SB_ADOPT_CARD_ID")
    if adopt:
        try:
            otto["card_message_id"] = int(adopt)
        except ValueError:
            logger.warning("SB_ADOPT_CARD_ID=%r is not an int, ignoring", adopt)
    return otto


def _save_otto(otto: dict) -> None:
    path = _otto_path()
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(otto, indent=ck.get("otto.json_indent"), sort_keys=True))
    tmp.replace(path)


def reset() -> dict:
    """Delete otto.json. Used by `sb card-reset`. Never touches Telegram."""
    path = _otto_path()
    existed = path.exists()
    if existed:
        path.unlink()
    return {"reset": True, "existed": existed}


# --------------------------------------------------------------------------
# Telegram Bot API (sync httpx)
# --------------------------------------------------------------------------

def _post(method: str, payload: dict) -> dict:
    token, _ = _telegram_creds()
    if not token:
        logger.warning("no TELEGRAM_BOT_TOKEN available, skipping %s", method)
        return {"ok": False, "description": "no token"}
    url = f"{ck.get('telegram.api_base')}/bot{token}/{method}"
    try:
        r = httpx.post(url, json=payload, timeout=ck.get("telegram.request_timeout_s"))
        return r.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("telegram %s failed: %s", method, exc)
        return {"ok": False, "description": str(exc)}


def _send(chat_id: str, text: str, keyboard: Optional[list] = None) -> Optional[int]:
    payload: dict[str, Any] = {"chat_id": chat_id, "text": text,
                                "parse_mode": ck.get("telegram.parse_mode"),
                                "disable_web_page_preview": True}
    if keyboard:
        payload["reply_markup"] = {"inline_keyboard": keyboard}
    data = _post("sendMessage", payload)
    if data.get("ok"):
        return data["result"]["message_id"]
    logger.warning("sendMessage failed: %s", data.get("description"))
    return None


def _edit(chat_id: str, message_id: int, text: str, keyboard: Optional[list] = None) -> bool:
    payload: dict[str, Any] = {"chat_id": chat_id, "message_id": message_id, "text": text,
                                "parse_mode": ck.get("telegram.parse_mode"),
                                "disable_web_page_preview": True}
    if keyboard:
        payload["reply_markup"] = {"inline_keyboard": keyboard}
    data = _post("editMessageText", payload)
    if data.get("ok"):
        return True
    desc = str(data.get("description", ""))
    if "message is not modified" in desc:
        return True  # not an edit, but not an error either
    logger.warning("editMessageText failed: %s", desc)
    return False


def _pin(chat_id: str, message_id: int) -> None:
    _post("unpinAllChatMessages", {"chat_id": chat_id})
    _post("pinChatMessage", {"chat_id": chat_id, "message_id": message_id, "disable_notification": True})


# --------------------------------------------------------------------------
# Engine client bridge (async API, called sync)
# --------------------------------------------------------------------------

def _run_async(coro):
    try:
        return asyncio.run(coro)
    except RuntimeError:
        # already inside a running loop on this thread — run in a fresh one
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            return ex.submit(lambda: asyncio.run(coro)).result()


def _list_sessions(otto: dict) -> list[dict]:
    """Prefer the live engine; fall back to otto.json's own cache so this
    module is independently testable before sovereign/engine exists."""
    try:
        from sovereign.engine import client as engine_client  # type: ignore
        sessions = _run_async(engine_client.list_sessions())
        if sessions is not None:
            return sessions
    except Exception as exc:
        logger.debug("engine list_sessions unavailable, using cache: %s", exc)
    return list(otto.get("sessions_cache", {}).values())


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

def _hhmm(ts: Any) -> str:
    fmt = ck.get("otto.time_format")
    if not ts:
        return datetime.now().strftime(fmt)
    try:
        return datetime.fromisoformat(str(ts).replace("Z", ck.get("otto.iso_utc_offset"))).strftime(fmt)
    except ValueError:
        return datetime.now().strftime(fmt)


def _is_done_today(ts: Any) -> bool:
    """Within the configurable 'done today' lookback window (see otto.done_today_window_hours)."""
    if not ts:
        return False
    try:
        when = datetime.fromisoformat(str(ts).replace("Z", ck.get("otto.iso_utc_offset"))).replace(tzinfo=None)
    except ValueError:
        return False
    window = timedelta(hours=ck.get("otto.done_today_window_hours"))
    return datetime.now() - when <= window


def _line_text(s: dict) -> str:
    repo = s.get("repo") or "·"
    task = str(s.get("task") or "")[:ck.get("otto.task_max_chars")]
    status = s.get("status")
    time = _hhmm(s.get("updated_at"))
    if status == "running":
        return ck.get("otto.line_running_template").format(repo=repo, task=task, step=s.get("step", "?"))
    if status == "waiting":
        return ck.get("otto.line_waiting_template").format(repo=repo, task=task, asking=s.get("asking") or "?")
    if status == "done":
        return ck.get("otto.line_done_template").format(repo=repo, task=task, time=time)
    if status == "stopped":
        return ck.get("otto.line_stopped_template").format(repo=repo, task=task, time=time)
    if status == "denied":
        return ck.get("otto.line_denied_template").format(repo=repo, task=task, time=time)
    if status == "failed":
        return ck.get("otto.line_failed_template").format(repo=repo, task=task, time=time)
    return ck.get("otto.line_fallback_template").format(repo=repo, task=task)


def _render_card(sessions: list[dict]) -> tuple[str, Optional[list]]:
    now = datetime.now().strftime(ck.get("otto.time_format"))
    running = [s for s in sessions if s.get("status") == "running"]
    waiting = [s for s in sessions if s.get("status") == "waiting"]
    done_today = [s for s in sessions
                  if s.get("status") in TERMINAL_STATUSES and _is_done_today(s.get("updated_at"))]

    lines = [
        ck.get("otto.card_header_template").format(time=now),
        ck.get("otto.card_counts_template").format(
            running=len(running), waiting=len(waiting), done=len(done_today)),
    ]
    for s in running + waiting:
        lines.append(_line_text(s))

    url = _public_url()
    if url:
        lines.append(ck.get("otto.footer_cockpit_url_template").format(url=url))
    else:
        lines.append(ck.get("otto.footer_laptop_only"))
        lines.append(ck.get("otto.footer_command_hints"))

    keyboard = None
    if url:
        max_rows = ck.get("otto.card_max_button_rows")
        id_chars = ck.get("otto.session_id_display_chars")
        rows = []
        for s in (running + waiting)[:max_rows]:
            sid = s.get("session_id", "")
            label = ck.get("otto.button_label_template").format(sid=sid[:id_chars])
            button_url = ck.get("otto.button_url_template").format(url=url, sid=sid)
            rows.append([{"text": label, "web_app": {"url": button_url}}])
        keyboard = rows or None

    return "\n".join(lines), keyboard


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------

def on_change(state: dict) -> dict:
    """Handle one session's state change. Never raises.

    Returns {session_id: line_message_id} for the session just processed
    (empty dict if no chat is configured or the send failed). This module
    never calls back into the engine (no set_line_message_id signal/update)
    -- the caller (A's notify_change activity) reads the returned id and
    stores it itself. That keeps on_change a plain, callback-free function
    of (state) -> result, safe to run on a worker thread without any
    workflow-reentrancy risk.
    """
    try:
        return _on_change(state)
    except Exception:
        logger.exception("on_change failed for session %s", state.get("session_id"))
        return {}


def _on_change(state: dict) -> dict:
    otto = _load_otto()
    _, chat_id = _telegram_creds()
    session_id = state.get("session_id")
    result: dict[str, int] = {}

    otto.setdefault("sessions_cache", {})
    if session_id:
        otto["sessions_cache"][session_id] = state

    if chat_id and session_id:
        line_text = _line_text(state)
        existing_id = otto["lines"].get(session_id) or state.get("line_message_id")
        if existing_id is None:
            new_id = _send(chat_id, line_text)
            if new_id is not None:
                otto["lines"][session_id] = new_id
                result[session_id] = new_id
        else:
            _edit(chat_id, int(existing_id), line_text)
            otto["lines"][session_id] = existing_id
            result[session_id] = int(existing_id)

    if chat_id:
        sessions = _list_sessions(otto)
        card_text, keyboard = _render_card(sessions)
        if otto.get("card_message_id") is None:
            new_card_id = _send(chat_id, card_text, keyboard)
            if new_card_id is not None:
                otto["card_message_id"] = new_card_id
                otto["sends"] += 1
                _pin(chat_id, new_card_id)
        else:
            if _edit(chat_id, int(otto["card_message_id"]), card_text, keyboard):
                otto["edits"] += 1

    _save_otto(otto)
    return result

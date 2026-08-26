"""hermes-agent plugin: sovereign-bus session control from chat.

Registers seven slash commands (sb-list, sb-show, sb-stop, sb-approve,
sb-deny, sb-steer, sb-undo) and one gateway hook (photo + caption ->
`sb intake` -> one DOC_COMMIT receipt line, crew#284 CP1). Each shells out to `$IDP/bin/sb <verb> ... --json` and
returns at most a few lines of plain text (config-table-driven, see below) —
no Telegram/Bot-API calls here, that is sovereign/otto/card.py's job.

This file is installed by symlink: `bin/sb install-plugin` links
sovereign/otto/hermes_plugin -> $HERMES_HOME/plugins/sovereign. Because it
runs from inside that symlink, it resolves its own repo root
(os.path.realpath(__file__)) rather than trusting any env var, per
CONTRACT.md's "IDP resolved from the plugin file's own path". That resolved
root is also added to sys.path so this module — running inside
hermes-agent's own interpreter, which does not have $IDP on its path — can
import sovereign.otto.config_keys (stdlib-only; never pulls httpx/temporalio
into hermes-agent's process).

The phase-1 configurability gate: every numeric/path/URL literal used here
(subprocess timeout, reply line cap, per-command truncation lengths) lives
in sovereign/otto/config_keys.py's OTTO_KEYS table.
"""

from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional


def _idp_root() -> Path:
    # __init__.py -> hermes_plugin -> otto -> sovereign -> IDP root
    return Path(os.path.realpath(__file__)).parent.parent.parent.parent


_IDP_ROOT = _idp_root()
if str(_IDP_ROOT) not in sys.path:
    sys.path.insert(0, str(_IDP_ROOT))

ck = importlib.import_module("sovereign.otto.config_keys")


def _run_sb(*args: str) -> tuple[bool, object]:
    sb = _idp_root() / "bin" / "sb"
    try:
        proc = subprocess.run(
            [str(sb), *args, "--json"], capture_output=True, text=True,
            timeout=ck.get("otto.plugin_sb_timeout_s"),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"sb invocation failed: {exc}"
    out = proc.stdout.strip()
    if proc.returncode != 0:
        err_max = ck.get("otto.plugin_error_max_chars")
        return False, (proc.stderr.strip() or out or f"sb exited {proc.returncode}")[:err_max]
    try:
        return True, json.loads(out)
    except (json.JSONDecodeError, ValueError):
        return True, out


def _first_arg(raw_args: str) -> str:
    return raw_args.strip().split(maxsplit=1)[0] if raw_args.strip() else ""


def sb_list(raw_args: str) -> Optional[str]:
    ok, data = _run_sb("list")
    if not ok:
        return f"sb-list failed: {data}"
    items = data.get("sessions", data) if isinstance(data, dict) else data
    if not items:
        return "No sessions."
    max_lines = ck.get("otto.plugin_reply_max_lines")
    id_chars = ck.get("otto.session_id_display_chars")
    task_max = ck.get("otto.plugin_list_task_max_chars")
    lines = []
    for s in items[:max_lines]:
        sid = str(s.get("session_id", "?"))[:id_chars]
        lines.append(f"{sid} {s.get('status', '?')} {s.get('repo') or '·'} {str(s.get('task', ''))[:task_max]}")
    return "\n".join(lines)


def sb_show(raw_args: str) -> Optional[str]:
    sid = _first_arg(raw_args)
    if not sid:
        return ck.get("otto.plugin_usage_id_template").format(cmd="sb-show")
    ok, data = _run_sb("show", sid)
    if not ok:
        return f"sb-show failed: {data}"
    err_max = ck.get("otto.plugin_error_max_chars")
    if not isinstance(data, dict):
        return str(data)[:err_max]
    task_max = ck.get("otto.plugin_show_task_max_chars")
    output_max = ck.get("otto.plugin_show_output_max_chars")
    max_lines = ck.get("otto.plugin_reply_max_lines")
    lines = [
        f"{data.get('session_id', sid)} {data.get('status', '?')}",
        f"repo: {data.get('repo') or '·'}  step: {data.get('step', '?')}",
        f"task: {str(data.get('task', ''))[:task_max]}",
    ]
    if data.get("asking"):
        lines.append(f"needs: {data['asking']}")
    if data.get("last_output"):
        lines.append(f"last: {str(data['last_output'])[:output_max]}")
    return "\n".join(lines[:max_lines])


def sb_stop(raw_args: str) -> Optional[str]:
    sid = _first_arg(raw_args)
    if not sid:
        return ck.get("otto.plugin_usage_id_template").format(cmd="sb-stop")
    ok, data = _run_sb("stop", sid)
    return _receipt_line("stop", sid) if ok else f"sb-stop failed: {data}"


def sb_approve(raw_args: str) -> Optional[str]:
    sid = _first_arg(raw_args)
    if not sid:
        return ck.get("otto.plugin_usage_id_template").format(cmd="sb-approve")
    ok, data = _run_sb("approve", sid)
    return _receipt_line("approve", sid) if ok else f"sb-approve failed: {data}"


def sb_deny(raw_args: str) -> Optional[str]:
    sid = _first_arg(raw_args)
    if not sid:
        return ck.get("otto.plugin_usage_id_template").format(cmd="sb-deny")
    ok, data = _run_sb("deny", sid)
    return _receipt_line("deny", sid) if ok else f"sb-deny failed: {data}"


def sb_steer(raw_args: str) -> Optional[str]:
    min_parts = ck.get("otto.plugin_steer_min_parts")
    parts = raw_args.strip().split(maxsplit=1)
    if len(parts) < min_parts:
        return ck.get("otto.plugin_usage_steer")
    sid, text = parts[0], parts[1]
    ok, data = _run_sb("steer", sid, text)
    return _receipt_line("steer", sid) if ok else f"sb-steer failed: {data}"


# --- crew#284 CP1: every chat reply is a one-line receipt (spec 2.2) -------

def _receipt_line(op: str, sid: str) -> str:
    """The newest receipt in the signed chain for `sid`, as the one line
    spec 2.2 draws: mark, OP, hash, budget delta, state. Never prose."""
    ok, data = _run_sb("episodes")
    rows = data if isinstance(data, list) else (data.get("episodes", []) if isinstance(data, dict) else [])
    mine = [r for r in rows if isinstance(r, dict) and str(r.get("session_id", "")) == sid]
    if not mine:
        return str(ck.get("otto.receipt_fallback_template")).format(op=op.upper(), sid=sid)
    row = max(mine, key=lambda r: int(r.get("counter") or 0))
    try:
        receipt_mod = importlib.import_module("sovereign.presence.receipt")
        return receipt_mod.from_record(row).text
    except Exception as exc:  # the chain is the truth; the formatter is a convenience
        return f"[?] {op.upper()} | hash:{row.get('hash', '')} | formatter:{type(exc).__name__}"


def sb_undo(raw_args: str) -> Optional[str]:
    """`undo` from the phone reverts the commit the session's newest receipt
    names (spec 2.2 rule 5); `undo <id> <receipt-hash>` walks back to that one."""
    parts = raw_args.strip().split()
    if not parts:
        return ck.get("otto.plugin_usage_id_template").format(cmd="sb-undo")
    sid = parts[0]
    args = ["undo", sid, "--by", str(ck.get("otto.receipt_by"))]
    if len(parts) > 1:
        args += ["--to", parts[1]]
    ok, data = _run_sb(*args)
    return _receipt_line("undo", sid) if ok else f"sb-undo failed: {data}"


def _intake_repo() -> str:
    configured = str(ck.get("otto.intake_repo") or "").strip()
    if configured:
        return configured
    return os.environ.get("ESTATE_HOME") or str(Path.home() / ".estate")


def _chat_id(event) -> Optional[str]:
    src = getattr(event, "source", None)
    for holder in (src, event):
        cid = getattr(holder, "chat_id", None)
        if cid:
            return str(cid)
    return None


def _send_line(event, line: str) -> bool:
    """One Telegram message through the card's existing Bot API client."""
    cid = _chat_id(event)
    if not cid:
        return False
    try:
        card = importlib.import_module("sovereign.otto.card")
        return card._send(cid, line) is not None
    except Exception:
        return False


def on_pre_gateway_dispatch(event=None, **_kw) -> Optional[dict]:
    """Spec 2.3: a photo with a caption never reaches the model as chat. It
    goes through `sb intake`, which extracts, commits under docs/ and writes
    a DOC_COMMIT receipt; the only reply is that receipt's one line. A photo
    without a caption, or a message without a photo, is dispatched normally."""
    media = list(getattr(event, "media_urls", None) or [])
    caption = str(getattr(event, "text", "") or "").strip()
    if not media or not caption:
        return None
    image = str(media[0])
    ok, data = _run_sb("intake", image, "--repo", _intake_repo(), "--caption", caption)
    if ok and isinstance(data, dict) and data.get("line"):
        line = str(data["line"])
    else:
        err_max = ck.get("otto.plugin_error_max_chars")
        line = f"[x] DOC_COMMIT | refused:{str(data)[:err_max]}"
    _send_line(event, line)
    return {"action": "skip", "reason": line}


def register(ctx) -> None:
    ctx.register_command("sb-list", sb_list, description="List sovereign-bus sessions")
    ctx.register_command("sb-show", sb_show, description="Show one session", args_hint="<id>")
    ctx.register_command("sb-stop", sb_stop, description="Stop a running session", args_hint="<id>")
    ctx.register_command("sb-approve", sb_approve, description="Approve a waiting session", args_hint="<id>")
    ctx.register_command("sb-deny", sb_deny, description="Deny a waiting session", args_hint="<id>")
    ctx.register_command("sb-steer", sb_steer, description="Steer a running session", args_hint="<id> <text>")
    ctx.register_command("sb-undo", sb_undo, description="Revert the commit a session's receipt names", args_hint="<id> [receipt-hash]")
    if hasattr(ctx, "register_hook"):
        ctx.register_hook("pre_gateway_dispatch", on_pre_gateway_dispatch)

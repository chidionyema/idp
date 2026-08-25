"""hermes-agent plugin: sovereign-bus session control from chat.

Registers six slash commands (sb-list, sb-show, sb-stop, sb-approve,
sb-deny, sb-steer). Each shells out to `$IDP/bin/sb <verb> ... --json` and
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
    return f"stopped {sid}" if ok else f"sb-stop failed: {data}"


def sb_approve(raw_args: str) -> Optional[str]:
    sid = _first_arg(raw_args)
    if not sid:
        return ck.get("otto.plugin_usage_id_template").format(cmd="sb-approve")
    ok, data = _run_sb("approve", sid)
    return f"approved {sid}" if ok else f"sb-approve failed: {data}"


def sb_deny(raw_args: str) -> Optional[str]:
    sid = _first_arg(raw_args)
    if not sid:
        return ck.get("otto.plugin_usage_id_template").format(cmd="sb-deny")
    ok, data = _run_sb("deny", sid)
    return f"denied {sid}" if ok else f"sb-deny failed: {data}"


def sb_steer(raw_args: str) -> Optional[str]:
    min_parts = ck.get("otto.plugin_steer_min_parts")
    parts = raw_args.strip().split(maxsplit=1)
    if len(parts) < min_parts:
        return ck.get("otto.plugin_usage_steer")
    sid, text = parts[0], parts[1]
    ok, data = _run_sb("steer", sid, text)
    return f"steered {sid}" if ok else f"sb-steer failed: {data}"


def register(ctx) -> None:
    ctx.register_command("sb-list", sb_list, description="List sovereign-bus sessions")
    ctx.register_command("sb-show", sb_show, description="Show one session", args_hint="<id>")
    ctx.register_command("sb-stop", sb_stop, description="Stop a running session", args_hint="<id>")
    ctx.register_command("sb-approve", sb_approve, description="Approve a waiting session", args_hint="<id>")
    ctx.register_command("sb-deny", sb_deny, description="Deny a waiting session", args_hint="<id>")
    ctx.register_command("sb-steer", sb_steer, description="Steer a running session", args_hint="<id> <text>")

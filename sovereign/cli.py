#!/usr/bin/env python3
"""Sovereign Bus CLI: `bin/sb <command> ...`. See sovereign/CONTRACT.md.

Core subcommands (owner: builder A) are defined here. otto's and cockpit's
subcommands plug in through the try-import hook at the bottom of main() --
this module never imports them at module load time, so it works with
neither present (cp6: the engine runs with no vendor around).
"""
from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

from sovereign import config
from sovereign.engine import client as engine_client


def _emit(obj, as_json: bool) -> None:
    if as_json:
        print(json.dumps(obj, sort_keys=True, default=str))
        return
    if isinstance(obj, list):
        for row in obj:
            print(json.dumps(row, sort_keys=True, default=str))
    else:
        print(obj)


def _add_json(p: argparse.ArgumentParser) -> None:
    p.add_argument("--json", action="store_true", help="print JSON")


# ---- core commands (engine) ----


def cmd_start(args: argparse.Namespace) -> int:
    budget_resolved = config.get("budget.default", cli_value=args.budget)
    if budget_resolved.value is None:
        print("budget required", file=sys.stderr)
        return config.CLI_EXIT_USAGE_ERROR
    if args.estate:
        # cp21 wiring, partial by attach/README.md's own admission: repo
        # defaults to the attach root so a step's own git/file work happens
        # there. Routing this session's receipts under
        # attach_core.estate_dir_for(Path(args.estate))/receipts.jsonl
        # needs engine/workflow.py's append_receipt activity to take a
        # path param -- it always writes config.SB_RECEIPTS today -- so
        # that half is out of scope for this patch (attach/README.md
        # flags it as residual, not mine to invent).
        from sovereign.attach import core as attach_core  # noqa: F401

        args.repo = args.repo or args.estate
    res = asyncio.run(
        engine_client.start(
            args.task, runner=args.runner, repo=args.repo, by=args.by, budget=int(budget_resolved.value)
        )
    )
    _emit(res, args.json)
    return 0


def cmd_refill(args: argparse.Namespace) -> int:
    res = asyncio.run(
        engine_client.signal(
            args.session_id, "refill", args.by, tokens=args.tokens, signed=args.signed
        )
    )
    _emit(res, args.json)
    return 0


def cmd_verify_receipts(args: argparse.Namespace) -> int:
    from sovereign.engine import receipts as receipts_mod

    res = receipts_mod.verify()
    _emit(res, args.json)
    return 0 if res.get("ok") else 1


def cmd_audit(args: argparse.Namespace) -> int:
    """cp34: `sb audit --verify` -- phase 1's audit chain IS the signed
    receipt chain (cp19), so this is a thin alias of verify-receipts, not a
    second implementation. --verify is accepted (and currently the only
    mode) for cp34's exact CLI shape; audit with no flag also verifies,
    since phase 1 has no other audit action yet."""
    return cmd_verify_receipts(args)


def cmd_root(args: argparse.Namespace) -> int:
    """cp9: `sb root --json` reports {root, parent, nodes, verified} for
    .estate/heads/shadow_main -- the branch pointer cp8's sidecar advances
    once per write."""
    from sovereign.engine import shadow_root

    res = shadow_root.verify()
    _emit(res, args.json)
    return 0 if res.get("verified") else 1


def cmd_consensus(args: argparse.Namespace) -> int:
    """cp11: `sb consensus --json` -- {reads, matches, mismatches, rate}
    aggregated from every cp10 dualread receipt on disk."""
    from sovereign.sidecar import dualread

    _emit(dualread.summary(), args.json)
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    res = asyncio.run(engine_client.list_sessions())
    _emit(res, args.json)
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    res = asyncio.run(engine_client.show(args.session_id))
    _emit(res, args.json)
    return 0


def cmd_stop(args: argparse.Namespace) -> int:
    res = asyncio.run(engine_client.signal(args.session_id, "stop", args.by, args.reason or ""))
    _emit(res, args.json)
    return 0


def cmd_approve(args: argparse.Namespace) -> int:
    res = asyncio.run(engine_client.signal(args.session_id, "approve", args.by))
    _emit(res, args.json)
    return 0


def cmd_deny(args: argparse.Namespace) -> int:
    res = asyncio.run(engine_client.signal(args.session_id, "deny", args.by))
    _emit(res, args.json)
    return 0


def cmd_steer(args: argparse.Namespace) -> int:
    res = asyncio.run(engine_client.signal(args.session_id, "steer", args.by, args.text or ""))
    _emit(res, args.json)
    return 0


def cmd_episodes(args: argparse.Namespace) -> int:
    res = asyncio.run(engine_client.episodes(args.kind))
    _emit(res, args.json)
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    if getattr(args, "config_command", None) == "set":
        resolved = config.set_key(args.key, args.value, args.by)
        _emit({"key": resolved.key, "value": resolved.value, "source": resolved.source}, args.json)
        return 0

    if args.lint:
        hits = config.lint()
        for h in hits:
            print(f"{h.path}:{h.line} {h.kind} {h.snippet}")
        print(len(hits))
        return 1 if hits else 0

    rows = {}
    for key, resolved in config.resolve_all().items():
        if config.is_secret(key):
            rows[key] = {
                "value": "set" if resolved.value else "unset",
                "default": "set" if resolved.default else "unset",
                "source": resolved.source,
            }
        else:
            rows[key] = {"value": resolved.value, "default": resolved.default, "source": resolved.source}
    _emit(rows, args.json)
    return 0


# ---- process management (up / down / worker) ----


def _read_pid(path: Path) -> int | None:
    try:
        return int(path.read_text().strip())
    except (OSError, ValueError):
        return None


def _alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError, PermissionError):
        return False


def _port_open(address: str, timeout: float = 1.0) -> bool:
    host, _, port_s = address.rpartition(config.NET_HOST_PORT_SEP)
    if not host or not port_s.isdigit():
        return False
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        return s.connect_ex((host, int(port_s))) == 0


def _spawn(cmd: list[str], log_path: Path, pid_path: Path) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a") as log_f:
        proc = subprocess.Popen(
            cmd,
            stdout=log_f,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            env=os.environ.copy(),
        )
    pid_path.write_text(str(proc.pid))
    return proc.pid


def cmd_up(args: argparse.Namespace) -> int:
    config.ensure_dirs()
    result = {"temporal": "already-running", "worker": "already-running"}

    if _alive(_read_pid(config.TEMPORAL_PID_FILE)) or _port_open(
        config.TEMPORAL_ADDRESS, config.CLI_PORT_PROBE_TIMEOUT_S
    ):
        pass
    else:
        host, _, port_s = config.TEMPORAL_ADDRESS.rpartition(config.NET_HOST_PORT_SEP)
        temporal_cmd = [
            "temporal", "server", "start-dev",
            "--db-filename", str(config.TEMPORAL_DB),
            "--namespace", config.TEMPORAL_NAMESPACE,
            "--headless",
            "--ip", host or config.TEMPORAL_HOST,
            "--port", port_s or config.TEMPORAL_PORT,
        ]
        pid = _spawn(temporal_cmd, config.TEMPORAL_LOG_FILE, config.TEMPORAL_PID_FILE)
        result["temporal"] = f"started pid={pid}"
        deadline = time.time() + config.CLI_UP_WAIT_DEADLINE_S
        while time.time() < deadline and not _port_open(
            config.TEMPORAL_ADDRESS, config.CLI_PORT_PROBE_TIMEOUT_S
        ):
            time.sleep(config.CLI_UP_POLL_INTERVAL_S)

    if _alive(_read_pid(config.WORKER_PID_FILE)):
        pass
    else:
        worker_cmd = [sys.executable, "-m", "sovereign.cli", "worker"]
        pid = _spawn(worker_cmd, config.WORKER_LOG_FILE, config.WORKER_PID_FILE)
        result["worker"] = f"started pid={pid}"
        time.sleep(1.0)

    _emit(result, args.json)
    return 0


def _stop_by_pid(pid: int) -> None:
    """Signals exactly this one pid -- never a process group, never a
    `pkill` pattern match. A process-group kill (os.killpg(os.getpgid(pid),
    ...)) is only as safe as the pid it is handed: a stale or reused pid --
    the recorded process already exited and the OS gave that number to
    something else, e.g. the very shell that is running `sb down` -- puts
    that shell's own process group on the receiving end, which is exactly
    what happened (2026-08-25: `bin/sb down` printed "Terminated: 15" for
    the calling shell while the real Temporal dev server, a different pid
    the stale pid file never recorded, kept running). Signaling only the
    literal pid removes that failure mode: the worst case is a no-op
    ProcessLookupError, never a group we do not own."""
    try:
        os.kill(pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError):
        return
    deadline = time.time() + config.CLI_DOWN_WAIT_DEADLINE_S
    while time.time() < deadline and _alive(pid):
        time.sleep(config.CLI_UP_POLL_INTERVAL_S)
    if _alive(pid):
        try:
            os.kill(pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            pass


def cmd_down(args: argparse.Namespace) -> int:
    result = {}
    for name, pid_path in (("worker", config.WORKER_PID_FILE), ("temporal", config.TEMPORAL_PID_FILE)):
        pid = _read_pid(pid_path)
        if pid is None:
            result[name] = "not-running"
            continue
        if _alive(pid):
            _stop_by_pid(pid)
            result[name] = f"stopped pid={pid}"
        else:
            result[name] = "not-running"
        try:
            pid_path.unlink()
        except FileNotFoundError:
            pass
    _emit(result, args.json)
    return 0


def cmd_worker(args: argparse.Namespace) -> int:
    from sovereign.engine.worker import run_worker

    asyncio.run(run_worker())
    return 0


def cmd_install_plugin(args: argparse.Namespace) -> int:
    try:
        otto_cli = importlib.import_module("sovereign.otto.cli")
    except ImportError:
        _emit({"status": "not-installed", "reason": "sovereign.otto is not present on this checkout"}, args.json)
        return 0
    fn = getattr(otto_cli, "install_plugin", None)
    if fn is None:
        _emit({"status": "not-installed", "reason": "sovereign.otto.cli has no install_plugin()"}, args.json)
        return 0
    res = fn()
    _emit(res, args.json)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sb", description="Sovereign Bus")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("start", help="start a session")
    p.add_argument("--task", required=True)
    p.add_argument("--runner", default=config.SB_DEFAULT_RUNNER)
    p.add_argument("--repo", default=None)
    p.add_argument("--by", default="cli")
    p.add_argument("--budget", type=int, default=None)
    p.add_argument("--estate", default=None, help="attach root; repo defaults to it, receipts chain under its estate dir")
    _add_json(p)
    p.set_defaults(func=cmd_start)

    p = sub.add_parser("refill", help="signal a halted session to resume with more budget")
    p.add_argument("session_id")
    p.add_argument("--tokens", type=int, required=True)
    p.add_argument("--by", required=True)
    p.add_argument("--signed", action="store_true")
    _add_json(p)
    p.set_defaults(func=cmd_refill)

    p = sub.add_parser("verify-receipts", help="verify the signed receipt chain")
    _add_json(p)
    p.set_defaults(func=cmd_verify_receipts)

    p = sub.add_parser("audit", help="cp34 -- verify the audit chain (alias of verify-receipts in phase 1)")
    p.add_argument("--verify", action="store_true", help="verify the chain (the only mode phase 1 has)")
    _add_json(p)
    p.set_defaults(func=cmd_audit)

    p = sub.add_parser("config", help="show or change engine configuration")
    _add_json(p)
    p.add_argument("--lint", action="store_true", help="report magic literals outside config.py")
    config_sub = p.add_subparsers(dest="config_command")
    p_set = config_sub.add_parser("set", help="set one config key in estate.toml")
    p_set.add_argument("key")
    p_set.add_argument("value")
    p_set.add_argument("--by", required=True)
    p.set_defaults(func=cmd_config)

    p = sub.add_parser("root", help="cp9 -- show and verify the shadow Merkle root, the shadow_main head")
    _add_json(p)
    p.set_defaults(func=cmd_root)

    p = sub.add_parser("consensus", help="cp11 -- legacy versus DAG dual-read match rate")
    _add_json(p)
    p.set_defaults(func=cmd_consensus)

    p = sub.add_parser("list", help="list sessions")
    _add_json(p)
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("show", help="show one session")
    p.add_argument("session_id")
    _add_json(p)
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("stop", help="stop a session")
    p.add_argument("session_id")
    p.add_argument("--by", required=True)
    p.add_argument("--reason", default="")
    _add_json(p)
    p.set_defaults(func=cmd_stop)

    p = sub.add_parser("approve", help="approve a waiting session")
    p.add_argument("session_id")
    p.add_argument("--by", required=True)
    _add_json(p)
    p.set_defaults(func=cmd_approve)

    p = sub.add_parser("deny", help="deny a waiting session")
    p.add_argument("session_id")
    p.add_argument("--by", required=True)
    _add_json(p)
    p.set_defaults(func=cmd_deny)

    p = sub.add_parser("steer", help="steer a running session")
    p.add_argument("session_id")
    p.add_argument("--by", required=True)
    p.add_argument("--text", default="")
    _add_json(p)
    p.set_defaults(func=cmd_steer)

    p = sub.add_parser("episodes", help="query receipts")
    p.add_argument("--kind", default=None)
    _add_json(p)
    p.set_defaults(func=cmd_episodes)

    p = sub.add_parser("up", help="start temporal dev server + worker if not running")
    _add_json(p)
    p.set_defaults(func=cmd_up)

    p = sub.add_parser("down", help="stop worker + temporal dev server")
    _add_json(p)
    p.set_defaults(func=cmd_down)

    p = sub.add_parser("worker", help="run the worker in the foreground")
    _add_json(p)
    p.set_defaults(func=cmd_worker)

    p = sub.add_parser("install-plugin", help="install the hermes plugin (delegates to otto.cli)")
    _add_json(p)
    p.set_defaults(func=cmd_install_plugin)

    # Plug-in hook: otto and cockpit register their own subcommands here if
    # their package is present. Absence of either is not an error (cp6).
    for modname in ("sovereign.otto.cli", "sovereign.cockpit.cli", "sovereign.attach.cli"):
        try:
            mod = importlib.import_module(modname)
        except ImportError:
            continue
        register = getattr(mod, "register", None)
        if callable(register):
            register(sub)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

"""sovereign.presence.cli -- subcommands registered onto bin/sb by
sovereign.cli's discovery loop.

  digest [--json] [--launchd]   the signed daily digest (spec 2.5); --launchd
                                prints the launchd plist that runs it at
                                presence.digest_hour
  status [--json]               running / waiting / burn counts and the
                                sentence Siri speaks (spec 2.6)
  presence [--json]             the current presence state and dot colour
                                (what the SwiftBar plugin shows)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from sovereign import config
from sovereign.presence import config_keys, digest as digest_mod, state as state_mod, status as status_mod


def _emit(obj: object, as_json: bool, text: str | None = None) -> None:
    if as_json:
        print(json.dumps(obj, sort_keys=True, default=str))
    else:
        print(text if text is not None else obj)


def _launchd_plist() -> str:
    """The plist for launchd, the scheduler this machine already runs.
    Paths are computed from this checkout and the resolved config, never
    typed (LAW 46)."""
    label = str(config_keys.resolve("presence.digest_label", config))
    hour = int(config_keys.resolve("presence.digest_hour", config))
    sb = Path(__file__).resolve().parents[2] / "bin" / "sb"
    log = config.SOVEREIGN_HOME / "logs" / "digest.log"
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0"><dict>\n'
        f"  <key>Label</key><string>{label}</string>\n"
        f"  <key>ProgramArguments</key><array><string>{sb}</string><string>digest</string><string>--send</string></array>\n"
        f"  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>{hour}</integer><key>Minute</key><integer>0</integer></dict>\n"
        f"  <key>EnvironmentVariables</key><dict><key>ESTATE_HOME</key><string>{config.ESTATE_HOME}</string></dict>\n"
        f"  <key>StandardOutPath</key><string>{log}</string>\n"
        f"  <key>StandardErrorPath</key><string>{log}</string>\n"
        "</dict></plist>\n"
    )


def cmd_digest(args: argparse.Namespace) -> int:
    if args.launchd:
        print(_launchd_plist(), end="")
        return 0
    d = digest_mod.build()
    if args.send:
        from sovereign.presence import chat

        chat.send(chat.TelegramSink(), d)
    _emit(digest_mod.as_dict(d), args.json, d.text)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    from sovereign.engine import client as engine_client

    try:
        sessions = asyncio.run(engine_client.list_sessions())
    except Exception as exc:
        print(f"status: engine unreachable: {exc}", file=sys.stderr)
        return 1
    summary = status_mod.summarize(sessions)
    _emit(summary, args.json, summary["spoken"])
    return 0


def cmd_presence(args: argparse.Namespace) -> int:
    current = state_mod.read()
    _emit(current, args.json, f"{current['state']} ({current['dot']})")
    return 0


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("digest", help="R13 -- the signed daily digest, at most six lines")
    p.add_argument("--json", action="store_true")
    p.add_argument("--send", action="store_true", help="also send it to the founder chat (the 09:00 job does this)")
    p.add_argument("--launchd", action="store_true", help="print the launchd plist for the 09:00 digest")
    p.set_defaults(func=cmd_digest)

    p = subparsers.add_parser("status", help="R14 -- running, waiting and burn counts; what Siri speaks")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_status)

    p = subparsers.add_parser("presence", help="R2/R3 -- the current presence state and menu bar dot colour")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_presence)

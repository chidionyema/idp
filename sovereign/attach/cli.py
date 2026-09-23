"""`sb attach`, `sb status`, `sb halt` -- argparse subcommands.

register(sub) is called by sovereign/cli.py (owner: builder A) on its
top-level subparsers action, once A adds "sovereign.attach.cli" to the
plug-in tuple at the bottom of main() (see README.md).
"""
from __future__ import annotations

import argparse
import asyncio
import json

from sovereign.attach import config_keys as ck
from sovereign.attach import core


def register(sub) -> None:
    p_attach = sub.add_parser("attach", help=ck.get("attach.cli_attach_help"))
    p_attach.add_argument("path")
    p_attach.add_argument("--write-policy", action="store_true",
                           help=ck.get("attach.cli_write_policy_help"))
    p_attach.add_argument("--json", action="store_true")
    p_attach.set_defaults(func=_cmd_attach)

    p_status = sub.add_parser("status", help=ck.get("attach.cli_status_help"))
    p_status.add_argument("--json", action="store_true")
    p_status.set_defaults(func=_cmd_status)

    p_halt = sub.add_parser("halt", help=ck.get("attach.cli_halt_help"))
    p_halt.add_argument("--all", action="store_true", required=True, help=ck.get("attach.cli_halt_all_help"))
    p_halt.add_argument("--by", required=True)
    p_halt.add_argument("--signed", action="store_true")
    p_halt.add_argument("--json", action="store_true")
    p_halt.set_defaults(func=_cmd_halt)


def _cmd_attach(args: argparse.Namespace) -> int:
    result = core.attach(args.path, write_policy=args.write_policy)
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        for line in result["receipt_lines"]:
            print(line)
        print(f"root={result['root']} nodes={result['nodes']} hash={result['hash']} "
              f"estate_dir={result['estate_dir']} mode={result['mode']}")
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    result = asyncio.run(core.status())
    if args.json:
        print(json.dumps(result, sort_keys=True, default=str))
    else:
        if not result["estates"]:
            print("no attached estates")
        for e in result["estates"]:
            print(f"{e['root']} mode={e['mode']} running={e['running']} sessions={len(e['sessions'])}")
    return 0


def _cmd_halt(args: argparse.Namespace) -> int:
    result = asyncio.run(core.halt_all(args.by, signed=args.signed))
    if args.json:
        print(json.dumps(result, sort_keys=True, default=str))
    else:
        print(f"halted {result['halted']} session(s)")
        for s in result["sessions"]:
            print(f"  {s['session_id']} ok={s['ok']} receipt#{s['receipt_counter']}")
    return 0

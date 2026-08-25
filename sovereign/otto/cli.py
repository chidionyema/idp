"""`sb card`, `sb card-reset`, `sb install-plugin` — argparse subcommands.

register(sub) is called by sovereign/cli.py (owner: builder A) on its
top-level subparsers action, per CONTRACT.md:
    for m in (sovereign.otto.cli, sovereign.cockpit.cli):
        try: import m; m.register(subparsers)
"""

from __future__ import annotations

import json
import os
import plistlib
from pathlib import Path
from typing import Optional

from sovereign.otto import card
from sovereign.otto import config_keys as ck


def register(sub) -> None:
    p_card = sub.add_parser("card", help="Show Otto's pinned-card state (does not send)")
    p_card.add_argument("--json", action="store_true")
    p_card.set_defaults(func=_cmd_card)

    p_reset = sub.add_parser("card-reset", help=ck.get("otto.cli_card_reset_help"))
    p_reset.add_argument("--json", action="store_true")
    p_reset.set_defaults(func=_cmd_card_reset)

    p_install = sub.add_parser("install-plugin", help=ck.get("otto.cli_install_plugin_help"))
    p_install.add_argument("--json", action="store_true")
    p_install.set_defaults(func=_cmd_install_plugin)


def _cmd_card(args) -> int:
    otto = card._load_otto()
    out = {"card_message_id": otto.get("card_message_id"), "sends": otto.get("sends", 0),
           "edits": otto.get("edits", 0), "lines": len(otto.get("lines", {}))}
    if args.json:
        print(json.dumps(out))
    else:
        print(f"card_message_id={out['card_message_id']} sends={out['sends']} "
              f"edits={out['edits']} lines={out['lines']}")
    return 0


def _cmd_card_reset(args) -> int:
    out = card.reset()
    print(json.dumps(out) if args.json else f"reset (existed={out['existed']})")
    return 0


def _hermes_home() -> Path:
    env = os.environ.get("HERMES_HOME")
    if env:
        return Path(env)
    plist_path = Path.home() / ck.get("otto.hermes_gateway_plist_relpath")
    try:
        with plist_path.open("rb") as f:
            data = plistlib.load(f)
        value = data.get("EnvironmentVariables", {}).get("HERMES_HOME")
        if value:
            return Path(value)
    except (OSError, plistlib.InvalidFileException):
        pass
    return Path.home() / ck.get("otto.hermes_home_default_dirname")


def _cmd_install_plugin(args) -> int:
    hermes_home = _hermes_home()
    source = Path(__file__).resolve().parent / "hermes_plugin"
    plugins_dir = hermes_home / "plugins"
    plugins_dir.mkdir(parents=True, exist_ok=True)
    link = plugins_dir / ck.get("otto.hermes_plugin_link_name")
    if link.is_symlink() or link.exists():
        link.unlink()
    link.symlink_to(source, target_is_directory=True)
    out = {"source": str(source), "link": str(link), "hermes_home": str(hermes_home),
           "restart_needed": True}
    if args.json:
        print(json.dumps(out))
    else:
        print(f"Symlinked {source} -> {link}")
        print("Restart hermes-agent (gateway or CLI session) to load the sovereign plugin. "
              "This command does not restart it.")
    return 0

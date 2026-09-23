"""sovereign.cockpit.cli — subcommands registered onto bin/sb by
sovereign.cli's discovery loop (CONTRACT.md:
`for m in (sovereign.otto.cli, sovereign.cockpit.cli): try import m; m.register(subparsers)`).

  cockpit          serve the cockpit (blocks; also what the launchd job runs)
  menu [--json]    setChatMenuButton so the Telegram chat opens the cockpit
  tunnel           print the cloudflared named-tunnel commands (prints only)
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from urllib.parse import urlencode

from sovereign.cockpit import config_keys

try:
    from sovereign import config
except Exception:  # pragma: no cover - importable before A lands sovereign/config.py
    config = None


def _cfg(name: str, default: object = None) -> object:
    return getattr(config, name, default) if config is not None else default


def _telegram_post(method: str, token: str, payload: dict) -> dict:
    api_base = config_keys.resolve("telegram.api_base", config)
    content_type = config_keys.resolve("cockpit.content_type_json", config)
    timeout_s = config_keys.resolve("telegram.request_timeout_s", config)
    url = f"{api_base}/bot{token}/{method}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": content_type},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return json.loads(resp.read())


def _telegram_get(method: str, token: str, params: dict) -> dict:
    api_base = config_keys.resolve("telegram.api_base", config)
    timeout_s = config_keys.resolve("telegram.request_timeout_s", config)
    url = f"{api_base}/bot{token}/{method}?{urlencode(params)}"
    with urllib.request.urlopen(url, timeout=timeout_s) as resp:
        return json.loads(resp.read())


def cmd_cockpit(args: argparse.Namespace) -> int:
    from sovereign.cockpit.server import serve

    serve(port=args.port, bind=args.bind)
    return 0


def cmd_menu(args: argparse.Namespace) -> int:
    token = _cfg("TELEGRAM_BOT_TOKEN")
    chat_id = _cfg("TELEGRAM_HOME_CHANNEL")
    public_url = _cfg("ESTATE_PUBLIC_URL")
    exit_config_error = config_keys.resolve("cockpit.exit_config_error", config)
    if not token or not chat_id:
        print(
            "menu: TELEGRAM_BOT_TOKEN / TELEGRAM_HOME_CHANNEL not configured",
            file=sys.stderr,
        )
        return exit_config_error
    required_scheme = config_keys.resolve("telegram.required_url_scheme", config)
    if not public_url or not str(public_url).startswith(required_scheme):
        print(
            "menu: ESTATE_PUBLIC_URL is unset or not https:// -- refusing to point the "
            "chat menu button at a URL the Telegram client will not open as a web_app",
            file=sys.stderr,
        )
        return exit_config_error
    button_text = config_keys.resolve("cockpit.menu_button_text", config)
    try:
        result = _telegram_post(
            "setChatMenuButton",
            token,
            {
                "chat_id": chat_id,
                "menu_button": {
                    "type": "web_app",
                    "text": button_text,
                    "web_app": {"url": public_url},
                },
            },
        )
        current = _telegram_get("getChatMenuButton", token, {"chat_id": chat_id})
    except urllib.error.URLError as exc:
        print(f"menu: Telegram API call failed: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(current))
    else:
        print(f"set: {result.get('ok')}  current: {current.get('result')}")
    return 0 if result.get("ok") else 1


def cmd_tunnel(args: argparse.Namespace) -> int:
    port = config_keys.resolve("cockpit.port", config)
    local_host = "localhost"
    print(
        "# cloudflared named tunnel for the cockpit -- printing only, nothing here runs.\n"
        "cloudflared tunnel login\n"
        "cloudflared tunnel create otto\n"
        "cloudflared tunnel route dns otto otto.<your-domain>\n"
        "cat > ~/.cloudflared/config.yml <<'EOF'\n"
        "tunnel: otto\n"
        "credentials-file: <path-to-tunnel-id>.json\n"
        "ingress:\n"
        f"  - hostname: otto.<your-domain>\n"
        f"    service: http://{local_host}:{port}\n"
        "  - service: http_status:404\n"
        "EOF\n"
        "cloudflared service install\n"
        "# then: export ESTATE_PUBLIC_URL=https://otto.<your-domain> ; bin/sb menu"
    )
    return 0


def register(subparsers: argparse._SubParsersAction) -> None:
    p_cockpit = subparsers.add_parser("cockpit", help="serve the Otto cockpit (blocks)")
    p_cockpit.add_argument("--port", type=int, default=None)
    p_cockpit.add_argument("--bind", default=None)
    p_cockpit.set_defaults(func=cmd_cockpit)

    p_menu = subparsers.add_parser("menu", help="set the Telegram chat menu button to the cockpit")
    p_menu.add_argument("--json", action="store_true")
    p_menu.set_defaults(func=cmd_menu)

    p_tunnel = subparsers.add_parser("tunnel", help="print the cloudflared named-tunnel commands")
    p_tunnel.set_defaults(func=cmd_tunnel)

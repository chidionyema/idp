#!/usr/bin/env python3
"""infra/recovery/telegram-digest.py -- one message per window, not one per event.

The founder's complaint about the delivery lane was not that it was wrong, it was that it was a
feed: 42 messages at once, nothing findable. A digest is the same information in the shape a person
can read: a count, the classes that happened, and a pointer. Only alerts that need a decision get
their own card, and those go through the approval inbox, not this sender.

    telegram-digest.py --outbox PATH --cursor PATH [--window-minutes 15] [--dry-run]

It marks nothing delivered that it did not send, so a failed send is retried whole -- a digest that
half-sends would double-count and confuse the very thing it exists to clarify.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request


def load(path: str) -> list[str]:
    if not os.path.exists(path):
        return []
    with open(path, errors="replace") as fh:
        return [ln for ln in fh.read().splitlines() if ln.strip()]


def cursor(path: str) -> int:
    try:
        with open(path) as fh:
            return int(json.load(fh).get("delivered", 0))
    except (OSError, ValueError):
        return 0


def summarise(lines: list[str]) -> str:
    classes: dict[str, int] = {}
    for ln in lines:
        try:
            kind = json.loads(ln).get("kind") or json.loads(ln).get("class") or "event"
        except ValueError:
            kind = "event"
        classes[kind] = classes.get(kind, 0) + 1
    parts = [f"{n} {k}" for k, n in sorted(classes.items(), key=lambda kv: -kv[1])]
    return f"{len(lines)} update(s): " + ", ".join(parts[:6]) + (" …" if len(parts) > 6 else "")


def send(token: str, chat: str, text: str) -> bool:
    data = urllib.parse.urlencode({"chat_id": chat, "text": text[:3900],
                                   "disable_notification": "false"}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:  # noqa: S310 - fixed https host
            return json.loads(r.read().decode()).get("ok") is True
    except Exception:  # noqa: BLE001 - a failed digest is retried
        return False


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--outbox", required=True)
    ap.add_argument("--cursor", required=True)
    ap.add_argument("--window-minutes", type=int, default=15)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    lines = load(a.outbox)
    done = cursor(a.cursor)
    pending = lines[done:]
    if not pending:
        print("nothing to digest")
        return 0
    text = summarise(pending)
    if a.dry_run:
        print(text)
        return 0
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat = os.environ.get("TELEGRAM_HOME_CHANNEL", "")
    if not token or not chat:
        print("BLIND: no telegram credential; nothing sent", file=sys.stderr)
        return 0
    if not send(token, chat, text):
        print("send failed; cursor untouched", file=sys.stderr)
        return 1
    os.makedirs(os.path.dirname(a.cursor) or ".", exist_ok=True)
    with open(a.cursor, "w") as fh:
        json.dump({"delivered": len(lines), "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, fh)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

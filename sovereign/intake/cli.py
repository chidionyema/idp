"""`sb intake <image> --repo <checkout> [--caption ...]` -- the laptop entry
point (R42). Registered through the plug-in hook in sovereign/cli.py, the
same way attach and cockpit register theirs."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sovereign import intake as intake_pkg


def _cmd_intake(args: argparse.Namespace) -> int:
    def reply(_channel: str, text: str) -> None:
        print(text)

    try:
        result = intake_pkg.from_laptop(
            Path(args.image),
            args.caption,
            Path(args.repo),
            reply=None if args.json else reply,
            session_id=args.session,
            budget_remaining=args.budget,
            mime=args.mime,
        )
    except (intake_pkg.IntakeRefused, intake_pkg.ExtractionError) as e:
        print(f"refused: {e}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps({
            "file": result.relative_path,
            "commit": result.commit,
            "tags": list(result.extraction.tags),
            "tokens": result.tokens_charged,
            "receipt_counter": result.receipt.get("counter"),
            "line": result.receipt_line,
        }, sort_keys=True))
    return 0


def register(sub) -> None:
    p = sub.add_parser("intake", help="R8 and R42 -- a photo becomes a committed markdown file and one receipt line")
    p.add_argument("image", help="path to the image file")
    p.add_argument("--repo", required=True, help="git checkout the file is committed into")
    p.add_argument("--caption", default="", help="what the founder said with the photo")
    p.add_argument("--session", default=None, help="session id stamped on the receipt")
    p.add_argument("--budget", type=int, default=None, help="tokens remaining; refused at zero")
    p.add_argument("--mime", default=None, help="image MIME type when not the default")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=_cmd_intake)

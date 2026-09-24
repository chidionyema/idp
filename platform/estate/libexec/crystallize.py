#!/usr/bin/env python3
"""crystallize.py — write an intent YAML from a validated pattern."""

from __future__ import annotations
import re
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
INTENTS = HOME / ".estate" / "intents"
DANGER = re.compile(r"(?:do\s+not|exec\s+[\$\(]|eval\s+|source\s+/dev/)", re.I)


def slugify(topic: str) -> str:
    return topic.strip().replace(" ", "-").lower()


def main():
    topic = ""
    command = ""
    description = ""
    dry_run = "true"
    force = "false"

    for arg in sys.argv[1:]:
        if arg.startswith("topic="):
            topic = arg.split("=", 1)[1]
        elif arg.startswith("command="):
            command = arg.split("=", 1)[1]
        elif arg.startswith("description="):
            description = arg.split("=", 1)[1]
        elif arg.startswith("dry_run="):
            dry_run = arg.split("=", 1)[1]
        elif arg.startswith("force="):
            force = arg.split("=", 1)[1]

    if not topic or not command:
        print("ERROR: topic= and command= required", file=sys.stderr)
        sys.exit(1)

    if DANGER.search(command):
        print("ERROR: command contains dangerous pattern", file=sys.stderr)
        sys.exit(1)

    slug = slugify(topic)
    filename = INTENTS / f"{slug}.yaml"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S%z")

    content = textwrap.dedent(f"""\
        name: {slug}
        description: >-
          {description or "Crystallized intent: " + topic}
        created_by: estate:crystallize
        created_at: "{now}"
        intent_name: {slug}
        steps:
          - name: run
            intent: shell.verify
            args:
              command: '{command}'
        """)

    if dry_run == "true":
        print(f"[DRY RUN] Would write: {filename}")
        print(content)
        return

    if filename.exists() and force != "true":
        print(
            f"ERROR: {filename} exists. Use force=true to overwrite.", file=sys.stderr
        )
        sys.exit(1)

    INTENTS.mkdir(parents=True, exist_ok=True)
    filename.write_text(content)
    print(f"WRITEN: {filename}")


if __name__ == "__main__":
    main()

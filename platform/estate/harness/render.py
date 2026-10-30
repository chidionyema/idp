#!/usr/bin/env python3
"""Render the one estate workflow (AGENTS.md) into what each harness loads, and check for drift.

WHY. 2026-10-29 audit: three tracked AGENTS.md copies had three checksums, and a sampled pi session
saw a generated capability index, not the workflow. One workflow only exists if every harness
carries the same text. This renders the canonical file verbatim into each harness's instruction
path, stamped with its sha256, and `check` fails on any copy that is missing or stale.

    render.py render --source AGENTS.md --home ~    # write every harness copy
    render.py check  --source AGENTS.md --home ~    # exit 1 on MISSING or DRIFT
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

# harness -> instruction file, relative to the home directory. claude/codex/opencode use their
# documented global-instruction paths; pi and kimi paths are declared here and must be confirmed
# against each harness before the installer relies on them (see README.md).
HARNESSES = {
    "claude-code": ".claude/CLAUDE.md",
    "pi": ".pi/AGENTS.md",
    "codex": ".codex/AGENTS.md",
    "kimi": ".kimi/AGENTS.md",
    "opencode": ".config/opencode/AGENTS.md",
}
MARKER = "<!-- estate-workflow sha256={digest} harness={name} source=AGENTS.md -->"


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def rendered(name: str, text: str) -> str:
    return MARKER.format(digest=digest(text), name=name) + "\n" + text


def status(name: str, text: str, home: Path) -> tuple[str, Path]:
    path = home / HARNESSES[name]
    if not path.is_file():
        return "MISSING", path
    return ("OK" if path.read_text() == rendered(name, text) else "DRIFT"), path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("action", choices=["render", "check"])
    ap.add_argument("--source", required=True, type=Path)
    ap.add_argument("--home", required=True, type=Path)
    args = ap.parse_args(argv)
    text = args.source.read_text()
    bad = 0
    for name in HARNESSES:
        if args.action == "render":
            path = args.home / HARNESSES[name]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(rendered(name, text))
            print(f"WROTE    {name:12} {path}")
            continue
        state, path = status(name, text, args.home)
        bad += state != "OK"
        print(f"{state:8} {name:12} {path}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

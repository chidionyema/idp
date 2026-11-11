#!/usr/bin/env python3
"""Per-launch Claude tool budget and the settings that attach its hook."""

import argparse
import fcntl
import json
import os
from pathlib import Path
import shlex
import sys
import time

MAX_CALLS = 20
MAX_SECONDS = 20 * 60


def initialize(state, settings, harness):
    with harness.open() as stream:
        current = json.load(stream)
    if current.get("disableAllHooks") or current.get("allowManagedHooksOnly"):
        raise ValueError("the Claude harness disables session hooks")
    command = shlex.join(
        [sys.executable, str(Path(__file__).resolve()), "pre", "--state", str(state)]
    )
    with state.open("x") as stream:
        json.dump(
            {
                "started": time.clock_gettime(time.CLOCK_MONOTONIC),
                "calls": 0,
                "denials": 0,
            },
            stream,
        )
    with settings.open("x") as stream:
        json.dump(
            {
                "hooks": {
                    "PreToolUse": [
                        {
                            "matcher": "",
                            "hooks": [{"type": "command", "command": command}],
                        }
                    ]
                }
            },
            stream,
        )
    print(MAX_SECONDS)


def reserve(state):
    """Serialize parallel calls and refuse an exhausted or unreadable budget."""
    with state.open("r+") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        record = json.load(stream)
        elapsed = time.clock_gettime(time.CLOCK_MONOTONIC) - record["started"]
        if elapsed < 0 or elapsed >= MAX_SECONDS:
            reason = "deadline"
        elif record["calls"] >= MAX_CALLS:
            reason = "tool_call_cap"
        else:
            reason = None
            record["calls"] += 1
        if reason:
            record["denials"] += 1
            record["last_denial"] = reason
        record["elapsed_seconds"] = round(elapsed, 3)
        stream.seek(0)
        json.dump(record, stream)
        stream.truncate()
        stream.flush()
        os.fsync(stream.fileno())
    if reason:
        print(
            f"FLEET_BUDGET_EXHAUSTED: {reason} "
            f"({record['calls']}/{MAX_CALLS} calls, {elapsed:.3f}/{MAX_SECONDS} seconds)",
            file=sys.stderr,
        )
        return 2
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("--settings", type=Path, required=True)
    init.add_argument("--harness", type=Path, required=True)
    pre = commands.add_parser("pre")
    for command in (init, pre):
        command.add_argument("--state", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "pre":
            return reserve(args.state)
        initialize(args.state, args.settings, args.harness)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"FLEET_BUDGET_UNAVAILABLE: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

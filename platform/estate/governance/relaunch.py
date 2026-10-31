"""The relaunch half of the supervisor: it outlives the session it replaces.

Killing a session that owns its own relaunch kills the relaunch, so the relaunch is a
separate detached process: it waits for the old session's pid to disappear, then starts a new
one with the plug-the-hole instruction as its first message. The new session starts locked
(see ledger.lock_session) and stays locked until its proof exits zero.

Run directly:

    python3 -m platform.estate.governance.relaunch --instruction-file f --cwd DIR --session S
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from typing import List, Optional

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def pi_binary() -> str:
    """The pi CLI. Falls back through the places it is installed."""
    found = shutil.which("pi")
    if found:
        return found
    for candidate in (
        os.path.expanduser("~/.local/bin/pi"),
        os.path.expanduser("~/.npm-global/bin/pi"),
        "/opt/homebrew/bin/pi",
        "/usr/local/bin/pi",
    ):
        if os.path.exists(candidate):
            return candidate
    return "pi"


def wait_for_death(pid: Optional[int], grace: float = 30.0) -> bool:
    if not pid:
        return True
    deadline = time.time() + grace
    while time.time() < deadline:
        try:
            os.kill(pid, 0)
        except OSError:
            return True
        time.sleep(0.2)
    return False


def build_argv(instruction: str, model: str = "", session: str = "") -> List[str]:
    argv = [pi_binary(), "--print"]
    if model:
        argv += ["--model", model]
    if session:
        argv += ["--session-id", session]
    argv.append(instruction)
    return argv


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="relaunch a session under lockdown")
    parser.add_argument("--instruction-file", required=True)
    parser.add_argument("--cwd", required=True)
    parser.add_argument("--session", default="")
    parser.add_argument("--model", default="")
    parser.add_argument("--provider", default="")
    parser.add_argument("--pid", type=int, default=0)
    parser.add_argument("--grace", type=float, default=30.0)
    args = parser.parse_args(argv)

    died = wait_for_death(args.pid or None, args.grace)
    try:
        with open(args.instruction_file) as f:
            instruction = f.read()
    except OSError as exc:
        print(f"relaunch: cannot read the instruction: {exc}", flush=True)
        return 2

    env = dict(os.environ)
    env["PYTHONPATH"] = REPO_ROOT + os.pathsep + env.get("PYTHONPATH", "")
    if args.provider:
        env["ESTATE_MODEL_PROVIDER"] = args.provider
    cmd = build_argv(instruction, args.model, args.session)
    print(f"relaunch: old session died={died}; starting {cmd[0]}", flush=True)
    try:
        proc = subprocess.run(cmd, cwd=args.cwd, env=env)  # noqa: S603 - argv is data
    except OSError as exc:
        print(f"relaunch: cannot start pi: {exc}", flush=True)
        return 3
    print(f"relaunch: session exited {proc.returncode}", flush=True)
    return int(proc.returncode)


if __name__ == "__main__":
    sys.exit(main())

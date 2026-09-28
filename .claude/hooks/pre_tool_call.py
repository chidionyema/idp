#!/usr/bin/env python3
import json, sys
from pathlib import Path

MAX_LINES = 50
LOG_DIR = Path.home() / ".pi/agent/state"


def main():
    inp = json.loads(sys.stdin.read())
    if inp.get("tool_name") != "Bash":
        return
    ti = inp.get("tool_input", {})
    cmd = ti.get("command", "")
    if not cmd or "| head" in cmd or "| tail" in cmd or ti.get("run_in_background"):
        return
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log = LOG_DIR / "last_exec.log"
    w = f'__out=$({cmd} 2>&1); echo "$__out" > {log}; __l=$(echo "$__out" | wc -l); if [ "$__l" -gt {MAX_LINES} ]; then echo "$__out" | head -n 25; echo "[... $(($__l - {MAX_LINES})) lines truncated ...]"; echo "$__out" | tail -n 25; else echo "$__out"; fi'
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "updatedInput": {
                        "command": w,
                        "description": ti.get("description", ""),
                    },
                }
            }
        )
    )


if __name__ == "__main__":
    main()

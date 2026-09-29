#!/usr/bin/env python3
"""Watchdog for the laptop router (launchd label com.estate.litellm-local). Debounced, cooled
down, stateful.

The founder armed this on the laptop on 2026-09-29 as part of freezing the router (the stage
~/.estate/litellm-local is root-owned and read-only). It was written in place and never in
source; this file is that script, staged by `bin/litellm-local install` next to the router it
guards, and run every 15 s by launchd/ai.estate.litellm-watchdog.plist.tmpl.

Reads/writes ~/.estate/state/watchdog.json. Restarts the router only after 3 consecutive health
failures, and never sooner than 90 s after a previous restart, so a slow start is never
mistaken for a dead router and a crash loop cannot be amplified by its own guardian.
"""

import datetime
import json
import os
import pathlib
import subprocess
import sys
import time

HOME = pathlib.Path.home()
STATE = HOME / ".estate/state/watchdog.json"
LOG = HOME / "Library/Logs/litellm-watchdog.log"
URL = "http://127.0.0.1:4000/health/liveliness"
LABEL = f"gui/{os.getuid()}/com.estate.litellm-local"

FAIL_THRESHOLD = 3
COOLDOWN_SECS = 90


def log(msg):
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%FT%TZ")
    with open(LOG, "a") as f:
        f.write(f"{ts} {msg}\n")


def load_state():
    if STATE.exists():
        try:
            return json.loads(STATE.read_text())
        except Exception as e:
            log(f"state unreadable, starting fresh: {e!r}")
    return {"failures": 0, "last_restart_at": 0}


def save_state(s):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(s))


def probe():
    r = subprocess.run(
        ["curl", "-sf", "-m", "3", "-o", "/dev/null", "-w", "%{http_code}", URL],
        capture_output=True,
        text=True,
    )
    return r.stdout.strip() == "200"


def restart():
    log("restart: kickstart com.estate.litellm-local")
    subprocess.run(["launchctl", "kickstart", "-k", LABEL], capture_output=True)


def main():
    now = time.time()
    s = load_state()

    if probe():
        if s["failures"]:
            log(f"recovered after {s['failures']} failure(s)")
        s["failures"] = 0
        save_state(s)
        return

    s["failures"] += 1
    log(f"probe failed ({s['failures']}/{FAIL_THRESHOLD})")

    if s["failures"] < FAIL_THRESHOLD:
        save_state(s)
        return

    since = now - s.get("last_restart_at", 0)
    if since < COOLDOWN_SECS:
        log(f"threshold hit but cooldown active ({int(since)}s < {COOLDOWN_SECS}s)")
        save_state(s)
        return

    restart()
    s["last_restart_at"] = now
    s["failures"] = 0
    save_state(s)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"watchdog error: {e!r}")
        sys.exit(0)

#!/usr/bin/env python3
"""Watchdog for the laptop router (launchd label com.estate.litellm-local). Debounced, cooled
down, stateful.

The founder armed this on the laptop on 2026-09-29 as part of freezing the router (the stage
~/.estate/litellm-local is root-owned and read-only). It was written in place and never in
source; this file is that script, staged by `bin/litellm-local install` next to the router it
guards, and run every 15 s by launchd/ai.estate.litellm-watchdog.plist.tmpl.

Reads/writes ~/.estate/state/watchdog.json. Restarts the router only after 3 consecutive health
failures, and never sooner than 240 s after a previous restart, so a slow start is never
mistaken for a dead router and a crash loop cannot be amplified by its own guardian.

ONLY A REFUSED PORT IS A FAILURE. On 2026-10-02 this restarted the router 12 times: every one
followed a 3 s curl timeout while the laptop's load average sat at 50-90, i.e. a router that was
listening and slow, not dead. Each kickstart cut every live session (the agents saw
"Connection error") and the ~50 s restart added load. router-doctor learned the same rule on
2026-09-28 ("29 of 35 restarts were this. Only a refused port is healed."). So a timeout or an
HTTP error from a listening process is logged and never counted; only curl's "could not connect"
(exit 7) counts toward a restart. The cooldown is 240 s because a start under that load took
over 90 s, and the old 90 s cooldown let the guardian kill a router that was still starting.
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
COOLDOWN_SECS = 240
PROBE_TIMEOUT_SECS = 10
CURL_COULD_NOT_CONNECT = 7


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
    """'ok', 'refused' (nothing listening: the only verdict that counts), or 'slow:<why>'."""
    r = subprocess.run(
        [
            "curl",
            "-s",
            "-m",
            str(PROBE_TIMEOUT_SECS),
            "-o",
            "/dev/null",
            "-w",
            "%{http_code}",
            URL,
        ],
        capture_output=True,
        text=True,
    )
    if r.returncode == 0 and r.stdout.strip() == "200":
        return "ok"
    if r.returncode == CURL_COULD_NOT_CONNECT:
        return "refused"
    return f"slow:curl={r.returncode} http={r.stdout.strip() or '-'}"


def restart():
    log("restart: kickstart com.estate.litellm-local")
    subprocess.run(["launchctl", "kickstart", "-k", LABEL], capture_output=True)


def main():
    now = time.time()
    s = load_state()

    verdict = probe()
    if verdict.startswith("slow"):
        # Listening but not answering in time: not dead, so neither counted nor restarted.
        log(f"probe {verdict} -- listening, not restarted")
        return
    if verdict == "ok":
        if s["failures"]:
            log(f"recovered after {s['failures']} failure(s)")
        s["failures"] = 0
        save_state(s)
        return

    s["failures"] += 1
    log(f"probe refused ({s['failures']}/{FAIL_THRESHOLD})")

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

"""Turn launchd plists into schedule.yml entries. Stdout only.

Daemons (KeepAlive) and vendor jobs stay on launchd: launchd is the substrate's
supervisor, Dagster is the estate's scheduler (architecture/workspace.dsl).
"""
from __future__ import annotations

import glob
import os
import plistlib
import sys

import yaml

HOME = os.path.expanduser("~")
AGENTS = os.path.join(HOME, "Library", "LaunchAgents")
SKIP_PREFIX = ("com.adobe.", "com.valvesoftware.", "homebrew.")


def tilde(s: str) -> str:
    return s.replace(HOME, "~") if s.startswith(HOME) else s


def cron_for(pl: dict) -> str | None:
    if "StartCalendarInterval" in pl:
        entries = pl["StartCalendarInterval"]
        if isinstance(entries, dict):
            entries = [entries]
        minutes = sorted({e.get("Minute", 0) for e in entries})
        hours = sorted({e["Hour"] for e in entries if "Hour" in e})
        m = ",".join(str(x) for x in minutes) or "0"
        h = ",".join(str(x) for x in hours) or "*"
        return f"{m} {h} * * *"
    if "StartInterval" in pl:
        secs = int(pl["StartInterval"])
        step = max(1, round(secs / 60))
        if step >= 60:
            hstep = max(1, round(secs / 3600))
            return f"0 */{hstep} * * *" if hstep < 24 else "0 0 * * *"
        return f"*/{step} * * * *"
    return None


def main() -> int:
    jobs: dict[str, dict] = {}
    for path in sorted(glob.glob(os.path.join(AGENTS, "*.plist"))):
        label = os.path.basename(path)[:-6]
        if label.startswith(SKIP_PREFIX):
            continue
        with open(path, "rb") as f:
            pl = plistlib.load(f)
        if pl.get("KeepAlive") or pl.get("RunAtLoad") and "StartInterval" not in pl and "StartCalendarInterval" not in pl:
            continue
        cron = cron_for(pl)
        if not cron:
            continue
        args = [tilde(a) for a in pl.get("ProgramArguments", [])]
        job = {
            "cron": cron,
            "command": args,
            "skip_on_battery": False,
            "timeout_s": 1800,
        }
        if pl.get("WorkingDirectory"):
            job["cwd"] = tilde(pl["WorkingDirectory"])
        env = {k: tilde(v) for k, v in (pl.get("EnvironmentVariables") or {}).items() if k != "PATH"}
        if env:
            job["env"] = env
        jobs[label] = job
    yaml.safe_dump({"jobs": jobs}, sys.stdout, sort_keys=True, width=120)
    print(f"# {len(jobs)} jobs imported from {tilde(AGENTS)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

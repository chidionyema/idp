"""Is the research ledger fresh, measured without asking this machine what time it is (crew#586).

The `research` tenet asks whether crew/science/RESEARCH-LEDGER.jsonl has an entry inside the
last H hours. The first version compared the entry's `date` with `datetime.now()`, the shape
crew#583 forbids: two clocks, one of them this machine's, and a MacBook whose battery has died
stamps 1970. `now` here is the `Date` header of a GitHub API response -- a clock this machine
cannot move -- and an entry is fresh only when it sits between `now - H hours` and `now`. A stamp
from a reset clock reads stale in either direction; it can never read fresh. No API answer is
BLIND (exit 2), never a fall-back to the local clock.
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import subprocess
from email.utils import parsedate_to_datetime

STAMP_KEYS = ("ts", "timestamp", "date", "when", "at")
SKEW = dt.timedelta(minutes=5)   # a writer's clock may run this far ahead of GitHub's; more is a dead clock


def authority_now() -> dt.datetime | None:
    """The GitHub API's clock, from the Date header of a request that needs no scope. None = no answer."""
    try:
        p = subprocess.run(["gh", "api", "-i", "/rate_limit"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    for line in p.stdout.splitlines():
        if line.lower().startswith("date:"):
            try:
                return parsedate_to_datetime(line.split(":", 1)[1].strip()).astimezone(dt.timezone.utc)
            except (TypeError, ValueError):
                return None
    return None


def stamps(ledger: pathlib.Path) -> tuple[list[dt.datetime], int]:
    """(parsed stamps, rows) of the ledger; raises OSError/ValueError when it cannot be read."""
    rows = [json.loads(line) for line in ledger.read_text().splitlines() if line.strip()]
    out = []
    for row in rows:
        for k in STAMP_KEYS:
            if k in row:
                try:
                    s = dt.datetime.fromisoformat(str(row[k]).replace("Z", "+00:00"))
                except ValueError:
                    break
                out.append(s if s.tzinfo else s.replace(tzinfo=dt.timezone.utc))
                break
    return out, len(rows)


def ledger_fresh(ledger: pathlib.Path, hours: int, now: dt.datetime | None = None) -> int:
    """0 fresh, 1 stale, 2 BLIND. `now` is injected by tests; callers leave it to the authority.
    The newest entry decides. An entry ahead of the authority clock means a clock is behind the
    ledger (the crew#583 incident) and the row is BLIND, never green."""
    try:
        seen, n = stamps(ledger)
    except (OSError, ValueError) as e:
        print(f"BLIND research ledger unreadable at {ledger}: {e}")
        return 2
    if not seen:
        print(f"research ledger: no entry carries a stamp, of {n}")
        return 1
    now = now or authority_now()
    if now is None:
        print("BLIND research ledger: no clock to measure against (gh api gave no Date header); the local clock is not one")
        return 2
    newest = max(seen)
    if newest > now + SKEW:
        print(f"BLIND research ledger: a clock is behind the ledger; newest entry {newest.isoformat(timespec='seconds')} "
              f"is ahead of the API clock {now.isoformat(timespec='seconds')}")
        return 2
    age_h = (now - newest).total_seconds() / 3600.0
    verdict = "inside" if age_h <= hours else "older than"
    print(f"research ledger: newest entry {age_h:.1f}h old, {verdict} {hours}h of {n} entries "
          f"(now {now.isoformat(timespec='seconds')} from the API clock)")
    return 0 if age_h <= hours else 1

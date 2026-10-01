#!/usr/bin/env python3
"""policy-status — what the environment's policy gate decided on real intent runs.

One spoken line for the voice surface (the last stdout line is what Fleet speaks), then a
per-intent table. Reads only what estate-execute recorded in ~/.estate/estate.db
(policy_decisions); prints nothing it did not measure.
"""

import os
import sqlite3
import sys
from pathlib import Path

DB = Path(os.environ.get("ESTATE_DB") or (Path.home() / ".estate" / "estate.db"))
HOURS = int(os.environ.get("POLICY_STATUS_HOURS", "24"))


def main() -> int:
    if not DB.exists():
        print("The policy gate has no ledger yet.")
        return 1
    conn = sqlite3.connect(str(DB))
    has = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='policy_decisions'"
    ).fetchone()
    if not has:
        print("The policy gate has not decided anything yet.")
        return 1
    since = f"-{HOURS} hour"
    total, refused, held, mode = conn.execute(
        "SELECT COUNT(*), SUM(decision='refuse'), SUM(decision='hold'), MAX(mode) "
        "FROM policy_decisions WHERE at >= datetime('now', ?)",
        (since,),
    ).fetchone()
    total = total or 0
    refused = refused or 0
    held = held or 0
    rows = conn.execute(
        "SELECT intent, decision, COUNT(*), ROUND(AVG(p_fail),2), MAX(n), MAX(latency_us) "
        "FROM policy_decisions WHERE at >= datetime('now', ?) AND decision != 'allow' "
        "GROUP BY intent, decision ORDER BY 3 DESC LIMIT 10",
        (since,),
    ).fetchall()
    for intent, decision, c, p, n, us in rows:
        print(f"{decision:6} {intent:32} x{c:<4} p_fail={p} n={n} {us}us")
    if total == 0:
        print(f"No intent ran through the policy gate in the last {HOURS} hours.")
        return 0
    verb = "held or refused" if mode == "enforce" else "would have held or refused"
    top = f" Top: {rows[0][0]}." if rows else ""
    print(
        f"Policy gate in {mode} mode: {total} intents scored in {HOURS} hours, "
        f"{verb} {refused + held}.{top}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

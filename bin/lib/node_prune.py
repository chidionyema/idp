"""Choose the node a pool may give back: the one that is not running.

A surge that never finished leaves the pool at two nodes: the one that kept serving and the one
that never came up (its instance is STOPPED). OKE will not shrink a pool with an update, so the
pool stays at two, the free tier's one-node allowance is spent, and every apply of the cluster is
refused with "nodes-per-node-pool limit has been exceeded" (2026-10-28). The node that is not
running is the one that goes.

The rule, in one line: exactly one node is running, and at least one other node's instance is
STOPPED -> those stopped nodes are the ones to delete. Anything else is refused, and the refusal
says why. A running node is never chosen.

Reads a JSON array of rows on stdin: [{"id": "...", "name": "...", "state": "RUNNING"}, ...]
Prints one line per node to delete ("PRUNE <id> <name>") or a single refusal ("REFUSE <why>").

The second mode, "ids", reads what the OCI CLI prints for `--raw-output` and prints one id per
line. That is the whole reason it exists: `--query 'data[].id' --raw-output` prints a JSON ARRAY,
and word-splitting that array turns its brackets and quotes into "pool ids" (2026-10-28, the
surge door read no pool at all, fell through to the legacy path and deleted nothing).

Pure: no OCI calls, no clock, no environment. The caller does the reading and the deleting.
"""

from __future__ import annotations

import json
import sys
from typing import Any

# An instance in one of these states is not serving anything, and OKE will not keep it forever.
DEAD = ("STOPPED",)


def choose(rows: list[dict[str, Any]]) -> tuple[list[str], str]:
    """Return (node ids to delete, reason). The reason is empty when there is work to do."""
    if not rows:
        return [], "the pool has no nodes"
    running = [r for r in rows if str(r.get("state", "")).upper() == "RUNNING"]
    if len(running) != 1:
        return [], f"expected exactly 1 running node in the pool, found {len(running)}"
    dead = [
        r
        for r in rows
        if str(r.get("state", "")).upper() in DEAD
        and r.get("id") != running[0].get("id")
    ]
    if not dead:
        states = ", ".join(f"{r.get('name')}={r.get('state')}" for r in rows)
        return [], f"no node is stopped; the pool is {states}"
    return [str(r["id"]) for r in dead if r.get("id")], ""


def parse_ids(text: str) -> list[str]:
    """Read the ids out of what the OCI CLI prints for --raw-output.

    A query that returns one value prints the bare string; a query that returns many prints a
    JSON array. Both arrive here, so both are read the same way: JSON first, and a single line
    of text only when it is not JSON at all.
    """
    try:
        data = json.loads(text)
    except ValueError:
        stripped = text.strip()
        if not stripped or "\n" in stripped or not stripped.startswith("ocid1."):
            return []
        return [stripped]
    if isinstance(data, list):
        return [str(x) for x in data if x]
    if isinstance(data, str) and data.strip():
        return [data.strip()]
    return []


def main(argv: list[str]) -> int:
    if argv and argv[0] == "ids":
        for i in parse_ids(sys.stdin.read()):
            print(i)
        return 0
    try:
        rows = json.load(sys.stdin)
    except ValueError:
        print("REFUSE the pool's nodes were not readable JSON")
        return 0
    if not isinstance(rows, list):
        print("REFUSE the pool's nodes are not a list")
        return 0
    ids, reason = choose(rows)
    if reason:
        print(f"REFUSE {reason}")
        return 0
    for r in rows:
        if str(r.get("id")) in ids:
            print(f"PRUNE {r.get('id')} {r.get('name')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

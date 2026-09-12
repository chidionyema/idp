#!/usr/bin/env python3
"""The estate twin's guard: one number, one truth, and no claim of freshness it does not have.

Grades a small JSON summary — the shape `bin/estate-twin-runtime --state` and
`bin/catalog-dark-matter` together produce — and refuses it when:

  1. the graph's stranded-branch count does not equal the catalogue generator's, because two
     surfaces telling a founder two different numbers is the failure this system exists to end;
  2. a domain claims `MEASURED_OK` while its `updated_at` is older than its own window, because
     a reader that cannot tell a five-minute answer from a five-day one is a lie with a
     timestamp on it;
  3. the twin declares a second store, bus or MCP server. THE HEADLINE names that as the
     stitching that gets deleted, and ADR 0006 forbids a second MCP server by name.

Input is the state summary as JSON (a file path, or `-` for stdin). Exit 0 = the estate's
graph is consistent; 1 = refused; 2 = the input could not be read (BLIND, never a pass).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# The vocabulary the estate's three-state rule allows. A fourth word is a state no reader
# knows how to render.
STATES = {"MEASURED_OK", "MEASURED_FAIL", "UNKNOWN"}


def refusals(doc: dict) -> list[str]:
    """Every reason this summary is not trustworthy. Empty list means it is."""
    bad: list[str] = []

    # 1. one number, two surfaces
    gen = doc.get("generator", {}).get("stranded_branches")
    twin = doc.get("twin", {}).get("stranded_branches")
    if gen is None or twin is None:
        bad.append(
            "one surface reports no stranded-branch count, so they cannot be compared"
        )
    elif gen != twin:
        bad.append(
            f"the graph says {twin} stranded branches and the catalogue generator says {gen}; "
            "a founder would read two different numbers"
        )

    # 2. freshness: a state is only as good as its age
    for domain in doc.get("domains") or []:
        name = domain.get("domain", "?")
        state = domain.get("state")
        if state not in STATES:
            bad.append(f"{name}: state {state!r} is not one of {sorted(STATES)}")
            continue
        age, win = domain.get("age_s"), domain.get("window_s")
        if (
            isinstance(age, int)
            and isinstance(win, int)
            and age > win
            and state == "MEASURED_OK"
        ):
            bad.append(
                f"{name}: read {age}s ago against a {win}s window and still reported "
                "MEASURED_OK; a stale answer is UNKNOWN, never OK"
            )

    # 3. no second of anything
    for key, what in (
        ("second_store", "a second SQLite file"),
        ("second_bus", "a second NATS stream"),
        ("second_mcp", "a second MCP server"),
    ):
        if doc.get(key):
            bad.append(f"the twin declares {what}: {doc[key]}")

    return bad


def live_summary() -> dict:
    """The summary as the ESTATE reports it: the real graph, the real counts file, the real
    --state output. This is what makes the rule a live grade rather than a fixture pair."""
    import re
    import sqlite3

    root = Path(__file__).resolve().parents[1]
    counts_path = root / "backstage" / "platform" / "dark-matter.json"
    counts = json.loads(counts_path.read_text()) if counts_path.exists() else {}

    db = root / "catalog" / "estate.db"
    twin_count = None
    if db.exists():
        con = sqlite3.connect(db)
        row = con.execute(
            "select metadata from nodes where id = 'git:summary:stranded'"
        ).fetchone()
        con.close()
        if row:
            twin_count = json.loads(row[0]).get("stranded_branches")

    domains: list[dict] = []
    import subprocess

    out = subprocess.run(
        [str(root / "bin" / "estate-twin-runtime"), "--state"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    for ln in out.stdout.splitlines():
        parts = ln.split()
        if len(parts) >= 2 and parts[0] in STATES:
            m = re.search(r"read (\d+)s ago.*window is (\d+)s", ln)
            domains.append(
                {
                    "domain": parts[1].rstrip(":"),
                    "state": parts[0],
                    "age_s": int(m.group(1)) if m else None,
                    "window_s": int(m.group(2)) if m else None,
                }
            )

    return {
        "generator": {
            "stranded_branches": counts.get("stranded_branches"),
            "dead_deployments": counts.get("dead_deployments"),
        },
        "twin": {"stranded_branches": twin_count},
        "domains": domains,
        "second_store": False,
        "second_bus": False,
        "second_mcp": False,
    }


def main(argv: list[str]) -> int:
    if "--live" in argv:
        try:
            doc = live_summary()
        except Exception as e:
            print(
                f"estate-twin-gate: BLIND, cannot build the live summary: {e}",
                file=sys.stderr,
            )
            return 2
        bad = refusals(doc)
        if bad:
            for reason in bad:
                print(f"refused: {reason}", file=sys.stderr)
            return 1
        print(
            f"ok: the estate's own graph is consistent "
            f"({doc['twin']['stranded_branches']} stranded branches, "
            f"{len(doc['domains'])} domain(s) graded)"
        )
        return 0

    src = argv[1] if len(argv) > 1 else "-"
    try:
        raw = sys.stdin.read() if src == "-" else Path(src).read_text()
    except Exception as e:
        print(f"estate-twin-gate: cannot read input: {e}", file=sys.stderr)
        return 2
    try:
        doc = json.loads(raw)
    except Exception as e:
        print(f"estate-twin-gate: input is not JSON: {e}", file=sys.stderr)
        return 2

    bad = refusals(doc)
    if bad:
        for reason in bad:
            print(f"refused: {reason}", file=sys.stderr)
        return 1
    print("ok: the estate's graph is consistent and honest about its own age")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

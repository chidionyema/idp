#!/usr/bin/env python3
"""G2: the ten domains the estate owns and its graph could not see.

docs/specs/2026-09-12-estate-twin-complete-spec.md §13.2. Each domain below is one the
estate runs and none of its inventories reported. The acceptance test asks the SAME question
of every one: is there a node in the graph for it, with a real reading behind it.

This is the test the emitter must make pass. It is written first, and it fails today.

Run: python3 tests/test_estate_twin_domains.py
"""

from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "catalog" / "estate.db"

# domain -> the node type the graph must carry, and a fragment of a node id to look for.
# One row per domain from §13.2. The emitter is free to name ids as it likes; the TYPE is
# the contract, because that is what a reader queries.
DOMAINS = [
    ("identity", "spiffe-workload", "spiffe"),
    ("network", "network-allowance", "netfence"),
    ("certificates", "certificate", "cert"),
    ("capacity", "capacity", "capacity"),
    ("cost", "spend", "llm"),
    ("data", "pipeline", "dagster"),
    ("postgres", "database", "estate-db"),
    ("sessions", "session", "session"),
    ("worktrees", "worktree", "wt"),
    ("bus", "stream", "ESTATE"),
]


def run(args: list[str], timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: S603 - fixed argv built in this file, no shell
        args, cwd=ROOT, capture_output=True, text=True, timeout=timeout
    )


def graph() -> sqlite3.Connection:
    if not DB.exists():
        print(
            f"FAIL  no graph at {DB.relative_to(ROOT)}; run bin/estate-twin-runtime --once"
        )
        raise SystemExit(1)
    return sqlite3.connect(DB)


def main() -> int:
    # A sweep must have been run by the caller; this test grades the result, it does not
    # produce it. That keeps the test fast and the emitter's own run separate.
    sweep = run(
        [str(ROOT / "bin" / "estate-twin-runtime"), "--once", "--code", "--domains"],
        timeout=900,
    )
    if sweep.returncode != 0:
        print("FAIL  the domain sweep did not run:")
        print("      " + (sweep.stdout + sweep.stderr).strip()[-600:])
        return 1
    print("      " + sweep.stdout.strip().splitlines()[-1])

    con = graph()
    failures: list[str] = []
    print()
    for domain, node_type, _hint in DOMAINS:
        row = con.execute(
            "select count(*), max(last_seen) from nodes where domain = ?", (domain,)
        ).fetchone()
        n, seen = row[0], row[1]
        typed = con.execute(
            "select count(*) from nodes where domain = ? and type = ?",
            (domain, node_type),
        ).fetchone()[0]
        fresh = con.execute(
            "select count(*) from freshness where domain = ?", (domain,)
        ).fetchone()[0]
        ok = n > 0 and typed > 0 and fresh > 0
        mark = "ok  " if ok else "FAIL"
        print(
            f"{mark} {domain:14s} nodes={n:<4d} typed={typed:<4d} fresh={fresh} last={seen}"
        )
        if not ok:
            missing = []
            if n == 0:
                missing.append("no node")
            if typed == 0:
                missing.append(f"no node of type {node_type!r}")
            if fresh == 0:
                missing.append("no freshness row")
            failures.append(f"{domain}: {', '.join(missing)}")
            # A domain the estate does not run is UNKNOWN, which is a reading, not a gap.
            # The scan must be able to tell that apart from a domain that was simply missed.
            if domain not in (sweep.stdout + sweep.stderr):
                failures.append(f"{domain}: the sweep did not name it at all")
    con.close()

    print()
    if failures:
        print(f"{len(failures)} FAILED")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"all {len(DOMAINS)} domains are in the graph with a real reading")
    return 0


if __name__ == "__main__":
    sys.exit(main())


def test_the_render_workflow_asks_for_every_domain():
    """The sweep that publishes the cluster's graph must collect the runtime half.

    `bin/estate-twin-runtime --once --code` collects the code half only. The 12 runtime
    domains need `--domains` as well. The workflow called it with `--code` alone until
    2026-09-13, so the run published a one-node graph and printed ok; only the BLIND line in
    the step caught it, and only because the node count was under a floor.

    This grades the invocation itself, so the flag cannot go missing again without a failure
    that names the flag.
    """
    wf = ROOT / ".github" / "workflows" / "catalog-render.yml"
    text = wf.read_text()
    calls = [ln for ln in text.splitlines() if "estate-twin-runtime --once" in ln]
    assert calls, f"{wf}: no step runs the emitter at all"
    for call in calls:
        assert "--code" in call, f"the emitter runs without --code: {call.strip()}"
        assert "--domains" in call, (
            "the emitter runs without --domains, so the runtime half -- pods, Flux, "
            f"identity, network, certificates, capacity, cost, data, postgres, sessions, "
            f"worktrees, bus -- is never collected: {call.strip()}"
        )


def test_the_db_push_carries_the_graph():
    """The artifact the cluster pulls must carry the graph, not only the declared assets.

    `bin/idp-estate-db-push` ran db-gen straight into the artifact's database, and db-gen
    publishes with SQLite's `.restore`, which REPLACES the whole file. So any node/edge row
    written before it was destroyed. Measured 2026-09-13 with the real inventory:

        the emitter wrote 945 node(s)
        db-gen then ran:   NODES GONE   (457 assets)

    The pod pulled a database with 457 assets and no graph tables at all. This grades the
    ORDER: the emitter must run against the artifact database after db-gen, and the push must
    say how many graph nodes it is shipping.
    """
    script = (ROOT / "bin" / "idp-estate-db-push").read_text()
    assert "estate-twin-runtime" in script, (
        "bin/idp-estate-db-push never runs bin/estate-twin-runtime, so the artifact it pushes "
        "carries the declared assets and no graph -- estate-mcp then serves a database with "
        "no nodes table"
    )
    gen = script.index("bin/db-gen")
    twin = script.index("estate-twin-runtime")
    assert twin > gen, (
        "the emitter runs BEFORE db-gen in bin/idp-estate-db-push. db-gen publishes with "
        "SQLite's .restore, which replaces the file, so the graph is destroyed before the "
        "push -- the order is the defect"
    )
    assert "graph node(s)" in script, (
        "the push does not report how many graph nodes it ships, so a graph-less artifact "
        "reads as a success"
    )

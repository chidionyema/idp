"""INS-00011 falsifiers for bin/estate-memory-engine.

Each test here exists to FIRE on a known-bad state. A test that cannot fail is
not a test, so every assertion is paired with the pre-fix behaviour it rejects.
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

ENGINE = "/Users/roseonyema/Documents/code/idp/bin/estate-memory-engine"


def _run(
    args: list[str], env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, ENGINE, *args],
        capture_output=True,
        text=True,
        timeout=60,
        env={**os.environ, **(env or {})},
    )


def _scalar(db: str, sql: str) -> str:
    conn = sqlite3.connect(db)
    try:
        row = conn.execute(sql).fetchone()
    finally:
        conn.close()
    return "" if row is None else str(row[0])


@pytest.fixture()
def fresh_db(tmp_path: Path) -> str:
    return str(tmp_path / "estate.db")


def test_engine_loads_and_runs(fresh_db: str) -> None:
    """A load failure is a hard failure, never a skip: the engine must actually execute."""
    proc = _run(["bootstrap"], {"ESTATE_DB_PATH": fresh_db})
    assert proc.returncode == 0, f"engine failed to run: {proc.stderr[-800:]}"


def test_bootstrap_creates_strict_tables(fresh_db: str) -> None:
    """STRICT is the schema lock: without it SQLite silently accepts any type."""
    _run(["bootstrap"], {"ESTATE_DB_PATH": fresh_db})
    conn = sqlite3.connect(fresh_db)
    try:
        rows = conn.execute(
            "select name, sql from sqlite_master where type='table'"
        ).fetchall()
    finally:
        conn.close()
    names = {r[0]: (r[1] or "") for r in rows}
    for table in ("bitemporal_facts", "negative_memory_graveyard", "active_focus_pins"):
        assert table in names, f"missing table {table}"
        assert "STRICT" in names[table], f"{table} is not declared STRICT"


def test_supersession_is_nondestructive(fresh_db: str) -> None:
    """The core bi-temporal claim: a new fact invalidates the old one instead of deleting it."""
    _run(["bootstrap"], {"ESTATE_DB_PATH": fresh_db})
    _run(
        ["assert-fact", "llm.mumchimp.com", "origin_substrate", "cloudflare-worker"],
        {"ESTATE_DB_PATH": fresh_db},
    )
    q = (
        "select count(*) from bitemporal_facts where "
        "subject='llm.mumchimp.com' and predicate='origin_substrate'"
    )
    assert _scalar(fresh_db, q) == "1", "the first fact was not recorded"

    _run(
        [
            "assert-fact",
            "llm.mumchimp.com",
            "origin_substrate",
            "cloudflare-workers-v2",
        ],
        {"ESTATE_DB_PATH": fresh_db},
    )
    assert _scalar(fresh_db, q) == "2", "history was destroyed instead of superseded"
    active = _scalar(
        fresh_db,
        q + " and valid_to_ts is null",
    )
    assert active == "1", f"exactly one fact may be active, got {active}"


def test_render_focus_never_prints_a_blank_instruction(fresh_db: str) -> None:
    """FIRES on the defect found live: the ledger is heterogeneous, so a `link` or
    `evidence` row was rendered as an instruction with an empty body."""
    _run(["bootstrap"], {"ESTATE_DB_PATH": fresh_db})
    proc = _run(["render-focus"], {"ESTATE_DB_PATH": fresh_db})
    assert proc.returncode == 0, proc.stderr[-800:]
    for line in proc.stdout.splitlines():
        if line.strip().startswith("- [INS-"):
            assert ":" in line, f"instruction line has no body separator: {line!r}"
            body = line.split(":", 1)[1].strip()
            assert body not in ('""', "", "''"), f"blank instruction rendered: {line!r}"


def test_render_focus_is_token_bounded(fresh_db: str) -> None:
    """Active Focus is a <1,200-token header. It must stay small as facts accumulate."""
    _run(["bootstrap"], {"ESTATE_DB_PATH": fresh_db})
    for i in range(60):
        _run(
            ["assert-fact", f"subject-{i}", "some_predicate", f"v{i}"],
            {"ESTATE_DB_PATH": fresh_db},
        )
    proc = _run(["render-focus"], {"ESTATE_DB_PATH": fresh_db})
    assert proc.returncode == 0, proc.stderr[-800:]
    # ~4 chars per token; 1,200 tokens is a generous ~6,000 char ceiling.
    assert len(proc.stdout) < 6000, f"Active Focus grew to {len(proc.stdout)} chars"


def test_negative_memory_deduplicates_and_counts_hits(fresh_db: str) -> None:
    """The graveyard must escalate on repeat, which is how it stops the repeat."""
    _run(["bootstrap"], {"ESTATE_DB_PATH": fresh_db})
    for _ in range(3):
        _run(
            [
                "record-failure",
                "git-push",
                "git push --force",
                "PROTECTED_BRANCH",
                "use the lane",
            ],
            {"ESTATE_DB_PATH": fresh_db},
        )
    hits = _scalar(
        fresh_db,
        "select hit_count from negative_memory_graveyard where error_signature='PROTECTED_BRANCH'",
    )
    # 1 from bootstrap's own seeding of a different signature is not counted here;
    # three calls on the same grave must accumulate past one.
    assert hits == "3", f"hit_count did not accumulate coherently: {hits}"


def test_drifted_fact_auto_invalidates(fresh_db: str) -> None:
    """Self-falsifying memory: a fact whose probe fails must invalidate itself."""
    _run(["bootstrap"], {"ESTATE_DB_PATH": fresh_db})
    conn = sqlite3.connect(fresh_db)
    try:
        conn.execute(
            "insert into bitemporal_facts values "
            "('FCT-DRIFT','drift.subject','drift.pred','v',1.0,0,NULL,1,NULL,'test','exit 1')"
        )
        conn.commit()
    finally:
        conn.close()

    _run(["verify-facts"], {"ESTATE_DB_PATH": fresh_db})
    assert (
        _scalar(
            fresh_db,
            "select valid_to_ts from bitemporal_facts where fact_id='FCT-DRIFT'",
        )
        != "None"
    ), "a drifted fact stayed active"

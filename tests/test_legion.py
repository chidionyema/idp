"""INS-00011 falsifiers for bin/legion.

Legion's value is the guarantee that a formation either reaches VERIFIED_YIELD or
is fence-failed -- it must never report success it did not prove.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

LEGION = "/Users/roseonyema/Documents/code/idp/bin/legion"
ALL_FORMATIONS = (
    "sniper",
    "phalanx",
    "pipeline",
    "swarm",
    "supervisor",
    "adversarial",
    "tournament",
    "sieve",
)


def _run(
    args: list[str], env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, LEGION, *args],
        capture_output=True,
        text=True,
        timeout=120,
        cwd="/Users/roseonyema/Documents/code/idp",
        env={**os.environ, **(env or {})},
    )


@pytest.fixture()
def fresh_db(tmp_path: Path) -> str:
    return str(tmp_path / "estate.db")


def test_legion_loads(fresh_db: str) -> None:
    proc = _run(["status"], {"ESTATE_DB_PATH": fresh_db})
    assert proc.returncode == 0, f"legion failed to load: {proc.stderr[-800:]}"
    assert "missions" in proc.stdout


@pytest.mark.parametrize("formation", ALL_FORMATIONS)
def test_every_formation_is_dispatchable(fresh_db: str, formation: str) -> None:
    """All eight formations named in INS-00011 must exist and produce shards."""
    proc = _run(
        [
            "dispatch",
            "--ins",
            "INS-00011",
            "--formation",
            formation,
            "--goal",
            f"probe {formation}",
            "--paths",
            "bin/a,bin/b,bin/c",
            "--falsifier",
            "true",
        ],
        {"ESTATE_DB_PATH": fresh_db},
    )
    assert proc.returncode == 0, f"{formation} failed: {proc.stderr[-500:]}"
    payload = json.loads(proc.stdout)
    assert payload["formation"] == formation
    assert payload["subtasks_spawned"] >= 1, f"{formation} spawned no shards"


def test_passing_falsifier_yields_verified(fresh_db: str) -> None:
    proc = _run(
        [
            "dispatch",
            "--formation",
            "tournament",
            "--goal",
            "ok",
            "--falsifier",
            "true",
        ],
        {"ESTATE_DB_PATH": fresh_db},
    )
    payload = json.loads(proc.stdout)
    assert payload["status"] == "VERIFIED_YIELD", payload
    assert payload["winner_worker"], "a verified mission must name its winner"


def test_failing_falsifier_is_fenced_never_verified(fresh_db: str) -> None:
    """The guarantee: a mission whose falsifier fails must NOT report VERIFIED_YIELD."""
    proc = _run(
        [
            "dispatch",
            "--formation",
            "tournament",
            "--goal",
            "bad",
            "--falsifier",
            "exit 1",
        ],
        {"ESTATE_DB_PATH": fresh_db},
    )
    payload = json.loads(proc.stdout)
    assert payload["status"] == "FAILED_FENCED", payload
    assert payload["winner_worker"] is None, "a fenced mission must not name a winner"
    assert payload["ok"] is False


def test_falsifier_is_actually_executed(fresh_db: str) -> None:
    """A falsifier that wrote a file must have run; otherwise the gate is decorative."""
    marker = Path(fresh_db).parent / "ran.marker"
    proc = _run(
        [
            "dispatch",
            "--formation",
            "sniper",
            "--goal",
            "prove-run",
            "--falsifier",
            f"touch {marker}",
        ],
        {"ESTATE_DB_PATH": fresh_db},
    )
    assert proc.returncode == 0, proc.stderr[-500:]
    assert marker.exists(), "the falsifier command never executed"


def test_phalanx_shards_are_disjoint(fresh_db: str) -> None:
    """Phalanx only works because the file sets do not overlap."""
    proc = _run(
        [
            "dispatch",
            "--formation",
            "phalanx",
            "--goal",
            "disjoint",
            "--paths",
            "a/**,b/**,c/**",
            "--falsifier",
            "true",
        ],
        {"ESTATE_DB_PATH": fresh_db},
    )
    payload = json.loads(proc.stdout)
    globs = [s["allowed_paths_glob"] for s in payload["subtasks"]]
    assert len(globs) == 3, globs
    assert len(set(globs)) == len(globs), f"shards overlap: {globs}"


def test_missions_persist_and_are_listed(fresh_db: str) -> None:
    _run(
        [
            "dispatch",
            "--formation",
            "sniper",
            "--goal",
            "persisted",
            "--falsifier",
            "true",
        ],
        {"ESTATE_DB_PATH": fresh_db},
    )
    proc = _run(["status"], {"ESTATE_DB_PATH": fresh_db})
    payload = json.loads(proc.stdout)
    assert any("persisted" in m["goal_snip"] for m in payload["missions"]), payload


def test_tables_are_strict(fresh_db: str) -> None:
    _run(["status"], {"ESTATE_DB_PATH": fresh_db})
    conn = sqlite3.connect(fresh_db)
    try:
        rows = conn.execute(
            "select name, sql from sqlite_master where type='table' and name like 'legion_%'"
        ).fetchall()
    finally:
        conn.close()
    assert rows, "no legion tables were created"
    for name, sql in rows:
        assert "STRICT" in (sql or ""), f"{name} is not declared STRICT"

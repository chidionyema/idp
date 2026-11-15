"""Falsifier for bin/sdo-probe: a missing bus must never read as available."""

import json
import sqlite3
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "bin" / "sdo-probe"


def run(*args):
    return subprocess.run([str(PROBE), *args, "--json"], capture_output=True, text=True)


def test_a_missing_bus_is_absent_and_exits_three(tmp_path):
    p = run("--db", str(tmp_path / "nope.db"))
    assert p.returncode == 3, p.stdout + p.stderr
    body = json.loads(p.stdout)
    assert body["verdict"] == "SDO_ABSENT"


def test_a_shaped_bus_is_available(tmp_path):
    db = tmp_path / "genesis.db"
    con = sqlite3.connect(db)
    con.execute("pragma journal_mode=WAL")
    con.execute(
        "create table instructions (instruction_id text primary key, payload text not null)"
    )
    con.execute("insert into instructions values ('I-8080', '{}')")
    con.commit()
    con.close()
    p = run("--db", str(db))
    assert p.returncode == 0, p.stdout + p.stderr
    body = json.loads(p.stdout)
    assert body["verdict"] == "SDO_AVAILABLE"
    assert body["probed"][0]["shape_table"] == "instructions"


def test_a_database_without_the_table_is_not_available(tmp_path):
    db = tmp_path / "other.db"
    sqlite3.connect(db).execute(
        "create table unrelated (x integer)"
    ).connection.commit()
    p = run("--db", str(db))
    assert p.returncode == 3, p.stdout + p.stderr
    assert json.loads(p.stdout)["verdict"] == "SDO_ABSENT"

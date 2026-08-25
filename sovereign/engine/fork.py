"""Sovereign fork (cp12): zero-cost AI sandboxes, production untouched.

Founder: "sb fork staging creates a full copy of production state in
under a second ... Zero database copies." A fork IS a second head
pointer file under shadow.heads_dir, holding the same DAG root
shadow_main already names -- creating one copies a few bytes of JSON,
never a row of the legacy DB and never a DAG node file, which is why it
is a-second-or-less regardless of how large the estate has grown
(features/sovereign-bus/cp12_ai_sandbox.feature, "Fork under a second").

A write against a fork never reaches production: attach_sidecar() wires
a sovereign.sidecar.core.DBSidecar to a connection of the fork's own
(open_connection()), a dag_dir of the fork's own (fork_dag_dir()), and a
receipts file/head-anchor pair of the fork's own (fork_receipts_paths())
-- sovereign.engine.receipts.append()/verify() and
sovereign.engine.shadow_root.update_head()/verify() all take these as
optional overrides now, defaulting to production's own when omitted, so
every existing caller is unaffected and a fork's chain is never mixed
with main's ("the fork's receipts are chained separately from main").

Storage: `create()` decides "memory" or "disk" once, at fork-creation
time, by counting the forks already open against config.FORK_MAX_PARALLEL
-- the (max_parallel + 1)th fork and beyond gets a disk-backed sqlite
file under config.FORK_DIR instead of `:memory:` ("The cap is a key").
Either way only the target table's own CREATE TABLE statement is
mirrored in, read from the legacy DB's sqlite_master -- schema only, no
row of production's data is copied (cp12's "Zero database copies": a
fork's rows come only from writes made against the fork itself).

`drop()` removes a fork's head pointer only. It never touches
config.SIDECAR_DAG_DIR, fork_dag_dir(), or a fork's receipts file --
every DAG node a dropped fork ever pointed at stays on disk, archived,
because deleting a Merkle DAG node a receipt or another fork's history
might still reference is exactly the kind of edit a hash chain exists to
catch (cp12: "its DAG nodes remain (archived, never deleted)").
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

from sovereign import config
from sovereign.engine import shadow_root


class UnknownForkError(ValueError):
    """Raised by switch()/drop()/attach_sidecar() for a name that is
    neither production's own shadow_main nor a fork present in
    list_forks() -- never a bare KeyError or FileNotFoundError, so a
    caller can catch this one class regardless of which of the three
    operations it came from."""


def _reserved_names() -> set[str]:
    return {config.SHADOW_HEAD_FILENAME}


def fork_head_path(name: str) -> Path:
    return config.SHADOW_HEADS_DIR / name


def list_forks() -> list[str]:
    """Every branch pointer under shadow.heads_dir except production's
    own (shadow_main) and any in-flight tmp file -- the exact set
    `sb drop` can remove and `sb switch` can move to."""
    if not config.SHADOW_HEADS_DIR.exists():
        return []
    reserved = _reserved_names()
    return sorted(
        p.name
        for p in config.SHADOW_HEADS_DIR.iterdir()
        if p.is_file() and p.name not in reserved and not p.name.endswith(".tmp")
    )


def _storage_for_new_fork() -> str:
    return "disk" if len(list_forks()) >= config.FORK_MAX_PARALLEL else "memory"


def fork_dag_dir(name: str) -> Path:
    return config.FORK_DIR / name / "dag"


def fork_receipts_paths(name: str) -> tuple[Path, Path]:
    """(receipts_path, head_anchor_path) -- a fork's own hash-chained
    receipts file and signed head anchor, isolated from production's
    (config.SB_RECEIPTS, config.RECEIPTS_HEAD)."""
    base = config.FORK_DIR / name
    return base / "receipts.jsonl", base / "receipts.head"


def fork_db_path(name: str) -> Path:
    return config.FORK_DIR / name / "state.db"


def create(name: str) -> dict[str, Any]:
    """Zero-cost fork: copies production's current DAG root pointer into
    a new head file under shadow.heads_dir/<name>. Reads exactly one
    file (shadow_main's own head JSON, via shadow_root.verify()) and
    writes exactly one file (name's own); no row of the legacy DB and no
    DAG node file is read, written, or even opened."""
    t0 = time.perf_counter()
    prod_root = shadow_root.verify()["root"]
    storage = _storage_for_new_fork()
    config.SHADOW_HEADS_DIR.mkdir(parents=True, exist_ok=True)
    dest = fork_head_path(name)
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    tmp.write_text(json.dumps({"root": prod_root, "storage": storage}, sort_keys=True))
    os.replace(tmp, dest)
    elapsed_ms = (time.perf_counter() - t0) * config.MS_PER_SECOND
    return {"name": name, "root": prod_root, "storage": storage, "elapsed_ms": elapsed_ms}


def fork_storage(name: str) -> str:
    if name not in list_forks():
        raise UnknownForkError(name)
    try:
        return json.loads(fork_head_path(name).read_text()).get("storage", "memory")
    except (OSError, json.JSONDecodeError):
        return "memory"


def current() -> str:
    if config.FORK_WORKING_POINTER.exists():
        return config.FORK_WORKING_POINTER.read_text().strip() or config.SHADOW_HEAD_FILENAME
    return config.SHADOW_HEAD_FILENAME


def switch(name: str) -> dict[str, Any]:
    """Moves the one working-pointer file (config.FORK_WORKING_POINTER)
    to name. name must already be production's own shadow_main or a
    fork present in list_forks() -- switch() never creates a branch, it
    only points at one that already exists."""
    if name != config.SHADOW_HEAD_FILENAME and name not in list_forks():
        raise UnknownForkError(name)
    config.FORK_WORKING_POINTER.parent.mkdir(parents=True, exist_ok=True)
    tmp = config.FORK_WORKING_POINTER.with_suffix(config.FORK_WORKING_POINTER.suffix + ".tmp")
    tmp.write_text(name)
    os.replace(tmp, config.FORK_WORKING_POINTER)
    return {"working": name}


def drop(name: str) -> dict[str, Any]:
    """Removes name's head pointer from shadow.heads_dir -- the branch is
    gone from list_forks() -- but every DAG node and receipt it ever
    wrote stays on disk, archived (module docstring). If name was the
    current working branch, switches back to production first, so the
    working pointer is never left naming a branch that no longer
    exists."""
    if name not in list_forks():
        raise UnknownForkError(name)
    if current() == name:
        switch(config.SHADOW_HEAD_FILENAME)
    fork_head_path(name).unlink(missing_ok=True)
    return {"dropped": name}


def _mirror_ddl(table: str) -> str:
    """Reads the target table's own CREATE TABLE statement from the
    legacy DB's sqlite_master and nothing else -- no row is read here.
    Schema-only replication is what makes a fork copy-on-write: a fork's
    rows come from the writes an agent makes against it, not from a bulk
    copy of production's data."""
    db_path, _, _ = config.SIDECAR_TARGET.partition("#")
    with sqlite3.connect(db_path) as legacy:
        row = legacy.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
        ).fetchone()
    if row is None or row[0] is None:
        raise UnknownForkError(f"no such legacy table: {table!r}")
    return row[0]


def open_connection(name: str, table: str, storage: str) -> sqlite3.Connection:
    if storage == "disk":
        path = fork_db_path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path))
    else:
        conn = sqlite3.connect(config.FORK_MEMORY_DSN)
    conn.execute(_mirror_ddl(table))
    conn.commit()
    return conn


def attach_sidecar(name: str, table: str) -> tuple[sqlite3.Connection, Any]:
    """Returns (connection, DBSidecar) wired entirely to name's own
    storage: open_connection() for the data, fork_dag_dir(name) for the
    DAG, fork_head_path(name) for the root pointer, and
    fork_receipts_paths(name) for the receipt chain -- so every write an
    agent makes against the returned connection advances name's own
    root and chains into name's own receipts file, and touches nothing
    production owns. Imports sovereign.sidecar.core lazily: that module
    does not import this one, but importing it at module load here would
    still tie fork.py's own import time to sidecar/core.py's, which
    engine/shadow_root.py's own precedent (see its GENESIS_NODE_HASH
    comment) treats as worth avoiding on principle, not just when a
    cycle actually exists."""
    from sovereign.sidecar.core import DBSidecar

    storage = fork_storage(name)
    conn = open_connection(name, table, storage)
    receipts_path, receipts_head_path = fork_receipts_paths(name)
    sidecar = DBSidecar(
        conn,
        table,
        dag_dir=fork_dag_dir(name),
        head_path=fork_head_path(name),
        receipts_path=receipts_path,
        receipts_head_path=receipts_head_path,
    ).attach()
    return conn, sidecar

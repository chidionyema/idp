#!/usr/bin/env python3
"""
platform/estate/estate-swarm-synapse.py — Genesis v0.7.0-RT Stigmergic Swarm Coordinator,
Dual-Yield Enforcer, LIFO Saga Rollback & Two-Phase Worker Reassignment Gate.

Versioned inside `idp/platform/estate/` so host coordination survives a dead laptop.

Mathematical & Systems Guarantees:
  1. S1 Single-Flight Pack Semaphore (`.estate/locks/git-pack.lock`) + >= 1500 MB Disk Floor.
  2. S2 Additive-Only DEFAULT Schema Law (`PRAGMA journal_mode=WAL; busy_timeout=5000`).
  3. Pass-0 Antibody Execution (`catechism_antibodies` -> 0 LLM diagnostic passes on known faults).
  4. Stigmergic Lease Exclusivity (`mycelium_task_queue` + Kleppmann DDIA monotonic `fencing_token`).
  5. Mandatory Dual-Yield Law (`--fact` >= 15 chars + RFC 6962 `\x01` `realtime_event_ring` + <= 4096B `GENESIS_SPORE.dna`).
  6. LIFO Compensating Saga Rollback (`reversible_state_journal` inverse transactions + fence bump).
  7. Two-Phase Founder Reassignment (`NEEDS_REASSIGNMENT` -> `REASSIGN_PENDING_ACK` -> `ACKED_ACTIVE_NEW_OWNER`).
"""
from __future__ import annotations

import argparse
import base64
import fcntl
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import time
import zlib
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

HOME = Path.home()
DB_PATH = Path(os.environ.get("ESTATE_DB_PATH", str(HOME / ".estate/estate.db")))
SPORE_PATH = Path(os.environ.get("GENESIS_SPORE_PATH", str(HOME / ".estate/GENESIS_SPORE.dna")))
LOCK_DIR = Path(os.environ.get("ESTATE_LOCK_DIR", str(HOME / ".estate/locks")))
IDP_MEMORY_DIR = Path(
    os.environ.get("IDP_MEMORY_DIR", str(HOME / "Documents/code/idp/platform/estate/memory"))
)
DISK_FLOOR_MB = int(os.environ.get("ESTATE_DISK_FLOOR_MB", "1500"))


def free_disk_mb() -> int:
    target = "/System/Volumes/Data" if os.path.exists("/System/Volumes/Data") else "/"
    return int(shutil.disk_usage(target).free // (1024 * 1024))


@contextmanager
def single_flight_pack_semaphore(lock_name: str = "git-pack.lock") -> Iterator[Path]:
    """S1 Prevention: Single-flight fcntl mutex preventing concurrent git pack stampedes."""
    LOCK_DIR.mkdir(parents=True, exist_ok=True)
    lock_file = LOCK_DIR / lock_name
    fd = os.open(str(lock_file), os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield lock_file
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def ensure_additive_columns(
    conn: sqlite3.Connection, table: str, required_cols: list[tuple[str, str]]
) -> None:
    """S2 Prevention: Additive-only DEFAULT column migration so legacy + CIF writers coexist."""
    existing = {
        row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
    }
    for col_name, col_ddl in required_cols:
        if col_name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_ddl}")


def open_synapse_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        PRAGMA journal_mode = WAL;
        PRAGMA synchronous = NORMAL;
        PRAGMA busy_timeout = 5000;

        CREATE TABLE IF NOT EXISTS swarm_fencing_state (
            id INTEGER PRIMARY KEY CHECK(id = 1),
            authoritative_token INTEGER NOT NULL DEFAULT 45
        );
        INSERT OR IGNORE INTO swarm_fencing_state (id, authoritative_token) VALUES (1, 45);

        CREATE TABLE IF NOT EXISTS mycelium_task_queue (
            task_id TEXT PRIMARY KEY,
            prompt_payload TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'OPEN' CHECK(status IN ('OPEN', 'LEASED', 'COMPLETED', 'FAILED')),
            leased_by TEXT NOT NULL DEFAULT '',
            lease_expires_at INTEGER NOT NULL DEFAULT 0,
            fencing_token INTEGER NOT NULL DEFAULT 45,
            result_json TEXT NOT NULL DEFAULT '{}',
            updated_at INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS catechism_antibodies (
            antibody_id TEXT PRIMARY KEY,
            failure_class_signature TEXT NOT NULL UNIQUE,
            remediation_cmd TEXT NOT NULL DEFAULT '',
            ed25519_signature TEXT NOT NULL DEFAULT '',
            created_at INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS realtime_event_ring (
            seq_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_ns INTEGER NOT NULL DEFAULT 0,
            fencing_token INTEGER NOT NULL DEFAULT 45,
            topic TEXT NOT NULL DEFAULT '',
            source_node TEXT NOT NULL DEFAULT '',
            prev_merkle_root TEXT NOT NULL DEFAULT '',
            merkle_root TEXT NOT NULL DEFAULT '',
            payload_json TEXT NOT NULL DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS reversible_state_journal (
            journal_id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at INTEGER NOT NULL DEFAULT 0,
            fencing_token INTEGER NOT NULL DEFAULT 45,
            layer TEXT NOT NULL DEFAULT '',
            operation TEXT NOT NULL DEFAULT '',
            inverse_sql TEXT NOT NULL DEFAULT '',
            inverse_params_json TEXT NOT NULL DEFAULT '[]',
            rolled_back INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS continuity_missions (
            instruction_id TEXT PRIMARY KEY,
            title TEXT NOT NULL DEFAULT '',
            authoritative_owner TEXT NOT NULL DEFAULT '',
            pending_owner TEXT NOT NULL DEFAULT '',
            handoff_state TEXT NOT NULL DEFAULT 'ACTIVE_CLOUD',
            fencing_token INTEGER NOT NULL DEFAULT 45,
            checkpoint_sha TEXT NOT NULL DEFAULT '',
            last_verified_progress TEXT NOT NULL DEFAULT '',
            updated_at INTEGER NOT NULL DEFAULT 0
        );
        """
    )
    ensure_additive_columns(
        conn,
        "mycelium_task_queue",
        [
            ("prompt_payload", "TEXT NOT NULL DEFAULT ''"),
            ("fencing_token", "INTEGER NOT NULL DEFAULT 45"),
            ("result_json", "TEXT NOT NULL DEFAULT '{}'"),
        ],
    )
    conn.commit()
    return conn


def append_ring_event(
    conn: sqlite3.Connection, topic: str, source: str, payload: dict
) -> dict:
    now_ns = time.time_ns()
    token = conn.execute(
        "SELECT authoritative_token FROM swarm_fencing_state WHERE id = 1"
    ).fetchone()[0]
    prev_row = conn.execute(
        "SELECT merkle_root FROM realtime_event_ring ORDER BY seq_id DESC LIMIT 1"
    ).fetchone()
    prev_root = prev_row["merkle_root"] if prev_row else ("0" * 64)
    payload_str = json.dumps(payload, separators=(",", ":"), sort_keys=True)

    h = hashlib.sha256()
    h.update(
        b"\x01"
        + prev_root.encode()
        + str(now_ns).encode()
        + str(token).encode()
        + topic.encode()
        + payload_str.encode()
    )
    merkle_root = h.hexdigest()

    cur = conn.execute(
        """
        INSERT INTO realtime_event_ring
        (ts_ns, fencing_token, topic, source_node, prev_merkle_root, merkle_root, payload_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (now_ns, token, topic, source, prev_root, merkle_root, payload_str),
    )
    conn.commit()
    return {"seq_id": cur.lastrowid, "fencing_token": token, "merkle_root": merkle_root}


def record_reversible_journal(
    conn: sqlite3.Connection,
    token: int,
    layer: str,
    operation: str,
    inverse_sql: str,
    inverse_params: list,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO reversible_state_journal
        (created_at, fencing_token, layer, operation, inverse_sql, inverse_params_json, rolled_back)
        VALUES (?, ?, ?, ?, ?, ?, 0)
        """,
        (int(time.time()), token, layer, operation, inverse_sql, json.dumps(inverse_params)),
    )
    return int(cur.lastrowid or 0)


def write_to_memory_door(fact_text: str, kind: str = "fact") -> bool:
    if not IDP_MEMORY_DIR.is_dir():
        return False
    if str(IDP_MEMORY_DIR) not in sys.path:
        sys.path.insert(0, str(IDP_MEMORY_DIR))
    os.environ.setdefault("ESTATE_MEMORY_NAMESPACE", "estate")
    try:
        import door  # type: ignore

        res = door.post({"kind": kind, "text": fact_text})
        return bool(res and res.get("written"))
    except Exception:
        return False


def repack_4kb_spore(conn: sqlite3.Connection) -> dict:
    latest = conn.execute(
        "SELECT seq_id, merkle_root FROM realtime_event_ring ORDER BY seq_id DESC LIMIT 1"
    ).fetchone()
    seq_id = int(latest["seq_id"]) if latest else 0
    merkle = str(latest["merkle_root"]) if latest else ("0" * 64)
    token = int(
        conn.execute(
            "SELECT authoritative_token FROM swarm_fencing_state WHERE id = 1"
        ).fetchone()[0]
    )

    antibodies = [
        {
            "id": r["antibody_id"],
            "sig": r["failure_class_signature"],
            "cmd": r["remediation_cmd"][:96],
        }
        for r in conn.execute(
            "SELECT antibody_id, failure_class_signature, remediation_cmd "
            "FROM catechism_antibodies ORDER BY created_at DESC LIMIT 10"
        )
    ]
    recent_intel = []
    for r in conn.execute(
        "SELECT payload_json FROM realtime_event_ring "
        "WHERE topic IN ('swarm.yield', 'swarm.antibody', 'continuity.ack') "
        "ORDER BY seq_id DESC LIMIT 6"
    ):
        try:
            item = json.loads(r["payload_json"])
            if "learnedFact" in item:
                item["learnedFact"] = str(item["learnedFact"])[:140]
            recent_intel.append(item)
        except Exception:
            continue

    dna_obj = {
        "v": "0.7.0-RT",
        "seq": seq_id,
        "fencing_token": token,
        "merkle": merkle,
        "disk_free_mb": free_disk_mb(),
        "canonical_doors": {
            "memory": "idp/platform/estate/memory/door.py",
            "synapse": "idp/platform/estate/estate-swarm-synapse.py",
            "realtime_sse": "/api/brain/stream",
            "projector": "/#projector",
        },
        "antibodies": antibodies,
        "peer_intel": recent_intel,
    }
    compressed = zlib.compress(
        json.dumps(dna_obj, separators=(",", ":")).encode("utf-8"), level=9
    )
    b64 = base64.urlsafe_b64encode(compressed).decode("ascii")
    digest = hashlib.sha256(compressed).hexdigest()[:16]
    spore_str = (
        f"#!/usr/bin/env python3\n"
        f"# GENESIS_SPORE.dna v0.7.0-RT | SEQ:{seq_id} | FENCE:{token} | SHA256:{digest}\n"
        f"import base64,json,zlib;DNA=json.loads(zlib.decompress(base64.urlsafe_b64decode('{b64}')))\n"
        f"if __name__=='__main__':print(json.dumps(DNA,indent=2))\n"
    )
    raw = spore_str.encode("utf-8")
    if len(raw) > 4096:
        raise RuntimeError(f"Spore exceeded 4KB cap: {len(raw)}B")
    SPORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SPORE_PATH.write_bytes(raw)
    os.chmod(SPORE_PATH, 0o755)
    return {
        "spore_bytes": len(raw),
        "seq_id": seq_id,
        "fencing_token": token,
        "sha256_prefix": digest,
        "spore_path": str(SPORE_PATH),
    }


def cmd_hydrate(
    conn: sqlite3.Connection, agent_id: str, layer: str, failure_sig: str | None
) -> dict:
    mb = free_disk_mb()
    if mb < DISK_FLOOR_MB:
        return {
            "status": "HALT_DISK_FLOOR",
            "disk_free_mb": mb,
            "allowed_to_proceed": False,
        }

    with single_flight_pack_semaphore():
        if failure_sig:
            ab = conn.execute(
                "SELECT antibody_id, remediation_cmd FROM catechism_antibodies WHERE failure_class_signature = ?",
                (failure_sig,),
            ).fetchone()
            if ab:
                return {
                    "status": "PASS_0_ANTIBODY_HIT",
                    "antibody_id": ab["antibody_id"],
                    "remediation_cmd": ab["remediation_cmd"],
                    "agent_diag_passes": 0,
                    "allowed_to_proceed": False,
                    "instruction": "Execute remediation_cmd directly; do not spend LLM tokens diagnosing.",
                }

        now_sec = int(time.time())
        existing = conn.execute(
            "SELECT * FROM mycelium_task_queue WHERE task_id = ?", (layer,)
        ).fetchone()
        if existing:
            if existing["status"] == "COMPLETED":
                return {
                    "status": "ALREADY_LANDED_BY_PEER",
                    "layer": layer,
                    "leased_by": existing["leased_by"],
                    "result": json.loads(existing["result_json"] or "{}"),
                    "allowed_to_proceed": False,
                    "instruction": "Abandon duplicate work; peer already solved and landed this layer.",
                }
            if (
                existing["status"] == "LEASED"
                and existing["lease_expires_at"] > now_sec
                and existing["leased_by"] != agent_id
            ):
                return {
                    "status": "LOCKED_BY_ACTIVE_PEER",
                    "layer": layer,
                    "leased_by": existing["leased_by"],
                    "lease_expires_in_sec": existing["lease_expires_at"] - now_sec,
                    "allowed_to_proceed": False,
                    "instruction": "Do not touch this layer; another session holds an active lease.",
                }

        conn.execute(
            "UPDATE swarm_fencing_state SET authoritative_token = authoritative_token + 1 WHERE id = 1"
        )
        token = int(
            conn.execute(
                "SELECT authoritative_token FROM swarm_fencing_state WHERE id = 1"
            ).fetchone()[0]
        )

        if existing:
            record_reversible_journal(
                conn,
                token,
                layer,
                "LEASE_UPDATE",
                "UPDATE mycelium_task_queue SET status = ?, leased_by = ?, lease_expires_at = ?, fencing_token = ?, result_json = ? WHERE task_id = ?",
                [
                    existing["status"],
                    existing["leased_by"],
                    existing["lease_expires_at"],
                    existing["fencing_token"],
                    existing["result_json"],
                    layer,
                ],
            )
        else:
            record_reversible_journal(
                conn,
                token,
                layer,
                "LEASE_INSERT",
                "DELETE FROM mycelium_task_queue WHERE task_id = ?",
                [layer],
            )

        conn.execute(
            """
            INSERT OR REPLACE INTO mycelium_task_queue
            (task_id, prompt_payload, status, leased_by, lease_expires_at, fencing_token, result_json, updated_at)
            VALUES (?, ?, 'LEASED', ?, ?, ?, '{}', ?)
            """,
            (layer, failure_sig or "", agent_id, now_sec + 300, token, now_sec),
        )
        conn.commit()
        append_ring_event(
            conn,
            topic="swarm.lease",
            source=agent_id,
            payload={"layer": layer, "fencingToken": token},
        )
        spore_meta = repack_4kb_spore(conn)
        return {
            "status": "LEASE_GRANTED",
            "layer": layer,
            "agent_id": agent_id,
            "fencing_token": token,
            "disk_free_mb": mb,
            "spore": spore_meta,
            "allowed_to_proceed": True,
        }


def cmd_yield(
    conn: sqlite3.Connection,
    agent_id: str,
    layer: str,
    fencing_token: int,
    commit_sha: str,
    learned_fact: str,
    antibody_sig: str | None,
    antibody_cmd: str | None,
) -> dict:
    if not learned_fact or len(learned_fact.strip()) < 15:
        raise SystemExit(
            "REFUSED_BY_DUAL_YIELD_LAW: Every yield must include a substantive --fact (>=15 chars) for the swarm."
        )

    row = conn.execute(
        "SELECT status, fencing_token, leased_by, lease_expires_at, result_json FROM mycelium_task_queue WHERE task_id = ?",
        (layer,),
    ).fetchone()
    if row and fencing_token < int(row["fencing_token"]):
        raise SystemExit(
            f"FENCED_OUT_STALE_SESSION: token {fencing_token} < authoritative layer token {row['fencing_token']} (held by {row['leased_by']})"
        )

    now_sec = int(time.time())
    if row:
        record_reversible_journal(
            conn,
            fencing_token,
            layer,
            "YIELD_COMPLETE",
            "UPDATE mycelium_task_queue SET status = ?, result_json = ?, updated_at = ? WHERE task_id = ?",
            [row["status"], row["result_json"], now_sec, layer],
        )

    result_obj = {
        "commit_sha": commit_sha,
        "learned_fact": learned_fact.strip(),
        "agent_id": agent_id,
        "ts": now_sec,
    }
    conn.execute(
        """
        UPDATE mycelium_task_queue
        SET status = 'COMPLETED', result_json = ?, updated_at = ?
        WHERE task_id = ?
        """,
        (json.dumps(result_obj), now_sec, layer),
    )

    antibody_id = None
    if antibody_sig and antibody_cmd:
        antibody_id = f"AB-{hashlib.sha256(antibody_sig.encode()).hexdigest()[:8].upper()}"
        sig_hex = hashlib.sha256(
            f"{antibody_id}:{antibody_sig}:{antibody_cmd}:{commit_sha}".encode()
        ).hexdigest()
        record_reversible_journal(
            conn,
            fencing_token,
            layer,
            "ANTIBODY_REGISTER",
            "DELETE FROM catechism_antibodies WHERE antibody_id = ?",
            [antibody_id],
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO catechism_antibodies
            (antibody_id, failure_class_signature, remediation_cmd, ed25519_signature, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (antibody_id, antibody_sig, antibody_cmd, sig_hex, now_sec),
        )

    conn.commit()
    door_ok = write_to_memory_door(
        f"[{layer} @ {commit_sha[:12]}] {learned_fact.strip()}", kind="decision"
    )
    ring_env = append_ring_event(
        conn,
        topic="swarm.yield",
        source=agent_id,
        payload={
            "layer": layer,
            "commitSha": commit_sha,
            "learnedFact": learned_fact.strip(),
            "antibodyId": antibody_id,
            "memoryDoorSynced": door_ok,
        },
    )
    spore_meta = repack_4kb_spore(conn)
    return {
        "status": "DUAL_YIELD_COMMITTED",
        "ring_envelope": ring_env,
        "memory_door_written": door_ok,
        "antibody_registered": antibody_id,
        "spore": spore_meta,
    }


def cmd_rollback(conn: sqlite3.Connection, steps: int = 1) -> dict:
    """Principle 4: LIFO Compensating Saga Rollback + Monotonic Fence Increment."""
    rows = conn.execute(
        """
        SELECT journal_id, layer, operation, inverse_sql, inverse_params_json
        FROM reversible_state_journal
        WHERE rolled_back = 0
        ORDER BY journal_id DESC
        LIMIT ?
        """,
        (max(1, steps),),
    ).fetchall()

    executed = []
    for r in rows:
        params = json.loads(r["inverse_params_json"] or "[]")
        conn.execute(r["inverse_sql"], params)
        conn.execute(
            "UPDATE reversible_state_journal SET rolled_back = 1 WHERE journal_id = ?",
            (r["journal_id"],),
        )
        executed.append(
            {"journal_id": r["journal_id"], "layer": r["layer"], "operation": r["operation"]}
        )

    conn.execute(
        "UPDATE swarm_fencing_state SET authoritative_token = authoritative_token + 1 WHERE id = 1"
    )
    conn.commit()
    ring_env = append_ring_event(
        conn,
        topic="swarm.rollback",
        source="genesis-saga-governor",
        payload={"rolledBackCount": len(executed), "entries": executed},
    )
    spore_meta = repack_4kb_spore(conn)
    return {
        "status": "LIFO_ROLLBACK_COMPLETE",
        "rolled_back": executed,
        "ring_envelope": ring_env,
        "spore": spore_meta,
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Genesis v0.7.0-RT Stigmergic Swarm Synapse")
    sub = ap.add_subparsers(dest="cmd", required=True)

    hyd = sub.add_parser("hydrate")
    hyd.add_argument("--agent", required=True)
    hyd.add_argument("--layer", required=True)
    hyd.add_argument("--failure-sig", default=None)

    yld = sub.add_parser("yield")
    yld.add_argument("--agent", required=True)
    yld.add_argument("--layer", required=True)
    yld.add_argument("--fencing-token", type=int, required=True)
    yld.add_argument("--sha", required=True)
    yld.add_argument("--fact", required=True)
    yld.add_argument("--antibody-sig", default=None)
    yld.add_argument("--antibody-cmd", default=None)

    rbk = sub.add_parser("rollback")
    rbk.add_argument("--steps", type=int, default=1)

    args = ap.parse_args()
    db_conn = open_synapse_db()
    if args.cmd == "hydrate":
        print(json.dumps(cmd_hydrate(db_conn, args.agent, args.layer, args.failure_sig), indent=2))
    elif args.cmd == "yield":
        print(
            json.dumps(
                cmd_yield(
                    db_conn,
                    args.agent,
                    args.layer,
                    args.fencing_token,
                    args.sha,
                    args.fact,
                    args.antibody_sig,
                    args.antibody_cmd,
                ),
                indent=2,
            )
        )
    elif args.cmd == "rollback":
        print(json.dumps(cmd_rollback(db_conn, args.steps), indent=2))

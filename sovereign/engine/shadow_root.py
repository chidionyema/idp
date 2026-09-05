"""Shadow root (cp9): a branch pointer that tracks legacy state one to one.

`.estate/heads/shadow_main` always names the Merkle root -- the DAG node
hash cp8's sidecar wrote most recently -- that is equal to the legacy DB's
current state. The root hash IS the checkpoint: nothing here stores the
DB's state a second time, it stores where in cp8's DAG that state already
lives.

update_head() is called once per node cp8's DBSidecar.drain() writes, so
the head changes exactly once per drained write (the cp9 feature's "Root
advances with every write"). verify() walks the DAG backward from the
head to genesis the same way sovereign.engine.receipts.verify() walks its
hash chain: each node's own hash is recomputed and checked against its
filename, and prev_node_hash must resolve to a node that exists, all the
way to GENESIS_NODE_HASH. A broken link, a missing node file, or a cycle
all fail closed (verified=False), never a silent pass.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from sovereign import config

# Mirrors sovereign.sidecar.core.GENESIS_NODE_HASH exactly (same derivation
# from config.RECEIPTS_HASH_HEX_LEN) rather than importing it -- core.py
# calls update_head() below, so importing core here would be circular.
GENESIS_NODE_HASH = "0" * config.RECEIPTS_HASH_HEX_LEN


def head_path() -> Path:
    return config.SHADOW_HEADS_DIR / config.SHADOW_HEAD_FILENAME


def update_head(node_hash: str, dag_dir: Path) -> None:
    """Called by cp8's DBSidecar right after it writes a DAG node --
    the same "never blocks the legacy write" contract applies here: this
    runs during drain(), after the legacy write already committed, so a
    failure here is a sidecar-side degradation, not a legacy-write
    failure."""
    hp = head_path()
    hp.parent.mkdir(parents=True, exist_ok=True)
    tmp = hp.with_suffix(hp.suffix + ".tmp")
    tmp.write_text(json.dumps({"root": node_hash, "dag_dir": str(dag_dir)}, sort_keys=True))
    os.replace(tmp, hp)


def verify() -> dict[str, Any]:
    """Returns {root, parent, nodes, verified} -- the exact shape
    `bin/sb root --json` reports. `nodes` counts every node walked from
    the head back to (but not including) genesis; `parent` is the root
    node's own prev_node_hash."""
    hp = head_path()
    if not hp.exists():
        return {"root": None, "parent": None, "nodes": 0, "verified": False}
    try:
        head = json.loads(hp.read_text())
    except (OSError, json.JSONDecodeError):
        return {"root": None, "parent": None, "nodes": 0, "verified": False}

    root = head.get("root")
    dag_dir = Path(head.get("dag_dir", ""))
    node_hash = root
    parent: str | None = None
    count = 0
    seen: set[str] = set()
    verified = True

    while node_hash and node_hash != GENESIS_NODE_HASH:
        if node_hash in seen:
            verified = False
            break
        seen.add(node_hash)
        node_path = dag_dir / f"{node_hash}.json"
        if not node_path.exists():
            verified = False
            break
        try:
            body = json.loads(node_path.read_text())
        except (OSError, json.JSONDecodeError):
            verified = False
            break
        if hashlib.sha256(config.canonical_json(body)).hexdigest() != node_hash:
            verified = False
            break
        count += 1
        prev = body.get("prev_node_hash", GENESIS_NODE_HASH)
        if count == 1:
            parent = prev
        node_hash = prev

    return {"root": root, "parent": parent, "nodes": count, "verified": verified}

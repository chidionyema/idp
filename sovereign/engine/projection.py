"""Projection views (cp14): a rebuildable hot store compiled entirely from
cp8's immutable Merkle DAG, never trusted to survive on its own.

`rebuild()` deletes nothing itself -- a caller (or `bin/sb rebuild`) may
have already deleted the store -- but always starts from an empty state
and replays every DAG node from genesis to the current head
(shadow_root's head), oldest first, applying each INSERT/UPDATE/DELETE in
order. The result is written back to disk keyed by table and rowid, along
with the root hash the replay reached, so a later caller can tell in one
comparison whether the store is still fresh (`ensure_fresh()`) without
re-walking the whole DAG.

Test isolation follows the one pattern the rest of sovereign/engine/
already uses (sovereign/engine/test_flip.py, sovereign/sidecar/
test_sidecar.py): patch.object the relevant config.* paths, never a
parallel set of override parameters.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from sovereign import config
from sovereign.engine import receipts as receipts_mod
from sovereign.engine import shadow_root


def store_path() -> Path:
    return config.PROJECTION_STORE_PATH


def _walk_nodes_oldest_first(dag_dir: Path, root: str | None) -> list[dict[str, Any]] | None:
    """Mirrors shadow_root.verify()'s backward walk (head to genesis) but
    collects and returns every node body, oldest first, for replay.
    Returns None (fail closed, never a partial or wrong-order replay) on
    any broken link, missing file or cycle -- the exact conditions
    verify() itself already treats as verified=False."""
    bodies: list[dict[str, Any]] = []
    node_hash = root
    seen: set[str] = set()
    while node_hash and node_hash != shadow_root.GENESIS_NODE_HASH:
        if node_hash in seen:
            return None
        seen.add(node_hash)
        node_path = dag_dir / f"{node_hash}.json"
        if not node_path.exists():
            return None
        try:
            body = json.loads(node_path.read_text())
        except (OSError, json.JSONDecodeError):
            return None
        if hashlib.sha256(config.canonical_json(body)).hexdigest() != node_hash:
            return None
        bodies.append(body)
        node_hash = body.get("prev_node_hash", shadow_root.GENESIS_NODE_HASH)
    bodies.reverse()
    return bodies


def _apply(state: dict[str, dict[str, Any]], body: dict[str, Any]) -> None:
    table = body["table"]
    rowid = str(body["rowid"])
    tbl_state = state.setdefault(table, {})
    if body["op"] == "DELETE":
        tbl_state.pop(rowid, None)
    else:
        tbl_state[rowid] = body.get("row")


def rebuild(by: str = "boot") -> dict[str, Any]:
    """Replays the whole DAG from genesis and writes the resulting
    projection to disk. Returns {root, verified, tables, rows}. verified
    is False (and the store on disk is left untouched) the moment
    _walk_nodes_oldest_first fails closed -- a rebuild never overwrites a
    working store with a broken one."""
    root_state = shadow_root.verify()
    root = root_state["root"]

    state: dict[str, dict[str, Any]] = {}
    verified = root_state["verified"]
    if root is not None and verified:
        bodies = _walk_nodes_oldest_first(config.SIDECAR_DAG_DIR, root)
        if bodies is None:
            verified = False
        else:
            for body in bodies:
                _apply(state, body)

    result = {
        "root": root,
        "verified": verified,
        "tables": sorted(state.keys()),
        "rows": sum(len(t) for t in state.values()),
    }
    if not result["verified"]:
        return result

    path = store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps({"root": root, "tables": state}, sort_keys=True))
    os.replace(tmp, path)

    text = config.REBUILD_RECEIPT_TEMPLATE.format(root=root)
    receipts_mod.append({
        "session_id": "-", "kind": "rebuild", "by": by, "text": text,
        "step": 0, "status": "rebuilt", "task": "", "runner": "",
        "root": root, "rows": result["rows"],
    })
    return result


def current_view_root() -> str | None:
    path = store_path()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text()).get("root")
    except (OSError, json.JSONDecodeError):
        return None


def ensure_fresh(by: str = "boot") -> dict[str, Any]:
    """The boot check (cp14): compares the projection store's own
    recorded root against the current shadow-root head. Any mismatch --
    a deleted store, a stale one, or a head that has moved since the
    store was last built -- triggers rebuild() and returns its result
    with rebuilt=True; an already-fresh store returns rebuilt=False
    without touching the DAG at all."""
    current_root = shadow_root.verify()["root"]
    stored_root = current_view_root()
    if stored_root is not None and stored_root == current_root:
        return {"root": current_root, "rebuilt": False}
    result = rebuild(by=by)
    result["rebuilt"] = True
    return result


def read(table: str, rowid: Any) -> dict[str, Any] | None:
    """Reads one row from the projection store as it stands -- never
    triggers a rebuild itself (call ensure_fresh() first if freshness
    matters to the caller); a stale read is a caller decision, not
    something this function should hide."""
    path = store_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return data.get("tables", {}).get(table, {}).get(str(rowid))

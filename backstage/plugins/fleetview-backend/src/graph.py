"""FleetView estate graph snapshot: every node and edge in `catalog/estate.db`, for a spatial
view of the estate instead of a table (the standing complaint this answers: blast.py already
computes real graph data -- nodes, edges, hops -- and the page renders it as a bullet list).

Read-only, whole-graph read. This does not walk the graph (that is blast.py's `blast_radius_for`,
reused as-is by the canvas on click) -- it hands over every node and edge once so the frontend can
lay them out and let a click trigger the real walk. No node or edge is invented, scored, or
filtered here: what `bin/estate-twin-runtime` has swept is what ships, unedited.

Same "never fabricated" rule as blast.py: a database that does not exist yet is GraphUnavailable
(503), never an empty snapshot claiming the estate has no nodes.

CONFIG: `ESTATE_DB` overrides the default path, same variable blast.py reads -- one database,
never a second one for this reader.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[4]
_DB_DEFAULT = _ROOT / "catalog" / "estate.db"


class GraphUnavailable(RuntimeError):
    """Raised when the estate graph has never been swept. routes.py turns this into 503,
    matching blast.py's own rule for a real gap versus a fabricated empty answer."""


def _db_path() -> Path:
    return Path(os.environ.get("ESTATE_DB", str(_DB_DEFAULT)))


def graph_snapshot() -> dict[str, Any]:
    db = _db_path()
    if not db.exists():
        raise GraphUnavailable(
            f"no asset database at {db}; bin/estate-twin-runtime --once has never run"
        )
    con = sqlite3.connect(str(db))
    try:
        nodes = [
            {"id": node_id, "domain": domain, "type": typ, "status": status}
            for node_id, domain, typ, status in con.execute(
                "SELECT id, domain, type, status FROM nodes"
            )
        ]
        edges = [
            {"source_id": source_id, "target_id": target_id, "relation": relation}
            for source_id, target_id, relation in con.execute(
                "SELECT source_id, target_id, relation FROM edges"
            )
        ]
    finally:
        con.close()
    return {"nodes": nodes, "edges": edges}

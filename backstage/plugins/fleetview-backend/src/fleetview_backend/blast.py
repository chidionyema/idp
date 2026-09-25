"""FleetView item #7: blast radius, on the board instead of a terminal.

`bin/estate-twin-runtime --blast-radius <node_id>` already answers the founder's question --
"if this dies, what dies with it" -- by walking the `edges` table `bin/estate-twin-runtime`
itself writes into `catalog/estate.db`. That answer exists today only as a CLI flag: a person
has to be at a terminal with the repo checked out to ask it. This module is the same answer,
reached from a Backstage door instead (standing rule 2026-09-09: every ticket names the exact
UI surface a person presses, never a terminal).

It does not reimplement the graph walk (THE HEADLINE: never script what a proven platform
already solves) -- it loads `bin/estate-twin-runtime` as a module by path, the same way
`routes.py` loads this plugin's own sibling modules, and calls its real `blast_radius()`
function and `edges` table directly. `bin/estate-twin-runtime` has no `.py` suffix, so
`importlib.util.spec_from_file_location` alone returns None for it (confirmed by hand); an
explicit `SourceFileLoader` is what makes an extensionless script importable.

No session-to-node mapping is invented here. FleetView's sessions carry a `repo` field, but the
graph's nodes are `k8s:deployment:<ns>:<name>`, `git:branch:<b>` and `code:module:<dotted>` --
none of them keyed by repo, and guessing a match would be exactly the kind of fabricated claim
this estate's "measured, not guessed" rule exists to prevent. This exposes the query itself, by
the node id the graph already uses (visible via `bin/estate-twin-runtime --state`), as a Fleet
page tool -- not a per-row automatic answer that could be wrong.

CONFIG (LAW 46): ESTATE_DB, default `<repo>/catalog/estate.db` -- same variable
`bin/estate-twin-runtime`, `notes.py` and `signals.py` all read.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import sqlite3
from pathlib import Path
from types import ModuleType
from typing import Any

_ROOT = Path(__file__).resolve().parents[4]
_DB_DEFAULT = _ROOT / "catalog" / "estate.db"
_TWIN_SCRIPT = _ROOT / "bin" / "estate-twin-runtime"


class InvalidQuery(ValueError):
    """Raised for a request with no node id -- routes.py turns this into 400."""


class GraphUnavailable(RuntimeError):
    """Raised when the graph has never been swept -- routes.py turns this into 503, the same
    status `bin/estate-twin-runtime --blast-radius` itself reports (exit code 2, 'run --once')."""


def _load_twin_module() -> ModuleType:
    loader = importlib.machinery.SourceFileLoader(
        "fleetview_estate_twin_impl", str(_TWIN_SCRIPT)
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    if spec is None:
        raise GraphUnavailable(f"cannot load {_TWIN_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def _db_path() -> Path:
    return Path(os.environ.get("ESTATE_DB", str(_DB_DEFAULT)))


def blast_radius_for(node_id: str) -> dict[str, Any]:
    """What is downstream (and upstream) of `node_id`, straight from the graph's own `edges`
    table. `downstream`/`upstream` are empty lists, never omitted, when the graph has no edges
    recorded for this node -- that is the real, honest answer `bin/estate-twin-runtime` itself
    gives ("nothing recorded in edges; the graph cannot answer this yet"), not a sign of an
    empty blast radius.
    """
    node_id = (node_id or "").strip()
    if not node_id:
        raise InvalidQuery("node_id is required")

    db = _db_path()
    if not db.exists():
        raise GraphUnavailable(
            f"no asset database at {db}; bin/estate-twin-runtime --once has never run"
        )

    twin = _load_twin_module()
    con = sqlite3.connect(str(db))
    try:
        downstream = [
            {"node_id": nid, "hops": hops, "relation": relation}
            for nid, hops, relation in twin.blast_radius(con, node_id)
        ]
        upstream = [
            {"node_id": src, "relation": relation}
            for src, relation in con.execute(
                "SELECT source_id, relation FROM edges WHERE target_id = ?", (node_id,)
            )
        ]
    finally:
        con.close()

    return {"node_id": node_id, "downstream": downstream, "upstream": upstream}

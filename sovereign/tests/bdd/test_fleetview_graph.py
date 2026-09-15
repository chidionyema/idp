"""FleetView estate graph snapshot: src/graph.py, graded the same way
test_fleetview_blast_radius.py grades its sibling module -- a plain unit suite against a seeded
copy of the same `nodes`/`edges` schema `bin/estate-twin-runtime` writes into `catalog/estate.db`.

Proves graph.py's own contract: a whole, unfiltered snapshot of both tables, and the same honest
'graph not swept yet' distinct from 'swept and empty' that blast.py already established.
"""

from __future__ import annotations

import importlib.util
import sqlite3
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
GRAPH_MODULE = REPO / "backstage" / "plugins" / "fleetview-backend" / "src" / "graph.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _seed(db_path: Path) -> None:
    con = sqlite3.connect(str(db_path))
    con.executescript(
        """
        CREATE TABLE nodes (
            id TEXT PRIMARY KEY, domain TEXT NOT NULL, type TEXT NOT NULL,
            status TEXT NOT NULL, metadata TEXT NOT NULL,
            last_seen TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE edges (
            source_id TEXT NOT NULL, target_id TEXT NOT NULL, relation TEXT NOT NULL,
            PRIMARY KEY (source_id, target_id, relation)
        );
        """
    )
    con.executemany(
        "INSERT INTO nodes (id, domain, type, status, metadata) VALUES (?, ?, ?, ?, '{}')",
        [
            ("k8s:deployment:idp:catalogue", "runtime", "deployment", "active"),
            ("k8s:deployment:idp:reader", "runtime", "deployment", "dead"),
            ("git:summary:stranded", "code", "summary", "stranded"),
        ],
    )
    con.execute(
        "INSERT INTO edges (source_id, target_id, relation) VALUES (?, ?, ?)",
        ("k8s:deployment:idp:catalogue", "k8s:deployment:idp:reader", "serves"),
    )
    con.commit()
    con.close()


@pytest.fixture()
def graph(monkeypatch, tmp_path):
    db = tmp_path / "estate.db"
    _seed(db)
    monkeypatch.setenv("ESTATE_DB", str(db))
    return _load(GRAPH_MODULE, "fleetview_graph_under_test")


def test_a_graph_that_has_never_been_swept_is_unavailable_not_an_empty_snapshot(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("ESTATE_DB", str(tmp_path / "does-not-exist.db"))
    module = _load(GRAPH_MODULE, "fleetview_graph_unswept")
    with pytest.raises(module.GraphUnavailable):
        module.graph_snapshot()


def test_snapshot_returns_every_node_unfiltered(graph):
    result = graph.graph_snapshot()
    ids = {n["id"] for n in result["nodes"]}
    assert ids == {
        "k8s:deployment:idp:catalogue",
        "k8s:deployment:idp:reader",
        "git:summary:stranded",
    }


def test_snapshot_carries_domain_type_and_status_per_node(graph):
    result = graph.graph_snapshot()
    by_id = {n["id"]: n for n in result["nodes"]}
    assert by_id["k8s:deployment:idp:reader"]["domain"] == "runtime"
    assert by_id["k8s:deployment:idp:reader"]["type"] == "deployment"
    assert by_id["k8s:deployment:idp:reader"]["status"] == "dead"


def test_snapshot_returns_every_edge_unfiltered(graph):
    result = graph.graph_snapshot()
    assert result["edges"] == [
        {
            "source_id": "k8s:deployment:idp:catalogue",
            "target_id": "k8s:deployment:idp:reader",
            "relation": "serves",
        }
    ]


def test_a_swept_but_empty_graph_is_empty_lists_not_an_error(monkeypatch, tmp_path):
    db = tmp_path / "estate.db"
    con = sqlite3.connect(str(db))
    con.executescript(
        """
        CREATE TABLE nodes (id TEXT PRIMARY KEY, domain TEXT NOT NULL, type TEXT NOT NULL,
            status TEXT NOT NULL, metadata TEXT NOT NULL,
            last_seen TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE edges (source_id TEXT NOT NULL, target_id TEXT NOT NULL, relation TEXT NOT NULL,
            PRIMARY KEY (source_id, target_id, relation));
        """
    )
    con.commit()
    con.close()
    monkeypatch.setenv("ESTATE_DB", str(db))
    module = _load(GRAPH_MODULE, "fleetview_graph_empty")
    assert module.graph_snapshot() == {"nodes": [], "edges": []}

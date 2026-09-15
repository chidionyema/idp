"""FleetView blast radius (item #7): src/blast.py, graded the same way test_fleetview_signals.py
and test_fleetview_notes.py grade their modules -- a plain unit suite against a seeded copy of
the same `nodes`/`edges` schema `bin/estate-twin-runtime` writes into `catalog/estate.db`.

This does not re-test `bin/estate-twin-runtime`'s own `blast_radius()` walk (that belongs to its
own suite); it proves blast.py's own contract: input validation, an honest 'graph not swept yet'
distinct from an honest 'no edges recorded', and that the real graph-walk function is the one
actually called, not a reimplementation that could drift from it.
"""

from __future__ import annotations

import importlib.util
import sqlite3
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
BLAST_MODULE = REPO / "backstage" / "plugins" / "fleetview-backend" / "src" / "blast.py"


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
        "INSERT INTO nodes (id, domain, type, status, metadata) VALUES (?, 'runtime', 'deployment', 'active', '{}')",
        [
            ("k8s:deployment:idp:catalogue",),
            ("k8s:deployment:idp:catalogue-replica",),
            ("k8s:deployment:idp:reader",),
        ],
    )
    con.executemany(
        "INSERT INTO edges (source_id, target_id, relation) VALUES (?, ?, ?)",
        [
            (
                "k8s:deployment:idp:catalogue",
                "k8s:deployment:idp:catalogue-replica",
                "replicates",
            ),
            (
                "k8s:deployment:idp:catalogue-replica",
                "k8s:deployment:idp:reader",
                "serves",
            ),
        ],
    )
    con.commit()
    con.close()


@pytest.fixture()
def blast(monkeypatch, tmp_path):
    db = tmp_path / "estate.db"
    _seed(db)
    monkeypatch.setenv("ESTATE_DB", str(db))
    return _load(BLAST_MODULE, "fleetview_blast_under_test")


def test_a_blank_node_id_is_invalid(blast):
    with pytest.raises(blast.InvalidQuery):
        blast.blast_radius_for("")


def test_a_graph_that_has_never_been_swept_is_unavailable_not_empty(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("ESTATE_DB", str(tmp_path / "does-not-exist.db"))
    module = _load(BLAST_MODULE, "fleetview_blast_unswept")
    with pytest.raises(module.GraphUnavailable):
        module.blast_radius_for("k8s:deployment:idp:catalogue")


def test_downstream_walks_the_real_edges_table_multiple_hops(blast):
    result = blast.blast_radius_for("k8s:deployment:idp:catalogue")
    assert result["node_id"] == "k8s:deployment:idp:catalogue"
    downstream = {row["node_id"]: row for row in result["downstream"]}
    assert downstream["k8s:deployment:idp:catalogue-replica"]["hops"] == 1
    assert downstream["k8s:deployment:idp:reader"]["hops"] == 2


def test_upstream_is_the_reverse_edge(blast):
    result = blast.blast_radius_for("k8s:deployment:idp:catalogue-replica")
    assert result["upstream"] == [
        {"node_id": "k8s:deployment:idp:catalogue", "relation": "replicates"}
    ]


def test_a_node_with_no_recorded_edges_gets_empty_lists_not_an_error(blast):
    result = blast.blast_radius_for("k8s:deployment:idp:nothing-points-here")
    assert result["downstream"] == []
    assert result["upstream"] == []

"""A pool may give back the node that is not running, and never the one that is.

2026-10-28: the worker pool held two nodes because a surge on 2026-08-27 never finished. The
one that kept serving was ACTIVE; the one that never came up was STOPPED. OKE will not shrink a
pool with an update, so the pool stayed at two, the free tier's one-node allowance was spent, and
every apply of the cluster was refused with "nodes-per-node-pool limit has been exceeded" -- the
cluster could not create the bridge that is its only road in.

The rule is deliberately narrow: exactly one node is running, and the others are stopped. A
running node is never a candidate, and a pool with two running nodes (a surge in flight) is
refused, because that is the surge door's own case and not this one.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "bin" / "lib" / "node_prune.py"


def _load():
    loader = importlib.machinery.SourceFileLoader("node_prune", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def _run(rows: list[dict]) -> list[str]:
    out = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(rows),
        capture_output=True,
        text=True,
        timeout=30,
    )
    return [line for line in out.stdout.splitlines() if line.strip()]


def test_the_stopped_node_is_the_one_that_goes():
    mod = _load()
    ids, reason = mod.choose(
        [
            {"id": "ocid1.run", "name": "node-0", "state": "RUNNING"},
            {"id": "ocid1.dead", "name": "node-1", "state": "STOPPED"},
        ]
    )
    assert ids == ["ocid1.dead"] and reason == ""


def test_a_running_node_is_never_chosen():
    mod = _load()
    ids, _ = mod.choose(
        [
            {"id": "ocid1.run", "name": "node-0", "state": "RUNNING"},
            {"id": "ocid1.run2", "name": "node-1", "state": "RUNNING"},
            {"id": "ocid1.dead", "name": "node-2", "state": "STOPPED"},
        ]
    )
    # two running nodes: a surge is in flight, which is the surge door's case, not this one
    assert ids == []


def test_a_pool_with_one_running_node_and_nothing_stopped_is_refused():
    mod = _load()
    ids, reason = mod.choose(
        [{"id": "ocid1.run", "name": "node-0", "state": "RUNNING"}]
    )
    assert ids == [] and "no node is stopped" in reason


def test_a_pool_with_no_running_node_is_refused():
    mod = _load()
    ids, reason = mod.choose(
        [
            {"id": "ocid1.a", "name": "node-0", "state": "STOPPED"},
            {"id": "ocid1.b", "name": "node-1", "state": "STOPPED"},
        ]
    )
    assert ids == [] and "exactly 1 running node" in reason


def test_an_empty_pool_is_refused():
    mod = _load()
    ids, reason = mod.choose([])
    assert ids == [] and "no nodes" in reason


def test_the_command_prints_one_prune_line_per_stopped_node():
    lines = _run(
        [
            {"id": "ocid1.run", "name": "node-0", "state": "RUNNING"},
            {"id": "ocid1.dead", "name": "node-1", "state": "STOPPED"},
        ]
    )
    assert lines == ["PRUNE ocid1.dead node-1"]


def test_the_command_refuses_instead_of_guessing():
    lines = _run([{"id": "ocid1.run", "name": "node-0", "state": "RUNNING"}])
    assert len(lines) == 1 and lines[0].startswith("REFUSE ")


def test_unreadable_input_is_a_refusal_not_a_crash():
    out = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input="not json",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert out.returncode == 0 and "REFUSE" in out.stdout


def test_the_cli_prints_a_json_array_of_ids_as_ids():
    # The OCI CLI prints `--query 'data[].id' --raw-output` as a JSON ARRAY. Word-splitting it
    # turned its brackets and quotes into "pool ids" on 2026-10-28, every pool read failed, and
    # the surge door deleted nothing.
    mod = _load()
    ids = mod.parse_ids('[\n  "ocid1.nodepool.a",\n  "ocid1.nodepool.b"\n]\n')
    assert ids == ["ocid1.nodepool.a", "ocid1.nodepool.b"]


def test_a_single_value_query_is_read_as_one_id():
    mod = _load()
    assert mod.parse_ids('"ocid1.nodepool.a"\n') == ["ocid1.nodepool.a"]
    assert mod.parse_ids("ocid1.nodepool.a\n") == ["ocid1.nodepool.a"]


def test_unreadable_cli_output_yields_no_ids():
    mod = _load()
    assert mod.parse_ids("") == []
    assert mod.parse_ids("ServiceError: could not read the pools\n") == []


def test_the_ids_command_prints_one_id_per_line():
    out = subprocess.run(
        [sys.executable, str(SCRIPT), "ids"],
        input='["ocid1.a", "ocid1.b"]',
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert out.returncode == 0
    assert out.stdout.split() == ["ocid1.a", "ocid1.b"]


def test_the_surge_door_reads_the_pools_through_the_ids_parser():
    # The door must not word-split a JSON array again: the regression is a shell bug, so the
    # guard lives next to the door that had it.
    door = SCRIPT.parent.parent / "idp-oke-surge-node"
    text = door.read_text(encoding="utf-8")
    assert text.count('node_prune.py" ids') >= 2

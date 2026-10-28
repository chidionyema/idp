"""oci-nodepool-reconcile rules, proved offline (idp#7343)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
LIB = REPO / "platform" / "estate" / "libexec"
spec = importlib.util.spec_from_file_location(
    "nprec", LIB / "oci-nodepool-reconcile.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def node(i, state="ACTIVE"):
    return {"id": i, "lifecycle-state": state}


def test_phantom_detected():
    v = mod.classify([node("a")], {"a": "TERMINATED"})
    assert v[0]["verdict"] == "phantom" and v[0]["pool_says"] == "ACTIVE"


def test_terminating_is_phantom():
    assert mod.classify([node("a")], {"a": "TERMINATING"})[0]["verdict"] == "phantom"


def test_live_node_kept_for_every_non_dead_state():
    for s in (
        "RUNNING",
        "STOPPED",
        "STOPPING",
        "PROVISIONING",
        "STARTING",
        "MOVING",
        "WEIRD",
    ):
        assert mod.classify([node("a")], {"a": s})[0]["verdict"] == "keep", s


def test_pool_record_never_decides():
    # pool says DELETED/FAILED, instance RUNNING: kept
    assert mod.classify([node("a", "FAILED")], {"a": "RUNNING"})[0]["verdict"] == "keep"


def test_missing_instance_is_phantom():
    v = mod.classify([node("a")], {})
    assert v[0]["verdict"] == "phantom" and v[0]["instance_says"] == "ABSENT"


def test_mixed_pool():
    vs = mod.classify(
        [node("a"), node("b"), node("c")], {"a": "RUNNING", "b": "TERMINATED"}
    )
    assert [v["verdict"] for v in vs] == ["keep", "phantom", "phantom"]
    assert [v["node_id"] for v in mod.phantoms(vs)] == ["b", "c"]


def test_empty_pool():
    assert mod.classify([], {"a": "TERMINATED"}) == []
    assert mod.classify(None, {}) == []
    assert "empty pool" in mod.render("p", "pid", [])


def test_cli_writes_only_phantoms(tmp_path):
    pools = [
        {"id": "P1", "name": "a1", "nodes": [node("x"), node("y")]},
        {"id": "P2", "name": "e", "nodes": []},
    ]
    (tmp_path / "p.json").write_text(json.dumps(pools))
    (tmp_path / "i.json").write_text(json.dumps({"x": "TERMINATED", "y": "RUNNING"}))
    assert (
        mod.main(
            [
                "--pools",
                str(tmp_path / "p.json"),
                "--instances",
                str(tmp_path / "i.json"),
                "--ids-out",
                str(tmp_path / "ids"),
            ]
        )
        == 0
    )
    assert (tmp_path / "ids").read_text() == "P1 x\n"


def test_door_shape():
    sh = (LIB / "oci-nodepool-reconcile.sh").read_text()
    assert "--is-decrement-size true --force" in sh
    assert 'MODE="${1:-plan}"' in sh
    for forbidden in ("volume delete", "instance terminate"):
        assert forbidden not in sh
    y = (REPO / "platform/estate/intents/oci-nodepool-reconcile.yaml").read_text()
    assert (
        'apply: {type: string, default: "false"}' in y and "halt_on_failure: true" in y
    )

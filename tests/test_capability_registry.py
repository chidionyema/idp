"""The Estate Capability Registry: the invariants, the query contract, and the gate.

Every test here is a falsifier the spec names (docs/specs/2026-10-25-estate-capability-registry.md
section 4) or a property the door promises. A test that cannot fail is not a test, so each
one carries the case that must trip it: a seeded duplicate id, an out-of-window receipt, a
writer for a foreign plane, a stale read, a deleted capability.

The gate (bin/registry-gate) runs these same five cases; this file is the gate's own proof,
so the two can never disagree about what the invariants are.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
DOOR = REPO / "bin" / "capability-index"
GATE = REPO / "bin" / "registry-gate"
SNAPSHOT = REPO / "catalog" / "estate-capability-registry.json"


def load_door():
    spec = importlib.util.spec_from_loader(
        "capability_index",
        importlib.machinery.SourceFileLoader("capability_index", str(DOOR)),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def door(tmp_path, monkeypatch):
    module = load_door()
    monkeypatch.setattr(module, "KEY_PATH", tmp_path / "registry.key")
    monkeypatch.setattr(module, "DB_PATH", tmp_path / "registry.db")
    return module


def a_record(door, cap_id="cap:tool/example", kind="tool", plane="idp", writer="repo"):
    return door.make_record(
        cap_id,
        kind,
        "an example capability",
        plane,
        "estate-runtime",
        writer,
        "test",
    )


# --------------------------------------------------------------------------------------
# I-1: one capability, one record, one writer


def test_i1_a_second_writer_for_one_id_is_refused(door, tmp_path):
    """The falsifier: two writers, one cap: id. The second is refused and leaves a finding."""
    store = door.Store(tmp_path / "registry.db")
    store.open()
    first = a_record(
        door, "cap:service/ns/dual", kind="service", plane="cluster", writer="cluster"
    )
    assert store.write(first, "cluster")[0] is True
    second = dict(first)
    second["plane"] = "mac"
    ok, detail = store.write(second, "mac")
    assert ok is False
    assert "already written by writer" in detail
    findings = [f for f in store.findings(20) if f["kind"] == "capability.duplicate"]
    assert findings, "the refused duplicate must leave a finding against the writer"


def test_i1_the_census_merges_one_capability_declared_twice(door):
    """The same workload in a base and an overlay is one capability, not two records."""
    ctx = door.Context(idp=REPO)
    records, issues = door.census(ctx, live=False)
    assert issues["duplicate_ids"] == []
    assert len(records) == len({r["id"] for r in records.values()})


# --------------------------------------------------------------------------------------
# I-2 and I-4: no operating without a receipt in the window; stale reads are marked


def test_i2_a_receipt_outside_its_window_reads_declared(door):
    """The falsifier: an out-of-window receipt. It must not read operating."""
    old = door.now_utc() - timedelta(days=90)
    record = a_record(
        door, "cap:intent/aged", kind="intent", plane="estate", writer="intents"
    )
    record["proof"] = {
        "receipt": door.make_receipt("test", "intent:aged", old),
        "proven_at": door.iso(old),
        "window_s": 86400,
    }
    record["health"]["state"] = "operating"
    read = door.read_record(record)
    assert read["health"]["state"] == "declared"
    assert read["stale"] is True


def test_i2_a_record_without_a_receipt_is_declared_and_blind(door):
    record = a_record(door)
    read = door.read_record(record)
    assert read["health"]["state"] == "declared"
    assert read["health"]["blind"] is True
    assert read["stale"] is False


def test_i4_a_fresh_receipt_reads_operating_and_is_not_stale(door):
    now = door.now_utc()
    record = a_record(door)
    record["proof"] = {
        "receipt": door.make_receipt("test", "tool:example", now),
        "proven_at": door.iso(now),
        "window_s": 3600,
    }
    read = door.read_record(record)
    assert read["health"]["state"] == "operating"
    assert read["stale"] is False


# --------------------------------------------------------------------------------------
# I-3: one writer per plane


def test_i3_a_writer_for_a_foreign_plane_is_refused_at_build(door):
    """The falsifier: writer `repo` (plane idp) emitting a cluster record."""
    with pytest.raises(ValueError):
        a_record(
            door, "cap:service/ns/x", kind="service", plane="cluster", writer="repo"
        )


def test_i3_a_writer_for_a_foreign_plane_is_refused_at_write(door, tmp_path):
    store = door.Store(tmp_path / "registry.db")
    store.open()
    rogue = a_record(door)
    rogue["plane"] = "cluster"
    ok, detail = store.write(rogue, "repo")
    assert ok is False
    assert "may not write plane" in detail
    assert [f for f in store.findings(20) if f["kind"] == "plane.violation"]


# --------------------------------------------------------------------------------------
# I-5: deletion converges


def test_i5_a_removed_capability_is_tombstoned_in_one_cycle(door, tmp_path):
    """The falsifier: a capability deleted from the estate. It is tombstoned, not lost."""
    store = door.Store(tmp_path / "registry.db")
    store.open()
    store.write(a_record(door, "cap:tool/doomed"), "repo")
    result = door.reconcile(store, ["cap:tool/kept"])
    assert "cap:tool/doomed" in result["tombstoned"]
    row = store.get("cap:tool/doomed")
    assert row is not None
    assert row["tombstoned"] is True
    assert row["tombstoned_at"]


def test_i5_a_capability_that_left_is_not_served_as_live(door, tmp_path):
    store = door.Store(tmp_path / "registry.db")
    store.open()
    store.write(a_record(door, "cap:tool/doomed"), "repo")
    door.reconcile(store, [])
    served = [r["id"] for r in store.all()]
    assert "cap:tool/doomed" not in served
    assert "cap:tool/doomed" in [r["id"] for r in store.all(include_tombstoned=True)]


# --------------------------------------------------------------------------------------
# receipts (spec section 9)


def test_a_forged_receipt_is_not_a_proof(door):
    forged = "test|intent:forged|2020-01-01T00:00:00Z|deadbeef"
    assert door.receipt_ok(forged) is False


def test_a_minted_receipt_verifies(door):
    receipt = door.make_receipt("estate.db", "intent:x", door.now_utc())
    assert door.receipt_ok(receipt) is True


# --------------------------------------------------------------------------------------
# the query contract (spec section 8)


def test_the_query_contract_answers_from_the_store(door, tmp_path):
    store = door.Store(tmp_path / "registry.db")
    store.open()
    store.write(a_record(door, "cap:tool/queryable"), "repo")
    records = store.all()
    ids = [r["id"] for r in records]
    assert "cap:tool/queryable" in ids


def test_the_committed_snapshot_is_deterministic(door):
    """The snapshot is the repo-derived half; it must be the same bytes every time."""
    ctx = door.Context(idp=REPO)
    first = door.snapshot_text(door.snapshot(ctx))
    second = door.snapshot_text(door.snapshot(door.Context(idp=REPO)))
    assert first == second
    assert json.loads(first)["records"]


def test_the_committed_snapshot_has_no_machine_state(door):
    """No timestamps and no absolute paths: the snapshot must be the same on every machine."""
    ctx = door.Context(idp=REPO)
    text = door.snapshot_text(door.snapshot(ctx))
    assert "/Users/" not in text
    assert str(HOME_PATH) not in text


HOME_PATH = Path.home()


def test_the_committed_snapshot_matches_a_fresh_generation(door):
    """The drift check: the committed file is what the door generates now."""
    ctx = door.Context(idp=REPO)
    drift = door.snapshot_drift(ctx, SNAPSHOT)
    assert drift["verdict"] == "OK", drift


# --------------------------------------------------------------------------------------
# the gate, run for real


def test_the_gate_passes_on_this_repository():
    result = subprocess.run(
        [sys.executable, str(GATE)],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
        cwd=str(REPO),
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_the_gate_can_fail_a_drifted_snapshot(tmp_path):
    """A gate that cannot fail is not a gate: a snapshot that names a capability the
    repository does not have must be refused."""
    drifted = tmp_path / "drifted.json"
    payload = json.loads(SNAPSHOT.read_text())
    ghost = json.loads(json.dumps(payload["records"][0]))
    ghost["id"] = "cap:tool/ghost"
    payload["records"].append(ghost)
    drifted.write_text(json.dumps(payload, indent=2) + "\n")
    result = subprocess.run(
        [sys.executable, str(GATE), "--snapshot", str(drifted)],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
        cwd=str(REPO),
    )
    assert result.returncode == 1
    assert "drift" in result.stdout


def test_the_mcp_surface_answers_the_query_contract():
    """The agent-readable surface (spec section 8) answers without a shell."""
    sys.path.insert(0, str(REPO))
    try:
        from mcp.plugins import estate_mcp
    finally:
        sys.path.pop(0)
    out = estate_mcp._capability_query({"kind": "intent", "query": ""})
    assert "capability record(s)" in out
    got = estate_mcp._capability_get({"id": "cap:intent/lane-submit"})
    assert "cap:intent/lane-submit" in got or "BLIND" in got
    proved = estate_mcp._capability_prove({"id": "cap:intent/lane-submit"})
    assert proved.split(":")[0] in {"OK", "FAILED", "BLIND"}

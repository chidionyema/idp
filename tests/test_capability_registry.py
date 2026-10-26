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
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
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


# --------------------------------------------------------------------------------------
# the evidence lifecycle (spec section 14): a component is built, and the map must follow


def test_the_gate_fails_a_lagging_snapshot_without_strict(tmp_path):
    """A component was built and the witness does not name it: the merge point is not true.

    This is the case that used to be a finding. It is now a failure in the DEFAULT mode,
    because a witness that lags the estate is drift, and drift that can land is not a
    guarantee: the founder's rule is that the map is true at the merge point by
    mathematics (the witness is a pure function of the tree) and not by an agent
    remembering to refresh it.
    """
    payload = json.loads(SNAPSHOT.read_text())
    assert len(payload["records"]) > 2
    dropped = payload["records"].pop()["id"]
    lagging = tmp_path / "lagging.json"
    lagging.write_text(json.dumps(payload, indent=2) + "\n")
    result = subprocess.run(
        [sys.executable, str(GATE), "--snapshot", str(lagging)],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
        cwd=str(REPO),
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "drift" in result.stdout
    assert dropped in result.stdout


def test_the_census_names_the_estates_own_implementation():
    """The map names the code that does the work, not only the scripts that are run.

    Measured 2026-10-26: the census named bin/ (434 executables) and the manifests,
    and it did NOT name platform/**.py -- the efficiency chain, the cache guardian, the
    request ceiling, the symbol slicer. A query for `symbol-slicer` answered 0 records
    on a main that has shipped platform/estate/libexec/symbol_slicer.py since #7212.
    A map that cannot answer "does the estate already have this?" is not a map.
    """
    payload = json.loads(SNAPSHOT.read_text())
    layers = [r for r in payload["records"] if r.get("kind") == "layer"]
    assert layers, "the estate's own modules must be in the map"
    by_path = {r.get("path"): r for r in layers}
    slicer = "platform/estate/libexec/symbol_slicer.py"
    assert slicer in by_path, (
        "a module that ships in the tree must be named: {}".format(
            sorted(p for p in by_path if p and "symbol_slicer" in p)
        )
    )
    # every layer record names a file that exists, and no file is named twice
    for path, record in by_path.items():
        assert path and (REPO / path).is_file(), path
        assert record["id"] == "cap:layer/{}".format(path[:-3].replace("/", "-")), (
            record
        )
    assert len({r["id"] for r in layers}) == len(layers), "one module, one record"


def test_the_witness_needs_no_claim_but_another_file_does():
    """The witness is generated, so it belongs to nobody's claim; a product file still does.

    The claim-gate exempts the witness path from claim coverage, because the pipeline
    regenerates it (section 14) and an agent must not have to claim a file it never
    touched. The exemption is narrow: any other path outside the claim is still refused.
    """
    sys.path.insert(0, str(REPO / "bin"))
    try:
        spec = importlib.util.spec_from_loader(
            "claim_gate",
            importlib.machinery.SourceFileLoader(
                "claim_gate", str(REPO / "bin" / "claim-gate")
            ),
        )
        claim_gate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(claim_gate)
    finally:
        sys.path.pop(0)
    now = datetime.now(timezone.utc)
    comment = {
        "body": "CLAIM agent=pi paths=bin/some-file heartbeat={}".format(
            now.replace(microsecond=0).isoformat().replace("+00:00", "Z")
        )
    }

    def fetch(repo, number):
        return {"state": "open"}, [comment]

    text = "Claim: chidionyema/idp#7203\nAgent: pi"
    witness = claim_gate.verdict(
        text, ["catalog/estate-capability-registry.json"], "chidionyema/idp", fetch, now
    )
    assert witness == [], witness
    product = claim_gate.verdict(
        text, ["docs/some-note.md"], "chidionyema/idp", fetch, now
    )
    assert product, "a file outside every claim must still be refused"
    assert "outside every claim" in product[0]


def test_the_witness_is_regenerated_by_the_pipeline_not_by_an_agent():
    """The refresh is a step in the pipeline: the workflow regenerates and commits it."""
    workflow = REPO / ".github" / "workflows" / "registry-snapshot.yml"
    assert workflow.exists(), "the pipeline that keeps the witness true must exist"
    text = workflow.read_text()
    assert "bin/capability-index emit --write" in text, "the door must be the generator"
    assert "pull_request" in text, "it must run on the change it exists for"
    assert "git push" in text, "the regenerated witness must reach the branch"
    assert "catalog/estate-capability-registry.json" in text
    # the bot's commit goes through the estate's own commit-msg hook, so it carries the
    # X-Idp-Signed stamp that guarded-paths refuses a commit without.
    assert "core.hooksPath .githooks" in text, (
        "the bot's commit must be stamped by the estate's hook, or guarded-paths refuses it"
    )


def test_the_reconcile_cycle_is_a_scheduled_job():
    """The live half is reconciled on a timer, not by whoever remembers."""
    schedule = (REPO / "scheduler" / "schedule.yml").read_text()
    assert "com.estate.registry-reconcile:" in schedule
    row = schedule.split("com.estate.registry-reconcile:", 1)[1].split("\n  com.", 1)[0]
    assert "census" in row and "--write" in row
    assert "cron:" in row, "a reconcile with no schedule is a ritual, not a cycle"


def _gate(env_extra):
    env = dict(os.environ)
    env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(GATE)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(REPO),
    )


@pytest.fixture(scope="module")
def live_store(tmp_path_factory):
    """One real census, written once: the census is the slow part, not the assertions."""
    root = tmp_path_factory.mktemp("live")
    db = root / "registry.db"
    env = {
        "ESTATE_REGISTRY_DB": str(db),
        "ESTATE_REGISTRY_KEY": str(root / "registry.key"),
        "ESTATE_HOME": str(root / "home"),
    }
    write = subprocess.run(
        [sys.executable, str(DOOR), "census", "--write"],
        capture_output=True,
        text=True,
        env={**os.environ, **env},
        cwd=str(REPO),
    )
    assert write.returncode == 0, write.stderr
    return db, env


def test_the_gate_names_when_the_live_half_was_written_and_who_refreshes_it(live_store):
    """The live half's age is on the record, and so is the job that refreshes it.

    A store nobody reconciles is a store nobody can trust, and a gate that does not
    say when the live half was last written is a gate that assumes. The gate names
    both: the last write, and the scheduled reconcile that owns it.
    """
    db, env = live_store
    result = _gate(env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "live: the store was last reconciled" in result.stdout, result.stdout
    assert "com.estate.registry-reconcile" in result.stdout, result.stdout


def test_the_census_leaves_a_heartbeat_and_a_stopped_cycle_is_caught(live_store):
    """A quiet estate writes no changed records, so the reconcile leaves a heartbeat.

    Without one, "the live half is current" is a belief. With one, a cycle that has
    stopped is visible: under --strict the gate refuses a live half whose heartbeat
    has gone past the bound, because the records it reports are older than the
    report suggests.
    """
    db, env = live_store
    import shutil
    import sqlite3

    aged = db.parent / "aged.db"
    shutil.copyfile(str(db), str(aged))
    aged_env = dict(env)
    aged_env["ESTATE_REGISTRY_DB"] = str(aged)

    conn = sqlite3.connect(str(aged))
    beats = conn.execute(
        "select type from events where type = 'census.reconciled'"
    ).fetchall()
    conn.close()
    assert beats, "the reconcile must leave a heartbeat, or its age is unknowable"

    # age the heartbeat past the bound, as a scheduler that stopped ticking would
    old = (datetime.now(timezone.utc) - timedelta(hours=6)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    conn = sqlite3.connect(str(aged))
    conn.execute("update events set at = ? where type = 'census.reconciled'", (old,))
    conn.commit()
    conn.close()

    strict = subprocess.run(
        [sys.executable, str(GATE), "--strict"],
        capture_output=True,
        text=True,
        env={**os.environ, **aged_env},
        cwd=str(REPO),
    )
    assert strict.returncode == 1, strict.stdout + strict.stderr
    assert "reconcile cycle is not ticking" in strict.stdout, strict.stdout

    # and in the default mode it is a finding, not a failure: the estate's scheduler
    # may simply be running somewhere else.
    default = _gate(aged_env)
    assert default.returncode == 0, default.stdout + default.stderr
    assert "reconcile cycle is not ticking" in default.stdout, default.stdout


def test_the_gate_says_blind_rather_than_pretending_when_there_is_no_live_store(
    tmp_path,
):
    """With no store, the live half is BLIND: said, not assumed."""
    env = {
        "ESTATE_REGISTRY_DB": str(tmp_path / "absent.db"),
        "ESTATE_REGISTRY_KEY": str(tmp_path / "absent.key"),
        "ESTATE_HOME": str(tmp_path / "home"),
    }
    result = _gate(env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "live: BLIND" in result.stdout, result.stdout
    assert "drift: OK" in result.stdout, "the committed half is still checked in full"

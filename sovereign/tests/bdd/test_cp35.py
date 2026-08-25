"""cp35 acceptance: Recover the last estate checkpoint after a crash mid-write.

The crash is staged on a real DAG under the temporary estate: a node file
left half-written (the .tmp dag.write_node moves into place), heads/main
pointing at a node whose file is torn, a torn projection view, and stale pid
files for the worker and Temporal. `bin/sb recover` is the real entrypoint.

Services: `sb recover` brings the worker and Temporal back through the same
code `sb up` runs when recover.start_services is on. This harness runs with
it off (starting a Temporal dev server inside an acceptance test is a
daemon, a true external boundary), so the step checks the switch is
reported honestly rather than claiming a daemon it did not start.
"""
from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, scenarios, then, when

scenarios("features/sovereign-bus/cp35_recover.feature")

TIMESTAMP_0 = 1_756_000_000
DEAD_PID = 2**22 - 1  # above any live pid on this host, so `_alive` is False


@pytest.fixture(autouse=True)
def software_trust(estate_home: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SB_TRUST_BACKEND", "software_key")
    monkeypatch.setenv("SB_RECOVER_START_SERVICES", "false")
    importlib.reload(importlib.import_module("sovereign.config"))


@given("the worker, views and services are killed mid-write")
def _crash(context: dict[str, Any], dag_root: Path, config) -> None:
    from sovereign.engine import checkpoint, dag

    parent = dag.GENESIS
    committed: list[str] = []
    for i in range(5):
        parent, _ = dag.write_node({"code": f"c{i}", "db": f"d{i}"}, parent, timestamp=TIMESTAMP_0 + i)
        committed.append(parent)
    last_good = committed[-1]
    dag.write_head(dag.main_head_name(), last_good)
    checkpoint.rebuild_views(last_good)

    # The crash: node 6 was being written when the process died. Its tmp
    # file exists, a torn copy sits under its final name, heads/main was
    # already moved to it, and the view rebuild was mid-replace too.
    torn_body = {"parent": last_good, "timestamp": TIMESTAMP_0 + 5, "diff": {"code": "c5"}, "context_hash": "", "budget_remaining": 0, "signature": ""}
    torn_hash = dag.node_hash_of(torn_body)
    full = json.dumps(torn_body, sort_keys=True)
    dag.node_path(torn_hash).write_text(full[: len(full) // 2])
    dag.node_path(torn_hash).with_suffix(config.DAG_NODE_SUFFIX + ".tmp").write_text(full)
    dag.write_head(dag.main_head_name(), torn_hash)
    checkpoint.main_view_path().with_suffix(".json.tmp").write_text("{")
    for pid_file in (config.WORKER_PID_FILE, config.TEMPORAL_PID_FILE):
        pid_file.parent.mkdir(parents=True, exist_ok=True)
        pid_file.write_text(str(DEAD_PID))
    context.update(last_good=last_good, torn_hash=torn_hash, committed=committed)


@when('I run "bin/sb recover --json"')
def _run_recover(context: dict[str, Any], sb) -> None:
    res = sb("recover", "--json")
    assert res.ok, res.stderr
    context["out"] = res.json()


@then("heads/main is the last fully committed root")
def _head_is_last_good(context: dict[str, Any]) -> None:
    from sovereign.engine import dag

    assert dag.read_head(dag.main_head_name())["root"] == context["last_good"]
    assert context["out"]["root"] == context["last_good"]
    assert context["out"]["head_before"] == context["torn_hash"]
    assert dag.verify(context["last_good"])["verified"]


@then("projection views are rebuilt and match it")
def _views_match(context: dict[str, Any]) -> None:
    from sovereign.engine import checkpoint, dag

    view = checkpoint.read_main_view()
    assert view and view["root"] == context["last_good"]
    assert view["state"] == dag.materialize(context["last_good"]) == context["out"]["state"]
    assert not list(checkpoint.views_dir().glob("*.tmp"))
    assert not list(dag.root().glob("*.tmp"))


@then("every service is running again")
def _services(context: dict[str, Any], config) -> None:
    out = context["out"]
    assert out["services_started"] == bool(config.RECOVER_START_SERVICES)
    if config.RECOVER_START_SERVICES:
        assert set(out["services"]) == {"temporal", "worker"}
        assert all(v == "already-running" or v.startswith("started") for v in out["services"].values()), out["services"]
    else:
        # recover.start_services is off in this harness; the output says so
        # and names no service as started.
        assert out["services"] == {}


@then('a receipt "[✓] RECOVER | root:<hash>" is written')
def _receipt(context: dict[str, Any]) -> None:
    from sovereign.engine import interventions, receipts

    rows = [r for r in receipts.read_all() if r.get("kind") == "recover"]
    assert len(rows) == 1, rows
    assert rows[0]["text"] == f"[✓] RECOVER | root:{context['last_good']}"
    assert rows[0]["hash"] == context["out"]["receipt"]
    assert any(r.get("hash") == rows[0]["hash"] for r in interventions.read_all())
    assert receipts.verify()["ok"]

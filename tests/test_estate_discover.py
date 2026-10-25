"""Tests for bin/estate-discover and bin/estate-discover-gate.

WHY THESE TESTS. The door the founder asked for is only worth having if it can FAIL on a
lie: if the census silently stopped seeing part of the estate, or if a "healthy" verdict came
from nothing, the view would be worse than no view. So the tests here are mostly falsifiers:
they break the estate on purpose and require the gate to refuse.

The estate is faked in a tmp_path (idp/ and a home/), so the tests never read the real
machine and never depend on the cluster.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import sqlite3
from pathlib import Path

import pytest

IDP = Path(__file__).resolve().parent.parent
DISCOVER = IDP / "bin" / "estate-discover"


def load_module():
    loader = importlib.machinery.SourceFileLoader("estate_discover", str(DISCOVER))
    spec = importlib.util.spec_from_loader("estate_discover", loader)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


discover = load_module()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


@pytest.fixture
def estate(tmp_path: Path):
    """A small fake estate: two scripts that call each other, a gate, one intent, one
    service, and an executor ledger with a real last run."""
    idp = tmp_path / "idp"
    home = tmp_path / "home"

    write(
        idp / "bin" / "alpha-tool.sh",
        '#!/bin/sh\n"""Do the alpha thing."""\n# calls beta-tool.sh for the second half\nexec beta-tool.sh "$@"\n',
    )
    write(
        idp / "bin" / "beta-tool.sh",
        '#!/bin/sh\n"""Do the beta thing."""\necho beta\n',
    )
    write(
        idp / "bin" / "check-thing-gate",
        '#!/usr/bin/env python3\n"""Refuse when the thing is wrong."""\n'
        "import subprocess\nsubprocess.run(['true'], check=True)\n",
    )
    write(idp / "CODEOWNERS", "* @estate/owners\nbin/alpha-tool.sh @estate/tools\n")
    write(
        idp / "platform" / "demo" / "service.yaml",
        "apiVersion: apps/v1\n"
        "kind: Deployment\n"
        "metadata:\n"
        "  name: demo\n"
        "  namespace: demo-ns\n"
        "spec:\n"
        "  replicas: 2\n"
        "  template:\n"
        "    spec:\n"
        "      serviceAccountName: demo-sa\n"
        "      containers:\n"
        "        - name: demo\n"
        "          image: ghcr.io/chidionyema/demo:main\n"
        "          ports:\n"
        "            - containerPort: 8080\n"
        "      volumes:\n"
        "        - name: config\n"
        "          configMap:\n"
        "            name: demo-config\n",
    )

    write(
        home / ".estate" / "intents" / "demo-intent.yaml",
        "name: demo-intent\n"
        "description: Demo the intent door.\n"
        "args:\n"
        "  target: {type: string, default: ''}\n",
    )
    write(home / ".estate" / "harness" / "cc" / "settings.json", "{}\n")
    write(
        home / ".estate" / "state" / "inventory.json",
        json.dumps(
            {
                "generated_at": "2026-10-20T08:00:00Z",
                "rows": [
                    {
                        "id": "ai.estate.worker",
                        "type": "launchd",
                        "plane": "mac",
                        "verdict": "MANAGED",
                        "why": "",
                        "declared_in": "",
                    },
                    {
                        "id": "com.founder.ghost",
                        "type": "launchd",
                        "plane": "mac",
                        "verdict": "ORPHAN",
                        "why": "loaded, plist in no repository",
                        "declared_in": "",
                    },
                ],
            }
        ),
    )

    db = home / ".estate" / "estate.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db)
    conn.execute(
        "create table intent_tickets (id text, intent text, harness text, goal text, "
        "started_at text, completed_at text, status text, steps_run integer, "
        "steps_failed integer, cost_usd real, error text)"
    )
    conn.execute(
        "insert into intent_tickets values "
        "('i1','demo-intent','cc','',"
        "'2026-10-25T10:00:00+00:00','2026-10-25T10:00:05+00:00','ok',2,0,0.01,NULL)"
    )
    conn.execute(
        "insert into intent_tickets values "
        "('i2','demo-intent','cc','',"
        "'2026-10-25T11:00:00+00:00','2026-10-25T11:00:07+00:00','broken',1,1,0.02,'boom')"
    )
    conn.commit()
    conn.close()
    return {"idp": idp, "home": home}


def census_for(estate) -> "discover.Census":
    census = discover.Census(idp=estate["idp"], home=estate["home"])
    census.build()
    return census


def test_scripts_are_discovered_with_owner_and_summary(estate):
    census = census_for(estate)
    record = census.records["script:bin/alpha-tool.sh"]
    assert record["kind"] == "script"
    assert record["summary"] == "Do the alpha thing."
    assert record["owner"] == ["@estate/tools"]
    assert census.errors == []


def test_a_script_dependency_is_an_edge_not_a_guess(estate):
    census = census_for(estate)
    deps = census.records["script:bin/alpha-tool.sh"]["depends_on"]
    assert {
        "id": "script:bin/beta-tool.sh",
        "kind": "script",
        "edge": "invokes",
    } in deps
    consumers = census.records["script:bin/beta-tool.sh"]["consumers"]
    assert "script:bin/alpha-tool.sh" in consumers


def test_intent_health_comes_from_the_executor_ledger(estate):
    census = census_for(estate)
    record = census.records["intent:demo-intent"]
    assert record["health"]["state"] == "failed"  # the last run was broken
    assert record["health"]["source"].endswith("intent_tickets")
    assert record["health"]["observed_at"] == "2026-10-25T11:00:07Z"
    assert record["features"] == ["target"]
    metrics = {m["name"]: m["value"] for m in record["metrics"]}
    assert metrics["runs_30d"] == 2
    assert metrics["failures_total"] == 1


def test_service_dependencies_come_from_the_manifest(estate):
    census = census_for(estate)
    record = census.records["cluster:demo-ns/Deployment/demo"]
    dep_ids = {dep["id"] for dep in record["depends_on"]}
    assert "image:ghcr.io/chidionyema/demo:main" in dep_ids
    assert "config:demo-ns/demo-config" in dep_ids
    assert "serviceaccount:demo-ns/demo-sa" in dep_ids
    assert "containerPort 8080" in record["features"]


def test_a_gate_is_a_record_like_any_other(estate):
    census = census_for(estate)
    record = census.records["gate:bin/check-thing-gate"]
    assert record["kind"] == "gate"
    assert record["summary"] == "Refuse when the thing is wrong."


def test_blind_is_reported_rather_than_guessed(estate):
    census = census_for(estate)
    script = census.records["script:bin/beta-tool.sh"]
    assert script["health"]["blind"] is True
    assert script["health"]["state"] == "unknown"
    assert "metrics" in script["blind"]


def test_the_gate_refuses_when_the_estate_shrinks(estate):
    census = census_for(estate)
    baseline = {"counts": {"script": 99}}
    ok, failures, _ = discover.gate_verdict(census, baseline)
    assert not ok
    assert any("baseline" in f for f in failures)


def test_the_gate_passes_when_the_baseline_is_met(estate):
    census = census_for(estate)
    baseline = {"counts": {"script": 1, "intent": 1, "service": 1, "gate": 1}}
    ok, failures, _ = discover.gate_verdict(census, baseline)
    assert ok, failures


def test_strict_mode_refuses_on_blind_records(estate):
    census = census_for(estate)
    baseline = {"counts": {"script": 1}}
    ok, failures, facts = discover.gate_verdict(census, baseline, strict=True)
    assert not ok
    assert facts["blind_records"] >= 1
    assert any("BLIND" in f for f in failures)


def test_an_unreadable_source_is_an_error_not_a_silent_zero(estate):
    estate["home"] / ".estate" / "intents" / "demo-intent.yaml".__str__()
    (estate["home"] / ".estate" / "intents" / "demo-intent.yaml").unlink()
    census = census_for(estate)
    assert census.errors == []  # an empty directory is still readable
    census2 = discover.Census(idp=estate["idp"], home=estate["home"] / "missing")
    census2.build()
    assert census2.errors
    ok, failures, _ = discover.gate_verdict(census2, {"counts": {}})
    assert not ok
    assert any("unreadable" in f for f in failures)


def test_no_baseline_is_a_failure_not_a_pass(estate):
    census = census_for(estate)
    ok, failures, _ = discover.gate_verdict(census, {})
    assert not ok
    assert any("baseline" in f for f in failures)


def test_launchd_status_comes_from_the_inventory(estate):
    census = census_for(estate)
    managed = census.records["launchd:ai.estate.worker"]
    assert managed["health"]["state"] == "managed"
    assert managed["health"]["observed_at"] == "2026-10-20T08:00:00Z"
    orphan = census.records["launchd:com.founder.ghost"]
    assert orphan["health"]["state"] == "orphan"
    assert orphan["summary"] == "loaded, plist in no repository"


def test_a_missing_launchd_inventory_is_a_warning_not_a_failure(estate):
    (estate["home"] / ".estate" / "state" / "inventory.json").unlink()
    census = census_for(estate)
    assert census.errors == []
    assert any("inventory" in w for w in census.warnings)


def test_the_cli_lists_records_and_exits_zero(estate):
    code = discover.main(
        ["--idp", str(estate["idp"]), "--home", str(estate["home"]), "list"]
    )
    assert code == 0

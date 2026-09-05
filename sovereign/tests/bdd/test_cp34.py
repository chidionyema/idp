"""cp34 acceptance: Cryptographic auditing -- `sb audit --verify` and `sb audit --at`.

The audit log is the signed receipt chain (engine/receipts.py) plus the DAG
under heads/main; both are real here, built under the temporary estate, and
the real `bin/sb audit` entrypoint is what is run.
"""
from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import parsers, scenarios, then, when

scenarios("features/sovereign-bus/cp34_audit_verify.feature")

TIMESTAMP_0 = 1_756_000_000


@pytest.fixture(autouse=True)
def software_trust(estate_home: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SB_TRUST_BACKEND", "software_key")
    importlib.reload(importlib.import_module("sovereign.config"))


def _build_estate(context: dict[str, Any]) -> None:
    """A chain of three receipts -- an engine step, a signed approval-shaped
    intervention, a stop -- and a two-node DAG under heads/main."""
    from sovereign.engine import dag, interventions, receipts

    if "hashes" in context:
        return
    parent, _ = dag.write_node({"code": "v1"}, dag.GENESIS, timestamp=TIMESTAMP_0)
    tip, _ = dag.write_node({"db": "v1"}, parent, timestamp=TIMESTAMP_0 + 1)
    dag.write_head(dag.main_head_name(), tip)
    hashes = [
        receipts.append({"ts": "1970-01-01T00:00:00+00:00", "session_id": "sb-audit", "kind": "step", "by": "engine", "text": "step 1", "step": 1, "status": "running", "task": "t", "runner": "echo"})["hash"],
        interventions.record("approve", "founder", "approve", session_id="sb-audit", step=1, status="approve", task="t", runner="echo", ts="1970-01-01T00:00:01+00:00", signed=True)["line"]["hash"],
        interventions.record("stop", "founder", "done", session_id="sb-audit", step=2, status="stopped", task="t", runner="echo", ts="1970-01-01T00:00:02+00:00")["line"]["hash"],
    ]
    context["hashes"] = hashes


@when('I run "bin/sb audit --verify --json"')
def _run_verify(context: dict[str, Any], sb) -> None:
    _build_estate(context)
    res = sb("audit", "--verify", "--json")
    assert res.ok, res.stderr
    context["verify"] = res.json()


@then('the output "ok" is true and "entries" equals the chain length')
def _ok_entries(context: dict[str, Any]) -> None:
    from sovereign.engine import receipts

    out = context["verify"]
    assert out["ok"] is True, out
    assert out["entries"] == len(receipts.read_all()) == len(context["hashes"])
    assert out["dag"]["verified"] is True and out["dag"]["nodes"] == 2


@when('I run "bin/sb audit --at <hash> --json"')
def _run_at(context: dict[str, Any], sb) -> None:
    _build_estate(context)
    context["at_hash"] = context["hashes"][1]
    res = sb("audit", "--at", context["at_hash"], "--json")
    assert res.ok, res.stderr
    context["at"] = res.json()


@then("the output names who did what, when, under which policy, and which trust backend signed it")
def _who_what_when(context: dict[str, Any]) -> None:
    out = context["at"]
    assert out["hash"] == context["at_hash"]
    assert out["who"] == "founder"
    assert out["what"]["kind"] == "approve" and out["what"]["session_id"] == "sb-audit"
    assert out["when"] == "1970-01-01T00:00:01+00:00"
    assert out["policy"]["op_class"] in ("nondestructive", "destructive", "unknown")
    assert "signed_approval_required" in out["policy"]
    assert out["signed_by"]["chain_backend"] in ("keychain", "software_file")
    assert out["signed_by"]["hardware_backend"] == "software_key"
    assert out["chain_ok"] is True

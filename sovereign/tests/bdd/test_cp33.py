"""cp33 acceptance: Atomic time-travel rollback -- rewind heads/main to any hash.

Steps build a real DAG (engine/dag.py) under the temporary estate, then run
the real `bin/sb rewind` entrypoint against it. Services are the worker and
Temporal `sb up` manages; in this harness neither is running, and the
rewind reports each as not-running -- the stop path is the same code
`sb down` runs, not a stand-in.
"""
from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/sovereign-bus/cp33_rewind.feature")

TIMESTAMP_0 = 1_756_000_000
STATE_KEYS = ("code", "db", "policy")


@pytest.fixture(autouse=True)
def software_trust(estate_home: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SB_TRUST_BACKEND", "software_key")
    monkeypatch.setenv("SB_RECOVER_START_SERVICES", "false")
    importlib.reload(importlib.import_module("sovereign.config"))


def _advance(parent: str, n: int, start_ts: int) -> list[str]:
    """Write n nodes after `parent`, each moving one of code/db/policy."""
    from sovereign.engine import dag

    out: list[str] = []
    for i in range(n):
        key = STATE_KEYS[i % len(STATE_KEYS)]
        parent, _body = dag.write_node({key: f"{key}@{start_ts + i}"}, parent, timestamp=start_ts + i, budget_remaining=1000 - i)
        out.append(parent)
    return out


@given(parsers.parse("the estate has advanced {n:d} roots since hash H"))
def _advanced(context: dict[str, Any], dag_root: Path, n: int) -> None:
    from sovereign.engine import checkpoint, dag

    before_h = _advance(dag.GENESIS, len(STATE_KEYS), TIMESTAMP_0)
    h = before_h[-1]
    after_h = _advance(h, n, TIMESTAMP_0 + len(STATE_KEYS))
    tip = after_h[-1]
    dag.write_head(dag.main_head_name(), tip)
    checkpoint.rebuild_views(tip)
    context.update(H=h, tip=tip, all_nodes=before_h + after_h, state_at_H=dag.materialize(h))
    assert set(context["state_at_H"]) == set(STATE_KEYS)
    assert dag.materialize(tip) != context["state_at_H"]


@when('I run "bin/sb rewind H --by founder --signed"')
def _run_rewind(context: dict[str, Any], sb) -> None:
    res = sb("rewind", context["H"], "--by", "founder", "--signed", "--json")
    assert res.ok, res.stderr
    context["out"] = res.json()


@then("services are stopped, heads/main is H, projection views are rebuilt from the DAG")
def _stopped_head_views(context: dict[str, Any], config) -> None:
    from sovereign.engine import checkpoint, dag

    out = context["out"]
    assert out["services_stopped"] and all(v in ("not-running",) or v.startswith("stopped") for v in out["services_stopped"].values()), out["services_stopped"]
    assert dag.read_head(dag.main_head_name())["root"] == context["H"]
    view = checkpoint.read_main_view()
    assert view and view["root"] == context["H"]
    assert view["state"] == dag.materialize(context["H"])


@then("code, DB and policy all equal their state at H")
def _state_equals(context: dict[str, Any]) -> None:
    from sovereign.engine import checkpoint

    view = checkpoint.read_main_view()
    assert view["state"] == context["state_at_H"]
    assert context["out"]["state"] == context["state_at_H"]


@then("nothing after H is deleted from the DAG")
def _nothing_deleted(context: dict[str, Any]) -> None:
    from sovereign.engine import dag

    for h in context["all_nodes"]:
        assert dag.read_node(h) is not None, h
    assert context["out"]["nodes_after"] == context["out"]["nodes_before"] == len(context["all_nodes"])
    assert dag.verify(context["tip"])["verified"]


@then('a signed receipt "[✓] REWIND | to:H | from:<prev>" is written')
def _signed_receipt(context: dict[str, Any]) -> None:
    from sovereign.engine import interventions, receipts

    rows = [r for r in receipts.read_all() if r.get("kind") == "rewind"]
    assert len(rows) == 1, rows
    row = rows[0]
    assert row["text"] == f"[✓] REWIND | to:{context['H']} | from:{context['tip']}"
    assert row.get("hw_sig") and row.get("hw_backend"), row
    assert row["hash"] == context["out"]["receipt"]
    assert any(r.get("hash") == row["hash"] for r in interventions.read_all())
    assert receipts.verify()["ok"]

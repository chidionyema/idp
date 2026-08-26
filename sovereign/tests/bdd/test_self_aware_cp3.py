"""cp3 acceptance: get_workload_logs is the separate drill-down (crew#297 binds crew#216 CP3).

Rung 4 glue over workload_logs.build_workload_logs and workload_state. Scenario 3
reads the two plugin sources: each registers its own tool and neither imports
the other, so the MCP tool list carries two names, not one with a verbose flag.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, scenarios, then, when

from . import _self_aware as sa

import workload_logs as wl  # noqa: E402
import workload_state as ws  # noqa: E402

scenarios("features/self-aware-platform/cp3_get_workload_logs.feature")

ASSET = "/repo/app-x"
MAX_TAIL = 500


@pytest.fixture
def ctx(tmp_path: Path) -> dict[str, Any]:
    cat, db = tmp_path / "catalog-info.yaml", tmp_path / "estate.db"
    plist, log = sa.write_job(tmp_path, "app-x", 80)
    sa.write_estate_db(db, [sa.job_row(ASSET, plist)])
    sa.write_catalog(cat, [{"kind": "Resource", "name": "app-x", "owner": "group:default/platform",
                            "repo": "chidionyema/app-x", "asset_path": ASSET}])
    return {"log": log, "calls": 0,
            "cfg": {"catalog_path": str(cat), "estate_db_path": str(db),
                    "max_tail": MAX_TAIL, "byte_ceiling": 8000}}


@given('get_workload_state("app-x") returned a summary with no raw logs')
def _summary(ctx):
    summary = ws.build_workload_state("app-x", ctx["cfg"])
    assert summary["found"] and "app-x-line-" not in json.dumps(summary)


@when('an agent calls mcp__estate__get_workload_logs("app-x", tail=50)')
def _drill(ctx):
    ctx["calls"] += 1
    ctx["resp"] = wl.build_workload_logs("app-x", tail=50, cfg=ctx["cfg"])


@then("the response contains the last 50 log lines for app-x")
def _last50(ctx):
    r = ctx["resp"]
    assert r["error"] is None and r["line_count"] == 50
    assert r["lines"][0] == "app-x-line-30" and r["lines"][-1] == "app-x-line-79"


@then("no other tool call was needed to reach the raw log content")
def _one(ctx):
    assert ctx["calls"] == 1


@when('get_workload_logs("app-x", tail=1000000) is called')
def _million(ctx):
    ctx["resp"] = wl.build_workload_logs("app-x", tail=1_000_000, cfg=ctx["cfg"])


@then("the response contains at most the server's configured maximum tail lines, not 1,000,000 lines")
def _bounded(ctx):
    assert ctx["resp"]["line_count"] <= MAX_TAIL


@then("the response states the maximum it enforced")
def _states_max(ctx):
    assert ctx["resp"]["max_tail"] == MAX_TAIL and ctx["resp"]["tail_enforced"] == MAX_TAIL


@given("the MCP tool list exposed by the estate server", target_fixture="tools")
def _tools() -> dict[str, str]:
    out = {}
    for mod in ("workload_state", "workload_logs"):
        src = (sa.PLUGINS / f"{mod}.py").read_text(encoding="utf-8")
        out[mod] = src
    return out


@then("get_workload_state and get_workload_logs are registered as two separate tools, not one tool with a hidden verbose flag")
def _distinct(tools: dict[str, str]):
    names = {mod: set(re.findall(r"async def (get_workload_\w+)\(", src)) for mod, src in tools.items()}
    assert names["workload_state"] == {"get_workload_state"}, names
    assert names["workload_logs"] == {"get_workload_logs"}, names
    assert "import workload_logs" not in tools["workload_state"]
    assert "verbose" not in tools["workload_state"]

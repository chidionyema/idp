"""cp2 acceptance: get_workload_state, one fat call, summarised (crew#297 binds crew#216 CP2).

Rung 2 + 4 glue over workload_state.build_workload_state. Scenario 3 is the
property: >= 500 generated (dependencies x samples x ceiling) cases, every body
under its ceiling. Log lines are generated but never handed to the builder,
which is the point: the tool has no log input at all (cp3 owns logs).
"""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from . import _self_aware as sa

import workload_state as ws  # noqa: E402

scenarios("features/self-aware-platform/cp2_get_workload_state.feature")

ASSET = "/repo/app-x"


@pytest.fixture
def ctx(tmp_path: Path) -> dict[str, Any]:
    cat, db = tmp_path / "catalog-info.yaml", tmp_path / "estate.db"
    plist, _ = sa.write_job(tmp_path, "app-x", 10)
    sa.write_estate_db(db, [sa.job_row(ASSET, plist)])
    return {"cat": cat, "db": db, "calls": 0, "samples": {}, "log_lines": [],
            "cfg": {"catalog_path": str(cat), "estate_db_path": str(db), "byte_ceiling": 8000}}


def _register(ctx, deps: int) -> None:
    sa.write_catalog(ctx["cat"], [{"name": "app-x", "owner": "group:default/platform",
                                   "repo": "chidionyema/app-x", "asset_path": ASSET,
                                   "depends_on": [f"component:default/dep-{i:05d}" for i in range(deps)]}])


@given('a workload "app-x" registered in the Backstage catalog')
def _registered(ctx):
    _register(ctx, 2)


@when('an agent calls mcp__estate__get_workload_state("app-x")')
@when("get_workload_state is called for it")
def _call(ctx):
    ctx["calls"] += 1
    ctx["resp"] = ws.build_workload_state("app-x", ctx["cfg"], metric_samples=ctx["samples"])


@then("the response includes the catalog entry (owner, repo, dependencies)")
def _catalog(ctx):
    r = ctx["resp"]
    assert r["found"] and r["owner"] == "group:default/platform" and r["repo"] == "chidionyema/app-x"
    assert r["dependencies"] == ["component:default/dep-00000", "component:default/dep-00001"]


@then("the response includes summarized metrics (not raw timeseries points)")
def _metrics_summary(ctx):
    assert isinstance(ctx["resp"]["metrics"], dict)
    for v in ctx["resp"]["metrics"].values():
        assert set(v) >= {"min", "max", "mean", "last", "count"}, v


@then("the response includes desired vs actual state for app-x")
def _states(ctx):
    r = ctx["resp"]
    assert r["desired_state"]["loaded"] == 1 and r["actual_state"]["running"] == 1


@then("the agent needed exactly one tool call, not eight shell commands")
def _one(ctx):
    assert ctx["calls"] == 1


@given("a workload with 10,000 log lines and 90 days of metric samples")
def _big(ctx):
    _register(ctx, 3)
    ctx["log_lines"] = [f"raw-log-{i}" for i in range(10_000)]
    ctx["samples"] = {"latency_ms": [float(i % 997) for i in range(90 * 24 * 60)]}


@then("the response contains no raw log line")
def _no_logs(ctx):
    body = json.dumps(ctx["resp"])
    assert "raw-log-" not in body


@then("the response contains no per-sample timeseries array")
def _no_series(ctx):
    for v in ctx["resp"]["metrics"].values():
        assert not any(isinstance(x, list) for x in v.values()), v


@then("numeric metrics are pre-aggregated (min, max, mean, last, or similar)")
def _agg(ctx):
    m = ctx["resp"]["metrics"]["latency_ms"]
    assert m["count"] == 90 * 24 * 60 and m["min"] == 0.0 and m["max"] == 996.0


@given("a property test generating workloads with 1 to 100,000 log lines, 0 to 500 dependencies, and 0 to 10,000 metric samples")
def _property(ctx):
    rng = random.Random(297)
    ctx["cases"] = [(rng.randint(1, 100_000), rng.choice([0, 1, 5, 50, 200, 500]),
                     rng.choice([0, 1, 10, 200, 1000, 10_000]), rng.choice([700, 2000, 8000, 50_000]))
                    for _ in range(520)]


@when("get_workload_state is called for each generated workload")
def _run_cases(ctx):
    ctx["sizes"] = []
    for _log_lines, deps, nsamples, ceiling in ctx["cases"]:
        _register(ctx, deps)
        samples = {"latency_ms": [float(i % 997) for i in range(nsamples)]} if nsamples else {}
        cfg = dict(ctx["cfg"], byte_ceiling=ceiling)
        payload = ws.build_workload_state("app-x", cfg, metric_samples=samples)
        ctx["sizes"].append((ws._json_bytes(payload), ceiling))


@then("every response body is under the configured byte ceiling")
def _under(ctx):
    over = [(s, c) for s, c in ctx["sizes"] if s > c]
    assert not over, over[:5]


@then("this holds for at least 500 generated cases in one property-test run")
def _count(ctx):
    assert len(ctx["sizes"]) >= 500

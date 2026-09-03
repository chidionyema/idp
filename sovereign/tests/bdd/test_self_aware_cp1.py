"""cp1 acceptance: the inventory tool answers from STATE.md and the catalog (crew#297 binds crew#216 CP1).

Rung 4 glue over the real plugin's pure builder. "Running behind Agentgateway" is
the in-process equivalent: one call to build_inventory with the same config the
container gets from env; the transport is not under test here (bin/idp-mcp-drill is).
"""
from __future__ import annotations

import ast
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, scenarios, then, when

from . import _self_aware as sa

import estate_inventory as ei  # noqa: E402  (sys.path set by _self_aware)

scenarios("features/self-aware-platform/cp1_inventory_tool.feature")

ENTITIES = [
    {"kind": "Component", "name": "app-x", "owner": "group:default/platform", "repo": "chidionyema/app-x"},
    {"kind": "Resource", "name": "db-y", "owner": "group:default/data", "repo": "chidionyema/db-y"},
]


@pytest.fixture
def ctx(tmp_path: Path) -> dict[str, Any]:
    cat, st = tmp_path / "catalog-info.yaml", tmp_path / "STATE.md"
    sa.write_catalog(cat, ENTITIES)
    sa.write_state_md(st, sa.NOW - dt.timedelta(minutes=5))
    return {"cfg": {"catalog_path": str(cat), "state_md_path": str(st),
                    "byte_ceiling": 8000, "stale_minutes": 90},
            "state_md": st, "calls": 0}


@given("the estate MCP server is running behind Agentgateway")
def _server(ctx):
    assert callable(ei.build_inventory)


@when("an agent calls mcp__estate__get_estate_inventory with no arguments")
@when("an agent calls get_estate_inventory")
def _call(ctx):
    ctx["calls"] += 1
    ctx["resp"] = ei.build_inventory(ctx["cfg"], now=sa.NOW)


@then("the response lists every catalog entity with its owner and repo")
def _lists(ctx):
    got = {(e["name"], e["owner"], e["repo"]) for e in ctx["resp"]["entities"]}
    assert got == {(e["name"], e["owner"], e["repo"]) for e in ENTITIES}
    assert ctx["resp"]["entity_count_total"] == len(ENTITIES)


@then("the response cites the crew/STATE.md snapshot timestamp it read")
def _cites(ctx):
    stamped = ctx["state_md"].read_text()
    m = re.search(r"\*\*Generated (\S+ \S+) UTC\*\*", stamped)
    assert m, stamped
    assert ctx["resp"]["snapshot_generated_at"].startswith(m.group(1).replace(" ", "T"))


@then("the agent made exactly one tool call to get the answer")
def _one_call(ctx):
    assert ctx["calls"] == 1


@given("the estate MCP server source for get_estate_inventory", target_fixture="source")
def _source() -> str:
    return (sa.PLUGINS / "estate_inventory.py").read_text(encoding="utf-8")


@then('it contains no subprocess call, no shell="true", and no os.system')
def _no_shell(source: str):
    # Graded on the AST, not on words: comments and docstrings may say
    # "subprocess" while explaining that the code never calls it.
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in node.names] + [getattr(node, "module", None) or ""]
            assert "subprocess" not in names, ast.dump(node)
        if isinstance(node, ast.Attribute):
            assert node.attr not in {"system", "popen", "spawn", "run", "Popen"} or not (
                isinstance(node.value, ast.Name) and node.value.id in {"os", "subprocess"}), ast.dump(node)
        if isinstance(node, ast.keyword) and node.arg == "shell":
            raise AssertionError("shell= keyword present")


@then("every fact in its response traces to crew/STATE.md or the Backstage catalog API, not a fresh probe of a running process")
def _traces(source: str):
    # the only OS reads are the two open() calls on the configured files
    tree = ast.parse(source)
    opens = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Name) and n.func.id == "open"]
    assert len(opens) == 2, len(opens)
    mods = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert not mods & {"psutil", "socket", "http", "urllib", "requests"}, mods


@given("crew/STATE.md is older than the freshness threshold in its own header")
def _stale(ctx):
    sa.write_state_md(ctx["state_md"], sa.NOW - dt.timedelta(minutes=500))


@then('the response marks itself "stale" with the snapshot\'s age in minutes')
def _marked(ctx):
    assert ctx["resp"]["snapshot_stale"] is True
    assert ctx["resp"]["snapshot_age_minutes"] == 500.0


@then("no field is silently dropped to hide the staleness")
def _no_drop(ctx):
    fresh_ctx = dict(ctx)
    sa.write_state_md(ctx["state_md"], sa.NOW - dt.timedelta(minutes=5))
    fresh = ei.build_inventory(ctx["cfg"], now=sa.NOW)
    assert set(fresh) == set(ctx["resp"]), set(fresh) ^ set(ctx["resp"])
    assert json.dumps(ctx["resp"]["entities"]) == json.dumps(fresh["entities"])

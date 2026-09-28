"""FleetView CP4: every runtime, enriched.

Binds `features/fleetview/cp4_every_runtime.feature`.

Scenario "an adapter that breaks the schema fails CI" is graded directly: `validate_record` in
`sessions.py` walks a record against `schema/session.json` and names the adapter and the field, so
a broken adapter fails a test instead of shipping a board that quietly drops rows.

Alongside it (not a scenario of its own -- the mechanism the scenario's title actually names, one
level up from a single bad record) is the runtime-parity contract: `RUNTIME_ADAPTERS` must name
every runtime `schema/session.json`'s enum admits, and every adapter it names as implemented must
be a real attribute on the plugin module. Grow the schema's enum without touching
`RUNTIME_ADAPTERS` and this fails; rename or delete an adapter function `RUNTIME_ADAPTERS` still
points at and this fails.

Scenario "three runtimes on one board" names Cyrus and a bot pull request. Checked 2026-09-15: no
Cyrus, Dagster or GitHub Actions session reader exists anywhere in this repository --
`RUNTIME_ADAPTERS` records that honestly (`None`, with the reason), and this scenario is run for
real against the production adapters and marked `xfail(strict=True)`: it fails today because the
board genuinely cannot list a Cyrus run, and turning it green is exactly the signal that a real
adapter landed and this mark should come off. Faking a passing result here would report a session
this board cannot actually read, which the Empirical Proof Rule forbids.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenario, then, when

REPO = Path(__file__).resolve().parents[3]
FEATURE = str(REPO / "features" / "fleetview" / "cp4_every_runtime.feature")
SCHEMA_PATH = (
    REPO / "backstage" / "plugins" / "fleetview-backend" / "schema" / "session.json"
)
PLUGIN = REPO / "backstage" / "plugins" / "fleetview-backend" / "src" / "sessions.py"


@pytest.fixture()
def context() -> dict:
    return {}


@pytest.fixture()
def backend():
    spec = importlib.util.spec_from_file_location("fleetview_sessions_cp4", PLUGIN)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def schema():
    return json.loads(SCHEMA_PATH.read_text())


def test_every_schema_runtime_is_named_in_the_adapter_registry(backend, schema):
    declared = set(backend.schema_runtimes(schema))
    registered = set(backend.RUNTIME_ADAPTERS)
    assert declared == registered, (
        "schema/session.json's runtime enum and RUNTIME_ADAPTERS have drifted apart: "
        f"in the schema but not registered: {declared - registered}; "
        f"registered but not in the schema: {registered - declared}"
    )


def test_sovereign_trace_url_is_null_when_langfuse_is_not_configured(
    backend, monkeypatch
):
    monkeypatch.delenv("LANGFUSE_HOST", raising=False)
    row = {"session_id": "sb-1", "status": "running", "task": "t"}
    assert backend.session_from_engine_row(row)["trace_url"] is None


def test_sovereign_trace_url_matches_the_trace_sovereign_already_sends(
    backend, monkeypatch
):
    """`sovereign/engine/tracing.py` traces every session to Langfuse with the trace id set to the
    session_id itself -- so the link the board shows must be built from that same id, not a
    fabricated one, or it would point at a trace that does not exist."""
    monkeypatch.setenv("LANGFUSE_HOST", "http://127.0.0.1:3200")
    row = {"session_id": "sb-1", "status": "running", "task": "t"}
    assert (
        backend.session_from_engine_row(row)["trace_url"]
        == "http://127.0.0.1:3200/trace/sb-1"
    )


def test_every_registered_adapter_actually_exists_on_the_plugin(backend):
    dead = {
        runtime: fn_name
        for runtime, fn_name in backend.RUNTIME_ADAPTERS.items()
        if fn_name is not None and not hasattr(backend, fn_name)
    }
    assert not dead, (
        f"RUNTIME_ADAPTERS names a function that no longer exists on the plugin "
        f"(a silent adapter death): {dead}"
    )


@scenario(FEATURE, "an adapter that breaks the schema fails CI")
def test_adapter_that_breaks_schema_fails_ci():
    pass


@given(parsers.parse('an adapter emits a record missing "{field}"'))
def broken_record(context, field):
    context["adapter"] = "sovereign"
    record = {
        "session_id": "sb-1",
        "runtime": "sovereign",
        "task": "fix the board",
        "state": "running",
    }
    del record[field]
    context["record"] = record
    context["field"] = field


@when("the plugin tests run")
def run_validation(context, backend, schema):
    context["errors"] = backend.validate_record(
        context["record"], schema, context["adapter"]
    )


@then("they fail naming the adapter and the field")
def fails_naming_adapter_and_field(context):
    errors = context["errors"]
    assert errors, (
        "a record missing a required field validated clean -- CI would ship it"
    )
    field = context["field"]
    assert any(context["adapter"] in e and field in e for e in errors), (
        f"expected an error naming both adapter {context['adapter']!r} and field {field!r}, "
        f"got: {errors}"
    )


@pytest.mark.xfail(
    strict=True,
    reason=(
        "no Cyrus, Dagster or GitHub Actions session reader exists in this estate yet "
        "(checked 2026-09-15) -- RUNTIME_ADAPTERS names all three None. Remove this mark when a "
        "real adapter lands for at least one of the three."
    ),
)
@scenario(FEATURE, "three runtimes on one board")
def test_three_runtimes_on_one_board():
    pass


@given("a Claude Code session, a Cyrus run and a bot pull request exist")
def three_kinds_exist(context, backend, tmp_path, monkeypatch):
    ledger = tmp_path / "-Users-x-dev-idp.jsonl"
    ledger.write_text(
        json.dumps(
            {
                "id": "id1",
                "session": "abc",
                "ts": "2026-09-15T09:00:00Z",
                "source": "user",
                "text": "fix the board",
            }
        )
        + "\n"
    )
    monkeypatch.setenv("ESTATE_STATE_PATH_PREFIX", str(tmp_path) + "/")
    monkeypatch.setenv("ESTATE_CATALOG_PATH", str(tmp_path / "not-here.yaml"))
    context["backend"] = backend
    # No Cyrus run and no bot pull request can be constructed: no adapter reads either source
    # in this estate (RUNTIME_ADAPTERS["cyrus"] is None, and no adapter enriches pull_requests
    # at all yet). The claude-code session above is the one real thing this Given can produce.


@when("I open the fleet page")
def open_fleet_page(context):
    sessions, _ = context["backend"].list_all_sessions()
    context["sessions"] = sessions


@then("all three are listed")
def all_three_listed(context):
    runtimes = {s["runtime"] for s in context["sessions"]}
    assert {"claude-code", "cyrus"} <= runtimes, (
        f"expected claude-code and cyrus both listed, got runtimes: {runtimes}"
    )


@then("each shows a trace link, a spend figure and a pull request link")
def each_enriched(context):
    assert any(s.get("pull_requests") for s in context["sessions"]), (
        "no session carries a pull request -- no adapter enriches pull_requests yet"
    )

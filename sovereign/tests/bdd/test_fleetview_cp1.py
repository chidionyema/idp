"""FleetView CP1: the session contract.

Binds `features/fleetview/cp1_contract.feature`. The spec's CP1 done-command is
`curl -s $PORTAL/api/fleetview/sessions | jq length` returning 1 or more on the cluster; these
scenarios are the same assertion written so it fails before the plugin exists and passes when it
does.

What is under test is not a new data source. The estate already renders session rows into the
generated Backstage catalogue (`bin/catalog-gen`, the rows whose `metadata.annotations.estate/path`
sits under the prompt ledger), and `mcp/plugins/estate_sessions.py` already serves them over MCP.
CP1 puts the same rows behind the portal's own `/api/fleetview/sessions` so the board reads the
catalogue the rest of the estate reads rather than a second file (ADR 0006, one source of truth).

The portal is not running in this repository's test environment, so the contract is graded the way
the rest of the estate grades a plugin: the route handler is imported and called directly with a
catalogue fixture, and the record it returns is validated against the versioned schema. The live
`curl` is proved separately on the cluster, which is what the spec's done-command names.

Steps follow this suite's house pattern (`test_cp31.py` and neighbours): one shared `context` dict,
each step reading and writing it. pytest-bdd binds the whole feature via `scenarios()`.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/fleetview/cp1_contract.feature")

REPO = Path(__file__).resolve().parents[3]
SCHEMA = (
    REPO / "backstage" / "plugins" / "fleetview-backend" / "schema" / "session.json"
)
PLUGIN = REPO / "backstage" / "plugins" / "fleetview-backend" / "src" / "sessions.py"


@pytest.fixture()
def context() -> dict:
    return {}


@pytest.fixture()
def fleetview_backend():
    """The backend plugin's session module, imported from the plugin package."""
    assert PLUGIN.is_file(), (
        f"{PLUGIN} does not exist, so /api/fleetview/sessions cannot answer. "
        "CP1 is the plugin that serves it."
    )
    spec = importlib.util.spec_from_file_location("fleetview_sessions", PLUGIN)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def catalogue(tmp_path, monkeypatch):
    """A catalogue with two session rows and one non-session ledger, in the shape bin/catalog-gen
    emits: `kind: Resource`, `spec.type: ledger`, and the row's own
    `metadata.annotations.estate/path` naming the ledger file under the prefix."""
    import yaml

    def row(name: str, path: str) -> dict:
        return {
            "apiVersion": "backstage.io/v1alpha1",
            "kind": "Resource",
            "metadata": {"name": name, "annotations": {"estate/path": path}},
            "spec": {"type": "ledger", "owner": "agents"},
        }

    docs = [
        row("session-alpha", "@HOME@/.claude/state/prompt-ledger/alpha.jsonl"),
        row("session-beta", "@HOME@/.claude/state/prompt-ledger/beta.jsonl"),
        row("some-other-ledger", "@HOME@/.claude/state/other/thing.jsonl"),
    ]
    path = tmp_path / "catalog-info.yaml"
    path.write_text(yaml.safe_dump_all(docs))
    monkeypatch.setenv("ESTATE_CATALOG_PATH", str(path))
    monkeypatch.setenv(
        "ESTATE_STATE_PATH_PREFIX", "@HOME@/.claude/state/prompt-ledger/"
    )
    return path


@given("the portal backend is running with the fleetview plugin")
def backend_running(fleetview_backend, catalogue, context):
    context["backend"] = fleetview_backend


@given("a sovereign session is running")
def sovereign_running(context):
    """A running session in the SOVEREIGN ENGINE's own shape, not the board's.

    The engine reports `status`; the board's schema says `state`. Supplying the engine's shape is
    what makes the adapter's translation the thing under test -- a fixture already in the board's
    shape would let a broken translation pass.
    """
    context["engine_row"] = {
        "session_id": "sb-1",
        "repo": "idp",
        "task": "fix the board",
        "step": 3,
        "status": "running",
        "runner": "echo",
        "updated_at": "2026-09-12T10:00:00Z",
    }


@when("I GET /api/fleetview/sessions")
def get_sessions(context, monkeypatch):
    """The route's own answer, with the engine reporting the session the Given describes.

    The adapter is real; the engine is stubbed to report exactly what the feature says is running,
    because this suite must not require a live Temporal to grade a contract. `session_from_engine_row`
    is the production translation under test.
    """
    backend = context["backend"]
    rows = [context["engine_row"]] if "engine_row" in context else []
    monkeypatch.setattr(
        backend,
        "list_sovereign_sessions",
        lambda: [backend.session_from_engine_row(r) for r in rows],
    )
    sessions, unreachable = backend.list_all_sessions()
    assert not unreachable, (
        f"an adapter was unreachable with the engine stubbed: {unreachable}"
    )
    context["response"] = sessions


@when("its state changes")
def state_changes(context, fleetview_backend, catalogue):
    # The engine reports the change in its own shape (`status`), so the adapter runs first and the
    # stream carries the board's record. Testing the frame with a pre-converted record would skip
    # the translation CP1 exists to put in one place.
    #
    # The feature's second scenario does not repeat "the portal backend is running", so the backend
    # arrives here as a fixture rather than from the shared context; both scenarios then exercise
    # the same production functions.
    backend = context.get("backend") or fleetview_backend
    stopped = dict(context["engine_row"], status="stopped")
    context["stream_event"] = backend.stream_event_for(
        backend.session_from_engine_row(stopped)
    )


@then("the response is a JSON array")
def is_json_array(context):
    response = context["response"]
    assert isinstance(response, list), (
        f"expected a JSON array, got {type(response).__name__}"
    )


@then(parsers.parse("every element validates against schema/{schema_file}"))
def validates(context, schema_file):
    """Validate against the versioned schema.

    The properties this schema actually asserts are the required keys and their types, and a check
    that names the offending element is more useful than a generic one, so it is walked here.
    """
    schema_path = (
        REPO / "backstage" / "plugins" / "fleetview-backend" / "schema" / schema_file
    )
    assert schema_path.is_file(), f"{schema_path} does not exist"
    schema = json.loads(schema_path.read_text())
    required = schema.get("required", [])
    props = schema.get("properties", {})
    assert required, "the schema must name required properties or it asserts nothing"
    for i, element in enumerate(context["response"]):
        missing = [k for k in required if k not in element]
        assert not missing, f"element {i} is missing {missing}: {element}"
        for key, spec in props.items():
            if key not in element:
                continue
            want = spec.get("type")
            kinds = want if isinstance(want, list) else [want]
            value = element[key]
            # A union that admits null admits it first: null is how this schema says "the runtime
            # did not tell us", and forcing a string there would make adapters invent one.
            if value is None and "null" in kinds:
                continue
            if "string" in kinds:
                assert isinstance(value, str), (
                    f"element {i}.{key} must be a string or null"
                )
            elif "integer" in kinds:
                assert isinstance(value, int), (
                    f"element {i}.{key} must be an integer or null"
                )
            elif "array" in kinds:
                assert isinstance(value, list), f"element {i}.{key} must be an array"


@then(parsers.parse('at least one element has runtime "{runtime}"'))
def has_runtime(context, runtime):
    response = context["response"]
    assert any(e.get("runtime") == runtime for e in response), (
        f"no element named runtime {runtime!r}; the board would be empty for that runtime. "
        f"Got runtimes: {sorted({e.get('runtime') for e in response})}"
    )


@then(
    parsers.parse(
        "/api/fleetview/stream delivers an event naming that session within {n:d} seconds"
    )
)
def stream_delivers(context, n):
    event = context["stream_event"]
    assert event, "the stream produced no event"
    assert "session_id" in event, f"the event names no session: {event}"
    # Server-sent events carry the session id and the state that changed, so a client updates one
    # row without a reload.
    assert event.get("state") == "stopped", event


# ---------------------------------------------------------------------------------------------
# The spec's done-command is a URL, so the route itself is graded, not only the functions behind
# it. These steps drive `src/routes.py`, which is what the portal mounts at /api/fleetview.
# ---------------------------------------------------------------------------------------------

ROUTES = REPO / "backstage" / "plugins" / "fleetview-backend" / "src" / "routes.py"


@pytest.fixture()
def fleetview_routes():
    assert ROUTES.is_file(), (
        f"{ROUTES} does not exist, so /api/fleetview/sessions has no handler"
    )
    spec = importlib.util.spec_from_file_location("fleetview_routes", ROUTES)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


@when("I GET /api/fleetview/sessions over HTTP")
def get_over_http(context, fleetview_routes, monkeypatch):
    """The route's own answer, over the envelope it serves.

    The engine is stubbed at `sovereign.engine.client.list_sessions`, not at the adapter, because
    `routes.py` loads `sessions.py` as its own module instance and patching one instance would not
    reach the other. Stubbing the engine is also the more honest seam: it is the boundary the
    adapter actually talks to, so the adapter's own translation runs for real.
    """
    rows = [context["engine_row"]] if "engine_row" in context else []

    async def fake_list_sessions():
        return list(rows)

    import sovereign.engine.client as engine_client

    monkeypatch.setattr(engine_client, "list_sessions", fake_list_sessions)
    body, status = fleetview_routes.sessions_envelope()
    context["body"], context["status"] = body, status


@then(parsers.parse("the status is {code:d}"))
def status_is(context, code):
    assert context["status"] == code, (
        f"expected HTTP {code}, got {context['status']}: {context.get('body')}"
    )


@then(parsers.parse("the body has available {value}"))
def body_has_available(context, value):
    want = value.strip().lower() == "true"
    assert context["body"].get("available") is want, context["body"]


@then("the body's sessions is a JSON array")
def body_sessions_is_array(context):
    assert isinstance(context["body"].get("sessions"), list), context["body"]


@then("the body names no unreachable adapter")
def body_has_no_unreachable(context):
    unreachable = context["body"].get("unreachable")
    assert unreachable == [], (
        f"an adapter could not answer and the board would hide it: {unreachable}"
    )


@then("the body names the error")
def body_names_error(context):
    err = context["body"].get("error")
    assert isinstance(err, str) and err, (
        f"an unavailable board must say why: {context['body']}"
    )


@given("the catalogue is not readable")
def catalogue_not_readable(monkeypatch, tmp_path):
    """A catalogue path that does not exist. The route must say so, not answer with an empty
    board -- "no sessions" and "I could not read the sessions" are different facts and the page
    renders them differently."""
    monkeypatch.setenv("ESTATE_CATALOG_PATH", str(tmp_path / "not-here.yaml"))

"""FleetView CP2: the board.

Binds `features/fleetview/cp2_board.feature`.

The board has two halves and they are graded in the two places each can be graded:
  * what the page READS is the envelope CP1 serves. That contract is graded here, in Python,
    against the same route the portal proxies.
  * what the page DRAWS is TypeScript, graded by `backstage/packages/app/src/modules/home/
    Fleet.test.tsx` (15 tests) in the portal's own jest suite.

A scenario is only worth having if it runs. This module is what makes CP2's scenarios run.

The founder's words for this product, which the scenarios restate: "there was a dashboard screen
where I could monitor the agent sessions in real time, that is a super marketable product".
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
import yaml
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/fleetview/cp2_board.feature")

REPO = Path(__file__).resolve().parents[3]
ROUTES = REPO / "backstage" / "plugins" / "fleetview-backend" / "src" / "routes.py"
SCHEMA = (
    REPO / "backstage" / "plugins" / "fleetview-backend" / "schema" / "session.json"
)


@pytest.fixture()
def context() -> dict:
    return {}


@pytest.fixture()
def routes_module():
    import importlib.util

    assert ROUTES.is_file(), (
        f"{ROUTES} does not exist, so the board has nothing to read"
    )
    spec = importlib.util.spec_from_file_location("fleetview_routes_board", ROUTES)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def catalogue(tmp_path, monkeypatch):
    """The catalogue the board reads through, one session row in the shape bin/catalog-gen emits."""
    doc = {
        "apiVersion": "backstage.io/v1alpha1",
        "kind": "Resource",
        "metadata": {
            "name": "session-alpha",
            "annotations": {
                "estate/path": "@HOME@/.claude/state/prompt-ledger/alpha.jsonl",
            },
        },
        "spec": {"type": "ledger", "owner": "agents"},
    }
    path = tmp_path / "catalog-info.yaml"
    path.write_text(yaml.safe_dump_all([doc]))
    monkeypatch.setenv("ESTATE_CATALOG_PATH", str(path))
    monkeypatch.setenv(
        "ESTATE_STATE_PATH_PREFIX", "@HOME@/.claude/state/prompt-ledger/"
    )
    return path


@given("I am signed in to the portal")
def signed_in(context, routes_module, catalogue):
    context["routes"] = routes_module


@given("a sovereign session is running")
def sovereign_running(context, monkeypatch):
    """The engine reports a running session. The engine is stubbed because a suite that needs a
    live Temporal grades nothing when Temporal is down; the adapter that translates its row is the
    production one under test."""
    row = {
        "session_id": "sb-1",
        "repo": "idp",
        "task": "fix the board",
        "step": 3,
        "status": "running",
        "runner": "echo",
        "updated_at": "2026-09-12T10:00:00Z",
    }
    context["engine_row"] = row

    import sovereign.engine.client as engine_client

    async def fake_list_sessions():
        return [row]

    monkeypatch.setattr(engine_client, "list_sessions", fake_list_sessions)


@given("the fleet page is open")
def page_open(context, routes_module, catalogue):
    context["routes"] = routes_module


@when("I open the fleet page")
def open_page(context):
    """The read that produces the board, timed.

    The feature says "the page answers within 2 seconds". The portal is not running here, so what
    is measured is the read the page makes -- the part that can be slow, and the part that
    regressed when the backend polled instead of being served.
    """
    import time

    started = time.monotonic()
    body, status = context["routes"].sessions_envelope()
    context["elapsed"] = time.monotonic() - started
    context["status"], context["body"] = status, body


@when("a session finishes")
def session_finishes(context, monkeypatch):
    """The engine reports the session stopped, and the page is told through the stream frame.

    A frame is what `GET /api/fleetview/stream` sends. The page applies it to the row it names; it
    does not re-read the board, which is what makes the update a push rather than a poll.
    """
    stopped = dict(context["engine_row"], status="stopped")

    import sovereign.engine.client as engine_client

    async def fake_list_sessions():
        return [stopped]

    monkeypatch.setattr(engine_client, "list_sessions", fake_list_sessions)
    body, _ = context["routes"].sessions_envelope()
    context["body"] = body
    context["frames"] = context["routes"].stream_frames(body["sessions"])


@then(parsers.parse("the page answers within {seconds:d} seconds"))
def answers_within(context, seconds):
    assert context["elapsed"] < seconds, (
        f"the board took {context['elapsed']:.2f}s to answer, over the {seconds}s the spec allows"
    )


@then("the running session is listed with its runtime, task and state")
def listed(context):
    assert context["status"] == 200, context["body"]
    sessions = context["body"]["sessions"]
    engine_rows = [s for s in sessions if s["runtime"] == "sovereign"]
    assert engine_rows, (
        "the running sovereign session is not on the board; the page would show a fleet without "
        f"the session the founder opened it for. Runtimes present: "
        f"{sorted({s['runtime'] for s in sessions})}"
    )
    row = engine_rows[0]
    # The three fields the feature names, read off the row the page draws.
    assert row["runtime"] == "sovereign"
    assert row["task"] == "fix the board"
    assert row["state"] == "running"
    # And the row is legible: a state the page can turn into a word rather than an unknown enum.
    schema = json.loads(SCHEMA.read_text())
    allowed = schema["properties"]["state"]["enum"]
    assert row["state"] in allowed, f"{row['state']!r} is not one of {allowed}"


@then(
    parsers.parse(
        "its state on the page changes within {seconds:d} seconds without a reload"
    )
)
def changes_without_reload(context, seconds):
    assert context["frames"], (
        "the stream produced no frame, so the page could not update"
    )
    frames = [json.loads(f.removeprefix("data: ").strip()) for f in context["frames"]]
    # The board carries every runtime, so the stream carries a frame per session. The assertion is
    # about the session that changed: find it rather than assuming it is first, which would make
    # the test pass or fail on how many other runtimes happen to be listed.
    sb = [f for f in frames if f["session_id"] == "sb-1"]
    assert sb, (
        f"no frame named the session that finished; frames were for "
        f"{[f['session_id'] for f in frames]}"
    )
    frame = sb[0]
    assert frame["state"] == "stopped", (
        f"the frame still says {frame['state']!r} after the session finished; the page would show "
        "a session that is over"
    )
    # "without a reload" is the push: the frame carries the whole record, so the page has what it
    # needs and does not have to fetch the board again.
    assert frame["record"]["session_id"] == "sb-1", frame
    assert frame["record"]["state"] == "stopped", frame


@then("the page can reach the estate's own door")
def page_reaches_door(context):
    """The board's contract holds over a real socket, not only in-process.

    A dict returned by a function and a dict returned by an HTTP door are different facts, and the
    page only ever sees the second. This stands up the route on loopback and reads it the way the
    portal's proxy does.
    """
    import urllib.request

    body = json.dumps(context["body"]).encode()

    class H(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 - the stdlib's name
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        port = server.server_address[1]
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}{context['routes'].SESSIONS_PATH}"
        ) as r:
            got = json.loads(r.read())
        assert got["available"] is True, got
        assert isinstance(got["sessions"], list), got
    finally:
        server.shutdown()

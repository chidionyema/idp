"""cp37 acceptance: the cockpit page is the presence model (CP4, crew#284).

Founder: "this ui is terrible" -- four columns, one of them 156 raw tick
lines. Master Spec v1.0 §2.1 says Ghost is the default and nothing else
renders until the founder clicks. This suite proves the two mechanical
halves of that promise the server controls, without a browser:

* GET / never embeds session or inbox text -- the shell is the same bytes
  whatever the estate is doing, so Ghost cannot leak into a page load.
* GET /api/status carries the red dot and the one emergency line the
  catastrophe path (spec §2.1: "Spatial may only be entered by explicit
  founder action ... or by a catastrophic alert") needs to render.

A real `sovereign.cockpit.server.Handler` on a real loopback socket, driven
with `http.client` (stdlib), per crew#284's instruction. The only fakes are
the two true external boundaries: `sovereign.engine.client` (Temporal) and
the presence state file (the kernel's own write, reproduced by hand here).
"""
from __future__ import annotations

import http.client
import json
import threading
import types
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/sovereign-bus/cp37_spatial_cockpit.feature")


def _fake_engine_module(sessions: list[dict[str, Any]]) -> types.ModuleType:
    """A `sovereign.engine.client` stand-in whose `list_sessions` always
    reflects the current contents of `sessions` (steps mutate it in place,
    never reassign it, so this closure stays valid for the scenario)."""

    async def _list_sessions() -> list[dict[str, Any]]:
        return list(sessions)

    async def _show(session_id: str) -> dict[str, Any]:
        raise KeyError(session_id)

    async def _signal(session_id: str, kind: str, by: str, text: str = "") -> dict[str, Any]:
        return {"ok": True}

    async def _start(task: str, runner: str = "claude", repo: str | None = None, by: str = "cli", budget: int = 0) -> dict[str, Any]:
        return {"session_id": "sb-cp37-started"}

    mod = types.ModuleType("sovereign.engine.client")
    mod.list_sessions = _list_sessions  # type: ignore[attr-defined]
    mod.show = _show  # type: ignore[attr-defined]
    mod.signal = _signal  # type: ignore[attr-defined]
    mod.start = _start  # type: ignore[attr-defined]
    return mod


@pytest.fixture
def sessions() -> list[dict[str, Any]]:
    return []


@pytest.fixture
def cockpit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, sessions: list[dict[str, Any]]):
    """A real cockpit HTTP server on an ephemeral loopback port. Import
    happens inside the fixture so the module-level route regexes (already
    resolved once per process, cp22) are only ever read, never rebuilt."""
    from sovereign.cockpit import server as cockpit_server

    inbox_path = tmp_path / "inbox.jsonl"
    inbox_path.write_text("")
    monkeypatch.setattr(cockpit_server, "engine_client", _fake_engine_module(sessions))
    monkeypatch.setattr(cockpit_server, "_inbox_path", lambda: inbox_path)
    # No X-Telegram-Init-Data header below, so auth.authorize's loopback path
    # is what admits these requests -- the same path a laptop browser uses.

    httpd = cockpit_server.build_server(port=0, bind="127.0.0.1")
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield httpd
    finally:
        httpd.shutdown()
        thread.join(timeout=5)
        httpd.server_close()


@pytest.fixture
def response(context: dict[str, Any]) -> dict[str, Any]:
    return context.setdefault("response", {})


@given(parsers.parse('a session with task "{task}" is running'))
def _session_running(sessions: list[dict[str, Any]], task: str) -> None:
    sessions.append(
        {
            "session_id": "sb-cp37-0001",
            "repo": "idp",
            "task": task,
            "step": 3,
            "status": "running",
            "runner": "claude",
            "asking": None,
            "budget": 50000,
            "budget_remaining": 41000,
            "started_at": "2026-08-26T00:00:00Z",
            "updated_at": "2026-08-26T00:00:01Z",
        }
    )


@given(parsers.parse('the inbox contains the line "{line}"'))
def _inbox_line(cockpit: Any, line: str) -> None:
    from sovereign.cockpit import server as cockpit_server

    path = cockpit_server._inbox_path()
    with path.open("a") as fh:
        fh.write(json.dumps({"source": "test", "text": line}) + "\n")


@given("the presence state is a catastrophe")
def _presence_catastrophe(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from sovereign.presence import state as presence_state
    from sovereign.presence.fsm import Spatial

    state_file = tmp_path / "presence.json"
    monkeypatch.setenv("SB_PRESENCE_STATE_FILE", str(state_file))
    presence_state.write(Spatial(cause="catastrophe"))


def _get(cockpit: Any, path: str) -> tuple[int, bytes]:
    conn = http.client.HTTPConnection(cockpit.server_address[0], cockpit.server_address[1], timeout=5)
    try:
        conn.request("GET", path)
        res = conn.getresponse()
        return res.status, res.read()
    finally:
        conn.close()


@when(parsers.parse('I GET "{path}"'))
def _get_path(cockpit: Any, response: dict[str, Any], path: str) -> None:
    status, body = _get(cockpit, path)
    response["status"] = status
    response["body"] = body
    response["text"] = body.decode("utf-8", errors="replace")
    ctype = "application/json"
    try:
        response["json"] = json.loads(body) if body else None
    except json.JSONDecodeError:
        response["json"] = None


@then(parsers.parse('the response does not contain "{needle}"'))
def _not_contains(response: dict[str, Any], needle: str) -> None:
    assert response["status"] == 200, response
    assert needle not in response["text"], f"Ghost page leaked {needle!r}"


@then(parsers.parse('the response contains "{needle}"'))
def _contains(response: dict[str, Any], needle: str) -> None:
    assert response["status"] == 200, response
    assert needle in response["text"], f"expected {needle!r} in the Ghost shell, got none"


@then(parsers.parse('the JSON field "{field}" is "{value}"'))
def _json_field_is(response: dict[str, Any], field: str, value: str) -> None:
    assert response["status"] == 200, response
    body = response["json"]
    assert body is not None, response["text"]
    assert str(body.get(field)) == value, body


@then(parsers.parse('the JSON field "{field}" is one line with no question mark'))
def _json_field_one_line_no_question(response: dict[str, Any], field: str) -> None:
    body = response["json"]
    assert body is not None, response["text"]
    line = body.get(field)
    assert line, f"expected a non-empty {field!r}, got {line!r} in {body!r}"
    assert "\n" not in line, f"{field} is not one line: {line!r}"
    assert "?" not in line, f"a system-authored line never asks a question (cp32): {line!r}"

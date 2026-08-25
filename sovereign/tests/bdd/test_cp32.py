"""cp32 acceptance: Surfaces -- Haptic, Spatial, Converse and Voice

Owner: W3 (R2, R3, R14). The cockpit is the real HTTP server on an
ephemeral loopback port; only the engine client behind it is a fake
(Temporal is a true external boundary), and its signal() records what
the Spatial view asked for.
"""
from __future__ import annotations

import http.client
import itertools
import json
import threading
import types
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from .conftest import MessageSink

scenarios("features/sovereign-bus/cp32_surfaces.feature")

SESSIONS: list[dict[str, Any]] = [
    {"session_id": "sb-run1", "status": "running", "step": 4, "budget": 10000, "budget_remaining": 6000,
     "commit": "a" * 40, "updated_at": "2026-08-25T09:00:01+00:00", "task": "build"},
    {"session_id": "sb-run2", "status": "running", "step": 1, "budget": 2000, "budget_remaining": 1900,
     "commit": "b" * 40, "updated_at": "2026-08-25T09:00:02+00:00", "task": "test"},
    {"session_id": "sb-wait", "status": "waiting", "step": 2, "budget": 5000, "budget_remaining": 4000,
     "commit": "c" * 40, "updated_at": "2026-08-25T09:00:03+00:00", "task": "deploy"},
    {"session_id": "sb-halt", "status": "halted", "step": 9, "budget": 1000, "budget_remaining": 0,
     "commit": "d" * 40, "updated_at": "2026-08-25T09:00:04+00:00", "task": "migrate"},
]


@pytest.fixture
def cockpit(config, monkeypatch: pytest.MonkeyPatch, context: dict[str, Any]):
    """The real cockpit server over a fake engine client."""
    from sovereign.cockpit import server

    context["signals"] = []

    async def list_sessions() -> list[dict[str, Any]]:
        return [dict(s) for s in SESSIONS]

    async def signal(session_id: str, kind: str, by: str, text: str) -> dict[str, Any]:
        context["signals"].append((session_id, kind, by, text))
        return {"ok": True, "session_id": session_id, "kind": kind}

    monkeypatch.setattr(server, "engine_client", types.SimpleNamespace(list_sessions=list_sessions, signal=signal))
    httpd = server.build_server(port=0, bind="loopback")
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    host, port = httpd.server_address[0], httpd.server_address[1]

    def call(method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        conn = http.client.HTTPConnection(host, port, timeout=10)
        payload = json.dumps(body).encode() if body is not None else None
        conn.request(method, path, body=payload, headers={"Content-Type": "application/json"})
        resp = conn.getresponse()
        data = json.loads(resp.read())
        conn.close()
        assert resp.status == 200, (resp.status, data)
        return data

    yield call
    httpd.shutdown()
    httpd.server_close()


# --- Spatial graph reflects Temporal truth ---------------------------------


@when(parsers.parse('I open the cockpit "{view}" view'))
def _open_view(view: str, cockpit, config, context: dict[str, Any]) -> None:
    from sovereign.presence import config_keys

    assert view == "Spatial"
    context["graph"] = cockpit("GET", str(config_keys.resolve("presence.route_api_spatial", config)))


@then("every running session is a node coloured by health and sized by burn rate")
def _nodes(context: dict[str, Any]) -> None:
    from sovereign.presence import spatial

    nodes = {n["id"]: n for n in context["graph"]["nodes"]}
    running = [s for s in SESSIONS if s["status"] == "running"]
    assert set(context["graph"]["running"]) == {s["session_id"] for s in running}
    for s in running:
        n = nodes[s["session_id"]]
        assert n["colour"] == spatial.health_colour("running")
        assert n["size"] == spatial.node_size(spatial.burn_per_step(s))
    sizes = [nodes[s["session_id"]]["size"] for s in running]
    assert sizes[0] > sizes[1], "the session burning more per step is the bigger node"
    assert nodes["sb-halt"]["colour"] == spatial.health_colour("halted") != nodes["sb-run1"]["colour"]


@then("hovering a node shows hash, budget and last heartbeat")
def _hover(context: dict[str, Any]) -> None:
    for n in context["graph"]["nodes"]:
        src = next(s for s in SESSIONS if s["session_id"] == n["id"])
        assert n["hash"] == src["commit"]
        assert n["budget"] == src["budget"] and n["budget_remaining"] == src["budget_remaining"]
        assert n["last_heartbeat"] == src["updated_at"]


@then("right-click → Halt sends the stop signal")
def _halt(cockpit, context: dict[str, Any]) -> None:
    target = context["graph"]["running"][0]
    cockpit("POST", f"/api/sessions/{target}/stop", {"by": "spatial", "text": "halt from Spatial"})
    assert context["signals"] == [(target, "stop", "spatial", "halt from Spatial")]


# --- Haptic patterns map to states -----------------------------------------


@given("the haptic channel is configured")
def _haptic_on(monkeypatch: pytest.MonkeyPatch, context: dict[str, Any]) -> None:
    monkeypatch.setenv("SB_PRESENCE_HAPTIC_ENABLED", "1")
    context["inbox"] = []


@when("a state commits, a boundary approaches, and a halt is required")
def _three_events(context: dict[str, Any]) -> None:
    from sovereign.presence import fsm, haptic

    events = [fsm.StateCommit("sb-1"), fsm.BoundaryApproaching("sb-1"), fsm.HaltRequired("sb-1")]
    context["patterns"] = [haptic.send(e, context["inbox"].append) for e in events]
    context["states"] = [fsm.apply(fsm.Ghost(), e) for e in events]


@then("one tap, two taps and a sustained buzz are sent, respectively")
def _patterns(context: dict[str, Any]) -> None:
    from sovereign.presence.fsm import Haptic, Pattern

    assert context["patterns"] == [Pattern.TAP, Pattern.DOUBLE_TAP, Pattern.BUZZ]
    assert [l["pattern"] for l in context["inbox"]] == ["tap", "double_tap", "buzz"]
    assert context["states"] == [Haptic(Pattern.TAP), Haptic(Pattern.DOUBLE_TAP), Haptic(Pattern.BUZZ)]


@then("no chat message is sent for any of them")
def _no_chat(messages: MessageSink) -> None:
    messages.assert_silent()


# --- Siri status is read from the kernel -----------------------------------


@when(parsers.parse('the shortcut "{name}" runs'))
def _shortcut_runs(name: str, cockpit, context: dict[str, Any]) -> None:
    """The shortcut definition is the record; the test does what it says."""
    root = Path(__file__).resolve().parents[2] / "presence" / "shortcuts"
    definition = json.loads((root / f"{name.replace(' ', '-')}.json").read_text())
    assert definition["name"] == name
    payload = cockpit(definition["method"], definition["url_path"])
    context["spoken"] = payload[definition["speak_field"]]
    context["shortcut_path"] = definition["url_path"]


@then(parsers.parse("it speaks the running, waiting and burn counts from GET {path}"))
def _speaks(path: str, cockpit, config, context: dict[str, Any]) -> None:
    from sovereign.presence import config_keys, status

    assert path == context["shortcut_path"] == config_keys.resolve("presence.route_api_status", config)
    payload = cockpit("GET", path)
    assert context["spoken"] == status.speak(payload)
    assert payload["running"] == 2 and payload["waiting"] == 1
    assert payload["burn_per_step"] == round(1000 + 100)
    for value in (payload["running"], payload["waiting"], payload["burn_per_step"]):
        assert str(value) in context["spoken"]


# --- The system never opens Converse ---------------------------------------


@when("any surface fires")
def _any_surface(messages: MessageSink, context: dict[str, Any]) -> None:
    from sovereign.presence import chat, fsm, haptic

    act = fsm.FounderAct(kind="message", by="founder")
    states: list[fsm.Presence] = [
        fsm.Ghost(), *(fsm.Haptic(p) for p in fsm.Pattern),
        fsm.Spatial(cause="founder_click"), fsm.Spatial(cause="catastrophe"), fsm.Converse(initiated_by=act),
    ]
    events: list[fsm.SystemEvent] = [
        fsm.StateCommit("s"), fsm.BoundaryApproaching("s"), fsm.HaltRequired("s"),
        *(fsm.Catastrophe(kind=k, session_id="s") for k in ("integrity_failure", "lockdown", "dead_mans_switch")),
    ]
    inbox: list[dict[str, Any]] = []
    for state, event in itertools.product(states, events):
        after = fsm.apply(state, event)
        assert isinstance(after, fsm.Converse) == isinstance(state, fsm.Converse), (state, event, after)
        assert not isinstance(fsm.on_system_event(event), fsm.Converse)
        haptic.send(event, inbox.append)
    context["fired"] = len(inbox)
    # A system-authored chat message with a question in it cannot be built.
    with pytest.raises(chat.AsksAQuestion):
        chat.CatastropheAlert(cause="lockdown", hash="abc", remediation="approve?")
    with pytest.raises(chat.AsksAQuestion):
        chat.Digest(lines=("continue? hash:x",), receipts_hash="x", sig="s")
    chat.send(messages, chat.CatastropheAlert(cause="lockdown", hash="abc", remediation="bin/sb audit --verify"))


@then("no message is sent to the chat that asks the founder a question")
def _no_question(messages: MessageSink, context: dict[str, Any]) -> None:
    assert context["fired"] == 7 * 6
    assert all("?" not in m.text for m in messages.sent)
    assert messages.count() == 1, "the one catastrophe alert is the only chat message"

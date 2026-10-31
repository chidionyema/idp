"""The pod's intent path must reach the laptop's GOVERNED door, not an empty one.

Issue #7579, repair R2. The estate-mcp image ships the intent catalogue and NEITHER
`estate-execute` NOR the plan ledger, so the production `estate_invoke` had no gate at all:
the production intent path was not the governed door. The laptop owns the gate, the ledger and
the audit, so the pod asks the laptop over one authenticated, intent-scoped route.

These are falsifiers, not documentation: before the fix the pod path raised or silently
succeeded; after it these PASS. They pin five things:

  * a host that HAS a local door keeps using it -- the remote route is a fallback, not a
    replacement;
  * a host with NO local door forwards the intent to the laptop, with the caller's session
    travelling UNCHANGED (a programmatic session is not a voice session);
  * the request carries the bearer credential and structured JSON arguments;
  * a missing door configuration is a CLEAR error, never a false success;
  * a refusal or an HTTP error from the laptop is REPORTED, not swallowed.
"""

import importlib.machinery
import importlib.util
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
PLUGIN = REPO / "mcp" / "plugins" / "estate_mcp.py"

INTENT = """name: probe
description: A harmless probe.
args:
  who:
    type: string
    default: estate
    description: Whose report.
steps:
  - cmd: echo
"""


def _load(name, path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class _FakeDoor:
    """The laptop's door, for the pod's sake: a real HTTP server that records what it was sent."""

    def __init__(self, status=200, payload=None):
        self.status = status
        self.payload = (
            payload
            if payload is not None
            else {
                "ok": True,
                "stdout": "did the thing",
                "stderr": "",
                "exit_code": 0,
            }
        )
        self.requests = []
        self._server = None

    def __enter__(self):
        door = self

        class _Handler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802 - the http.server contract
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length)
                door.requests.append(
                    {
                        "path": self.path,
                        "auth": self.headers.get("Authorization"),
                        "content_type": self.headers.get("Content-Type"),
                        "body": json.loads(raw.decode("utf-8")),
                    }
                )
                body = json.dumps(door.payload).encode("utf-8")
                self.send_response(door.status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):
                return

        self._server = HTTPServer(("127.0.0.1", 0), _Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_exc):
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)
        return False

    @property
    def url(self):
        host, port = self._server.server_address
        return "http://{}:{}/intent/execute".format(host, port)


@pytest.fixture()
def plugin(tmp_path, monkeypatch):
    """The plugin, loaded with an isolated HOME, an isolated catalogue and no ambient session."""
    intents = tmp_path / "intents"
    intents.mkdir()
    (intents / "probe.yaml").write_text(INTENT)
    monkeypatch.setenv("ESTATE_INTENTS_DIR", str(intents))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    (tmp_path / "home" / ".estate" / "intents").mkdir(parents=True)
    monkeypatch.delenv("ESTATE_SESSION_ID", raising=False)
    monkeypatch.delenv("ESTATE_LAPTOP_INTENT_URL", raising=False)
    monkeypatch.delenv("ESTATE_LAPTOP_INTENT_TOKEN", raising=False)
    monkeypatch.delenv("ESTATE_LAPTOP_INTENT_TOKEN_FILE", raising=False)

    module = _load("estate_mcp_forwarding_under_test", PLUGIN)

    class _NoSession:
        @staticmethod
        def resolve_session_id():
            return ""

    monkeypatch.setattr(module, "_PLAN_CONTRACT", _NoSession)
    monkeypatch.setattr(module, "_PLAN_CONTRACT_TRIED", True)
    return module


def _write_token(tmp_path, monkeypatch, token="pod-door-token"):  # noqa: S107 -- a test credential
    path = tmp_path / "intent-token"
    path.write_text(token + "\n")
    monkeypatch.setenv("ESTATE_LAPTOP_INTENT_TOKEN_FILE", str(path))
    return token


def test_a_host_with_a_local_door_keeps_using_it(plugin, tmp_path, monkeypatch):
    """The remote route is a fallback. A laptop-hosted gateway must not take the long way round."""
    local = tmp_path / "home" / ".estate" / "bin" / "estate-execute"
    local.parent.mkdir(parents=True)
    local.write_text("#!/bin/sh\necho local\n")
    local.chmod(0o755)
    seen = {}

    class _Proc:
        returncode = 0
        stdout = "local"
        stderr = ""

    def _run(cmd, **kwargs):
        seen["cmd"] = cmd
        return _Proc()

    monkeypatch.setattr(plugin.subprocess, "run", _run)
    with _FakeDoor() as door:
        monkeypatch.setenv("ESTATE_LAPTOP_INTENT_URL", door.url)
        _write_token(tmp_path, monkeypatch)
        out = plugin._estate_invoke({"intent": "probe"})
    assert out == "local"
    assert "cmd" in seen
    assert door.requests == []


def test_a_pod_forwards_the_intent_to_the_laptops_door(plugin, tmp_path, monkeypatch):
    with _FakeDoor() as door:
        monkeypatch.setenv("ESTATE_LAPTOP_INTENT_URL", door.url)
        _write_token(tmp_path, monkeypatch)
        out = plugin._estate_invoke(
            {"intent": "probe", "args": {"who": "founder"}, "session_id": "prog-1"}
        )
    assert "did the thing" in out
    assert len(door.requests) == 1
    request = door.requests[0]
    assert request["path"] == "/intent/execute"
    assert request["auth"] == "Bearer pod-door-token"
    assert request["content_type"] == "application/json"
    assert request["body"]["intent"] == "probe"
    assert request["body"]["args"] == {"who": "founder"}


def test_the_session_travels_unchanged_and_unnamespaced(plugin, tmp_path, monkeypatch):
    """A programmatic session is not a voice session: it must never gain a `voice:` prefix."""
    with _FakeDoor() as door:
        monkeypatch.setenv("ESTATE_LAPTOP_INTENT_URL", door.url)
        _write_token(tmp_path, monkeypatch)
        plugin._estate_invoke({"intent": "probe", "session_id": "prog-session-1"})
    body = door.requests[0]["body"]
    assert body["session_id"] == "prog-session-1"
    assert not body["session_id"].startswith("voice:")


def test_an_unconfigured_door_is_a_clear_error(plugin):
    out = plugin._estate_invoke({"intent": "probe"})
    assert out.startswith("ERROR")
    assert "ESTATE_LAPTOP_INTENT_URL" in out


def test_a_refusal_from_the_laptop_is_reported(plugin, tmp_path, monkeypatch):
    payload = {
        "ok": False,
        "stdout": "",
        "stderr": "plan_not_declared",
        "exit_code": 3,
    }
    with _FakeDoor(payload=payload) as door:
        monkeypatch.setenv("ESTATE_LAPTOP_INTENT_URL", door.url)
        _write_token(tmp_path, monkeypatch)
        out = plugin._estate_invoke({"intent": "probe"})
    assert out.startswith("ERROR")
    assert "plan_not_declared" in out
    assert "exit 3" in out


def test_an_http_error_from_the_laptop_is_reported(plugin, tmp_path, monkeypatch):
    with _FakeDoor(status=401, payload={"detail": "no"}) as door:
        monkeypatch.setenv("ESTATE_LAPTOP_INTENT_URL", door.url)
        _write_token(tmp_path, monkeypatch)
        out = plugin._estate_invoke({"intent": "probe"})
    assert "401" in out


def test_the_mcp_schema_is_unchanged(plugin):
    """The forwarding adds no tool arguments: a gateway that already speaks `estate_invoke`
    keeps working."""
    schema = [t for t in plugin.TOOL_DEFS if t["name"] == "estate_invoke"][0][
        "inputSchema"
    ]
    assert set(schema["properties"]) == {"intent", "args", "session_id", "timeout"}
    assert schema["required"] == ["intent"]

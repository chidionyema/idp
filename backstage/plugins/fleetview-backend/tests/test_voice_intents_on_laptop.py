"""The pod matches a spoken intent and the laptop runs it (voice_intents._on_laptop).

A real HTTP server stands in for the laptop's /voice/intent, so the forward is the same urllib
call the sidecar makes over fleetview-mac-egress.yaml. The pod here has no estate-execute.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from fleetview_backend import voice_intents as vi

FLUX_RECONCILE_YAML = "name: flux-reconcile\nsteps:\n  - cmd: echo\n"
CI_STATUS_YAML = "name: ci-status\nsteps:\n  - cmd: echo\n"


class Laptop:
    def __init__(self) -> None:
        self.heard: list[dict] = []
        self.answers: list[tuple[int, dict | None]] = []


@pytest.fixture()
def laptop():
    state = Laptop()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802 -- http.server's name
            length = int(self.headers.get("Content-Length") or 0)
            state.heard.append(json.loads(self.rfile.read(length)))
            status, body = state.answers.pop(0)
            self.send_response(status)
            self.end_headers()
            if body is not None:
                self.wfile.write(json.dumps(body).encode())

        def log_message(self, *_args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    state.url = f"http://127.0.0.1:{server.server_port}/voice/intent"
    yield state
    server.shutdown()


@pytest.fixture(autouse=True)
def pod(tmp_path, monkeypatch):
    intents = tmp_path / "intents"
    intents.mkdir()
    (intents / "flux-reconcile.yaml").write_text(FLUX_RECONCILE_YAML)
    (intents / "ci-status.yaml").write_text(CI_STATUS_YAML)
    monkeypatch.setenv("FLEETVIEW_INTENTS_DIR", str(intents))
    monkeypatch.setenv("ESTATE_EXECUTE", str(tmp_path / "no-such-executor"))
    monkeypatch.setenv("FLEETVIEW_INTENT_LOG", str(tmp_path / "audit.jsonl"))
    vi._PENDING.clear()
    vi._REMOTE_PENDING.clear()
    yield tmp_path
    vi._PENDING.clear()
    vi._REMOTE_PENDING.clear()


def test_a_question_never_waits_on_the_laptop(laptop, monkeypatch):
    monkeypatch.setenv("FLEETVIEW_INTENTS_URL", laptop.url)
    assert vi.handle("how many agents are stuck", "s1") is None
    assert laptop.heard == []


def test_a_matched_intent_is_run_by_the_laptop(laptop, monkeypatch):
    monkeypatch.setenv("FLEETVIEW_INTENTS_URL", laptop.url)
    ran = vi.result("ci-status", "ok", "all green")
    laptop.answers.append((200, ran))
    assert vi.handle("check ci status", "s1") == ran
    assert laptop.heard == [{"text": "check ci status", "session_id": "s1"}]


def test_the_yes_reaches_the_laptop_that_asked(laptop, monkeypatch):
    monkeypatch.setenv("FLEETVIEW_INTENTS_URL", laptop.url)
    laptop.answers.append(
        (
            200,
            vi.result(
                "flux-reconcile",
                "pending_confirmation",
                "Run flux-reconcile? Say yes to confirm.",
            ),
        )
    )
    laptop.answers.append((200, vi.result("flux-reconcile", "ok", "reconciled")))
    assert vi.handle("run flux reconcile", "s2")["status"] == "pending_confirmation"
    assert vi.handle("yes", "s2")["text"] == "reconciled"
    assert [h["text"] for h in laptop.heard] == ["run flux reconcile", "yes"]


def test_a_yes_with_nothing_pending_is_not_forwarded(laptop, monkeypatch):
    monkeypatch.setenv("FLEETVIEW_INTENTS_URL", laptop.url)
    assert vi.handle("yes", "s3") is None
    assert laptop.heard == []


class Clock:
    """`time` for voice_intents, with monotonic() under the test's control.

    The real module's other names (time(), strftime) still work, so audits write real timestamps;
    only the clock this module measures pending confirmations with is moved.
    """

    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now

    def __getattr__(self, name):
        import time as real

        return getattr(real, name)


def test_a_yes_after_the_window_says_it_expired(laptop, monkeypatch):
    # Measured 2026-10-23T07:47Z through the public proxy: intent+args asked, the founder's "yes"
    # came two minutes later, and the answer was HTTP 204 with an empty body. PENDING_TTL_S is
    # 60 s, so that silence is ordinary, not a fault -- and silence is the one thing a voice
    # surface must never answer with.
    clock = Clock()
    monkeypatch.setattr(vi, "time", clock)
    monkeypatch.setenv("FLEETVIEW_INTENTS_URL", laptop.url)
    laptop.answers.append(
        (
            200,
            vi.result("flux-reconcile", "pending_confirmation", "Run flux-reconcile?"),
        )
    )
    vi.handle("run flux reconcile", "s8")
    clock.now = vi.PENDING_TTL_S + 30
    said = vi.handle("yes", "s8")
    assert said["status"] == "expired"
    assert "expired" in said["text"] and "Say" in said["text"]
    assert [h["text"] for h in laptop.heard] == ["run flux reconcile"]


def test_a_yes_to_a_confirmation_the_pod_holds_also_expires_out_loud(laptop, pod):
    clock = Clock()
    vi.time = clock  # noqa: SIM115 -- restored below
    try:
        vi._PENDING["s9"] = ("flux-reconcile", 0.0)
        clock.now = vi.PENDING_TTL_S + 1
        said = vi.handle("yes", "s9")
        assert said["status"] == "expired"
        assert "flux reconcile" in said["text"]
    finally:
        import time as real

        vi.time = real


def test_the_laptop_naming_nothing_lets_the_model_answer(laptop, monkeypatch):
    monkeypatch.setenv("FLEETVIEW_INTENTS_URL", laptop.url)
    laptop.answers.append((204, None))
    assert vi.handle("check ci status", "s4") is None


def test_the_arguments_reach_the_laptop_that_runs_them(laptop, monkeypatch, pod):
    # Measured in production 2026-10-23T05:0xZ: POST /voice/intent with
    # {intent: "pr-list", args: {limit: 2, state: "merged"}} was confirmed as "Run pr-list? Say yes
    # to confirm." and answered with OPEN pull requests, because the pod forwarded the intent's
    # name and dropped the values. The founder then approved something other than what they said.
    (pod / "intents" / "pr-list.yaml").write_text(
        "name: pr-list\nargs:\n  state: {type: string, default: open}\n  limit: {type: int, default: 10}\n"
        "steps:\n  - cmd: echo\n"
    )
    monkeypatch.setenv("FLEETVIEW_INTENTS_URL", laptop.url)
    laptop.answers.append(
        (
            200,
            vi.result(
                "pr-list",
                "pending_confirmation",
                "Run pr-list with limit 2, state merged? Say yes to confirm.",
            ),
        )
    )
    asked = vi.handle("pr-list", "s6", {"limit": 2, "state": "merged"})
    assert laptop.heard == [
        {"text": "pr-list", "session_id": "s6", "args": {"limit": 2, "state": "merged"}}
    ]
    assert (
        asked["text"] == "Run pr-list with limit 2, state merged? Say yes to confirm."
    )


def test_no_arguments_means_no_args_key_on_the_wire(laptop, monkeypatch):
    # The spoken path must look exactly as it did: an empty "args" would be a different request
    # to every reader of the audit log, and the laptop's own route treats {} as nothing said.
    monkeypatch.setenv("FLEETVIEW_INTENTS_URL", laptop.url)
    laptop.answers.append((200, vi.result("ci-status", "ok", "all green")))
    vi.handle("check ci status", "s7")
    assert laptop.heard == [{"text": "check ci status", "session_id": "s7"}]


def test_a_laptop_that_is_away_is_said_out_loud(monkeypatch):
    monkeypatch.setenv("FLEETVIEW_INTENTS_URL", "http://127.0.0.1:9/voice/intent")
    r = vi.handle("check ci status", "s5")
    assert r["status"] == "error"
    assert r["text"] == "The laptop is not answering, so that cannot run now."


def test_the_laptop_itself_runs_its_own_intents(laptop, monkeypatch, pod):
    # The Mac has estate-execute: it must never forward to itself.
    exe = pod / "estate-execute"
    exe.write_text('#!/bin/sh\necho "ran $1"\n')
    exe.chmod(0o755)
    monkeypatch.setenv("ESTATE_EXECUTE", str(exe))
    monkeypatch.setenv("FLEETVIEW_INTENTS_URL", laptop.url)
    assert vi.handle("check ci status", "s6")["text"] == "ran ci-status"
    assert laptop.heard == []

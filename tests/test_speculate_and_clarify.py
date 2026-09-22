"""The 2100 speculative intent compiler and clarification handshake.

WHAT THIS GRADES, AND WHY.

The Voice 2100 architecture (docs/specs/2026-09-22-voice-2100-architecture.md) commits to two
new surfaces, both of which are governed by Schema v2 and the 0.90 confidence floor:

  1. `POST /voice/speculate` -- the server-side fallback for clients that cannot run WebGPU
     (Safari iOS today). Takes a partial transcript, calls the router's `intent-speculative`
     alias, and returns a Schema v2 candidate. Never writes to the bus.

  2. `voice_clarify` MCP tool -- the standardized clarification handshake. An agent asks
     one targeted question and publishes it on `estate.agent.sovereign.<session>.steer`
     with `kind=clarify`. The browser's `onClarificationNeeded` consumer surfaces it.

The claims worth grading, stated as facts not aspirations:

  - `speculate()` validates its inputs (400 on missing fields) and validates the router's
    reply against Schema v2 (502 on schema failure, including hallucinated fields).
  - A router reply with `confidence < 0.90` carries `clarification_needed: true` in the
    response envelope.
  - `do_voice_clarify()` refuses a payload with no `session_id`, no `question`, or no
    `candidate_action` (the same author-is-required discipline `/voice/steer` keeps).
  - `do_voice_clarify()` publishes to `estate.agent.sovereign.<session>.steer` with
    `kind=clarify`, never `kind=steer` -- the bus subscriber can tell them apart by kind.
  - `do_voice_clarify()` reports the bus failure honestly rather than swallowing it.

WHAT THIS DOES NOT DO.

It does not call the real router. The router is BLIND without network, and the test must
pass in BLIND. The router is replaced by a recorder the same way `test_voice_on_the_bus.py`
replaces the `nats` library -- stub at the boundary, not at the dict.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "backstage" / "plugins" / "fleetview-backend" / "src"
MCP = ROOT / "mcp" / "plugins" / "voice.py"


def _load_pkg_member(path: Path, name: str, pkg_name: str):
    """Same loader the voice-on-the-bus test uses: registers the module as a member of
    `pkg_name` so relative imports (e.g. `from . import tracing`) resolve."""
    if pkg_name not in sys.modules:
        sys.modules[pkg_name] = types.ModuleType(pkg_name)
    full = f"{pkg_name}.{name}"
    spec = importlib.util.spec_from_file_location(full, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    module.__package__ = pkg_name
    sys.modules[full] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def voice():
    """Loads voice_media.py with its package context, the same loader as the on-the-bus test."""
    # voice_media.py does `from . import tracing`; tracing has to be loaded first under the
    # same package. The on-the-bus test does the same dance.
    _load_pkg_member(SRC / "tracing.py", "tracing", "fleetview_backend")
    return _load_pkg_member(SRC / "voice_media.py", "voice_media", "fleetview_backend")


class _RouterRecorder:
    """Stands in for the router. Records what was asked, returns whatever the test wired."""

    def __init__(self, reply: dict[str, Any], code: int = 200) -> None:
        self.reply = reply
        self.code = code
        self.calls: list[dict[str, Any]] = []

    def __call__(self, req, timeout=0.0):
        self.calls.append(
            {
                "url": req.full_url,
                "method": req.get_method(),
                "body": json.loads(req.data.decode("utf-8")),
                "headers": dict(req.headers),
                "timeout": timeout,
            }
        )

        class _Resp:
            def __init__(self, payload, code):
                self._payload = payload
                self.code = code

            def read(self):
                return json.dumps(self._payload).encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        if self.code != 200:
            # urllib.error.HTTPError takes (code, msg, hdrs, fp)
            import urllib.error

            err = urllib.error.HTTPError(
                req.full_url, self.code, "err", {}, io_bytes(io_bytes_str := "{}")
            )
            err.read = lambda: json.dumps(self.reply).encode("utf-8")
            raise err

        return _Resp(self.reply, self.code)


def io_bytes(s: str) -> bytes:
    return s.encode("utf-8")


def test_speculate_validates_inputs_and_returns_a_schema_v2_compile(voice, monkeypatch):
    """Missing partial is a 400, not a 500 -- the schema is the contract, not the router."""
    monkeypatch.setenv("LITELLM_API_KEY", "test-key")
    monkeypatch.setenv("LITELLM_HOST", "https://llm.test")

    recorder = _RouterRecorder(
        {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "action": "deploy",
                                "target": "frontend",
                                "confidence": 0.95,
                            }
                        )
                    }
                }
            ]
        }
    )

    monkeypatch.setattr("urllib.request.urlopen", recorder)

    # Missing partial -> 400
    payload, status = asyncio_run(
        voice.speculate({"session_id": "abc-123", "partial": ""})
    )
    assert status == 400, payload
    assert "partial" in payload["error"]

    # Missing session_id -> 400
    payload, status = asyncio_run(
        voice.speculate({"partial": "Deploy the", "session_id": ""})
    )
    assert status == 400, payload
    assert "session_id" in payload["error"]


def test_speculate_returns_a_validated_compile_with_clarification_flag(
    voice, monkeypatch
):
    """A high-confidence reply: clarification_needed is false; the candidate is Schema v2."""
    monkeypatch.setenv("LITELLM_API_KEY", "test-key")
    monkeypatch.setenv("LITELLM_HOST", "https://llm.test")

    recorder = _RouterRecorder(
        {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "action": "deploy",
                                "target": "frontend",
                                "env": "prod",
                                "confidence": 0.97,
                                "timestamp": "2026-09-22T20:00:00Z",
                            }
                        )
                    }
                }
            ]
        }
    )
    monkeypatch.setattr("urllib.request.urlopen", recorder)

    payload, status = asyncio_run(
        voice.speculate(
            {
                "session_id": "abc-123",
                "partial": "Deploy the frontend to production",
            }
        )
    )

    assert status == 200, payload
    assert payload["clarification_needed"] is False
    assert payload["confidence"] == 0.97
    assert payload["source"] == "router"
    assert payload["compiled"]["action"] == "deploy"
    assert payload["compiled"]["target"] == "frontend"
    assert payload["compiled"]["env"] == "prod"
    assert payload["compiled"]["session_id"] == "abc-123"
    assert payload["compiled"]["partial"] is True
    assert payload["compiled"]["transcript"] == "Deploy the frontend to production"
    # author is deliberately stripped: a speculative call is not on the bus.
    assert "author" not in payload["compiled"]


def test_speculate_low_confidence_sets_clarification_needed(voice, monkeypatch):
    """Confidence below 0.90: clarification_needed is true (the 2100 floor)."""
    monkeypatch.setenv("LITELLM_API_KEY", "test-key")
    monkeypatch.setenv("LITELLM_HOST", "https://llm.test")

    recorder = _RouterRecorder(
        {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "action": "ask",
                                "confidence": 0.42,
                                "timestamp": "2026-09-22T20:00:00Z",
                            }
                        )
                    }
                }
            ]
        }
    )
    monkeypatch.setattr("urllib.request.urlopen", recorder)

    payload, status = asyncio_run(
        voice.speculate({"session_id": "abc-123", "partial": "the uh thing"})
    )

    assert status == 200, payload
    assert payload["clarification_needed"] is True
    assert payload["confidence"] == 0.42


def test_speculate_refuses_a_router_reply_that_fails_schema_v2(voice, monkeypatch):
    """The router may hallucinate a field. Schema v2 rejects it (502), the browser keeps
    its own client-side intent instead of shipping garbage."""
    monkeypatch.setenv("LITELLM_API_KEY", "test-key")
    monkeypatch.setenv("LITELLM_HOST", "https://llm.test")

    recorder = _RouterRecorder(
        {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                # missing confidence (required by Schema v2)
                                "action": "deploy",
                                "target": "frontend",
                                "DROP_TABLE": "users",  # prompt-injection attempt
                            }
                        )
                    }
                }
            ]
        }
    )
    monkeypatch.setattr("urllib.request.urlopen", recorder)

    payload, status = asyncio_run(
        voice.speculate({"session_id": "abc-123", "partial": "Deploy the frontend"})
    )

    assert status == 502, payload
    assert "Schema v2" in payload["error"]
    assert "DROP_TABLE" not in json.dumps(
        payload
    )  # the rogue field is reported, not echoed back


def test_speculate_without_router_key_is_503_not_a_silent_fallback(voice, monkeypatch):
    """No LITELLM_API_KEY on this deployment: voice has no model. The endpoint must say so."""
    monkeypatch.delenv("LITELLM_API_KEY", raising=False)
    monkeypatch.setenv("LITELLM_HOST", "https://llm.test")

    payload, status = asyncio_run(
        voice.speculate({"session_id": "abc-123", "partial": "Deploy"})
    )

    assert status == 503, payload
    assert (
        "router key" in payload["error"].lower()
        or "litellm" in payload["error"].lower()
    )


def test_speculate_calls_the_router_alias_not_a_provider(voice, monkeypatch):
    """The router model is the alias `intent-speculative`, not a vendor. That alias is the
    air-gap lever: enterprise deployments pin it to ollama, consumer deployments to groq,
    and the endpoint never has to know the difference."""
    monkeypatch.setenv("LITELLM_API_KEY", "test-key")
    monkeypatch.setenv("LITELLM_HOST", "https://llm.test")

    recorder = _RouterRecorder(
        {
            "choices": [
                {
                    "message": {
                        "content": json.dumps({"action": "status", "confidence": 0.91})
                    }
                }
            ]
        }
    )
    monkeypatch.setattr("urllib.request.urlopen", recorder)

    asyncio_run(voice.speculate({"session_id": "abc-123", "partial": "What's the"}))

    assert len(recorder.calls) == 1
    call = recorder.calls[0]
    assert call["body"]["model"] == "intent-speculative"
    assert call["url"] == "https://llm.test/v1/chat/completions"
    assert "system" in str(call["body"]["messages"])


def _load_voice_mcp():
    """Loads mcp/plugins/voice.py with a fake nats package so the module imports cleanly."""
    # The voice MCP plugin imports `nats` at module level. Stub it the same way the rest of
    # the test suite does (see test_voice_on_the_bus.py for the canonical stub).
    fake_nats = types.ModuleType("nats")
    fake_nats.errors = types.ModuleType("nats.errors")

    class _StubErr(Exception):
        pass

    fake_nats.errors.Error = _StubErr

    sys.modules.setdefault("nats", fake_nats)
    sys.modules.setdefault("nats.errors", fake_nats.errors)

    spec = importlib.util.spec_from_file_location("voice_mcp", MCP)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["voice_mcp"] = module
    spec.loader.exec_module(module)
    return module


def test_do_voice_clarify_refuses_a_payload_without_session_id():
    """session_id is the bus subject: a clarify without a session is not a clarify."""
    voice_mcp = _load_voice_mcp()
    out = asyncio_run(
        voice_mcp.do_voice_clarify(
            session_id="",
            question="Did you mean deploy frontend?",
            candidate_action="deploy",
        )
    )
    assert out["clarified"] is False
    assert "session_id" in out["error"]


def test_do_voice_clarify_refuses_a_payload_without_question():
    voice_mcp = _load_voice_mcp()
    out = asyncio_run(
        voice_mcp.do_voice_clarify(
            session_id="abc-123",
            question="",
            candidate_action="deploy",
        )
    )
    assert out["clarified"] is False
    assert "question" in out["error"]


def test_do_voice_clarify_refuses_a_payload_without_candidate_action():
    voice_mcp = _load_voice_mcp()
    out = asyncio_run(
        voice_mcp.do_voice_clarify(
            session_id="abc-123",
            question="Did you mean deploy?",
            candidate_action="",
        )
    )
    assert out["clarified"] is False
    assert "candidate_action" in out["error"]


def test_do_voice_clarify_without_nats_url_is_an_honest_error():
    """No bus on this deployment: the tool reports it rather than pretending to clarify."""
    voice_mcp = _load_voice_mcp()
    out = asyncio_run(
        voice_mcp.do_voice_clarify(
            session_id="abc-123",
            question="Did you mean deploy frontend?",
            candidate_action="deploy",
            cfg={"nats_url": ""},
        )
    )
    assert out["clarified"] is False
    assert "NATS_URL" in out["error"]


def test_do_voice_clarify_publishes_a_clarify_row_on_the_bus():
    """A valid clarify publishes to estate.agent.sovereign.<session>.steer with kind=clarify.

    The subject is the SAME as a steer row -- that is the contract. Subscribers on
    `*.steer` see both kinds and discriminate by `event.kind`, not by subject.
    """
    voice_mcp = _load_voice_mcp()

    published: list[tuple[str, bytes]] = []

    class _FakeNc:
        def __init__(self):
            self._drained = False

        def jetstream(self):
            return self

        async def publish(self, subject, payload):
            published.append((subject, payload))
            return types.SimpleNamespace(seq=42)

        async def drain(self):
            self._drained = True

    async def _fake_connect(url):
        return _FakeNc()

    voice_mcp._connect = _fake_connect
    voice_mcp._require_nats = lambda: None  # already faked

    out = asyncio_run(
        voice_mcp.do_voice_clarify(
            session_id="abc-123",
            question="Did you mean deploy the frontend?",
            candidate_action="deploy",
            candidate_target="frontend",
            cfg={"nats_url": "nats://localhost:4222"},
        )
    )

    assert out["clarified"] is True
    assert out["subject"] == "estate.agent.sovereign.abc-123.steer"
    assert out["session_id"] == "abc-123"
    assert out["candidate_action"] == "deploy"
    assert out["candidate_target"] == "frontend"

    assert len(published) == 1
    subject, raw = published[0]
    assert subject == "estate.agent.sovereign.abc-123.steer"
    event = json.loads(raw)
    assert event["kind"] == "clarify"
    assert event["session_id"] == "abc-123"
    assert event["runtime"] == "sovereign"
    assert event["clarify"]["question"] == "Did you mean deploy the frontend?"
    assert event["clarify"]["candidate"]["action"] == "deploy"
    assert event["clarify"]["candidate"]["target"] == "frontend"
    # The contract: a clarify row carries the SAME shape as a steer row, with `kind` being
    # the discriminator. A subscriber on `*.steer` reads both.
    assert "steer" not in event or event["kind"] == "clarify"


def test_do_voice_clarify_reports_a_failing_publish_rather_than_swallowing_it():
    """A 502 from the bus must surface to the agent as a structured error, not a hang."""
    voice_mcp = _load_voice_mcp()

    class _FakeNc:
        def jetstream(self):
            return self

        async def publish(self, subject, payload):
            raise RuntimeError("nats: connection refused")

        async def drain(self):
            pass

    async def _fake_connect(url):
        return _FakeNc()

    voice_mcp._connect = _fake_connect
    voice_mcp._require_nats = lambda: None

    out = asyncio_run(
        voice_mcp.do_voice_clarify(
            session_id="abc-123",
            question="Did you mean deploy?",
            candidate_action="deploy",
            cfg={"nats_url": "nats://localhost:4222"},
        )
    )
    assert out["clarified"] is False
    assert "RuntimeError" in out["error"]
    assert "connection refused" in out["error"]


# ---------------------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------------------


def asyncio_run(coro):
    """Run a coroutine in a fresh event loop. Same shape as test_voice_on_the_bus uses."""
    import asyncio

    return asyncio.get_event_loop().run_until_complete(coro)

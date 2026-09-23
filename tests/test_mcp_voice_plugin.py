"""MCP voice plugin: any agent framework can subscribe to voice with 3 lines.

WHAT THIS GRADES, AND WHY.

The voice MCP plugin (mcp/plugins/voice.py) exposes voice intents to any MCP-compatible
agent. Three claims matter:

  1. voice_intent_stream yields intents with the fields agents need: text, author,
     session_id, timestamp, confidence.
  2. voice_speak publishes to the bus and reports honestly whether it landed.
  3. voice_last_intent reads from local history so an agent can catch up without
     subscribing to the live stream.

The NATS adapter itself is not the subject — it is graded in test_voice_on_the_bus.py.
Here the adapter is replaced by a recorder so the plugin's own logic is measured.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest


class _FakeJetStream:
    """Stands in for nc.jetstream()."""

    def __init__(self, recorder: "_Recorder") -> None:
        self._recorder = recorder

    async def subscribe(self, subject: str):
        self._recorder.subscribed_subjects.append(subject)
        return _FakeSubscription(self._recorder)

    async def publish(self, subject: str, payload: bytes):
        ack = _FakeAck()
        self._recorder.published.append((subject, payload, ack))
        return ack


class _FakeAck:
    def __init__(self) -> None:
        self.seq = 42


class _FakeSubscription:
    """Yields fake messages for testing."""

    def __init__(self, recorder: "_Recorder") -> None:
        self._recorder = recorder

    @property
    def messages(self):
        return self

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._recorder.messages_to_yield:
            return self._recorder.messages_to_yield.pop(0)
        raise StopAsyncIteration


class _FakeMessage:
    """A fake NATS message."""

    def __init__(self, data: bytes) -> None:
        self.data = data
        self.acked = False

    async def ack(self):
        self.acked = True


class _Recorder:
    """Stands in for the `nats` package."""

    def __init__(self) -> None:
        self.published: list[tuple[str, bytes, _FakeAck]] = []
        self.subscribed_subjects: list[str] = []
        self.drained = False
        self.connect_kwargs: dict = {}
        self.messages_to_yield: list[_FakeMessage] = []

    async def connect(self, url: str, **kwargs):
        self.url = url
        self.connect_kwargs = kwargs
        return self

    def jetstream(self):
        return _FakeJetStream(self)

    async def drain(self):
        self.drained = True


@pytest.fixture()
def voice_plugin(monkeypatch, tmp_path):
    """The voice plugin wired to a recording bus."""
    recorder = _Recorder()
    monkeypatch.setitem(sys.modules, "nats", recorder)
    monkeypatch.setenv("NATS_URL", "nats://nats.event-bus.svc:4222")

    # Use a temp file for history
    history_path = tmp_path / "voice-intents.jsonl"
    monkeypatch.setenv("VOICE_INTENT_HISTORY_PATH", str(history_path))

    # Import the module fresh
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "voice_plugin_under_test",
        Path(__file__).resolve().parents[1] / "mcp" / "plugins" / "voice.py",
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    class Fixture:
        def __init__(self):
            self.module = module
            self.bus = recorder
            self.history_path = history_path

    return Fixture()


def test_voice_speak_publishes_to_the_bus(voice_plugin):
    """voice_speak puts a row on estate.agent.sovereign.speak."""
    result = asyncio.run(
        voice_plugin.module.do_voice_speak(
            text="Four agents are stuck",
            voice="af_sky",
            session_id="test-session-123",
        )
    )

    assert result["spoken"] is True
    assert result["subject"] == "estate.agent.sovereign.speak"
    assert result["voice"] == "af_sky"
    assert result["text"] == "Four agents are stuck"

    # Check what was actually published
    assert len(voice_plugin.bus.published) == 1
    subject, payload, _ack = voice_plugin.bus.published[0]
    assert subject == "estate.agent.sovereign.speak"
    event = json.loads(payload.decode())
    assert event["kind"] == "speak"
    assert event["speak"]["text"] == "Four agents are stuck"
    assert event["speak"]["voice"] == "af_sky"


def test_voice_speak_refuses_empty_text(voice_plugin):
    """An empty text is refused, not published."""
    result = asyncio.run(voice_plugin.module.do_voice_speak(text="", voice="af_sky"))

    assert result["spoken"] is False
    assert "text" in result["error"]
    assert voice_plugin.bus.published == []


def test_voice_speak_degrades_when_bus_unavailable(voice_plugin, monkeypatch):
    """No NATS_URL is a named degradation, never a crash."""
    monkeypatch.delenv("NATS_URL", raising=False)

    result = asyncio.run(
        voice_plugin.module.do_voice_speak(
            text="test", cfg={"nats_url": "", "history_path": "", "history_limit": 100}
        )
    )

    assert result["spoken"] is False
    assert "NATS_URL" in result["error"]


def test_voice_last_intent_reads_from_history(voice_plugin):
    """voice_last_intent reads from the local history file."""
    # Write some intents to history
    intents = [
        {
            "text": "first intent",
            "author": "user1",
            "timestamp": "2026-09-22T10:00:00Z",
        },
        {
            "text": "second intent",
            "author": "user2",
            "timestamp": "2026-09-22T10:01:00Z",
        },
        {
            "text": "third intent",
            "author": "user1",
            "timestamp": "2026-09-22T10:02:00Z",
        },
    ]
    voice_plugin.history_path.write_text(
        "\n".join(json.dumps(i) for i in intents) + "\n",
        encoding="utf-8",
    )

    result = voice_plugin.module.do_voice_last_intent(limit=10)

    assert len(result) == 3
    # Newest first
    assert result[0]["text"] == "third intent"
    assert result[1]["text"] == "second intent"
    assert result[2]["text"] == "first intent"


def test_voice_last_intent_respects_limit(voice_plugin):
    """voice_last_intent respects the limit parameter."""
    intents = [
        {
            "text": f"intent {i}",
            "author": "user",
            "timestamp": f"2026-09-22T10:0{i}:00Z",
        }
        for i in range(5)
    ]
    voice_plugin.history_path.write_text(
        "\n".join(json.dumps(i) for i in intents) + "\n",
        encoding="utf-8",
    )

    result = voice_plugin.module.do_voice_last_intent(limit=2)

    assert len(result) == 2
    # Newest first
    assert result[0]["text"] == "intent 4"
    assert result[1]["text"] == "intent 3"


def test_voice_last_intent_returns_empty_when_no_history(voice_plugin):
    """voice_last_intent returns an empty list when there is no history."""
    result = voice_plugin.module.do_voice_last_intent(limit=10)
    assert result == []


def test_voice_intent_stream_subscribes_to_steer_events(voice_plugin):
    """voice_intent_stream subscribes to estate.agent.sovereign.*.steer."""
    # Add a message to yield
    event = {
        "session_id": "test-session",
        "runtime": "sovereign",
        "kind": "steer",
        "at": "2026-09-22T10:00:00Z",
        "steer": {
            "text": "stop the deploy",
            "author": "founder",
            "confidence": 0.95,
        },
    }
    voice_plugin.bus.messages_to_yield.append(_FakeMessage(json.dumps(event).encode()))

    # Collect yielded intents
    intents = []

    async def collect():
        async for intent in voice_plugin.module.do_voice_intent_stream():
            intents.append(intent)
            break  # Just collect one

    asyncio.run(collect())

    # Check subscription
    assert "estate.agent.sovereign.*.steer" in voice_plugin.bus.subscribed_subjects

    # Check yielded intent
    assert len(intents) == 1
    intent = intents[0]
    assert intent["text"] == "stop the deploy"
    assert intent["author"] == "founder"
    assert intent["session_id"] == "test-session"
    assert intent["timestamp"] == "2026-09-22T10:00:00Z"
    assert intent["confidence"] == 0.95


def test_voice_intent_stream_persists_to_history(voice_plugin):
    """voice_intent_stream writes intents to the history file."""
    event = {
        "session_id": "test-session",
        "runtime": "sovereign",
        "kind": "steer",
        "at": "2026-09-22T10:00:00Z",
        "steer": {"text": "land the commit", "author": "founder"},
    }
    voice_plugin.bus.messages_to_yield.append(_FakeMessage(json.dumps(event).encode()))

    async def collect():
        async for _intent in voice_plugin.module.do_voice_intent_stream():
            break

    asyncio.run(collect())

    # Check history was written
    assert voice_plugin.history_path.exists()
    history = voice_plugin.module.do_voice_last_intent(limit=10)
    assert len(history) == 1
    assert history[0]["text"] == "land the commit"


def test_voice_intent_stream_degrades_when_bus_unavailable(voice_plugin, monkeypatch):
    """No NATS_URL yields an error dict, never crashes."""
    monkeypatch.delenv("NATS_URL", raising=False)

    intents = []

    async def collect():
        async for intent in voice_plugin.module.do_voice_intent_stream(
            cfg={"nats_url": "", "history_path": "", "history_limit": 100}
        ):
            intents.append(intent)

    asyncio.run(collect())

    assert len(intents) == 1
    assert intents[0]["subscribed"] is False
    assert "NATS_URL" in intents[0]["error"]


def test_connect_budget_is_bounded(voice_plugin):
    """A failing connection gives up in seconds, not minutes."""
    asyncio.run(
        voice_plugin.module.do_voice_speak(
            text="test budget",
            voice="af_sky",
            session_id="budget-test",
        )
    )

    asked = voice_plugin.bus.connect_kwargs
    assert asked, "connect called with no options: that is the 120s default"

    attempts = asked["max_reconnect_attempts"]
    wait = asked["reconnect_time_wait"]
    worst_case = attempts * wait

    assert worst_case <= 5.0, (
        f"a failing connection may wait {worst_case}s "
        f"({attempts} attempts x {wait}s); the ceiling is 5s"
    )
    assert asked["connect_timeout"] <= 5.0

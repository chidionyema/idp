"""The voice transport rides the estate bus, and the board no longer dials a port.

WHAT THIS GRADES, AND WHY IT IS NOT A PROXY FOR IT.

Until 2026-09-22 the board's voice control opened `ws://127.0.0.1:8899/voice/stream` straight from
the browser. That worked on exactly one laptop: `localhost:8899` does not exist in the cluster, so
a portal served from anywhere else showed "voice service not reachable on 8899" -- a sentence no
deployed product can contain. The transport moved: MEANING onto the estate bus as
`estate.agent.event` rows, MEDIA over plain HTTP through the Backstage proxy.

Two claims follow from that move, and a comment asserting them is worth nothing, so:

  1. An utterance becomes a row the estate's ONE event contract accepts -- graded by the same
     schema, through the same validator, that `tests/test_estate_agent_event_contract.py` grades
     every other adapter with. Not a shape this test invented and then agreed with.
  2. Nothing in the page's voice code dials a host or opens a socket any more. Checked against the
     source with its comments stripped, because the comments in that file DESCRIBE the old
     `ws://127.0.0.1:8899` dial in order to explain why it is gone -- a scan that counted those
     would be a test that can only fail for the wrong reason.

The event construction under test is the REAL one: `nats_adapter.publish` builds the payload and
the subject, and only the `nats` library beneath it is replaced by a recorder. Stubbing at the
adapter's own boundary instead would have graded a dict this test wrote itself.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import re
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "backstage" / "plugins" / "fleetview-backend" / "src"
HOOK = ROOT / "backstage" / "packages" / "app" / "src" / "modules" / "home" / "useEstateVoice.ts"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# The contract validator, borrowed rather than rewritten: one schema, graded one way. It prefers
# the `jsonschema` library and falls back to the `check-jsonschema` CLI, and raises rather than
# passing when neither is present -- a validator that cannot validate must not report green.
_contract = _load(ROOT / "tests" / "test_estate_agent_event_contract.py", "estate_event_contract")
validate = _contract.validate


class _Recorder:
    """Stands in for the `nats` package, and records what was actually published."""

    def __init__(self) -> None:
        self.published: list[tuple[str, bytes]] = []
        self.drained = False

    # -- the `nats` module surface ------------------------------------------------------------
    async def connect(self, url: str):
        self.url = url
        return self

    # -- the connection surface ---------------------------------------------------------------
    def jetstream(self):
        return self

    async def publish(self, subject: str, payload: bytes):
        self.published.append((subject, payload))

    async def drain(self):
        self.drained = True

    # -- what the test reads ------------------------------------------------------------------
    def one(self) -> tuple[str, dict]:
        assert len(self.published) == 1, f"expected one row on the bus, got {len(self.published)}"
        subject, payload = self.published[0]
        return subject, json.loads(payload.decode())


class _Turn:
    """`turnlog.Turn` as a plain record, so the log's schema is not this test's business."""

    def __init__(self, **fields):
        self.fields = fields


class _Turnlog:
    def __init__(self) -> None:
        self.recorded: list[_Turn] = []
        self.Turn = _Turn

    def record(self, turn: _Turn) -> None:
        self.recorded.append(turn)


@pytest.fixture()
def voice(monkeypatch):
    """`voice_media`, wired to a recording bus and a speech engine that is not the subject here.

    The ASR and TTS models are ~1GB of weights that a test runner has no business loading, and
    what an utterance SOUNDS like is not what this file grades -- the transcript is given, and the
    event it turns into is measured.
    """
    recorder = _Recorder()
    monkeypatch.setitem(sys.modules, "nats", recorder)

    module = _load(SRC / "voice_media.py", "voice_media_under_test")
    # The adapter is loaded through `voice_media`'s own loader, so the module under test reaches
    # the same object this test inspects.
    monkeypatch.setenv("NATS_URL", "nats://nats.event-bus.svc:4222")

    engine = types.SimpleNamespace(ASR_SAMPLE_RATE=16_000, transcribe=lambda pcm: ("", 0.0))
    turnlog = _Turnlog()
    catalogue = types.SimpleNamespace()
    monkeypatch.setattr(module, "_voice_package", lambda: (engine, turnlog, catalogue))

    return types.SimpleNamespace(
        module=module, bus=recorder, engine=engine, turnlog=turnlog
    )


def test_an_utterance_becomes_a_steer_the_contract_accepts(voice):
    """What the founder SAID goes on the bus, in the estate's one schema, attributed."""
    voice.engine.transcribe = lambda pcm: ("stop the harness audit and land the commit", 0.41)

    body, status = asyncio.run(
        voice.module.hear(b"\0" * 64_000, session_id="voice-abc123", author="founder")
    )

    assert status == 200, body
    assert body["text"] == "stop the harness audit and land the commit"
    assert body["bus"]["published"] is True

    subject, event = voice.bus.one()
    # The subject family every other runtime publishes under, with `sovereign` -- where the voice
    # engine lives -- as the runtime. A subject outside `estate.agent.>` would never reach the
    # board's stream, which subscribes to exactly that.
    assert subject == "estate.agent.sovereign.voice-abc123.steer"

    ok, why = validate(event)
    assert ok, f"the utterance is not a row the estate contract accepts: {why}\n{event}"

    # A steer is the contract's word for a human correcting a session mid-flight, and it requires
    # an author for a reason the schema states: "the estate never runs a steer with no attributed
    # author". This is the whole reason an utterance is a steer and not a free-text field.
    assert event["kind"] == "steer"
    assert event["steer"] == {
        "text": "stop the harness audit and land the commit",
        "author": "founder",
    }


def test_the_end_of_a_turn_is_a_done_row_the_contract_accepts(voice):
    """The answer's end closes the session on the bus -- and carries none of its words."""
    body, status = asyncio.run(
        voice.module.answered(
            {
                "session_id": "voice-abc123",
                "asr_seconds": 0.41,
                "first_clause_seconds": 1.2,
                "total_seconds": 3.4,
                "tts_seconds": 1.1,
                "words": 7,
                "clauses": 2,
                "engine": "piper",
                "voice": "en_GB-jenny_dioco-medium",
                "outcome": "ok",
            }
        )
    )

    assert status == 200, body
    assert body["recorded"] is True
    assert len(voice.turnlog.recorded) == 1
    assert voice.turnlog.recorded[0].fields["llm_first_s"] == 1.2

    subject, event = voice.bus.one()
    assert subject == "estate.agent.sovereign.voice-abc123.done"
    ok, why = validate(event)
    assert ok, f"the end of a turn is not a row the estate contract accepts: {why}\n{event}"
    assert event["kind"] == "done"
    assert event["phase"] == "done"
    # THE ANSWER'S TEXT IS NOT ON THE BUS. The contract's one free-text target field names "a
    # file, command or URL target, NEVER its output", and a spoken reply is output. It is in the
    # turn log, which is what `answered` also writes.
    assert "tool" not in event


def test_an_unattributed_utterance_never_reaches_the_bus(voice):
    """The refusal is the point: a steer with no author is not published and then apologised for."""
    voice.engine.transcribe = lambda pcm: ("land the commit", 0.4)

    body, status = asyncio.run(
        voice.module.hear(b"\0" * 64_000, session_id="voice-abc123", author="")
    )

    assert status == 400
    assert "author" in body["error"]
    assert voice.bus.published == [], "an unattributed utterance reached the bus"


def test_an_empty_transcript_is_counted_not_published(voice):
    """Hearing nothing is a friction measurement, not an event about a session."""
    voice.engine.transcribe = lambda pcm: ("", 0.33)

    body, status = asyncio.run(
        voice.module.hear(b"\0" * 64_000, session_id="voice-abc123", author="founder")
    )

    assert status == 200
    assert body["empty"] is True
    assert voice.bus.published == [], "an utterance nobody could make out was published as a steer"
    assert voice.turnlog.recorded[0].fields["outcome"] == "empty"


def test_a_host_off_the_bus_says_so_rather_than_pretending(voice, monkeypatch):
    """No NATS_URL is a named degradation carried in the reply, never a silent success."""
    monkeypatch.delenv("NATS_URL", raising=False)
    voice.engine.transcribe = lambda pcm: ("land the commit", 0.4)

    body, status = asyncio.run(
        voice.module.hear(b"\0" * 64_000, session_id="voice-abc123", author="founder")
    )

    assert status == 200
    assert body["bus"]["published"] is False
    assert "NATS_URL" in body["bus"]["reason"]
    assert voice.bus.published == []


# ---------------------------------------------------------------------------------------------
# The page.
# ---------------------------------------------------------------------------------------------


def _code_without_comments(source: str) -> str:
    """The file's CODE. Its comments describe the dial that was removed and must not be scanned."""
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
    return "\n".join(re.sub(r"(^|\s)//.*$", "", line) for line in source.splitlines())


@pytest.mark.parametrize(
    ("needle", "why"),
    [
        ("8899", "the voice port -- a port that exists on one laptop and nowhere in the cluster"),
        ("new WebSocket", "an upgrade the Backstage proxy cannot carry"),
        ("127.0.0.1", "a host that is the browser's own machine, not the estate's"),
        ("localhost", "the same host by its other name"),
        ("EventSource", "an SSE client that cannot send the proxy's Authorization header"),
    ],
)
def test_the_page_does_not_dial_anything(needle, why):
    code = _code_without_comments(HOOK.read_text(encoding="utf-8"))
    assert needle not in code, f"useEstateVoice.ts still reaches for {needle}: {why}"


def test_the_page_talks_to_the_backend_through_the_proxy():
    """Every data call names the proxy, and the assets come from the app's own origin."""
    code = _code_without_comments(HOOK.read_text(encoding="utf-8"))
    assert "plugin://proxy/fleetview" in code
    # `fetchApi.fetch` is what attaches the token; a bare `fetch` would arrive unauthenticated and
    # the proxy answers 401 -- measured 2026-09-22 against a running backend.
    assert "fetchApi.fetch" in code
    assert code.count("await fetch(") == 0, "a raw fetch would reach the proxy with no credentials"

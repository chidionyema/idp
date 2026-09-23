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
HOOK = (
    ROOT
    / "backstage"
    / "packages"
    / "app"
    / "src"
    / "modules"
    / "home"
    / "useEstateVoice.ts"
)


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _load_pkg_member(path: Path, name: str, pkg_name: str):
    """Same as _load but registers the module as a member of `pkg_name` so relative
    imports inside it (e.g. `from . import tracing`) resolve. Used for files inside
    backstage/plugins/fleetview-backend/src/ whose imports are relative to src/."""
    import types as _types

    if pkg_name not in sys.modules:
        sys.modules[pkg_name] = _types.ModuleType(pkg_name)
    full = f"{pkg_name}.{name}"
    spec = importlib.util.spec_from_file_location(full, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    module.__package__ = pkg_name
    sys.modules[full] = module
    spec.loader.exec_module(module)
    return module


# The contract validator, borrowed rather than rewritten: one schema, graded one way. It prefers
# the `jsonschema` library and falls back to the `check-jsonschema` CLI, and raises rather than
# passing when neither is present -- a validator that cannot validate must not report green.
_contract = _load(
    ROOT / "tests" / "test_estate_agent_event_contract.py", "estate_event_contract"
)
validate = _contract.validate


class _Recorder:
    """Stands in for the `nats` package, and records what was actually published."""

    def __init__(self) -> None:
        self.published: list[tuple[str, bytes]] = []
        self.drained = False
        self.connect_kwargs: dict = {}
        self.streams: list[dict] = []

    # -- the `nats` module surface ------------------------------------------------------------
    async def connect(self, url: str, **kwargs):
        # The kwargs are recorded, not ignored: the retry budget the adapter asks for is the
        # difference between a 1.6-second voice turn and a 127-second one, so it is graded.
        self.url = url
        self.connect_kwargs = kwargs
        return self

    # -- the connection surface ---------------------------------------------------------------
    def jetstream(self):
        return self

    async def publish(self, subject: str, payload: bytes):
        self.published.append((subject, payload))

    async def add_stream(self, **config):
        # A JetStream server refuses a duplicate stream name with "stream name already in
        # use" -- the fake raises the same words, so the adapter's idempotence is graded
        # against the real refusal rather than a happy path that never re-provisions.
        if any(s["name"] == config["name"] for s in self.streams):
            raise RuntimeError("stream name already in use")
        self.streams.append(config)

    async def drain(self):
        self.drained = True

    # -- what the test reads ------------------------------------------------------------------
    def one(self) -> tuple[str, dict]:
        assert len(self.published) == 1, (
            f"expected one row on the bus, got {len(self.published)}"
        )
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

    module = _load_pkg_member(
        SRC / "tracing.py", "tracing", "fleetview_backend_src_under_test"
    )
    module = _load_pkg_member(
        SRC / "voice_media.py", "voice_media", "fleetview_backend_src_under_test"
    )
    # The adapter is loaded through `voice_media`'s own loader, so the module under test reaches
    # the same object this test inspects.
    monkeypatch.setenv("NATS_URL", "nats://nats.event-bus.svc:4222")

    engine = types.SimpleNamespace(
        ASR_SAMPLE_RATE=16_000, transcribe=lambda pcm: ("", 0.0)
    )
    turnlog = _Turnlog()
    catalogue = types.SimpleNamespace()
    monkeypatch.setattr(module, "_voice_package", lambda: (engine, turnlog, catalogue))

    return types.SimpleNamespace(
        module=module, bus=recorder, engine=engine, turnlog=turnlog
    )


def test_an_utterance_becomes_a_steer_the_contract_accepts(voice):
    """What the founder SAID goes on the bus, in the estate's one schema, attributed."""
    voice.engine.transcribe = lambda pcm: (
        "stop the harness audit and land the commit",
        0.41,
    )

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
    assert ok, (
        f"the end of a turn is not a row the estate contract accepts: {why}\n{event}"
    )
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
    assert voice.bus.published == [], (
        "an utterance nobody could make out was published as a steer"
    )
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
        (
            "8899",
            "the voice port -- a port that exists on one laptop and nowhere in the cluster",
        ),
        ("new WebSocket", "an upgrade the Backstage proxy cannot carry"),
        ("127.0.0.1", "a host that is the browser's own machine, not the estate's"),
        ("localhost", "the same host by its other name"),
        (
            "EventSource",
            "an SSE client that cannot send the proxy's Authorization header",
        ),
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
    assert code.count("await fetch(") == 0, (
        "a raw fetch would reach the proxy with no credentials"
    )


def test_a_steer_reaches_the_durability_boundary_not_just_the_response(
    voice, monkeypatch, tmp_path
):
    """/voice/steer's 200 is a PROMISE: the intent is in SQLite, durable against this process.

    This test exists because the failure mode SHIPPED (2026-09-22): outbox.py imported
    tracing package-relatively while every loader in the estate loads outbox.py without a
    package, so the import raised, steer() returned 500 at the durability boundary, and the
    FastAPI lifespan swallowed the same error around start_worker -- the drain never ran
    either. No test noticed, because none graded the row the endpoint promises to have
    written. A green 200 with no row behind it is ghost code; this is the gate.
    """
    monkeypatch.setenv("OUTBOX_DB_PATH", str(tmp_path / "outbox.db"))
    body = {
        "action": "steer",
        "confidence": 0.92,
        "session_id": "steer-durability-1",
        "author": "founder",
        "target": "agent #bf061c",
        "transcript": "stop the harness audit and land the commit",
    }

    accepted, status = asyncio.run(voice.module.steer(body))

    assert status == 200, accepted
    assert accepted["accepted"] is True
    assert accepted["outbox_id"], (
        "a 200 with no outbox row id is the ghost this test refuses"
    )

    # THE ROW IS THE CLAIM. What is graded is the durable side effect, not the response shape.
    outbox = voice.module._outbox()
    rows = outbox.recent(limit=5)
    assert rows, (
        "steer returned 200 but the outbox is empty: the intent was never durable"
    )
    row = rows[0]
    assert row["status"] == "pending", f"a fresh intent is pending, not {row['status']}"
    assert row["session_id"] == "steer-durability-1"
    assert row["kind"] == "steer"
    assert row["phase"] == "executing"
    assert row["id"] == accepted["outbox_id"]


def test_the_first_caller_provisions_the_stream_with_the_outboxs_15_minute_ttl(voice):
    """The bus has a stream, or nothing published to it can ever be replayed.

    Until 2026-09-22 no code in the estate created the JetStream stream: the chart provisions
    a capable server, `js.publish` to an uncovered subject is a 503, and the stream that
    existed on the cluster had been created by hand -- configuration that lived in nobody's
    checkout. The adapter now provisions it on first publish, and WHAT IS GRADED is the
    whole provisioning, not just that it happened:

      * the name and subjects, so the board's `estate.agent.>` subscription is covered;
      * the TTL, so the stream does not faithfully replay intents the outbox deliberately
        dropped: the number here must equal outbox.py's TTL_S, the drain-side expiry, or the
        two ends of the pipeline would disagree about what is stale;
      * idempotence: the second publish meets the server's real "already in use" refusal
        (the fake raises the same words) and must swallow exactly that and nothing else.
    """
    adapter = voice.module._nats()

    async def _publish_once(session: str) -> None:
        await adapter.publish(
            "nats://nats.event-bus.svc:4222",
            session_id=session,
            runtime="sovereign",
            kind="steer",
            phase="executing",
            steer={"text": "provision the bus", "author": "founder"},
        )

    asyncio.run(_publish_once("voice-provision-1"))
    assert len(voice.bus.streams) == 1, "first publish must provision the stream"
    cfg = voice.bus.streams[0]
    assert cfg["name"] == "ESTATE_AGENT"
    assert cfg["subjects"] == ["estate.agent.>"]
    # The TTL agreement, graded against the drain-side constant rather than a literal twice:
    outbox = voice.module._outbox()
    assert cfg["max_age"] == outbox.TTL_S * 1_000_000_000, (
        f"stream max_age {cfg['max_age']}ns does not match outbox TTL_S {outbox.TTL_S}s: "
        "the stream would replay intents the outbox expired, or drop ones it kept"
    )

    # Idempotence: the second publish meets "already in use" and must not raise or re-provision.
    asyncio.run(_publish_once("voice-provision-2"))
    assert len(voice.bus.streams) == 1, (
        "second publish re-provisioned or failed the stream"
    )
    assert len(voice.bus.published) == 2, "both publishes must still land on the bus"


def test_a_failing_publish_gives_up_in_a_second_not_two_minutes(voice):
    """The bus may be down; a person waiting to be heard may not pay for that.

    THIS TEST EXISTS BECAUSE THE DEFECT SHIPPED. nats-py's connect() defaults are tuned for a
    long-lived service connection -- max_reconnect_attempts=60 with reconnect_time_wait=2 -- and
    `publish` opens a connection for one event and drains it, so it inherited a 120-second retry
    budget it can never use. Measured 2026-09-22 on one /voice/hear request with 2.36s of speech:

        NATS_URL unreachable, stock defaults .... 127.00s   (asr 6.4s, the rest waiting)
        NATS_URL unset ..........................   4.10s
        NATS_URL unreachable, bounded budget ....   1.60s

    The transcript was byte-identical in all three. The turn was never broken -- it was correct
    and 79x too slow, which is the failure mode that does not announce itself.

    WHAT IS GRADED is the budget the adapter ASKS FOR, because that is the defect: the product of
    attempts and the wait between them is the worst case a caller can be made to wait, and the
    stock values multiply to 120s. A ceiling of 5s is far above the 0.39s a refused port and the
    0.17s an unresolvable name actually measured, and far below the two minutes that shipped.
    Delete the options and this fails at 120s, which is the point -- a gate that cannot fail is
    not a gate.
    """
    adapter = voice.module._nats()
    asyncio.run(
        adapter.publish(
            "nats://nats.event-bus.svc:4222",
            session_id="voice-budget",
            runtime="sovereign",
            kind="steer",
            phase="executing",
            steer={"text": "how long will you make me wait", "author": "founder"},
        )
    )

    asked = voice.bus.connect_kwargs
    assert asked, "publish called connect() with no options: that is the 120s default"

    attempts = asked["max_reconnect_attempts"]
    wait = asked["reconnect_time_wait"]
    worst_case = attempts * wait
    assert worst_case <= 5.0, (
        f"a failing publish may wait {worst_case}s "
        f"({attempts} attempts x {wait}s); the ceiling is 5s"
    )
    # connect_timeout bounds a single attempt that hangs rather than refusing -- a black-holed
    # address, which neither measurement above covers, so it is required but not timed here.
    assert asked["connect_timeout"] <= 5.0

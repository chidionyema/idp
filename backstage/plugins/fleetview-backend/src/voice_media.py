"""Voice media, through the door the board already uses -- and every turn onto the estate bus.

WHAT THIS REPLACES, AND WHY IT HAD TO GO.

`sovereign/voice/server.py` ran a second transport: the browser opened a WebSocket straight to
`http://127.0.0.1:8899` and pushed microphone PCM down it. `useEstateVoice.ts` carried the
hard-coded origin and a comment justifying it -- "Backstage's proxy is HTTP-only and cannot carry
an upgrade" -- which is true about upgrades and wrong about the conclusion. The board's live feed
already crosses that same proxy as Server-Sent Events, so the proxy was never the obstacle; the
WebSocket was a choice.

The cost of that choice is that `localhost:8899` DOES NOT EXIST IN THE CLUSTER. A browser loading
the portal from the cluster has no such port, so the voice half of the board could only ever work
on one laptop, with one process a person had started by hand -- and when that process was not
running, the board said "voice service not reachable on 8899", which is a sentence no deployed
product can contain. Two transports, one of which cannot be deployed, is the duplicate layer the
estate deletes (AGENTS.md: one of each layer; a second copy is stitching).

SO THE TRANSPORT SPLITS ALONG THE SEAM IT SHOULD ALWAYS HAVE HAD:

  MEANING goes on the bus. Each utterance is an `estate.agent.event` with kind=steer -- which is
  exactly what the contract already calls a human correcting a session mid-flight, with `text` and
  an attributed `author`. The answer's completion is a kind=done row. Both land on
  `estate.agent.sovereign.<session>.<kind>`, so what the founder SAID is on the same bus, in the
  same schema, as what every agent is doing -- and the board's existing `/stream` SSE carries it
  to the page with no new channel.

  MEDIA goes over plain HTTP through the Backstage proxy: `POST /voice/hear` takes one utterance
  of PCM and returns what it heard, `POST /voice/say` takes a clause and returns the audio for it.
  Neither needs an upgrade, so both proxy, so both work in the cluster.

WHAT STAYED PUT. The brain is `voice.py`'s `/voice/stream`, which was already here, already
proxied, and already prompted with the same fleet state `/sessions` serves. Adding a second
question-answering path would have been another duplicate; the browser now asks the one that
existed.

THE BUS IS BEST-EFFORT, AND SAYS SO. A publish that cannot reach NATS returns its reason in the
envelope (`bus.published: false`, `bus.reason`) rather than failing the turn or -- worse --
succeeding quietly. A laptop with no NATS_URL is not attached to the estate bus, and that is a
fact the caller can read, not a fault to hide.

CONFIG (LAW 46): NATS_URL (unset = not attached to the bus), plus everything
`sovereign/voice/engine.py` reads for the models themselves.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import jsonschema

from . import tracing

# The repo root, from this file's own location rather than the process's working directory:
# src -> fleetview-backend -> plugins -> backstage -> <repo>. The same `parents[4]` reach
# routes.py uses for platform/intent/observer.py.
_REPO_ROOT = Path(__file__).resolve().parents[4]

_NATS_ADAPTER_MODULE = Path(__file__).resolve().parent / "nats_adapter.py"
_OUTBOX_MODULE = Path(__file__).resolve().parent / "outbox.py"
_INTENT_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "intent-v2.json"

# Cached intent schema — loaded once per process.
_intent_schema: dict | None = None

# The runtime name this transport emits under. `sovereign` is in the contract's enum
# (platform/event-bus/contract/estate.agent.event.json) and is where the voice engine lives.
RUNTIME = "sovereign"

# One fixed sentence for a voice audition, long enough to hear a voice's rhythm and not just its
# timbre.
PREVIEW_TEXT = (
    "Four agents are stuck, all paused. Two on the harness audit, two on the commit."
)

# The first half of every refusal from an engine that cannot run where it was asked to. The second
# half is the exception itself, because "no module named numpy" tells a reader what is missing and
# "voice is unavailable" does not.
#
# IT NAMES THE SELECTED ENGINE, NOT THE SERVICE. Measured 2026-09-22 on this laptop: `say` returns
# 182796 bytes of audio in 1.7s while `piper` raises ModuleNotFoundError for numpy and `kokoro`
# answers 503 -- one host, one service, three engines, two of them dead. A refusal that said
# "voice is not installed here" would be false, and would send a reader to install a gigabyte of
# weights when switching engine is the fix.
_ENGINE_ABSENT = "this voice engine cannot run on this host (try another engine)"


def _voice_package():
    """`sovereign.voice` as a real package import, not a path-load.

    Every other module beside this one is reached by `spec_from_file_location`, because they are
    siblings that are not a package. `sovereign.voice` IS a package (it has `__init__.py` and its
    modules import each other relatively), so it is imported normally with the repo root on
    `sys.path` -- and that matters beyond tidiness: a path-load would give this process a SECOND
    copy of `engine`, with its own model cache and its own selected voice, so choosing a voice on
    one route would not change the voice another route speaks with.
    """
    root = str(_REPO_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    from sovereign.voice import catalogue, engine, turnlog  # noqa: PLC0415

    return engine, turnlog, catalogue


def _nats():
    spec = importlib.util.spec_from_file_location(
        "fleetview_nats_adapter_impl", _NATS_ADAPTER_MODULE
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module at {_NATS_ADAPTER_MODULE}")
    cached = sys.modules.get("fleetview_nats_adapter_impl")
    if cached is not None:
        return cached
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _outbox():
    spec = importlib.util.spec_from_file_location(
        "fleetview_outbox_impl", _OUTBOX_MODULE
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module at {_OUTBOX_MODULE}")
    cached = sys.modules.get("fleetview_outbox_impl")
    if cached is not None:
        return cached
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _get_intent_schema() -> dict:
    """Load and cache the intent-v2 JSON schema."""
    global _intent_schema
    if _intent_schema is not None:
        return _intent_schema
    if not _INTENT_SCHEMA_PATH.is_file():
        raise RuntimeError(f"intent schema not found at {_INTENT_SCHEMA_PATH}")
    with open(_INTENT_SCHEMA_PATH) as f:
        _intent_schema = json.load(f)
    return _intent_schema


def _nats_url() -> str:
    return os.environ.get("NATS_URL", "")


async def publish(
    session_id: str, kind: str, phase: str, **fields: Any
) -> dict[str, Any]:
    """Put one row on the estate bus, and report honestly whether it landed.

    NEVER RAISES. A voice turn is a conversation with a person; losing the bus must not lose the
    conversation. But it must not be silent either -- the returned dict is carried in the route's
    envelope, so "the bus did not take this" is something the caller can see and the board can
    say, which is the difference between degraded and broken.
    """
    url = _nats_url()
    if not url:
        return {
            "published": False,
            "reason": "NATS_URL is unset: this process is not attached to the estate bus",
        }
    try:
        await _nats().publish(
            url,
            session_id=session_id,
            runtime=RUNTIME,
            kind=kind,
            phase=phase,
            **fields,
        )
    except Exception as exc:  # noqa: BLE001 -- the reason is reported, never swallowed
        return {"published": False, "reason": f"{exc.__class__.__name__}: {exc}"}
    return {"published": True, "subject": f"estate.agent.{RUNTIME}.{session_id}.{kind}"}


async def steer(
    body: dict[str, Any], trace_context: dict[str, str] | None = None
) -> tuple[dict[str, Any], int]:
    """Receive a validated JSON intent from the browser, write to outbox, return instantly.

    THE SERVER RECEIVES ONLY THE INTENT, NEVER AUDIO OR TRANSCRIPT. The browser runs inference
    (the edge-compute goal, ADR 0033); this endpoint receives the result, validates it against
    a strict JSON schema, and writes it to an SQLite WAL buffer. The response returns in <50ms,
    before any NATS publish attempt.

    WHY AN OUTBOX. NATS can be unreachable — the cluster is down, the laptop is offline, the
    network blipped. The outbox decouples acceptance from delivery: the intent is durable the
    moment the 200 leaves the wire. A background worker drains to NATS on `estate.agent.
    sovereign.<session_id>.steer` with a 15-minute JetStream TTL.

    VALIDATION IS STRICT. `additionalProperties: false` in the schema means any field not in
    the schema is a rejection. This is deliberate: the browser's model can hallucinate fields,
    and the server must refuse them rather than silently passing garbage onto the bus.

    THE AUTHOR IS REQUIRED and overridden by the server from the authenticated session — the
    value in the payload is IGNORED. A steer with no attributed author is refused at the schema
    level (it is in `required`), but even if it were present, the server would replace it with
    the authenticated identity. The same discipline `hear` applies: "a steer with no attributed
    author is refused" is estate law, not a client convention.

    TRACING: If trace_context is provided (from HTTP headers), the span continues the browser's
    trace. The trace context is propagated to the outbox and onto the NATS message.
    """
    started = time.time()

    # Extract and attach trace context from the browser if provided.
    ctx = tracing.extract_context(trace_context) if trace_context else None

    with tracing.with_context(ctx):
        with tracing.server_span(
            "voice.receive",
            {
                "voice.endpoint": "/voice/steer",
                "voice.session_id": body.get("session_id", ""),
            },
        ) as receive_span:
            # Validate against the strict schema.
            validate_start = time.time()
            with tracing.span(
                "voice.validate", {"voice.schema": "intent-v2"}
            ) as validate_span:
                try:
                    schema = _get_intent_schema()
                    jsonschema.validate(instance=body, schema=schema)
                    validate_ms = round((time.time() - validate_start) * 1000, 1)
                    if validate_span:
                        validate_span.set_attribute(
                            "voice.validation.duration_ms", validate_ms
                        )
                        validate_span.set_attribute("voice.validation.success", True)
                except jsonschema.ValidationError as exc:
                    # Return a clear error: the path to the invalid field and what was wrong.
                    path = ".".join(str(p) for p in exc.absolute_path) or "(root)"
                    if validate_span:
                        validate_span.set_attribute("voice.validation.success", False)
                        validate_span.set_attribute(
                            "voice.validation.error", exc.message
                        )
                    return {
                        "error": "schema validation failed",
                        "path": path,
                        "message": exc.message,
                    }, 400
                except Exception as exc:  # noqa: BLE001 — schema load failure is a 500
                    if validate_span:
                        validate_span.set_attribute("voice.validation.success", False)
                        validate_span.set_attribute("voice.validation.error", str(exc))
                    return {"error": f"schema load failed: {exc}"}, 500

            session_id = str(body.get("session_id") or "").strip()
            # Author comes from the authenticated session, not the payload — but the schema requires it,
            # so we check that the caller at least provided SOMETHING. The actual value will be overridden
            # at the route level with the authenticated identity.
            author = str(body.get("author") or "").strip()
            if not session_id:
                return {"error": "session_id is required"}, 400
            if not author:
                return {
                    "error": "author is required: a steer with no attributed author is refused"
                }, 400

            # The payload for the bus: everything except session_id (which is in the subject).
            # We build the steer object the same way `hear` does.
            steer_payload = {
                "action": body.get("action"),
                "steer": {
                    "text": body.get("transcript") or f"[intent: {body.get('action')}]",
                    "author": author,
                },
            }
            if body.get("target"):
                steer_payload["target"] = body["target"]
            if body.get("env"):
                steer_payload["env"] = body["env"]
            if body.get("confidence") is not None:
                steer_payload["confidence"] = body["confidence"]
            if body.get("partial"):
                steer_payload["partial"] = body["partial"]

            # Propagate trace context to the outbox for NATS message headers.
            trace_headers = tracing.get_current_trace_context()
            if trace_headers:
                steer_payload["_trace_context"] = trace_headers

            # Write to the outbox — this is the durability boundary.
            outbox = _outbox()
            with tracing.span(
                "voice.outbox.write", {"voice.session_id": session_id}
            ) as outbox_span:
                try:
                    row_id = outbox.enqueue(
                        session_id=session_id,
                        runtime=RUNTIME,
                        kind="steer",
                        phase="executing",
                        payload=steer_payload,
                    )
                    if outbox_span:
                        outbox_span.set_attribute("voice.outbox.row_id", row_id)
                        outbox_span.set_attribute(
                            "voice.action", body.get("action", "")
                        )
                except Exception as exc:  # noqa: BLE001 — outbox failure is the one thing that is fatal
                    if outbox_span:
                        outbox_span.set_attribute("voice.outbox.error", str(exc))
                    return {"error": f"outbox write failed: {exc}"}, 500

            elapsed_ms = round((time.time() - started) * 1000, 1)
            if receive_span:
                receive_span.set_attribute("voice.elapsed_ms", elapsed_ms)
                receive_span.set_attribute("voice.outbox.row_id", row_id)

            return {
                "accepted": True,
                "outbox_id": row_id,
                "session_id": session_id,
                "action": body.get("action"),
                "elapsed_ms": elapsed_ms,
            }, 200


async def hear(pcm: bytes, session_id: str, author: str) -> tuple[dict[str, Any], int]:
    """One utterance of 16kHz float32 PCM in; what was heard out, and a steer row on the bus.

    THE AUTHOR IS REQUIRED, and the refusal is deliberate: the contract's `steer` object requires
    `author` because "the estate never runs a steer with no attributed author". A voice turn is
    the most attributable thing in the estate -- someone spoke it aloud -- so there is no case
    where the name is unavailable and no default that would be true.

    AN EMPTY TRANSCRIPT IS NOT AN ERROR, IT IS THE FRICTION ITSELF. The person spoke and nothing
    came back; that is the thing behind "I had to say it three times", so it is recorded as a turn
    with outcome=empty and answered 200 with `empty: true`. A 4xx here would put a normal, common
    event in the error path and out of the friction numbers.
    """
    engine, turnlog, _catalogue = _voice_package()
    session_id = (session_id or "").strip()
    author = (author or "").strip()
    if not session_id:
        return {"error": "session_id is required"}, 400
    if not author:
        return {
            "error": "author is required: a steer with no attributed author is refused"
        }, 400
    if not pcm:
        return {"error": "no audio in the request body"}, 400

    started = time.time()
    loop = asyncio.get_running_loop()
    # In a thread: transcription is CPU-bound and blocks. On the event loop it would stall every
    # other request in this process for the length of the utterance, including the board's SSE.
    try:
        transcript, asr_seconds = await loop.run_in_executor(
            None, engine.transcribe, pcm
        )
    except Exception as exc:  # noqa: BLE001 - see `say`: the reason is the product here
        return {"error": f"{_ENGINE_ABSENT}: {type(exc).__name__}: {exc}"}, 502
    audio_seconds = round(len(pcm) / 4 / engine.ASR_SAMPLE_RATE, 2)

    if not transcript:
        turnlog.record(
            turnlog.Turn(
                started=started,
                asr_s=asr_seconds,
                words=0,
                session_id=session_id,
                outcome="empty",
                detail=f"{audio_seconds}s of audio produced no words",
            )
        )
        return {
            "empty": True,
            "text": "",
            "asr_seconds": asr_seconds,
            "audio_seconds": audio_seconds,
        }, 200

    bus = await publish(
        session_id,
        kind="steer",
        phase="executing",
        steer={"text": transcript, "author": author},
    )
    return {
        "empty": False,
        "text": transcript,
        "asr_seconds": asr_seconds,
        "audio_seconds": audio_seconds,
        "received_seconds": round(time.time() - started, 3),
        "bus": bus,
    }, 200


async def say(text: str) -> tuple[bytes | None, str | None]:
    """One clause of text to 24kHz float32 PCM in the voice that is currently live.

    Returns (pcm, None) or (None, reason). A clause at a time rather than a whole answer, because
    the browser schedules each one on its AudioContext clock as it lands -- the same shape the old
    socket sent, so the playback path on the page did not have to change when the transport did.
    """
    engine, _turnlog, _catalogue = _voice_package()
    text = (text or "").strip()
    if not text:
        return None, "text is required"
    loop = asyncio.get_running_loop()
    try:
        pcm = await loop.run_in_executor(None, engine.synthesise, text)
    except Exception as exc:  # noqa: BLE001 - the reason is the product here
        # A HOST WITHOUT THE MODELS IS A NAMED REFUSAL, NOT A 500.
        #
        # Measured 2026-09-22 on this laptop: the interpreter that runs this service has no
        # `numpy`, so Piper raised ModuleNotFoundError out of the executor and the route answered
        # `500 Internal Server Error` with a traceback in the log and twenty-one bytes of nothing
        # on the page. The engine's absence is a FACT ABOUT THE HOST -- true of any checkout
        # without the ~1GB of ASR/TTS weights -- and the caller can only act on it if it is told,
        # so it comes back as a sentence a person can read.
        return None, f"{_ENGINE_ABSENT}: {type(exc).__name__}: {exc}"
    if not pcm:
        return None, "synthesis produced no audio on this host"
    return pcm, None


async def answered(body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """The turn ended: write it to the friction log and close it on the bus with a kind=done row.

    WHY THE BROWSER REPORTS THE TIMINGS. The socket measured them server-side, which was the only
    place it could. Split across HTTP, the numbers that matter are the ones on the page: the
    person experiences "how long until it started answering" at the speaker, after the request,
    the proxy and the audio scheduler -- so the browser's clock is not a worse measurement of the
    friction than the server's, it is the right one. The server-measured ASR time comes back from
    `hear` and is passed through here, so both halves of the turn are recorded in one row.

    THE DONE ROW CARRIES NO ANSWER TEXT, on purpose. The event contract is
    `additionalProperties: false` and says of the one free-text field that it names "a file,
    command or URL target, NEVER its output". A bus row says what a session is doing; the words it
    said belong in the turn log, which is what this also writes.
    """
    _engine, turnlog, _catalogue = _voice_package()
    session_id = str(body.get("session_id") or "").strip()
    if not session_id:
        return {"error": "session_id is required"}, 400

    def _num(key: str) -> float | None:
        value = body.get(key)
        try:
            return None if value is None else round(float(value), 3)
        except (TypeError, ValueError):
            return None

    total = _num("total_seconds")
    turnlog.record(
        turnlog.Turn(
            # The turn STARTED when the person stopped speaking, which is `total_seconds` ago.
            # Recording `now` instead would date every turn at the moment it finished and make a
            # slow turn indistinguishable from a late one.
            started=time.time() - (total or 0.0),
            asr_s=_num("asr_seconds"),
            llm_first_s=_num("first_clause_seconds"),
            llm_total_s=total,
            tts_s=_num("tts_seconds") or 0.0,
            words=int(body.get("words") or 0),
            clauses=int(body.get("clauses") or 0),
            engine=str(body.get("engine") or ""),
            voice=str(body.get("voice") or ""),
            session_id=session_id,
            outcome=str(body.get("outcome") or "ok"),
            detail=str(body.get("detail") or ""),
        )
    )
    bus = await publish(session_id, kind="done", phase="done")
    return {"recorded": True, "bus": bus}, 200


async def preview(
    want_engine: str, want_voice: str, text: str
) -> tuple[bytes | None, str | None]:
    """Audition a voice without making it live. See `catalogue.preview`."""
    _engine, _turnlog, catalogue = _voice_package()
    loop = asyncio.get_running_loop()
    sample = (text or "").strip() or PREVIEW_TEXT
    try:
        return await loop.run_in_executor(
            None, catalogue.preview, want_engine, want_voice, sample
        )
    except Exception as exc:  # noqa: BLE001 - see `say`: a host without the models says so
        return None, f"{_ENGINE_ABSENT}: {type(exc).__name__}: {exc}"


async def voices() -> dict[str, Any]:
    """Every voice this host can speak with. One catalogue, shared with the CLI and the page.

    IN A THREAD, THOUGH IT ONLY LISTS STRINGS. `catalogue()` asks `engine.models()` which engine
    is live, and on a host that HAS the speech models the first such call in a process loads
    faster-whisper -- 89.5s cumulative, the figure `sovereign/voice/engine.py` records in its own
    header. On the event loop that would freeze every other route in this service, including the
    board's own SSE, for a minute and a half the first time a picker opened.

    (On a host WITHOUT them this route is fast and still correct -- measured 2026-09-22 on this
    laptop at 1.5s for 81 voices -- because the catalogue is built from `say -v ?` and the voice
    archive's member list, neither of which needs the model loaded.)
    """
    _engine, _turnlog, catalogue = _voice_package()
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, catalogue.catalogue)


async def select(want_engine: str, want_voice: str) -> tuple[dict[str, Any], int]:
    """Switch the live voice. Run in a thread: the first Kokoro selection loads a 350MB model."""
    _engine, _turnlog, catalogue = _voice_package()
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, catalogue.select, want_engine, want_voice)


def log(limit: int = 50) -> dict[str, Any]:
    """Every voice turn, newest first -- the instrument for latency and friction.

    WHY IT EXISTS. The founder, 2026-09-20: "often i have to repeat myself many times -- you need
    to have logs so you can monitor the latency and friction of all voice comms". Nothing recorded
    a turn before that; nothing would read the record if this route did not cross the proxy.
    """
    _engine, turnlog, _catalogue = _voice_package()
    return {"turns": turnlog.recent(limit)}


def log_summary(limit: int = 200) -> dict[str, Any]:
    """The friction numbers: empty rate, median first-clause latency, per-voice speed."""
    _engine, turnlog, _catalogue = _voice_package()
    return turnlog.summary(limit)

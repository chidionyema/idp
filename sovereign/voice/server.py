"""The voice socket: one WebSocket per conversation, full duplex, interruptible.

THE PROTOCOL, and why each message exists:

  browser → server   BINARY   one utterance of 16kHz float32 PCM, sent when the VAD says speech
                              ENDED. The browser does the voice-activity detection because it is
                              free there and costs the estate CPU here -- and because a server
                              that listens to silence burns a core per idle caller.
  browser → server   TEXT     "barge_in". The person started talking over the answer. The server
                              cancels the in-flight task so the model stops generating and the
                              remaining audio is never sent. Without this the reply talks over
                              the interruption, which is the single most robotic thing a voice
                              interface can do.
  server → browser   TEXT     a JSON line: {"type":"transcript"|"clause"|"done"|"error", ...}.
                              Text frames carry the words, so a browser that cannot decode audio
                              still shows the conversation.
  server → browser   BINARY   24kHz float32 PCM for one clause. The browser schedules these
                              back-to-back on its own AudioContext clock.

WHY AUDIO AND TEXT ARE SEPARATE FRAMES rather than audio with a header: the browser needs to
schedule audio the instant it lands, and parsing a header first would put JSON decoding in the
playback path. It also means a dropped audio frame degrades to a missing clause, not a corrupt
stream.
"""

from __future__ import annotations

import asyncio
import json
import os
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from . import catalogue, engine, turnlog

app = FastAPI(title="sovereign voice")

# CORS FOR THE BACKSTAGE ORIGIN, because the voice socket cannot go through Backstage's proxy.
#
# Backstage's proxy-backend (0.6.16) is HTTP-only: it forwards requests, not upgrades, so a
# WebSocket to /voice/stream cannot be proxied the way /fleetview is. The Reactor therefore dials
# this process directly, which makes it a cross-origin call from localhost:3100, and without these
# headers the browser blocks it before a single frame moves.
#
# The allowed origins are LOOPBACK ONLY. This is a local development service; opening it to `*`
# would let any page in the browser open a microphone-bearing socket to the estate's voice engine.
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3100",
        "http://127.0.0.1:3100",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

# THE VAD AND ONNX ASSETS, SERVED FROM THIS PROCESS.
#
# They were loaded from jsdelivr until 2026-09-19, when the page failed on the founder's own
# machine with "Cannot read properties of undefined (reading 'MicVAD')" while loading perfectly
# in a headless test -- a browser-side block that the server cannot see and therefore cannot
# explain. A voice interface that needs a third-party CDN to be reachable is not a voice
# interface, so the eight files now ship in ./static and are served from here. The directory is
# optional: a checkout without it still serves the page, and the browser console says what is
# missing rather than the socket dying silently.
_STATIC = __import__("pathlib").Path(__file__).parent / "static"
if _STATIC.is_dir():
    app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")


@app.get("/log")
def voice_log(limit: int = 50):
    """Every voice turn, newest first -- the instrument for latency and friction.

    WHY THIS EXISTS. The founder, 2026-09-20: "often i have to repeat myself many times -- you need
    to have logs so you can monitor the latency and friction of all voice comms and troubleshoot
    and address all frictions." Nothing recorded a turn until now.
    """
    return {"turns": turnlog.recent(limit)}


@app.get("/log/summary")
def voice_log_summary(limit: int = 200):
    """The friction numbers: empty rate, median first-clause latency, per-voice speed.

    The view to open when something feels wrong. `empty_rate` is the one behind "I had to say it
    again"; `first_clause_median_s` is what a person experiences as "it is slow".
    """
    return turnlog.summary(limit)


@app.get("/voices")
def voices():
    """Every voice this host can speak with. ONE catalogue, shared with the FleetView backend.

    The list, the filtering and the .pt-archive trick that names Kokoro's voices without loading
    the model all live in `catalogue.py` now. They were written here, and when the board's voice
    transport moved onto the FleetView backend (2026-09-22) this file stopped being the only
    surface that needed them -- so they moved down to the package both surfaces import, rather
    than being copied into the second one.
    """
    return catalogue.catalogue()


@app.post("/voice/preview")
async def preview_voice(payload: dict):
    """Speak one fixed sentence in a candidate voice, WITHOUT making it live."""
    sample = str(payload.get("text") or "").strip() or (
        "Four agents are stuck, all paused. Two on the harness audit, two on the commit."
    )
    loop = asyncio.get_running_loop()
    # In a thread: a first Kokoro preview pays the model load, and on the event loop that would
    # stall every other socket in this process while a voice is auditioned.
    pcm, reason = await loop.run_in_executor(
        None,
        catalogue.preview,
        str(payload.get("engine") or ""),
        str(payload.get("voice") or ""),
        sample,
    )
    if pcm is None:
        return JSONResponse(content={"error": reason}, status_code=502 if "synthesis" in (reason or "") else 400)
    # Raw PCM, not JSON: the browser decodes it straight into an AudioBuffer, the same as a turn.
    return Response(content=pcm, media_type="application/octet-stream")


@app.post("/voice/select")
async def select_voice(payload: dict):
    """Switch the speaking voice at runtime. No restart, no edit, no deploy."""
    loop = asyncio.get_running_loop()
    body, status = await loop.run_in_executor(
        None,
        catalogue.select,
        str(payload.get("engine") or ""),
        str(payload.get("voice") or ""),
    )
    if status != 200:
        return JSONResponse(content=body, status_code=status)
    return body


@app.get("/healthz")
def healthz():
    """READY MEANS THE MODELS ARE PINNED, not that the process is up.

    The blueprint measured 89.5s to import faster_whisper on this class of CPU. A Kubernetes
    readiness probe that goes green on the socket would route conversations into a process still
    loading models, and every one of them would feel broken. So this route reports the load state
    and the failures explicitly, and a manifest should gate on `ready`.
    """
    m = engine.models()
    return {
        "ready": m.ready,
        "asr": m.asr is not None,
        # `tts` must be true for EITHER engine, not just Kokoro. It read `m.tts is not None`,
        # which is the Kokoro object -- so selecting the faster macOS engine would have made this
        # report `tts: false` on a host that can speak perfectly well.
        "tts": m.tts_engine is not None,
        "tts_engine": m.tts_engine,
        "tts_model": m.tts_model,
        "load_seconds": m.load_seconds,
        "errors": m.errors,
        "asr_model": engine.ASR_MODEL,
        "asr_sample_rate": engine.ASR_SAMPLE_RATE,
        "tts_sample_rate": engine.TTS_SAMPLE_RATE,
    }


@app.get("/")
def index():
    from pathlib import Path

    page = Path(__file__).parent / "client.html"
    body = page.read_text() if page.exists() else "<h1>client.html missing</h1>"
    # NO-CACHE ON THE PAGE ITSELF.
    #
    # Measured 2026-09-19: the founder's browser kept running an old client.html for many
    # reloads while the server had long since moved on -- so a fix shipped, was verified on the
    # server, and never reached the person. The page is the one file whose every edit must land
    # immediately, so it is served no-store rather than left to the browser's heuristics. The
    # /static/ assets are versioned by query string (?v=2) and stay cacheable.
    return HTMLResponse(
        body,
        headers={"Cache-Control": "no-store, must-revalidate", "Pragma": "no-cache"},
    )


@app.websocket("/voice/stream")
async def voice_stream(websocket: WebSocket):
    await websocket.accept()
    current: asyncio.Task | None = None
    history: list[dict[str, str]] = []
    timings: list[dict] = []

    async def send_json(payload: dict) -> None:
        try:
            await websocket.send_text(json.dumps(payload))
        except Exception:  # noqa: BLE001,S110 -- the peer is gone; the loop below will notice
            pass

    async def pipeline(question: str, log: "turnlog.Turn") -> None:
        """Answer one utterance, clause by clause, speaking each as it arrives.

        `log` ACCUMULATES THE TIMINGS. Before this, every number here was computed, sent to the
        browser, displayed for a moment, and lost -- so "I had to repeat myself" and "it is slow"
        were unfalsifiable. The turn is now written to `voice_turns` whatever happens, including
        when it is interrupted.
        """
        turn_started = time.time()
        first_audio: float | None = None
        spoken: list[str] = []
        m = engine.models()
        log.engine = m.tts_engine or ""
        log.voice = m.tts_model or ""
        try:
            async for clause in engine.llm_clauses(question, history):
                # THE FIRST CLAUSE IS THE LATENCY. Marked before synthesis, because from the
                # person's side "it started answering" begins when the text exists, and the
                # synthesis time is measured separately below.
                log.first_clause()
                # Synthesis is CPU-bound and blocks; a thread keeps the socket responsive so a
                # barge-in arriving DURING synthesis is still seen.
                loop = asyncio.get_running_loop()
                tts_started = time.time()
                pcm = await loop.run_in_executor(None, engine.synthesise, clause)
                log.tts_s += time.time() - tts_started
                if first_audio is None:
                    first_audio = round(time.time() - turn_started, 3)
                if pcm:
                    await websocket.send_bytes(pcm)
                await send_json({"type": "clause", "text": clause})
                spoken.append(clause)
                log.clauses += 1
        except asyncio.CancelledError:
            # BARGE-IN. The person is talking. Report the interruption honestly and re-raise so
            # the task really is dead rather than merely quiet.
            log.outcome = "interrupted"
            log.detail = " ".join(spoken)[:200]
            turnlog.record(log)
            await send_json({"type": "interrupted", "after": " ".join(spoken)})
            raise
        else:
            log.finished()
            turnlog.record(log)
            history.append({"role": "user", "content": question})
            history.append({"role": "assistant", "content": " ".join(spoken)})
            del history[:-8]
            elapsed = round(time.time() - turn_started, 3)
            timings.append({"first_audio": first_audio, "total": elapsed})
            # THE NUMBER THAT MATTERS IS first_audio, not total: it is what the person experiences
            # as "how long until it started answering". `total` is how long the sentence took.
            await send_json(
                {
                    "type": "done",
                    "first_audio": first_audio,
                    "total": elapsed,
                    "clauses": len(spoken),
                }
            )

    try:
        while True:
            try:
                message = await websocket.receive()
            except RuntimeError:
                # THE DISCONNECT ITSELF RAISES. Starlette raises
                #   RuntimeError: Cannot call "receive" once a disconnect message has been received
                # when the peer has gone, so a plain `except WebSocketDisconnect` below never runs
                # and the traceback lands in the log on every closed tab -- which reads like a
                # server fault rather than a normal hang-up. Measured 2026-09-19 in the first
                # end-to-end run. Break instead, and let the finally-cleanup cancel the task.
                break

            if message.get("text") is not None:
                text = message["text"]
                if text == "barge_in":
                    if current and not current.done():
                        current.cancel()
                    continue
                if text == "timings":
                    await send_json({"type": "timings", "turns": timings})
                    continue
                continue

            pcm = message.get("bytes")
            if not pcm:
                continue

            started = time.time()
            loop = asyncio.get_running_loop()
            transcript, asr_seconds = await loop.run_in_executor(
                None, engine.transcribe, pcm
            )
            if not transcript:
                # AN EMPTY TRANSCRIPT IS THE FRICTION ITSELF -- the person spoke and nothing came
                # back. Counted, so "I had to say it three times" becomes a number rather than a
                # complaint.
                turnlog.record(
                    turnlog.Turn(
                        started=started,
                        asr_s=asr_seconds,
                        words=0,
                        outcome="empty",
                        detail=f"{round(len(pcm) / 4 / engine.ASR_SAMPLE_RATE, 2)}s of audio produced no words",
                    )
                )
                await send_json({"type": "empty"})
                continue

            await send_json(
                {
                    "type": "transcript",
                    "text": transcript,
                    "asr_seconds": asr_seconds,
                    "audio_seconds": round(len(pcm) / 4 / engine.ASR_SAMPLE_RATE, 2),
                    "received_seconds": round(time.time() - started, 3),
                }
            )

            log = turnlog.Turn(
                started=started, asr_s=asr_seconds, words=len(transcript.split())
            )
            if current and not current.done():
                current.cancel()
            current = asyncio.create_task(pipeline(transcript, log))

    except WebSocketDisconnect:
        pass
    finally:
        if current and not current.done():
            current.cancel()

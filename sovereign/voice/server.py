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
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from . import engine

app = FastAPI(title="sovereign voice")


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
        "tts": m.tts is not None,
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
    return HTMLResponse(page.read_text() if page.exists() else "<h1>client.html missing</h1>")


@app.websocket("/voice/stream")
async def voice_stream(websocket: WebSocket):
    await websocket.accept()
    current: asyncio.Task | None = None
    history: list[dict[str, str]] = []
    timings: list[dict] = []

    async def send_json(payload: dict) -> None:
        try:
            await websocket.send_text(json.dumps(payload))
        except Exception:  # noqa: BLE001 -- the peer is gone; the loop below will notice
            pass

    async def pipeline(question: str) -> None:
        """Answer one utterance, clause by clause, speaking each as it arrives."""
        turn_started = time.time()
        first_audio: float | None = None
        spoken: list[str] = []
        try:
            async for clause in engine.llm_clauses(question, history):
                # Synthesis is CPU-bound and blocks; a thread keeps the socket responsive so a
                # barge-in arriving DURING synthesis is still seen.
                loop = asyncio.get_running_loop()
                pcm = await loop.run_in_executor(None, engine.synthesise, clause)
                if first_audio is None:
                    first_audio = round(time.time() - turn_started, 3)
                if pcm:
                    await websocket.send_bytes(pcm)
                await send_json({"type": "clause", "text": clause})
                spoken.append(clause)
        except asyncio.CancelledError:
            # BARGE-IN. The person is talking. Report the interruption honestly and re-raise so
            # the task really is dead rather than merely quiet.
            await send_json({"type": "interrupted", "after": " ".join(spoken)})
            raise
        else:
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
            transcript, asr_seconds = await loop.run_in_executor(None, engine.transcribe, pcm)
            if not transcript:
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

            if current and not current.done():
                current.cancel()
            current = asyncio.create_task(pipeline(transcript))

    except WebSocketDisconnect:
        pass
    finally:
        if current and not current.done():
            current.cancel()

#!/usr/bin/env python3
"""FleetView launcher.

The plugin's logic lives in `fleetview_backend/routes.py` as a proper Python module.
This file is the HTTP shell that mounts its routes on the paths the Backstage board calls.

The Backstage backend's proxy plugin (app-config.yaml `proxy.endpoints./fleetview`)
forwards requests here, with `pathRewrite: { '^/api/fleetview': '' }`, so the launcher
listens at root and the proxy strips the prefix before forwarding.

Run:
    python -m fleetview_backend.serve 18790
"""

from __future__ import annotations

import asyncio
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

# fleetview_backend is installed as a package. All modules use normal imports.
from fleetview_backend import (
    claude_code_adapter,
    executor_link,
    metrics,
    nats_adapter,
    routes,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    nats_url = os.environ.get("NATS_URL", "")
    if nats_url:
        ledger_prefix = os.environ.get("ESTATE_STATE_PATH_PREFIX") or None
        try:
            asyncio.create_task(
                claude_code_adapter.run_claude_code_adapter(nats_url, ledger_prefix)
            )
        except Exception:  # noqa: BLE001, S110 -- adapter startup failure must not break the app
            pass
    yield


def build_app() -> FastAPI:
    app = FastAPI(title="FleetView", version="1.1.0", lifespan=lifespan)

    @app.get(routes.SESSIONS_PATH)
    def sessions():
        body, status = routes.sessions_envelope()
        return JSONResponse(content=body, status_code=status)

    @app.get(routes.STREAM_PATH)
    async def stream():
        nats_url = os.environ.get("NATS_URL", "")

        async def gen_nats():
            body, _status = routes.sessions_envelope()
            for record in body.get("sessions") or []:
                yield routes.stream_frames([record])[0]
            try:
                last_hb = asyncio.get_event_loop().time()
                async for event in nats_adapter.subscribe_stream(nats_url):
                    import json as _json

                    yield f"data: {_json.dumps(event)}\n\n"
                    now = asyncio.get_event_loop().time()
                    if now - last_hb >= 30:
                        yield ": heartbeat\n\n"
                        last_hb = now
            except Exception:  # noqa: BLE001
                while True:
                    await asyncio.sleep(30)
                    yield ": heartbeat\n\n"

        async def gen():
            body, _status = routes.sessions_envelope()
            for record in body.get("sessions") or []:
                yield routes.stream_frames([record])[0]
            while True:
                await asyncio.sleep(30)
                yield ": heartbeat\n\n"

        return StreamingResponse(
            gen_nats() if nats_url else gen(), media_type="text/event-stream"
        )

    @app.get(routes.NOTES_PATH)
    def notes_get(session_id: str):
        body, status = routes.notes_envelope(session_id)
        return JSONResponse(content=body, status_code=status)

    @app.post(routes.NOTES_PATH)
    async def notes_post(request: Request):
        body = await request.json()
        result, status = routes.add_note(body)
        return JSONResponse(content=result, status_code=status)

    @app.post(routes.NUDGE_PATH)
    async def nudge_post(request: Request):
        body = await request.json()
        result, status = routes.add_nudge(body)
        return JSONResponse(content=result, status_code=status)

    @app.get(routes.SIGNALS_PATH)
    def signals_get(session_id: str):
        body, status = routes.signals_envelope(session_id)
        return JSONResponse(content=body, status_code=status)

    @app.get(routes.TRACE_PATH)
    def trace_get(session_id: str):
        body, status = routes.trace_envelope(session_id)
        return JSONResponse(content=body, status_code=status)

    @app.get(routes.LEDGER_PATH)
    def ledger_get(session_id: str):
        body, status = routes.ledger_tail_envelope(session_id)
        return JSONResponse(content=body, status_code=status)

    @app.get(routes.BLAST_RADIUS_PATH)
    def blast_radius(node_id: str = ""):
        body, status = routes.blast_radius_envelope(node_id)
        return JSONResponse(content=body, status_code=status)

    @app.get(routes.GRAPH_PATH)
    def graph():
        body, status = routes.graph_envelope()
        return JSONResponse(content=body, status_code=status)

    @app.post(routes.CHECK_RECEIPTS_PATH)
    async def check_receipts_post(request: Request):
        body = await request.json()
        result, status = routes.check_receipts_envelope(body)
        return JSONResponse(content=result, status_code=status)

    @app.get(routes.MUTATIONS_PATH)
    async def mutations_get():
        body, status = await routes.mutations_envelope()
        return JSONResponse(content=body, status_code=status)

    @app.post(routes.MUTATIONS_APPROVE_PATH)
    async def mutations_approve_post(request: Request):
        body = await request.json()
        result, status = await routes.approve_mutation(body)
        return JSONResponse(content=result, status_code=status)

    @app.post(routes.MUTATIONS_REJECT_PATH)
    async def mutations_reject_post(request: Request):
        body = await request.json()
        result, status = await routes.reject_mutation(body)
        return JSONResponse(content=result, status_code=status)

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    @app.get("/metrics")
    def metrics_handler():
        if os.environ.get("METRICS_ENABLED", "").lower() not in (
            "1",
            "true",
            "yes",
            "on",
        ):
            raise HTTPException(status_code=404, detail="metrics not enabled")
        try:
            from sovereign.voice import turnlog  # noqa: PLC0415

            summary = turnlog.summary()
        except Exception:  # noqa: BLE001
            summary = {"turns": 0, "empty": 0, "errors": 0}
        body = metrics.render(summary)
        return Response(
            content=body, media_type="text/plain; version=0.0.4; charset=utf-8"
        )

    # ── voice routes ────────────────────────────────────────────────────────────
    # Lazy imports: voice and voice_media load Kokoro (~90s) on first use.
    # Keeping them out of module-level imports means the service starts immediately.

    @app.post("/voice/say")
    async def voice_say(request: Request):
        """Text → PCM streaming via Cartesia Sonic. One clause, immediate."""
        from fleetview_backend import voice_media as vm

        body = await request.json()
        pcm, err = await vm.say(body.get("text", ""))
        if err:
            return JSONResponse(content={"error": err}, status_code=502)
        return Response(content=pcm, media_type="audio/pcm")

    @app.post("/voice/hear")
    async def voice_hear(request: Request, session_id: str = "", author: str = ""):
        """PCM → transcript via Deepgram. Author required (estate law: no unattributed steer)."""
        from fleetview_backend import voice_media as vm

        pcm = await request.body()
        body, status = await vm.hear(pcm, session_id, author)
        return JSONResponse(content=body, status_code=status)

    @app.post("/voice/stream")
    async def voice_stream(request: Request):
        """Question → SSE clauses. Full conversation with fleet context + history."""
        from fleetview_backend import voice as voice_module

        body = await request.json()
        question = body.get("question", "")
        history = body.get("history") or []
        sessions_body, _ = routes.sessions_envelope()
        sessions = sessions_body.get("sessions") or []

        async def gen():
            try:
                async for frame in voice_module.stream_ask(question, sessions, history):
                    yield frame
            except Exception as exc:  # noqa: BLE001
                yield f"event: error\ndata: {{'error': '{exc}'}}\n\n"

        return StreamingResponse(gen(), media_type="text/event-stream")

    @app.post("/voice/done")
    async def voice_done(request: Request):
        """Turn ended: write friction log, close bus row."""
        from fleetview_backend import voice_media as vm

        body = await request.json()
        result, status = await vm.answered(body)
        return JSONResponse(content=result, status_code=status)

    @app.get("/voice/voices")
    async def voice_voices():
        """Catalogue: say / kokoro / piper groups + live engine. Does not load models."""
        from fleetview_backend import voice_media as vm

        return JSONResponse(content=await vm.voices())

    @app.post("/voice/select")
    async def voice_select(request: Request):
        """Switch live engine + voice."""
        from fleetview_backend import voice_media as vm

        body = await request.json()
        result, status = await vm.select(body.get("engine", ""), body.get("voice", ""))
        return JSONResponse(content=result, status_code=status)

    @app.get("/voice/log")
    async def voice_log(limit: int = 40):
        """Recent voice turns, newest first."""
        from fleetview_backend import voice_media as vm

        return JSONResponse(content=vm.log(limit=limit))

    @app.get("/voice/log/summary")
    async def voice_log_summary(limit: int = 200):
        """Friction stats: empty rate, median latencies, per-voice speed."""
        from fleetview_backend import voice_media as vm

        return JSONResponse(content=vm.log_summary(limit=limit))

    @app.post("/voice/speculate")
    async def voice_speculate(request: Request):
        """Server-side speculative intent for partial transcripts."""
        from fleetview_backend import voice_media as vm

        body = await request.json()
        trace_context = {
            k: v for k, v in request.headers.items() if k.lower().startswith("x-trace-")
        }
        result, status = await vm.speculate(body, trace_context or None)
        return JSONResponse(content=result, status_code=status)

    @app.post("/voice/steer")
    async def voice_steer(request: Request):
        """Validated JSON intent from browser → outbox → NATS. Author required."""
        from fleetview_backend import voice_media as vm

        body = await request.json()
        trace_context = {
            k: v for k, v in request.headers.items() if k.lower().startswith("x-trace-")
        }
        result, status = await vm.steer(body, trace_context or None)
        return JSONResponse(content=result, status_code=status)

    return app


def build_executor_app() -> FastAPI:
    app = FastAPI(title="FleetView executor relay", version="1.0.0")

    def _check_key(x_executor_key: str | None) -> None:
        expected = os.environ.get("FLEETVIEW_EXECUTOR_KEY")
        key_file = os.environ.get("FLEETVIEW_EXECUTOR_KEY_FILE")
        if not expected and key_file:
            try:
                expected = Path(key_file).read_text().strip() or None
            except FileNotFoundError:
                expected = None
        if expected and x_executor_key != expected:
            raise HTTPException(status_code=401, detail="bad or missing executor key")

    @app.post("/executor/poll")
    async def executor_poll(x_executor_key: str | None = Header(default=None)):
        _check_key(x_executor_key)
        return await executor_link.poll()

    @app.post("/executor/reply")
    async def executor_reply(
        request: Request, x_executor_key: str | None = Header(default=None)
    ):
        _check_key(x_executor_key)
        body = await request.json()
        request_id = body.get("request_id", "")
        result = body.get("result", {})
        accepted = await executor_link.reply(request_id, result)
        return {"accepted": accepted}

    @app.get("/healthz")
    def healthz():
        return {"ok": True, "connected": executor_link.is_connected()}

    return app


def main():
    if len(sys.argv) not in (2, 3):
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    port = int(sys.argv[1])
    app = build_app()

    if len(sys.argv) == 3:
        executor_port = int(sys.argv[2])
        executor_app = build_executor_app()
        main_config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="info")
        executor_config = uvicorn.Config(
            executor_app,
            host="0.0.0.0",
            port=executor_port,
            log_level="info",
        )
        server = uvicorn.Server(configs=[main_config, executor_config])
    else:
        server = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="info")
        server = uvicorn.Server(server)

    server.run()


if __name__ == "__main__":
    main()

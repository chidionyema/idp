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
    approvals_adapter,
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
        # crew#1013: ensure all three estate streams exist before any adapter starts publishing.
        # Idempotent — safe to call every startup; the bus already knows streams that exist.
        try:
            await nats_adapter.ensure_estate_streams(nats_url)
        except Exception:  # noqa: BLE001, S110 -- bus may be down; adapters retry on publish
            pass
        ledger_prefix = os.environ.get("ESTATE_STATE_PATH_PREFIX") or None
        try:
            asyncio.create_task(
                claude_code_adapter.run_claude_code_adapter(nats_url, ledger_prefix)
            )
        except Exception:  # noqa: BLE001, S110 -- adapter startup failure must not break the app
            pass
        asyncio.create_task(approvals_adapter.run_approvals_adapter(nats_url))
        from fleetview_backend import efficiency_feed

        asyncio.create_task(efficiency_feed.publish_highlights(nats_url))
        from fleetview_backend import key_sync

        asyncio.create_task(key_sync.publish_alerts(nats_url))
    yield


async def _bus_reachable(nats_url: str) -> dict:
    """A TCP connect to the bus, bounded at 0.5s: reachable or not, and why."""
    if not nats_url:
        return {"reachable": False, "reason": "NATS_URL is unset"}
    from urllib.parse import urlparse  # noqa: PLC0415

    u = urlparse(nats_url)
    try:
        _r, w = await asyncio.wait_for(
            asyncio.open_connection(u.hostname, u.port or 4222), timeout=0.5
        )
        w.close()
        return {"reachable": True, "url": nats_url}
    except Exception as exc:  # noqa: BLE001 - the reason is the answer
        return {"reachable": False, "url": nats_url, "reason": type(exc).__name__}


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
            import json as _json

            async def _events():
                async for event in nats_adapter.subscribe_stream(nats_url):
                    yield f"data: {_json.dumps(event)}\n\n"

            async def _cues():
                async for cue in nats_adapter.subscribe_cues(nats_url):
                    yield routes.cue_frame(cue)

            async def _stories():
                async for on, story in nats_adapter.subscribe_stories(nats_url):
                    yield routes.story_frame(on, story)

            async def _approvals():
                async for approval in nats_adapter.subscribe_approvals(nats_url):
                    yield f"data: {__import__('json').json.dumps({'type': 'approval', **approval})}\n\n"

            last_hb = asyncio.get_event_loop().time()
            merged = nats_adapter.merge(
                nats_adapter.isolated("events", _events()),
                nats_adapter.isolated("cues", _cues()),
                nats_adapter.isolated("stories", _stories()),
                nats_adapter.isolated("approvals", _approvals()),
            )
            async for frame in merged:
                yield frame
                now = asyncio.get_event_loop().time()
                if now - last_hb >= 30:
                    yield ": heartbeat\n\n"
                    last_hb = now
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

    @app.get(routes.DEVICE_STATUS_PATH)
    def device_status():
        body, status = routes.device_status_envelope()
        return JSONResponse(content=body, status_code=status)

    @app.post(routes.DEVICE_AUTHORIZE_PATH)
    def device_authorize_post():
        # POST: this mints a single-use challenge, and a GET that changed state would be prefetchable.
        body, status = routes.device_authorize_envelope()
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

    @app.get(routes.MEMORY_PATH)
    def memory():
        body, status = routes.memory_envelope()
        return JSONResponse(content=body, status_code=status)

    @app.get(routes.GREENLANE_PATH)
    def greenlane():
        body, status = routes.greenlane_envelope()
        return JSONResponse(content=body, status_code=status)

    @app.get(routes.HARV_PATH)
    def harv():
        body, status = routes.harv_envelope()
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
    async def healthz():
        # `ok` is liveness and stays true; `bus` says whether the estate bus answers. 2026-09-27
        # the laptop's NATS was never installed, this answered {"ok": true} throughout, and every
        # voice turn and the board's live stream went without it with nobody told.
        return {"ok": True, "bus": await _bus_reachable(os.environ.get("NATS_URL", ""))}

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
            # stream_ask is a plain (sync) generator: it makes blocking urllib calls to the
            # router. Iterating it directly on the event loop -- `async for` doesn't even work,
            # since it has no __aiter__ -- would also stall every other request (the board's SSE
            # included) for the length of the router call. Each `next()` runs in a thread instead,
            # same reasoning `hear()` uses for the CPU-bound transcribe call.
            loop = asyncio.get_running_loop()
            it = iter(voice_module.stream_ask(question, sessions, history))
            _DONE = object()
            try:
                while True:
                    frame = await loop.run_in_executor(None, lambda: next(it, _DONE))
                    if frame is _DONE:
                        break
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

    @app.get("/efficiency")
    async def efficiency(since: str = "1h"):
        from fleetview_backend import efficiency_feed

        return JSONResponse(
            content=await asyncio.to_thread(efficiency_feed.summary, since)
        )

    @app.get("/efficiency/proof")
    async def efficiency_proof():
        from fleetview_backend import efficiency_feed

        return JSONResponse(content=await asyncio.to_thread(efficiency_feed.proof))

    @app.get("/efficiency/stream")
    async def efficiency_stream(since: str = "1h"):
        from fleetview_backend import efficiency_feed

        return StreamingResponse(
            efficiency_feed.stream(since), media_type="text/event-stream"
        )

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

    @app.get(routes.AGENT_JOBS_PATH)
    async def agent_jobs_get():
        # GitHub calls, up to a 10s timeout each: off the event loop, like /voice/intent.
        loop = asyncio.get_running_loop()
        body, status = await loop.run_in_executor(None, routes.agent_jobs_envelope)
        return JSONResponse(content=body, status_code=status)

    @app.post(routes.AGENT_JOBS_PATH)
    async def agent_jobs_post(request: Request):
        try:
            body = await request.json()
        except ValueError:
            body = None
        loop = asyncio.get_running_loop()
        result, status = await loop.run_in_executor(None, routes.submit_agent_job, body)
        return JSONResponse(content=result, status_code=status)

    @app.get(routes.CONCIERGE_TASKS_PATH)
    async def concierge_tasks_get():
        loop = asyncio.get_running_loop()
        body, status = await loop.run_in_executor(None, routes.concierge_tasks_envelope)
        return JSONResponse(content=body, status_code=status)

    @app.post(routes.CONCIERGE_TASKS_PATH)
    async def concierge_tasks_post(request: Request):
        try:
            body = await request.json()
        except ValueError:
            body = None
        loop = asyncio.get_running_loop()
        result, status = await loop.run_in_executor(
            None, routes.submit_concierge_task, body
        )
        return JSONResponse(content=result, status_code=status)

    @app.get(routes.KEY_SYNC_PATH)
    async def key_sync_get():
        loop = asyncio.get_running_loop()
        body, status = await loop.run_in_executor(None, routes.key_sync_envelope)
        return JSONResponse(content=body, status_code=status)

    @app.post("/voice/intent")
    async def voice_intent(request: Request):
        """Utterance -> committed estate intent. 204 when it names none: the brain answers."""
        from fleetview_backend import voice_intents as vi

        try:
            body = await request.json()
        except ValueError:
            body = {}
        if not isinstance(body, dict):
            body = {}
        text = str(body.get("text") or "")
        session_id = str(body.get("session_id") or "")
        # handle() may run a subprocess for up to 120s: off the event loop, like /voice/stream.
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, vi.handle, text, session_id)
        if result is None:
            return Response(status_code=204)
        return JSONResponse(content=result)

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
        # 0.0.0.0 (RC-1b 2026-10-03): the anonymous voice door's Service
        # (overlays/oke/fleetview-voice-service.yaml) must reach this port from the edge
        # (Traefik, ns edge); reachability is governed by that Service + its port-scoped
        # NetworkPolicy, exactly like the 8091 relay below.
        main_config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")  # noqa: S104
        executor_config = uvicorn.Config(
            executor_app,
            host="0.0.0.0",  # noqa: S104 -- pre-existing on main; executor relay is key-checked (_check_key)
            port=executor_port,
            log_level="info",
        )
        # uvicorn.Server takes one Config; there is no `configs=` (the src-layout move, 2e364b4b,
        # wrote one, and every two-port start raised TypeError). Two servers on one loop.
        main_server = uvicorn.Server(main_config)
        executor_server = uvicorn.Server(executor_config)

        async def _serve_both():
            await asyncio.gather(main_server.serve(), executor_server.serve())

        asyncio.run(_serve_both())
        return

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    main()

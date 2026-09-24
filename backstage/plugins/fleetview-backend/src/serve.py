#!/usr/bin/env python3
"""FleetView launcher.

The plugin's logic lives in `backstage/plugins/fleetview-backend/src/routes.py` as a pure
Python module (no FastAPI imports). This file is the HTTP shell that mounts its
`sessions_envelope()`, `stream_frames()`, `notes_envelope()`/`add_note()`, `add_nudge()`,
`blast_radius_envelope()`, `graph_envelope()`, `check_receipts_envelope()`, `signals_envelope()`
and `mutations_envelope()`/`approve_mutation()`/`reject_mutation()` on the paths the Backstage
board calls (`/api/fleetview/sessions`, `/stream`, `/notes`, `/nudge`, `/signals`, `/blast-radius`,
`/graph`, `/check-receipts`, `/mutations`, `/mutations/approve`, `/mutations/reject`).

This used to live at `/tmp/serve_fv.py` -- a real dev launcher with no repo path, so it vanished
with the machine's temp directory and could not be run from a clean checkout. Moved into the
plugin's own `src/` alongside the routes it mounts (item #6's build turned this up while wiring
the nudge route through it).

Run (per docs/tutorials/demo/fleetview.md):
    ESTATE_CATALOG_PATH=<repo>/catalog/catalog-info.yaml \\
        python <repo>/backstage/plugins/fleetview-backend/src/serve.py 18790 \\
        <repo>/backstage/plugins/fleetview-backend/src/routes.py

The Backstage backend's proxy plugin (app-config.yaml `proxy.endpoints./fleetview`)
forwards requests here, with `pathRewrite: { '^/api/fleetview': '' }`, so the launcher
listens at root and the proxy strips the prefix before forwarding.

A fourth, optional argv starts a second, separately-bound server for the mutations relay
(`executor_link.py`): `/executor/poll` and `/executor/reply`, the two doors
`platform/executor/fleetview_register.py` (the laptop companion) speaks to. It binds `0.0.0.0`,
not `127.0.0.1` like the app above -- the one new network surface this launcher opens, reachable
only through the tailnet Service+ACL a cluster deployment adds around it (see the PR). Omitting
the argv (every existing local-dev invocation) leaves this off entirely: no new port, no new
behaviour, `routes.py`'s mutation handlers keep calling `mutations.py` directly, exactly as
before.
"""

from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

_EXECUTOR_LINK_MODULE = Path(__file__).resolve().parent / "executor_link.py"
_METRICS_MODULE = Path(__file__).resolve().parent / "metrics.py"
_VOICE_MEDIA_MODULE = Path(__file__).resolve().parent / "voice_media.py"


def _load_executor_link():
    """Same fixed-name `sys.modules` cache `routes.py`'s `_executor_link()` uses, and for the
    same reason: this module holds the one laptop connection's state, and `routes.py`'s mutation
    handlers must see the exact object this process's executor app is polling, not a fresh,
    disconnected re-exec of the file."""
    import sys

    name = "fleetview_executor_link_impl"
    cached = sys.modules.get(name)
    if cached is not None:
        return cached
    spec = importlib.util.spec_from_file_location(name, _EXECUTOR_LINK_MODULE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module at {_EXECUTOR_LINK_MODULE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _load_routes(routes_path: Path):
    spec = importlib.util.spec_from_file_location("fleetview_routes", routes_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load routes module at {routes_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_voice_media():
    """Load voice_media.py ONCE, with its package context, cached in sys.modules.

    voice_media.py does `from . import tracing`, a relative import that only resolves when the
    module is registered under a real parent package (its `__package__` is set). The tests
    (test_speculate_and_clarify.py, test_voice_on_the_bus.py) do exactly this dance -- load
    tracing.py first under the same synthetic package, then voice_media.py. A bare
    spec_from_file_location would raise `ImportError: attempted relative import with no known
    parent package`, which is why the bare load failed until this fix.

    The fixed package name also caches the module so `sovereign.voice` (imported by
    _voice_package) stays a single shared instance: a voice selected on one route voices every
    route, not a per-loader second copy.
    """
    import sys
    import types

    pkg = "fleetview_backend"
    if pkg not in sys.modules:
        sys.modules[pkg] = types.ModuleType(pkg)

    def _load_member(path: Path, name: str):
        full = f"{pkg}.{name}"
        if full in sys.modules:
            return sys.modules[full]
        spec = importlib.util.spec_from_file_location(full, path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot load module at {path}")
        module = importlib.util.module_from_spec(spec)
        module.__package__ = pkg
        sys.modules[full] = module
        spec.loader.exec_module(module)
        return module

    _load_member(Path(__file__).resolve().parent / "tracing.py", "tracing")
    return _load_member(_VOICE_MEDIA_MODULE, "voice_media")


def _build_voice_routes(app: FastAPI) -> None:
    """Mount the voice fleet's routes. THIS IS THE SPINAL CORD.

    `voice_media.py` implements `hear`, `say`, `answered`, `voices`, `select`, `log`, `log_summary`
    and `preview`, and the board's `useEstateVoice.ts` already polls `/voice/voices`, `/voice/select`,
    `/voice/log` and `/voice/log/summary`. But until this block existed, NOT ONE of them was
    registered on the app -- the board talked to endpoints that returned 404 through the proxy, and
    the founder's friction panel (`voiceLog`/`voiceStats`) rendered nothing. These routes are the
    join between a working brain and a working body.

    The brain (`/voice/stream`) is voice.py's own SSE route, reached through `voice_media.py`'s
    `ask`; it stays where it is -- this block only wires the MEDIA and the INSTRUMENT, which are
    what the board polls.
    """
    vm = _load_voice_media()

    @app.post("/voice/hear")
    async def voice_hear(request: Request):
        # A steer with no attributed author is refused: the estate never runs an unattributed
        # steer. The author comes from the authenticated session at the proxy layer; hear() refuses
        # a blank one, so the route passes it through rather than inventing a default.
        body = await request.body()
        session_id = request.query_params.get("session_id", "")
        author = request.headers.get("x-voice-author", "")
        result, status = await vm.hear(body, session_id, author)
        return JSONResponse(content=result, status_code=status)

    @app.post("/voice/say")
    async def voice_say(request: Request):
        body = await request.json()
        pcm, reason = await vm.say(body.get("text", ""))
        if pcm is None:
            return JSONResponse(content={"error": reason}, status_code=502)
        return Response(content=pcm, media_type="application/octet-stream")

    @app.post("/voice/answered")
    async def voice_answered(request: Request):
        body = await request.json()
        result, status = await vm.answered(body)
        return JSONResponse(content=result, status_code=status)

    @app.get("/voice/voices")
    async def voice_voices():
        return JSONResponse(content=await vm.voices())

    @app.post("/voice/select")
    async def voice_select(request: Request):
        body = await request.json()
        try:
            result, status = await vm.select(
                body.get("engine", ""), body.get("voice", "")
            )
        except Exception as exc:  # noqa: BLE001 -- select() may raise on a weird arg; report it
            return JSONResponse(content={"error": str(exc)}, status_code=400)
        return JSONResponse(content=result, status_code=status)

    @app.get("/voice/log")
    async def voice_log(limit: int = 50):
        return JSONResponse(content=vm.log(limit))

    @app.get("/voice/log/summary")
    async def voice_log_summary(limit: int = 200):
        return JSONResponse(content=vm.log_summary(limit))

    @app.post("/voice/preview")
    async def voice_preview(request: Request):
        body = await request.json()
        pcm, reason = await vm.preview(
            body.get("engine", ""), body.get("voice", ""), body.get("text", "")
        )
        if pcm is None:
            return JSONResponse(content={"error": reason}, status_code=502)
        return Response(content=pcm, media_type="application/octet-stream")

    return app


def build_app(routes_path: Path) -> FastAPI:
    routes = _load_routes(routes_path)

    _nats_adapter_module = routes_path.parent / "nats_adapter.py"
    _claude_code_adapter_module = routes_path.parent / "claude_code_adapter.py"

    def _load_nats_adapter():
        spec = importlib.util.spec_from_file_location(
            "fleetview_nats_adapter_impl", _nats_adapter_module
        )
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot load module at {_nats_adapter_module}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _load_claude_code_adapter():
        spec = importlib.util.spec_from_file_location(
            "fleetview_claude_code_adapter_impl", _claude_code_adapter_module
        )
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot load module at {_claude_code_adapter_module}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        nats_url = os.environ.get("NATS_URL", "")
        if nats_url:
            ledger_prefix = os.environ.get("ESTATE_STATE_PATH_PREFIX") or None
            try:
                cc_adapter = _load_claude_code_adapter()
                asyncio.create_task(
                    cc_adapter.run_claude_code_adapter(nats_url, ledger_prefix)
                )
            # S110: the swallow is deliberate and already carries its reason on the line
            # above -- an adapter that cannot start must not take the board down with it.
            except Exception:  # noqa: BLE001, S110 — adapter startup failure must not break the app
                pass
        yield

    app = FastAPI(title="FleetView", version="1.1.0", lifespan=lifespan)

    @app.get(routes.SESSIONS_PATH)
    def sessions():
        body, status = routes.sessions_envelope()
        return JSONResponse(content=body, status_code=status)

    @app.get(routes.STREAM_PATH)
    async def stream():
        nats_url = os.environ.get("NATS_URL", "")

        if nats_url:

            async def gen_nats():
                # Initial frame: one event per current session so the page renders on connect.
                body, _status = routes.sessions_envelope()
                for record in body.get("sessions") or []:
                    yield routes.stream_frames([record])[0]
                # Subscribe to NATS and yield each message as an SSE data frame,
                # interleaving a heartbeat comment every 30s so proxies keep the connection.
                try:
                    nats_module = _load_nats_adapter()
                    last_hb = asyncio.get_event_loop().time()
                    async for event in nats_module.subscribe_stream(nats_url):
                        import json as _json

                        yield f"data: {_json.dumps(event)}\n\n"
                        now = asyncio.get_event_loop().time()
                        if now - last_hb >= 30:
                            yield ": heartbeat\n\n"
                            last_hb = now
                except Exception:  # noqa: BLE001 — NATS failure falls back to heartbeat loop
                    while True:
                        await asyncio.sleep(30)
                        yield ": heartbeat\n\n"

            return StreamingResponse(gen_nats(), media_type="text/event-stream")

        async def gen():
            # Initial frame: one event per current session so the page renders on connect.
            body, _status = routes.sessions_envelope()
            for record in body.get("sessions") or []:
                yield routes.stream_frames([record])[0]
            # Heartbeat: a comment line keeps the connection open across proxies without
            # the page misreading it as a session change. The session contract is in
            # schema/session.json -- nothing here invents one.
            while True:
                await asyncio.sleep(30)
                yield ": heartbeat\n\n"

        return StreamingResponse(gen(), media_type="text/event-stream")

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

    # crew#973 CP2: Deploy River data endpoints
    @app.get(routes.JOURNEYS_PATH)
    def journeys_get(limit: int = 30):
        body, status = routes.journeys_envelope(limit)
        return JSONResponse(content=body, status_code=status)

    # crew#973 CP3: SSE tail for the Deploy River narration
    @app.get(routes.JOURNEYS_STREAM_PATH)
    async def journeys_stream():
        async def gen():
            last_sha = None
            while True:
                frames = routes.journeys_tail_frames(last_sha)
                for frame in frames:
                    yield frame
                    # Track the newest sha we've emitted; a malformed frame is ignored.
                    try:
                        import json as _json

                        data = _json.loads(frame[6:])  # strip "data: "
                        last_sha = data.get("sha", last_sha)
                    except _json.JSONDecodeError:
                        pass
                yield ": heartbeat\n\n"
                await asyncio.sleep(15)

        return StreamingResponse(gen(), media_type="text/event-stream")

    # crew#973 CP4: time-scrub — journeys as of a UTC timestamp
    # MUST be before /journeys/{sha} so FastAPI matches it first (route order matters)
    @app.get("/journeys/at")
    def journeys_at_get(as_of: str = ""):
        body, status = routes.journeys_at_time_envelope(as_of)
        return JSONResponse(content=body, status_code=status)

    @app.get("/journeys/{sha}")
    def journey_get(sha: str):
        body, status = routes.deploy_journey_envelope(sha)
        return JSONResponse(content=body, status_code=status)

    # crew#973 CP4: interrogation — proxy one question to HolmesGPT
    @app.get("/ask-holmes")
    def ask_holmes_get(q: str = ""):
        body, status = routes.ask_holmes_envelope(q)
        return JSONResponse(content=body, status_code=status)

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    @app.get("/metrics")
    def metrics():
        """The voice metrics, in Prometheus text format, read from the SAME turnlog the board
        reads. METRICS_ENABLED honours the opt-in: unset/false means the endpoint 404s, because a
        metrics door advertised on a host that did not opt in is a new surface, not a feature. When
        enabled, every gauge renders (NaN when no turns yet) so the metric NAMES exist on first
        scrape and dashboards do not gap out before the first turn."""
        if os.environ.get("METRICS_ENABLED", "").lower() not in (
            "1",
            "true",
            "yes",
            "on",
        ):
            raise HTTPException(status_code=404, detail="metrics not enabled")
        spec = importlib.util.spec_from_file_location(
            "fleetview_metrics", _METRICS_MODULE
        )
        if spec is None or spec.loader is None:
            raise HTTPException(status_code=500, detail="metrics module unavailable")
        metrics_mod = importlib.util.module_from_spec(spec)
        import sys as _sys

        root = str(Path(__file__).resolve().parents[4])
        if root not in _sys.path:
            _sys.path.insert(0, root)
        spec.loader.exec_module(metrics_mod)
        try:
            from sovereign.voice import turnlog  # noqa: PLC0415

            summary = turnlog.summary()
        except Exception:  # noqa: BLE001 -- no voice models means no turns, not no metrics
            summary = {"turns": 0, "empty": 0, "errors": 0}
        body = metrics_mod.render(summary)
        return Response(
            content=body, media_type="text/plain; version=0.0.4; charset=utf-8"
        )

    _build_voice_routes(app)

    return app


def build_executor_app() -> FastAPI:
    """The mutations-relay's own tiny app: two doors, nothing else. A laptop reaching this port
    can only long-poll for queued verbs and answer them -- it cannot, from here, read or change
    anything `routes.py`'s own handlers do not themselves choose to relay."""
    link = _load_executor_link()
    app = FastAPI(title="FleetView executor relay", version="1.0.0")

    def _check_key(x_executor_key: str | None) -> None:
        import os

        # In-cluster (OKE): the key is a mounted Secret volume file, not an env var --
        # secrets-not-from-env-vars refuses a Pod that sources a secret via env valueFrom
        # (Kyverno blocked this sidecar's own rollout on 2026-09-15 for exactly that).
        # Local `docker run`/laptop launches still set FLEETVIEW_EXECUTOR_KEY directly.
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
        return await link.poll()

    @app.post("/executor/reply")
    async def executor_reply(
        request: Request, x_executor_key: str | None = Header(default=None)
    ):
        _check_key(x_executor_key)
        body = await request.json()
        request_id = body.get("request_id", "")
        result = body.get("result", {})
        accepted = await link.reply(request_id, result)
        return {"accepted": accepted}

    @app.get("/healthz")
    def healthz():
        return {"ok": True, "connected": link.is_connected()}

    return app


def main():
    if len(sys.argv) not in (3, 4):
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    port = int(sys.argv[1])
    routes_path = Path(sys.argv[2]).resolve()
    if not routes_path.is_file():
        print(f"routes module not found: {routes_path}", file=sys.stderr)
        sys.exit(2)
    app = build_app(routes_path)

    if len(sys.argv) == 4:
        executor_port = int(sys.argv[3])
        executor_app = build_executor_app()
        main_config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="info")
        executor_config = uvicorn.Config(
            executor_app,
            host="0.0.0.0",  # noqa: S104 -- the one deliberate non-loopback bind this launcher makes; see the module docstring
            port=executor_port,
            log_level="info",
        )
        main_server = uvicorn.Server(main_config)
        executor_server = uvicorn.Server(executor_config)

        async def _serve_both():
            await asyncio.gather(main_server.serve(), executor_server.serve())

        asyncio.run(_serve_both())
        return

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    main()

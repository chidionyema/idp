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
from fastapi.responses import JSONResponse, StreamingResponse

_EXECUTOR_LINK_MODULE = Path(__file__).resolve().parent / "executor_link.py"


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


def _load_config_guard(routes_path: Path):
    """`config_guard.py`, beside routes.py. Path-loaded like every sibling module here.

    Registered in `sys.modules` before `exec_module` because this module uses `@dataclass`,
    which resolves `cls.__module__` through `sys.modules` at decoration time. The other
    siblings get away without it because none of them decorate; the executor link uses the
    same `sys.modules` idiom for a different reason (singleton state).
    """
    path = routes_path.parent / "config_guard.py"
    spec = importlib.util.spec_from_file_location("fleetview_config_guard", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load config guard at {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["fleetview_config_guard"] = module
    spec.loader.exec_module(module)
    return module


def build_app(routes_path: Path) -> FastAPI:
    routes = _load_routes(routes_path)

    # FAIL FAST (2026-09-18). Until this call, a process launched with an empty environment
    # started, bound its port and served traffic, then answered 502/503 per button while never
    # saying 'I am not configured'. Validated here because a consequence of a key or an object
    # store is a fact about this object, not a fact about production -- every startup path,
    # including the tests, goes through build_app, so there is one check rather than two.
    #
    # ESTATE_DB is the only required var: without it every read returns nothing and an empty
    # board is indistinguishable from a fleet with no work. NATS_URL and LANGFUSE_HOST are
    # deliberately optional -- unset they turn a feature off, and those routes already answer
    # 'unavailable' with the reason, which is an honest answer and not a startup failure.
    _config_guard = _load_config_guard(routes_path)
    config = _config_guard.require_config()
    # Printed, not logged: this is what a person reads in a terminal or a pod's first lines,
    # and a degraded start has to be visible without clicking anything.
    print(_config_guard.startup_banner(config), flush=True)

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
            except Exception:  # noqa: BLE001, S110 — adapter startup failure must not break the app
                pass
        yield

    app = FastAPI(title="FleetView", version="1.1.0", lifespan=lifespan)

    @app.get(routes.SESSIONS_PATH)
    def sessions():
        body, status = routes.sessions_envelope()
        return JSONResponse(content=body, status_code=status)

    @app.get(routes.HISTORY_PATH)
    def history(session_id: str = "", since: str = "", until: str = ""):
        payload, status = routes.history_envelope(session_id, since, until)
        return JSONResponse(content=payload, status_code=status)

    @app.get(routes.QUERY_PATH)
    def query(directive: str = ""):
        """GET, because a question is not a mutation and a link to one should be shareable."""
        payload, status = routes.query_envelope(directive)
        return JSONResponse(content=payload, status_code=status)

    @app.post(routes.VOICE_STREAM_PATH)
    async def voice_stream(body: dict):
        """The same question, streamed as clauses.

        TWO ROUTES, ON PURPOSE. `/voice` returns one JSON answer and stays for any caller that
        wants a single response; `/voice/stream` sends each clause as it is written. The browser
        uses the stream, because a person waiting in silence for a finished paragraph is the
        difference between this feeling instant and feeling broken.
        """
        envelope, _status = routes.sessions_envelope()
        sessions = envelope.get("sessions") or []

        def gen():
            for chunk in routes.stream_voice(body, sessions):
                yield chunk

        return StreamingResponse(gen(), media_type="text/event-stream", headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        })

    @app.post(routes.VOICE_PATH)
    async def voice(body: dict):
        """Voice in, one or two sentences out. Read-only: it can describe the fleet and cannot
        change it, and the prompt says so in as many words."""
        # The SAME envelope /sessions serves. One source, so the spoken answer and the board can
        # never disagree about what the fleet is.
        envelope, _status = routes.sessions_envelope()
        payload, status = routes.ask_voice(body, envelope.get("sessions") or [])
        return JSONResponse(content=payload, status_code=status)

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

        async def gen_live():
            """LIVE FRAMES WITHOUT A BUS, measured from the ledger that is always being written.

            THE GAP THIS CLOSES. Without NATS_URL this route sent the initial frames and then
            nothing but `: heartbeat` for ever. Measured 2026-09-19: the stream authenticated
            (after a 401 fix), delivered 24 frames on connect, and then a heartbeat every 30s.
            Every trail, every jet and every "live" claim in the UI was therefore cosmetic -- the
            page could only ever be as fresh as the last 15-second poll.

            On this machine there IS a live source and it was already on disk: `session_events`
            gains a row every time a session writes. Tail ing that table costs one indexed query
            per second and needs no NATS, no cluster and no new dependency. It is the same table
            the recorder fills and the same one bin/idp-cluster-state reads.

            The poll is not removed; it is what makes a session that has gone QUIET still move to
            `stuck` on the board, and a row that only changes when it writes could otherwise sit
            `running` for ever.
            """
            body, _status = routes.sessions_envelope()
            for record in body.get("sessions") or []:
                yield routes.stream_frames([record])[0]

            seen = routes.newest_event_seq()
            last_full = asyncio.get_event_loop().time()
            while True:
                await asyncio.sleep(1.0)
                now = asyncio.get_event_loop().time()
                try:
                    newest = routes.newest_event_seq()
                except Exception:  # noqa: BLE001 -- a ledger read that fails is not fatal
                    newest = seen
                if newest > seen:
                    # Something wrote. Send every session that moved, so a burst of tool calls
                    # arrives as a burst rather than one frame per second.
                    seen = newest
                    fresh, _st = routes.sessions_envelope()
                    for record in fresh.get("sessions") or []:
                        yield routes.stream_frames([record])[0]
                elif now - last_full >= 15:
                    # Nothing wrote: still send the board so a session that has gone quiet moves
                    # to `stuck` on the page without waiting for a client poll.
                    last_full = now
                    fresh, _st = routes.sessions_envelope()
                    for record in fresh.get("sessions") or []:
                        yield routes.stream_frames([record])[0]
                if now - last_full >= 30:
                    yield ": heartbeat\n\n"
                    last_full = now

        return StreamingResponse(
            gen_live(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
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

    @app.post(routes.STOP_PATH)
    async def stop_post(request: Request):
        body = await request.json()
        result, status = routes.add_stop(body)
        return JSONResponse(content=result, status_code=status)

    @app.post(routes.APPROVE_PATH)
    async def approve_post(request: Request):
        body = await request.json()
        result, status = routes.add_approve(body)
        return JSONResponse(content=result, status_code=status)

    @app.post(routes.DENY_PATH)
    async def deny_post(request: Request):
        body = await request.json()
        result, status = routes.add_deny(body)
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

    @app.get(routes.DEVICE_STATUS_PATH)
    def device_status_get():
        body, status = routes.device_status_envelope()
        return JSONResponse(content=body, status_code=status)

    @app.post(routes.DEVICE_AUTHORIZE_PATH)
    def device_authorize_post():
        # POST, not GET: this mints a single-use challenge, and a GET that changed state would
        # be both wrong and prefetchable. The proxy's allowedMethods for this key already
        # carries POST (app-config.yaml), so no config change is needed for the route to reach.
        body, status = routes.device_authorize_envelope()
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

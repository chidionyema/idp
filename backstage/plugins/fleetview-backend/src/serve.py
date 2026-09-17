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

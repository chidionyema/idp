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
"""

from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse


def _load_routes(routes_path: Path):
    spec = importlib.util.spec_from_file_location("fleetview_routes", routes_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load routes module at {routes_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_app(routes_path: Path) -> FastAPI:
    routes = _load_routes(routes_path)
    app = FastAPI(title="FleetView", version="1.1.0")

    @app.get(routes.SESSIONS_PATH)
    def sessions():
        body, status = routes.sessions_envelope()
        return JSONResponse(content=body, status_code=status)

    @app.get(routes.STREAM_PATH)
    async def stream():
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
    def mutations_get():
        body, status = routes.mutations_envelope()
        return JSONResponse(content=body, status_code=status)

    @app.post(routes.MUTATIONS_APPROVE_PATH)
    async def mutations_approve_post(request: Request):
        body = await request.json()
        result, status = routes.approve_mutation(body)
        return JSONResponse(content=result, status_code=status)

    @app.post(routes.MUTATIONS_REJECT_PATH)
    async def mutations_reject_post(request: Request):
        body = await request.json()
        result, status = routes.reject_mutation(body)
        return JSONResponse(content=result, status_code=status)

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    return app


def main():
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    port = int(sys.argv[1])
    routes_path = Path(sys.argv[2]).resolve()
    if not routes_path.is_file():
        print(f"routes module not found: {routes_path}", file=sys.stderr)
        sys.exit(2)
    app = build_app(routes_path)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    main()

"""Loopback-only, token-authenticated JSON API and static execution explorer."""

from __future__ import annotations
import argparse
import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from .core import Store
from .analysis import analyse, compare

# The viewer is a single file that sits beside the package, not inside it: in the estate it is
# packages/aei/viewer.html (src layout), and in the delivered reference build it was one level up
# from the package. Both are looked for, and the missing one is named rather than a blank page.
_HERE = Path(__file__).resolve()
_CANDIDATES = (_HERE.parents[2] / "viewer.html", _HERE.parents[1] / "viewer.html")
VIEWER = next((p for p in _CANDIDATES if p.is_file()), _CANDIDATES[0])
MAX_BODY = 65536


def make_handler(store, token):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # Avoid accidentally logging auth headers or request bodies.

        def send(self, status, payload, mime="application/json"):
            raw = (
                json.dumps(payload).encode() if mime == "application/json" else payload
            )
            self.send_response(status)
            self.send_header("Content-Type", mime + "; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; form-action 'none'",
            )
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def authorised(self):
            auth = self.headers.get("Authorization", "")
            return hmac.compare_digest(auth, "Bearer " + token)

        def do_GET(self):
            u = urlparse(self.path)
            # The liveness door. It answers "is this process alive" and nothing else: no count,
            # no run id, no data. The token-authenticated surface is every other path.
            if u.path == "/healthz":
                return self.send(200, {"status": "ok"})
            if not self.authorised():
                return self.send(401, {"error": "unauthorised"})
            q = parse_qs(u.query)
            if u.path == "/health":
                return self.send(200, {"status": "ok", "store": "open"})
            if u.path == "/":
                return self.send(200, VIEWER.read_bytes(), "text/html")
            if u.path == "/api/runs":
                return self.send(200, {"runs": store.runs()})
            if u.path == "/api/run":
                rid = q.get("id", [""])[0]
                if not rid:
                    return self.send(400, {"error": "id required"})
                es = store.events(rid)
                return self.send(
                    200, {"run_id": rid, "events": es, "evaluation": analyse(es)}
                )
            if u.path == "/api/compare":
                a = q.get("a", [""])[0]
                b = q.get("b", [""])[0]
                if not a or not b:
                    return self.send(400, {"error": "a and b required"})
                return self.send(200, compare(store.events(a), store.events(b)))
            return self.send(404, {"error": "not found"})

        def do_POST(self):
            if not self.authorised():
                return self.send(401, {"error": "unauthorised"})
            if urlparse(self.path).path != "/api/events":
                return self.send(404, {"error": "not found"})
            try:
                size = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                return self.send(400, {"error": "bad content length"})
            if size < 1 or size > MAX_BODY:
                return self.send(413, {"error": "body limit exceeded"})
            try:
                obj = json.loads(self.rfile.read(size))
                result = store.append(obj)
            except (ValueError, UnicodeDecodeError) as exc:
                return self.send(400, {"error": str(exc)[:200]})
            return self.send(201 if result["accepted"] else 200, result)

    return Handler


def _open_store(args):
    """SQLite on the laptop, Postgres in OKE. One contract, two backings (packages/aei/src/aei/pgstore.py)."""
    kind = args.store
    if kind == "auto":
        kind = "postgres" if os.environ.get("AEI_POSTGRES_DSN") else "sqlite"
    if kind == "postgres":
        dsn = os.environ.get("AEI_POSTGRES_DSN", "")
        if not dsn:
            raise SystemExit(
                "AEI_POSTGRES_DSN is unset: refusing to fall back to a local file from OKE"
            )
        from .pgstore import PostgresStore

        return PostgresStore(dsn), "postgres"
    return Store(args.db), "sqlite"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="output/aei.sqlite3")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8766)
    p.add_argument(
        "--store",
        default=os.environ.get("AEI_STORE", "auto"),
        choices=("auto", "sqlite", "postgres"),
    )
    args = p.parse_args()
    token = os.environ.get("AEI_API_TOKEN", "")
    if len(token) < 24:
        p.error(
            "AEI_API_TOKEN must be set to a random secret of at least 24 characters"
        )
    if args.host not in ("127.0.0.1", "::1", "localhost"):
        # On the laptop the API is loopback-only, and the reference build says so. In OKE the
        # collector is a SERVICE the router pod pushes to, so it has to bind a routable address.
        # That is not a loosening done silently: it takes an explicit opt-in in the environment
        # (the manifest sets it), the API still refuses every unauthenticated call, and the
        # NetworkPolicy is what limits who may reach the port.
        if os.environ.get("AEI_ALLOW_PUBLIC_BIND") != "1":
            p.error(
                "AEI API is loopback-only; use an authenticated reverse proxy for remote access"
            )
    store, kind = _open_store(args)
    server = ThreadingHTTPServer((args.host, args.port), make_handler(store, token))
    print(
        f"AEI listening on http://{args.host}:{args.port}/ (token required, store={kind})",
        flush=True,
    )
    try:
        server.serve_forever()
    finally:
        server.server_close()
        store.close()


if __name__ == "__main__":
    main()

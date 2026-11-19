"""door -- the network boundary a web agent reaches the console through.

Run it in front of the app. A client with no live session never touches the app: the refusal
happens here, on the socket, before any application code runs. Everything bound is forwarded
unchanged, so this is a gate, not an inspector.

    python3 platform/estate/web/door.py --listen 127.0.0.1:3081 --upstream 127.0.0.1:3080

Refusals, in order: NO_SESSION 401 · EXPIRED_SESSION 403 · WRONG_TICKET 403 · REPLAY 409.
"""
from __future__ import annotations

import argparse
import http.server
import json
import sys
import urllib.error
import urllib.request

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import net_bind  # noqa: E402


def token_from(headers) -> str:
    auth = headers.get("Authorization") or ""
    if auth.startswith("Bearer "):
        return auth[7:].strip()
    cookie = headers.get("Cookie") or ""
    for part in cookie.split(";"):
        k, _, v = part.strip().partition("=")
        if k == "estate_session":
            return v.strip()
    return ""


class Door(http.server.BaseHTTPRequestHandler):
    upstream = "127.0.0.1:3080"
    protocol_version = "HTTP/1.1"

    def log_message(self, *_args):  # the estate's own log carries the decisions
        return

    def _refuse(self, code: int, why: str) -> None:
        body = json.dumps({"refused": why}).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle(self, method: str) -> None:
        if self.path == "/fleet":
            body = json.dumps({"agents": net_bind.recent()}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/health":
            body = b'{"door":"afloat"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        ticket = self.headers.get("X-Estate-Ticket") or ""
        token = token_from(self.headers)
        # A browser navigation from this machine IS the founder's console session. It gets a
        # session bound to the console instruction and a cookie, so the console stays usable
        # without a token in the URL; every other client must present a ticket.
        if not token and self.headers.get("Sec-Fetch-Mode", "") == "navigate" \
                and self.client_address[0] in ("127.0.0.1", "::1"):
            token = net_bind.open_session("founder-console", agent="founder-browser")
            self._bootstrap_cookie = token
        bound, why = net_bind.bind(token, ticket)
        if not bound:
            self._refuse(401 if why == "NO_SESSION" else 403, why)
            return
        fresh, why = net_bind.spend_nonce(token, self.headers.get("X-Estate-Nonce") or "")
        if not fresh:
            self._refuse(409, why)
            return

        net_bind.record(token, self.command, self.path, self.headers.get("User-Agent") or "")
        bootstrap = getattr(self, "_bootstrap_cookie", "")
        length = int(self.headers.get("Content-Length") or 0)
        payload = self.rfile.read(length) if length else None
        req = urllib.request.Request(  # noqa: S310 - the upstream is the operator's own loopback
            f"http://{self.upstream}{self.path}", data=payload, method=method
        )
        for k, v in self.headers.items():
            if k.lower() not in {"host", "authorization", "cookie", "content-length"}:
                req.add_header(k, v)
        try:
            # one loopback hop; the door must not outlive the app it fronts
            with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
                body = resp.read()
                self.send_response(resp.status)
                for k, v in resp.headers.items():
                    if k.lower() not in {"transfer-encoding", "content-length", "connection"}:
                        self.send_header(k, v)
                self.send_header("Content-Length", str(len(body)))
                if bootstrap:
                    self.send_header("Set-Cookie", f"estate_session={bootstrap}; Path=/; HttpOnly; SameSite=Lax")
                self.end_headers()
                self.wfile.write(body)
        except urllib.error.HTTPError as exc:
            self._refuse(exc.code, "UPSTREAM_STATUS")
        except OSError:
            self._refuse(502, "UPSTREAM_UNREACHABLE")

    def do_GET(self):  # noqa: N802 - BaseHTTPRequestHandler's contract
        self._handle("GET")

    def do_POST(self):  # noqa: N802
        self._handle("POST")

    def do_PUT(self):  # noqa: N802
        self._handle("PUT")

    def do_DELETE(self):  # noqa: N802
        self._handle("DELETE")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--listen", default="127.0.0.1:3081")
    ap.add_argument("--upstream", default="127.0.0.1:3080")
    args = ap.parse_args()
    host, _, port = args.listen.rpartition(":")
    Door.upstream = args.upstream
    srv = http.server.ThreadingHTTPServer((host or "127.0.0.1", int(port)), Door)
    print(f"door: {args.listen} -> {args.upstream}", flush=True)
    srv.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

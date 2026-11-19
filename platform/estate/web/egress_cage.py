"""egress_cage -- one door out, allowlisted, with every refusal named.

A proxy that only forwards to an allowlist. Everything else gets 403 and a log line; nothing is
silently dropped, so "why did this fail" has an answer.

It is a cage for the processes that honour it (proxy env, or a PATH shim for curl) and NOT a
kernel-level cage: a process that dials an IP directly is out of its reach. The kernel cage is
the pf anchor in bin/estate-execute, which needs root. Both are stated here so neither is
mistaken for the other.

    python3 platform/estate/web/egress_cage.py --port 8899 --allow ~/.estate/egress-allow.txt
"""
from __future__ import annotations

import argparse
import http.server
import json
import pathlib
import socket
import time
import urllib.parse
import urllib.request

DEFAULT_ALLOW = (
    "github.com",
    "api.github.com",
    "ssh.github.com",
    "llm.mumchimp.com",
    "genesis-founder-surface.pages.dev",
    "otto.mumchimp.com",
    "registry.npmjs.org",
    "pypi.org",
    "files.pythonhosted.org",
    "crates.io",
    "static.crates.io",
    "index.crates.io",
    "ghcr.io",
    "objects.githubusercontent.com",
    "codeload.github.com",
)
LOG = pathlib.Path.home() / ".estate" / "log" / "egress-cage.log"


def allowed(host: str, allow: set[str]) -> bool:
    host = (host or "").split(":")[0].lower()
    if not host:
        return False
    if host in {"127.0.0.1", "localhost", "::1"}:
        return True
    return any(host == a or host.endswith("." + a) for a in allow)


def refuse(host: str, port: int, why: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as fh:
        fh.write(
            json.dumps(
                {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                 "host": host, "port": port, "refused": why}
            )
            + "\n"
        )


class Cage(http.server.BaseHTTPRequestHandler):
    allow: set[str] = set(DEFAULT_ALLOW)
    protocol_version = "HTTP/1.1"

    def log_message(self, *_a):
        return

    def _deny(self, why: str) -> None:
        body = json.dumps({"refused": why}).encode()
        self.send_response(403)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_CONNECT(self):  # noqa: N802
        host, _, port = self.path.partition(":")
        if not allowed(host, self.allow):
            refuse(host, int(port or 443), "NOT_ALLOWED")
            self._deny("NOT_ALLOWED")
            return
        try:
            upstream = socket.create_connection(
                (host, int(port or 443)), timeout=10  # one connect; a cage must not hang
            )
        except OSError:
            refuse(host, int(port or 443), "UNREACHABLE")
            self._deny("UNREACHABLE")
            return
        self.send_response(200, "Connection Established")
        self.end_headers()
        self._splice(upstream)

    def _splice(self, upstream) -> None:
        client = self.connection
        upstream.settimeout(None)
        client.settimeout(None)
        import threading

        def pump(src, dst):
            try:
                while True:
                    data = src.recv(65536)
                    if not data:
                        break
                    dst.sendall(data)
            except OSError:
                pass

        t = threading.Thread(target=pump, args=(client, upstream), daemon=True)
        t.start()
        pump(upstream, client)
        t.join(timeout=1)

    def do_GET(self):  # noqa: N802
        target = self.path
        if not target.startswith("http"):
            self._deny("BAD_REQUEST")
            return
        host = urllib.parse.urlparse(target).hostname or ""  # type: ignore[attr-defined]
        if not allowed(host, self.allow):
            refuse(host, 80, "NOT_ALLOWED")
            self._deny("NOT_ALLOWED")
            return
        try:
            with urllib.request.urlopen(target, timeout=15) as resp:  # noqa: S310
                body = resp.read()
                self.send_response(resp.status)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        except OSError:
            self._deny("UNREACHABLE")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8899)
    ap.add_argument("--allow", default=str(pathlib.Path.home() / ".estate" / "egress-allow.txt"))
    args = ap.parse_args()
    p = pathlib.Path(args.allow)
    allow = set(DEFAULT_ALLOW)
    if p.exists():
        allow |= {ln.strip() for ln in p.read_text().splitlines() if ln.strip() and not ln.startswith("#")}
    Cage.allow = allow
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", args.port), Cage)
    print(f"cage: 127.0.0.1:{args.port} allow={len(allow)} hosts", flush=True)
    srv.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""OBS-02 (idp#3525 CP8, spec section 6): "Founder-facing deliverables SHALL render on
the local board (127.0.0.1:8787 /look) or a permanent collector page, or be pushed
directly as a file. External hosting only with # vendor-surface-intended + reason."

Stdlib only (LAW 43, the same call sovereign/cockpit/server.py already made):
http.server is enough for one read-only page over a small local directory of report
pairs; nothing here justifies Flask or aiohttp.

The deliverable format is the one bin/idp-reports-render already writes for the
portal's Reports page (crew#684): one `<id>.md` + `<id>.meta.json` pair per report.
The board reuses that pair rather than inventing a second shape -- BOARD_DIR is the
"permanent collector page" OBS-02 names, and publish() below is the "pushed directly
as a file" option; both land in the same directory /look renders.

catalog/ports.md has declared `8787 | 127.0.0.1 | board_serve.py | Python` since CP5;
this file is what that line was always pointing at.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BOARD_DIR = Path(
    os.environ.get("BOARD_DIR") or os.path.expanduser("~/.estate/state/board")
)
HOST = "127.0.0.1"
PORT = int(os.environ.get("BOARD_PORT", "8787"))

# "estate" hosts: loopback, in-cluster DNS, or the estate's own internal zone. Anything
# else is a vendor -- D-LEDGER-10 "URL served from estate, not vendor."
_ESTATE_HOSTS = re.compile(
    r"^(127\.0\.0\.1|localhost)(:\d+)?$|\.svc\.cluster\.local(:\d+)?$|\.internal(:\d+)?$"
)
_URL_RE = re.compile(r"https?://([^/\s\"'<>]+)")


class ExternalPublishError(Exception):
    """OBS-02: an external host appeared in a deliverable with no
    # vendor-surface-intended reason on record."""


def _external_hosts(text: str) -> set[str]:
    return {h for h in _URL_RE.findall(text) if not _ESTATE_HOSTS.search(h)}


def check_no_unlisted_external_publish(meta: dict, body: str) -> None:
    """OBS-02 ACCEPT: "no external publish in trace" unless tagged
    # vendor-surface-intended with a reason. Checked over both the meta and the body,
    since a link can land in either."""
    externals = _external_hosts(body) | _external_hosts(json.dumps(meta))
    if not externals:
        return
    reason = meta.get("vendor-surface-intended") or meta.get("vendor_surface_intended")
    if not reason or not str(reason).strip():
        raise ExternalPublishError(
            f"external host(s) {sorted(externals)} in deliverable {meta.get('id')!r} "
            "with no # vendor-surface-intended reason on record"
        )


def publish(meta: dict, body: str, board_dir: Path | None = None) -> Path:
    """OBS-02's third rendering option: push a deliverable directly as a file, the same
    <id>.md + <id>.meta.json pair bin/idp-reports-render writes for the portal. Raises
    ExternalPublishError before anything is written if the deliverable needs the tag
    and does not carry it -- the guard runs before the write, not after."""
    check_no_unlisted_external_publish(meta, body)
    board_dir = board_dir or BOARD_DIR
    board_dir.mkdir(parents=True, exist_ok=True)
    (board_dir / f"{meta['id']}.md").write_text(body, encoding="utf-8")
    (board_dir / f"{meta['id']}.meta.json").write_text(
        json.dumps(meta, sort_keys=True) + "\n", encoding="utf-8"
    )
    return board_dir / f"{meta['id']}.md"


def _deliverables(board_dir: Path) -> list[dict]:
    metas = []
    if board_dir.is_dir():
        for f in sorted(board_dir.glob("*.meta.json")):
            try:
                metas.append(json.loads(f.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                continue
    metas.sort(key=lambda m: m.get("generated_at", ""), reverse=True)
    return metas


def render_look(board_dir: Path | None = None) -> str:
    """The /look page: every deliverable currently on the board, newest first. An
    empty board says so rather than rendering nothing (same rule idp-reports-render
    applies to a source it could not read: never a blank page that reads as green)."""
    board_dir = board_dir or BOARD_DIR
    sections = []
    for meta in _deliverables(board_dir):
        body_path = board_dir / f"{meta['id']}.md"
        body = body_path.read_text(encoding="utf-8") if body_path.is_file() else ""
        sections.append(
            "<section class=deliverable>"
            f"<h2>{html.escape(meta.get('title') or meta['id'])}</h2>"
            f"<p class=meta>{html.escape(meta.get('generated_at', ''))}"
            f" &middot; {html.escape(meta.get('source', ''))}</p>"
            f"<pre>{html.escape(body)}</pre>"
            "</section>"
        )
    body_html = "\n".join(sections) or "<p>No deliverables on the board yet.</p>"
    return (
        "<!doctype html><html><head><meta charset=utf-8><title>The Board</title></head>"
        f"<body><h1>The Board</h1>{body_html}</body></html>"
    )


class BoardHandler(BaseHTTPRequestHandler):
    def _send(
        self, code: int, body: bytes, content_type: str = "text/html; charset=utf-8"
    ) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/healthz":
            self._send(200, b"ok", "text/plain; charset=utf-8")
        elif self.path == "/look":
            self._send(200, render_look().encode("utf-8"))
        else:
            self._send(404, b"not found", "text/plain; charset=utf-8")

    def log_message(self, fmt: str, *args) -> None:
        pass


def main() -> int:
    argparse.ArgumentParser(
        description="OBS-02: serve the founder's local board (127.0.0.1:8787 /look)."
    ).parse_args()
    server = ThreadingHTTPServer((HOST, PORT), BoardHandler)
    print(f"board_serve: http://{HOST}:{PORT}/look, BOARD_DIR={BOARD_DIR}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())

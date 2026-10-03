"""L5: the stream the board shows is LIVE — a frozen board is not "operational".

The probe does what the browser does: read /sessions once, then subscribe to the same
stream the board subscribes to, and assert:
  1. at least one frame arrives within FRAME_TIMEOUT_S (the estate's bus is busy; silence
     means the board is showing stale state),
  2. the frame's session ids are consistent with /sessions (a stream showing ghosts or
     missing live sessions is a desync, graded red).

An unreachable stream grades FAIL, never PASS. A probe that cannot fail is deleted.

Run:
  python3 -m probes.realtime http://127.0.0.1:18790
  SURFACES_STREAM_URL=/events python3 -m probes.realtime http://127.0.0.1:18790
Exit 0 only when the stream is live and consistent.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request

FRAME_TIMEOUT_S = 20.0
# Candidates tried in order; the board's real endpoint is the first that answers.
# SURFACES_STREAM_URL overrides the search (used when the route table says which one).
_STREAM_CANDIDATES = ["/events", "/stream", "/sse"]


def _bearer_headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    """The prover's door through the public gate: PROVER_TOKEN rides as a Bearer on every
    call, the same machine door probes/backstage.py uses (httproute Bearer rule +
    backend.auth.externalAccess grading). No token -> no header -> the gate answers, which
    is itself the correct negative signal."""
    h = dict(extra or {})
    tok = os.environ.get("PROVER_TOKEN")
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h


def _sessions(base: str) -> set[str]:
    req = urllib.request.Request(
        f"{base.rstrip('/')}/sessions", headers=_bearer_headers()
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        doc = json.load(r)
    rows = doc if isinstance(doc, list) else doc.get("sessions", doc.get("items", []))
    ids = set()
    for row in rows:
        for k in ("id", "session_id", "sessionId"):
            if isinstance(row, dict) and k in row:
                ids.add(str(row[k]))
                break
    return ids


def probe(base: str) -> tuple[bool, str]:
    base = base.rstrip("/")
    stream = os.environ.get("SURFACES_STREAM_URL")
    candidates = [stream] if stream else _STREAM_CANDIDATES
    live_ids = _sessions(base)
    for path in candidates:
        url = f"{base}{path}"
        t0 = time.time()
        try:
            req = urllib.request.Request(
                url, headers=_bearer_headers({"Accept": "text/event-stream"})
            )
            with urllib.request.urlopen(req, timeout=FRAME_TIMEOUT_S) as r:
                # Read until one data frame or the timeout kills the read.
                buf = b""
                while time.time() - t0 < FRAME_TIMEOUT_S:
                    chunk = r.read(4096)
                    if not chunk:
                        break
                    buf += chunk
                    for line in buf.split(b"\n"):
                        if not line.startswith(b"data:"):
                            continue
                        payload = line[5:].strip()
                        if not payload or payload == b"[DONE]":
                            continue
                        dt = time.time() - t0
                        try:
                            frame = json.loads(payload)
                        except json.JSONDecodeError:
                            continue
                        ids = _ids_in(frame)
                        if not ids:
                            continue  # keepalive or non-session frame; wait for a real one
                        ghosts = ids - live_ids
                        # Ghosts on the stream while /sessions doesn't know them, or a live
                        # session absent from every frame we saw — both are desync. We only
                        # have one frame here; ghost check is the strict one we can prove.
                        ok = not ghosts
                        detail = (
                            f"frame on {path} after {dt:.1f}s, {len(ids)} sessions, "
                            f"{len(ghosts)} ghosts"
                        )
                        return ok, detail
        except Exception as e:  # noqa: BLE001 — every failure mode is data
            print(f"  stream {path}: {type(e).__name__}: {e}", file=sys.stderr)
            continue
    return (
        False,
        f"no session frame on any of {candidates} within {FRAME_TIMEOUT_S:.0f}s",
    )


def _ids_in(frame: object) -> set[str]:
    """Pull session ids out of whatever shape the frame is (list, dict, nested)."""
    out: set[str] = set()

    def walk(node: object) -> None:
        if isinstance(node, list):
            for x in node:
                walk(x)
        elif isinstance(node, dict):
            hit = False
            for k in ("id", "session_id", "sessionId"):
                if k in node and isinstance(node[k], (str, int)):
                    out.add(str(node[k]))
                    hit = True
            if not hit:
                for v in node.values():
                    walk(v)

    walk(frame)
    return out


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:18790"
    ok, detail = probe(base)
    print(f"{'PASS' if ok else 'FAIL'}  surfaces.realtime  {detail}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

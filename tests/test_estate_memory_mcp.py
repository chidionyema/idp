"""The one memory behind the one voice: mcp/plugins/estate_memory.py.

Every case here runs the plugin against a real HTTP server on a real socket -- the store's
own shapes, its silence and its garbage -- because the thing worth grading is what the client
does over the wire, not what this repository says about it.

Proves the things the founder's ask depends on: a structured ingest every caller shapes the
same way, one namespace so context crosses surfaces, a deterministic key so a re-remembered
subject updates rather than piles up, exact filtering on the fields `remember` wrote even
though the server's own list endpoint cannot return them, the interceptor's Host-header
routing done correctly (crew#4602 follow-up: the one subtlety that 404s silently when it is
backwards), and a store that can be down -- or unauthorized, or still asleep -- without taking
an agent's answer with it. One test (`test_remember_then_recall_round_trips_through_the_real_
server`) runs no stub at all: the real platform/unified-memory-server main.py, against a
throwaway pgserver Postgres, on a real uvicorn socket.
"""

from __future__ import annotations

import importlib.util
import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "estate_memory",
    Path(__file__).resolve().parents[1] / "mcp" / "plugins" / "estate_memory.py",
)
memory = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(memory)


class Store:
    """A stand-in for unified-memory-server: it records every request -- method, path, the
    real headers object (so a duplicate header is visible, not collapsed by dict()) and the
    parsed JSON body -- and answers with a canned response."""

    def __init__(self, answer, status: int = 200):
        self.answer = answer
        self.status = status
        self.seen: list = []
        handler = self._handler()
        self.server = HTTPServer(("127.0.0.1", 0), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        # The port is real and the tests race the thread that binds it, so wait for the
        # socket itself rather than for a sleep to be long enough.
        socket.create_connection(
            ("127.0.0.1", self.server.server_port), timeout=2
        ).close()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server.server_port}"

    def _handler(self):
        store = self

        class Handler(BaseHTTPRequestHandler):
            def _handle(self):
                length = int(self.headers.get("content-length", "0"))
                raw = self.rfile.read(length).decode("utf-8") if length else ""
                body = json.loads(raw) if raw else None
                store.seen.append((self.command, self.path, self.headers, body))
                self.send_response(store.status)
                self.send_header("content-type", "application/json")
                self.end_headers()
                payload = store.answer
                out = payload if isinstance(payload, str) else json.dumps(payload)
                self.wfile.write(out.encode("utf-8"))

            do_GET = _handle
            do_PUT = _handle

            def log_message(self, *_args):
                pass

        return Handler

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def cfg_for(url: str, **over) -> dict:
    base = {
        "url": url,
        "host": "",
        "namespace": "agent",
        "token": "",
        "timeout_s": 5.0,
        "byte_ceiling": 8000,
    }
    base.update(over)
    return base


@pytest.fixture
def store():
    made = []

    def make(answer, status=200):
        s = Store(answer, status)
        made.append(s)
        return s

    yield make
    for s in made:
        s.close()


def test_remember_puts_the_envelope_to_a_deterministic_key(store):
    """One namespace serves every surface, and the key is a slug of subject: re-remembering
    the same subject must land on the same PUT path, so a chat's fact and an agent's fact
    converge instead of a namespace filling with duplicates."""
    s = store({"status": "CREATED", "version": 1})
    out = memory.do_remember(
        "the deepseek lane was revoked and hindsight stopped extracting",
        "hindsight",
        "incident",
        ["Memory", "memory", " lane "],
        "session-36c9262c",
        cfg=cfg_for(s.url),
    )
    assert out == {
        "written": True,
        "namespace": "agent",
        "key": "hindsight",
        "status": "CREATED",
        "version": 1,
    }
    method, path, _headers, body = s.seen[0]
    assert method == "PUT" and path == "/memories/agent/hindsight"
    envelope = json.loads(body["content"])
    assert envelope == {
        "text": "the deepseek lane was revoked and hindsight stopped extracting",
        "subject": "hindsight",
        "kind": "incident",
        "tags": ["lane", "memory"],
        "source": "session-36c9262c",
    }
    assert body["provenance"] == envelope
    assert body["namespace"] == "agent" and body["key"] == "hindsight"


def test_an_unknown_kind_becomes_a_fact_rather_than_a_refusal(store):
    """A fence that refuses correct work is an outage (LAW 38): a caller guessing the wrong
    kind still gets its memory written, filed under the safe one."""
    s = store({"status": "CREATED", "version": 1})
    out = memory.do_remember("x", "otto", "musing", [], "mcp", cfg=cfg_for(s.url))
    assert out["written"] is True
    envelope = json.loads(s.seen[0][3]["content"])
    assert envelope["kind"] == "fact"


def test_a_subject_with_no_letters_still_gets_a_stable_key(store):
    """No subject: still written (LAW 38 again), and the same content lands on the same key
    twice running, so it is at least idempotent even with nothing to converge it by name."""
    s = store({"status": "CREATED", "version": 1})
    memory.do_remember(
        "the same fact, twice", "", "fact", [], "mcp", cfg=cfg_for(s.url)
    )
    memory.do_remember(
        "the same fact, twice", "   ", "fact", [], "mcp", cfg=cfg_for(s.url)
    )
    paths = [path for _, path, _, _ in s.seen]
    assert paths[0] == paths[1] and paths[0].startswith("/memories/agent/note-")


def test_recall_gets_the_namespace_and_unwraps_the_envelope(store):
    """The list endpoint (main.py's memory_list_current) returns `content` only, never
    `provenance` -- so the fields `remember` promised must be readable from `content` alone,
    which is exactly what `remember`'s own envelope is for."""

    def fact(key, text, subject, kind, tags, valid_from):
        return {
            "key": key,
            "content": json.dumps(
                {
                    "text": text,
                    "subject": subject,
                    "kind": kind,
                    "tags": tags,
                    "source": "mcp",
                }
            ),
            "trust_tier": "raw_source",
            "version": 1,
            "valid_from": valid_from,
            "recorded_at": valid_from,
        }

    s = store(
        {
            "namespace": "agent",
            "facts": [
                fact(
                    "otto-gateway",
                    "the door moved",
                    "otto-gateway",
                    "decision",
                    ["door", "telegram"],
                    "2026-09-20T00:00:00+00:00",
                ),
                fact(
                    "superset",
                    "unrelated",
                    "superset",
                    "fact",
                    [],
                    "2026-09-20T00:00:00+00:00",
                ),
                fact(
                    "otto-gateway-old",
                    "wrong kind",
                    "otto-gateway",
                    "fact",
                    [],
                    "2026-09-19T00:00:00+00:00",
                ),
            ],
        }
    )
    out = memory.do_recall(
        "the door", "otto-gateway", "decision", ["door"], 5, cfg=cfg_for(s.url)
    )
    assert [m["text"] for m in out["memories"]] == ["the door moved"]
    method, path, _headers, _body = s.seen[0]
    assert method == "GET" and path == "/memories/agent"


def test_recall_reads_a_fact_written_some_other_way(store):
    """A row that is not the envelope shape (hand-written, curl, an older format) is still
    readable as plain text, never dropped for failing to parse -- degrade, never raise."""
    s = store(
        {
            "facts": [
                {
                    "key": "manual",
                    "content": "written by hand, not JSON",
                    "version": 1,
                    "valid_from": "2026-09-20T00:00:00+00:00",
                }
            ]
        }
    )
    out = memory.do_recall("written by hand", "", "", [], 5, cfg=cfg_for(s.url))
    assert out["memories"] == [
        {
            "text": "written by hand, not JSON",
            "metadata": {
                "subject": "",
                "kind": "",
                "tags": [],
                "source": "",
                "key": "manual",
                "valid_from": "2026-09-20T00:00:00+00:00",
            },
        }
    ]


def test_recall_orders_newest_first(store):
    def fact(key, text, valid_from):
        return {
            "key": key,
            "content": json.dumps(
                {
                    "text": text,
                    "subject": "",
                    "kind": "fact",
                    "tags": [],
                    "source": "mcp",
                }
            ),
            "version": 1,
            "valid_from": valid_from,
        }

    s = store(
        {
            "facts": [
                fact("a", "older", "2026-09-01T00:00:00+00:00"),
                fact("b", "newer", "2026-09-20T00:00:00+00:00"),
            ]
        }
    )
    out = memory.do_recall("", "", "", [], 5, cfg=cfg_for(s.url))
    assert [m["text"] for m in out["memories"]] == ["newer", "older"]


def test_the_interceptor_routes_on_an_explicit_host_header_not_the_dialled_address(
    store,
):
    """The KEDA HTTP add-on interceptor forwards purely on the Host header (its
    HTTPScaledObject names unified-memory.estate.internal as the only host it forwards) --
    dialling its address and sending ITS OWN name, or no override at all, 404s in production
    while a synthetic probe against the raw server URL keeps passing silently. Assert on the
    wire, via the real headers object (not a dict, which would collapse a duplicate): exactly
    one Host header, and it is the interceptor's configured name, never the loopback address
    this test actually dialled."""
    s = store({"facts": []})
    memory.do_recall(
        "q",
        "",
        "",
        [],
        5,
        cfg=cfg_for(s.url, host="unified-memory.estate.internal", token="tok-123"),
    )
    _method, _path, headers, _body = s.seen[0]
    assert headers.get_all("Host") == ["unified-memory.estate.internal"]
    assert headers.get("Authorization") == "Bearer tok-123"


def test_no_host_override_leaves_the_dialled_address_as_host(store):
    """A direct connection (local dev, or the test server below) never sets ESTATE_MEMORY_HOST,
    and must not send a stray header in that case -- exactly one Host line either way."""
    s = store({"facts": []})
    memory.do_recall("q", "", "", [], 5, cfg=cfg_for(s.url))
    _method, _path, headers, _body = s.seen[0]
    assert headers.get_all("Host") == [f"127.0.0.1:{s.server.server_port}"]


def test_a_store_that_is_down_never_costs_the_answer(store):
    """The socket is real and then it is gone: memory being unreachable is an error field,
    never an exception an agent's answer dies on."""
    s = store({})
    url = s.url
    s.close()
    assert memory.do_recall("q", "", "", [], 5, cfg=cfg_for(url))["memories"] == []
    assert (
        memory.do_remember("c", "s", "fact", [], "mcp", cfg=cfg_for(url))["written"]
        is False
    )


def test_a_refusal_from_the_server_is_an_error_field_not_a_crash(store):
    """403 (bad/revoked token) and 422 (the OWASP write guard) are real answers, not a
    connectivity failure -- the caller should see why, not "unreachable"."""
    s = store({"detail": "Access token invalid or revoked"}, status=403)
    out = memory.do_remember("c", "s", "fact", [], "mcp", cfg=cfg_for(s.url))
    assert out["written"] is False
    assert "403" in out["error"]


def test_a_body_that_is_not_json_is_an_error_not_a_crash(store):
    s = store("<html>gateway timeout</html>")
    out = memory.do_recall("q", "", "", [], 5, cfg=cfg_for(s.url))
    assert out["memories"] == [] and "not JSON" in out["error"]


def test_unset_url_never_opens_a_socket():
    off = cfg_for("")
    assert memory.do_recall("q", "", "", [], 5, cfg=off)["memories"] == []
    assert memory.do_remember("c", "s", "fact", [], "mcp", cfg=off)["written"] is False


def test_empty_content_is_refused_before_a_socket_opens(store):
    s = store({})
    out = memory.do_remember("   ", "s", "fact", [], "mcp", cfg=cfg_for(s.url))
    assert out["written"] is False and s.seen == []


def test_a_non_http_url_is_refused_before_urllib_sees_it():
    body, error = memory.request(
        cfg_for("file:///etc/passwd"), "GET", "/memories/agent"
    )
    assert body is None and "http(s)" in error


def test_the_recall_payload_is_held_under_the_ceiling(store):
    facts = [
        {
            "key": f"k{i}",
            "content": json.dumps(
                {
                    "text": "x" * 400,
                    "subject": "",
                    "kind": "fact",
                    "tags": [],
                    "source": "mcp",
                }
            ),
            "version": 1,
            "valid_from": f"2026-09-{i + 1:02d}T00:00:00+00:00",
        }
        for i in range(20)
    ]
    s = store({"facts": facts})
    out = memory.do_recall("", "", "", [], 20, cfg=cfg_for(s.url, byte_ceiling=1000))
    assert 0 < len(out["memories"]) < 20


def test_remember_then_recall_round_trips_through_the_real_server(tmp_path):
    """No stub: a real unified-memory-server (platform/unified-memory-server/main.py, its
    real lifespan and schema) against a throwaway pgserver Postgres, on a real uvicorn socket
    -- and this plugin's own do_remember/do_recall calling it exactly as estate-mcp will in
    production. This is the test that fails if the field mapping (namespace/key/envelope) is
    wrong even when every mocked-store test above still passes."""
    pgserver = pytest.importorskip("pgserver")
    pytest.importorskip("psycopg")
    pytest.importorskip("psycopg_pool")
    uvicorn = pytest.importorskip("uvicorn")

    import importlib.util as ilu
    import os
    import secrets
    import sys
    import time
    import uuid

    server_dir = (
        Path(__file__).resolve().parents[1] / "platform" / "unified-memory-server"
    )
    pg = pgserver.get_server(str(tmp_path / "pg"), cleanup_mode="delete")
    try:
        token = secrets.token_urlsafe(32)
        token_path = tmp_path / "token"
        token_path.write_text(token)

        for name in ("DATABASE_URL", "DATABASE_URL_FILE", "MEMORY_SURFACE_TOKEN_FILE"):
            os.environ.pop(name, None)
        os.environ["DATABASE_URL"] = pg.get_uri()
        os.environ["MEMORY_SURFACE_TOKEN_FILE"] = str(token_path)
        if str(server_dir) not in sys.path:
            sys.path.insert(0, str(server_dir))
        spec = ilu.spec_from_file_location(
            "umem_wiring_" + uuid.uuid4().hex[:8], server_dir / "main.py"
        )
        server_module = ilu.module_from_spec(spec)
        spec.loader.exec_module(server_module)

        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]

        uv_config = uvicorn.Config(
            server_module.app, host="127.0.0.1", port=port, log_level="error"
        )
        uv_server = uvicorn.Server(uv_config)
        thread = threading.Thread(target=uv_server.run, daemon=True)
        thread.start()
        deadline = time.time() + 20
        while not uv_server.started and time.time() < deadline and thread.is_alive():
            time.sleep(0.05)
        assert uv_server.started, "the real unified-memory-server never came up"
        try:
            cfg = cfg_for(f"http://127.0.0.1:{port}", token=token)

            written = memory.do_remember(
                "PoBR agent pub key mounted for shadow-verify",
                "shadow-verify",
                "decision",
                ["pobr"],
                "test",
                cfg=cfg,
            )
            assert written["written"] is True, written
            assert written["status"] == "CREATED"

            found = memory.do_recall(
                "pub key", "shadow-verify", "decision", ["pobr"], 5, cfg=cfg
            )
            assert [m["text"] for m in found["memories"]] == [
                "PoBR agent pub key mounted for shadow-verify"
            ]

            # Re-remembering the same subject updates the row instead of a second one.
            updated = memory.do_remember(
                "PoBR agent pub key rotated",
                "shadow-verify",
                "decision",
                ["pobr"],
                "test",
                cfg=cfg,
            )
            assert updated["written"] is True and updated["status"] == "UPDATED"
            again = memory.do_recall("rotated", "shadow-verify", "", [], 5, cfg=cfg)
            assert [m["text"] for m in again["memories"]] == [
                "PoBR agent pub key rotated"
            ]

            # A wrong bearer token is a 403, surfaced as an error, never a crash.
            wrong = memory.do_recall(
                "rotated",
                "",
                "",
                [],
                5,
                cfg=cfg_for(f"http://127.0.0.1:{port}", token="nope"),
            )
            assert wrong["memories"] == [] and "403" in wrong["error"]
        finally:
            uv_server.should_exit = True
            thread.join(timeout=10)
    finally:
        pg.cleanup()

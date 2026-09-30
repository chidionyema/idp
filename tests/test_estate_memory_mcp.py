"""The one memory behind the one voice: mcp/plugins/estate_memory.py -> the unified memory server.

Every case runs the plugin against a real HTTP server on a real socket that speaks the unified
memory server's shapes (PUT /memories/{ns}/{key}, GET /memories/{ns}), because the thing worth
grading is what the client does over the wire, not what this repository says about it.

Proves what the founder's ask depends on: a structured ingest every caller shapes the same way,
one namespace so context crosses surfaces, exact filtering on those fields, the Host and token
the interceptor and server require, and a store that can be down without costing an answer.
"""

from __future__ import annotations

import importlib.util
import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import unquote

import pytest

SPEC = importlib.util.spec_from_file_location(
    "estate_memory",
    Path(__file__).resolve().parents[1] / "mcp" / "plugins" / "estate_memory.py",
)
memory = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(memory)

TOKEN = "surface-token-for-tests"


class Store:
    """A stand-in for the unified memory server: it keeps what was PUT, lists it on GET,
    refuses a wrong token, and records every request it saw."""

    def __init__(self, raw: str | None = None, status: int = 200):
        self.raw, self.status = raw, status
        self.facts: dict = {}
        self.seen: list = []
        self.server = HTTPServer(("127.0.0.1", 0), self._handler())
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        socket.create_connection(
            ("127.0.0.1", self.server.server_port), timeout=2
        ).close()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server.server_port}"

    def _handler(self):
        store = self

        class Handler(BaseHTTPRequestHandler):
            def _answer(self, status, payload):
                self.send_response(status)
                self.send_header("content-type", "application/json")
                self.end_headers()
                raw = store.raw if store.raw is not None else json.dumps(payload)
                self.wfile.write(raw.encode("utf-8"))

            def _record(self, body=None):
                store.seen.append(
                    (self.command, unquote(self.path), dict(self.headers), body)
                )
                return self.headers.get("authorization") == f"Bearer {TOKEN}"

            def do_PUT(self):  # noqa: N802 - the stdlib's own name
                body = json.loads(self.rfile.read(int(self.headers["content-length"])))
                if not self._record(body):
                    return self._answer(
                        403, {"detail": "Access token invalid or revoked"}
                    )
                store.facts[body["key"]] = body
                self._answer(
                    store.status, {"status": "CREATED", "id": "x", "version": 1}
                )

            def do_GET(self):  # noqa: N802
                if not self._record():
                    return self._answer(
                        403, {"detail": "Access token invalid or revoked"}
                    )
                facts = [
                    {
                        "key": k,
                        "content": f["content"],
                        "provenance": f.get("provenance", {}),
                        "recorded_at": f"2026-09-29T18:00:{i:02d}+00:00",
                    }
                    for i, (k, f) in enumerate(store.facts.items())
                ]
                self._answer(store.status, {"namespace": "estate", "facts": facts})

            def log_message(self, *_args):
                pass

        return Handler

    def close(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def token_file(tmp_path):
    p = tmp_path / "token"
    p.write_text(TOKEN + "\n")
    return str(p)


@pytest.fixture
def store():
    made = []

    def make(raw=None, status=200):
        s = Store(raw, status)
        made.append(s)
        return s

    yield make
    for s in made:
        s.close()


@pytest.fixture
def cfg_for(token_file):
    def make(url: str, **over) -> dict:
        base = {
            "url": url,
            "host": "unified-memory.estate.internal",
            "token_file": token_file,
            "namespace": "estate",
            "timeout_s": 5.0,
            "byte_ceiling": 8000,
        }
        base.update(over)
        return base

    return make


def test_one_namespace_serves_every_surface_with_the_host_and_token_it_needs(
    store, cfg_for
):
    s = store()
    memory.do_remember(
        "a thing happened", "otto", "fact", [], "mcp", cfg=cfg_for(s.url)
    )
    memory.do_recall("thing", "", "", [], 5, cfg=cfg_for(s.url))
    (m1, p1, h1, _), (m2, p2, h2, _) = s.seen
    assert (m1, m2) == ("PUT", "GET")
    assert p1.startswith("/memories/estate/fact.otto.") and p2 == "/memories/estate"
    assert h1["Host"] == h2["Host"] == "unified-memory.estate.internal"


def test_remember_then_recall_returns_the_memory_with_its_fields(store, cfg_for):
    s = store()
    out = memory.do_remember(
        "the deepseek lane was revoked",
        "llm",
        "incident",
        ["Router", "router", " lane "],
        "session-1",
        cfg=cfg_for(s.url),
    )
    assert out["written"] is True and out["version"] == 1
    back = memory.do_recall(
        "deepseek revoked", "llm", "incident", ["lane"], 5, cfg=cfg_for(s.url)
    )
    assert back["memories"] == [
        {
            "text": "the deepseek lane was revoked",
            "metadata": {
                "subject": "llm",
                "kind": "incident",
                "source": "session-1",
                "tags": "lane,router",
            },
        }
    ]


def test_the_same_content_twice_is_one_memory(store, cfg_for):
    s = store()
    for _ in range(2):
        memory.do_remember("same", "otto", "fact", [], "mcp", cfg=cfg_for(s.url))
    assert len(s.facts) == 1


def test_an_unknown_kind_becomes_a_fact_rather_than_a_refusal(store, cfg_for):
    s = store()
    out = memory.do_remember("x", "otto", "musing", [], "mcp", cfg=cfg_for(s.url))
    assert out["written"] is True and out["metadata"]["kind"] == "fact"


def test_recall_filters_on_the_fields_and_words(store, cfg_for):
    s = store()
    c = cfg_for(s.url)
    memory.do_remember(
        "the door moved", "otto-gateway", "decision", ["door"], "a", cfg=c
    )
    memory.do_remember("unrelated", "superset", "fact", [], "a", cfg=c)
    memory.do_remember("the door is wrong kind", "otto-gateway", "fact", [], "a", cfg=c)
    out = memory.do_recall("door", "otto-gateway", "decision", ["door"], 5, cfg=c)
    assert [m["text"] for m in out["memories"]] == ["the door moved"]
    assert memory.do_recall("absent-word", "", "", [], 5, cfg=c)["memories"] == []


def test_a_wrong_token_is_an_error_not_a_crash(store, cfg_for, tmp_path):
    s = store()
    bad = tmp_path / "bad"
    bad.write_text("nope")
    out = memory.do_remember(
        "c", "s", "fact", [], "mcp", cfg=cfg_for(s.url, token_file=str(bad))
    )
    assert out["written"] is False and "403" in out["error"]


def test_no_token_file_never_opens_a_socket(store, cfg_for):
    s = store()
    out = memory.do_recall(
        "q", "", "", [], 5, cfg=cfg_for(s.url, token_file="/nonexistent")
    )
    assert out["memories"] == [] and "token" in out["error"] and s.seen == []


def test_a_store_that_is_down_never_costs_the_answer(store, cfg_for):
    s = store()
    url = s.url
    s.close()
    assert memory.do_recall("q", "", "", [], 5, cfg=cfg_for(url))["memories"] == []
    assert (
        memory.do_remember("c", "s", "fact", [], "mcp", cfg=cfg_for(url))["written"]
        is False
    )


def test_a_body_that_is_not_json_is_an_error_not_a_crash(store, cfg_for):
    s = store(raw="<html>gateway timeout</html>")
    out = memory.do_recall("q", "", "", [], 5, cfg=cfg_for(s.url))
    assert out["memories"] == [] and "not JSON" in out["error"]


def test_unset_url_never_opens_a_socket(cfg_for):
    off = cfg_for("")
    assert memory.do_recall("q", "", "", [], 5, cfg=off)["memories"] == []
    assert memory.do_remember("c", "s", "fact", [], "mcp", cfg=off)["written"] is False


def test_a_non_http_url_is_refused_before_urllib_sees_it(cfg_for):
    body, error = memory.call(cfg_for("file:///etc/passwd"), "GET")
    assert body is None and "http(s)" in error


def test_the_recall_payload_is_held_under_the_ceiling(store, cfg_for):
    s = store()
    c = cfg_for(s.url, byte_ceiling=1000)
    for i in range(20):
        memory.do_remember(f"{i} " + "x" * 400, "s", "fact", [], "mcp", cfg=c)
    out = memory.do_recall("", "", "", [], 20, cfg=c)
    assert 0 < len(out["memories"]) < 20

"""The one memory behind the one voice: mcp/plugins/estate_memory.py.

Every case here runs the plugin against a real HTTP server on a real socket -- the store's
own shapes, its silence and its garbage -- because the thing worth grading is what the client
does over the wire, not what this repository says about it.

Proves the four things the founder's ask depends on: a structured ingest every caller shapes
the same way, one bank so context crosses surfaces, exact filtering on those fields, and a
store that can be down without taking an agent's answer with it.
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
    """A stand-in for Hindsight: it records what arrived and answers what it was told to."""

    def __init__(self, answer: dict | str, status: int = 200):
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
            def do_POST(self):  # noqa: N802 - the stdlib's own name
                length = int(self.headers.get("content-length", "0"))
                body = self.rfile.read(length).decode("utf-8")
                store.seen.append((self.path, json.loads(body)))
                self.send_response(store.status)
                self.send_header("content-type", "application/json")
                self.end_headers()
                payload = store.answer
                raw = payload if isinstance(payload, str) else json.dumps(payload)
                self.wfile.write(raw.encode("utf-8"))

            def log_message(self, *_args):
                pass

        return Handler

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def cfg_for(url: str, **over) -> dict:
    base = {
        "url": url,
        "bank": "hermes",
        "org": "default",
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


def test_one_bank_serves_every_surface(store):
    """The bank is the retrieval scope. Otto writes to `hermes` from every channel it serves,
    so an agent that reads another bank reads an empty estate. Graded on the path that
    actually reaches the server, not on the string this module builds."""
    s = store({"operation_id": "op-1"})
    memory.do_remember(
        "a thing happened", "otto", "fact", [], "mcp", cfg=cfg_for(s.url)
    )
    memory.do_recall("a thing", "", "", [], 5, cfg=cfg_for(s.url))
    assert [path for path, _ in s.seen] == [
        "/v1/default/banks/hermes/memories",
        "/v1/default/banks/hermes/memories/recall",
    ]


def test_remember_sends_the_structured_shape(store):
    s = store({"operation_id": "op-1"})
    out = memory.do_remember(
        "the deepseek lane was revoked and hindsight stopped extracting",
        "hindsight",
        "incident",
        ["Memory", "memory", " lane "],
        "session-36c9262c",
        cfg=cfg_for(s.url),
    )
    assert out["written"] is True and out["operation_id"] == "op-1"
    _, payload = s.seen[0]
    assert payload["async"] is True
    assert payload["items"][0]["metadata"] == {
        "subject": "hindsight",
        "kind": "incident",
        "source": "session-36c9262c",
        "tags": "lane,memory",
    }


def test_an_unknown_kind_becomes_a_fact_rather_than_a_refusal(store):
    """A fence that refuses correct work is an outage (LAW 38): a caller guessing the wrong
    kind still gets its memory written, filed under the safe one."""
    s = store({})
    out = memory.do_remember("x", "otto", "musing", [], "mcp", cfg=cfg_for(s.url))
    assert out["written"] is True
    assert s.seen[0][1]["items"][0]["metadata"]["kind"] == "fact"


def test_recall_filters_on_the_fields_remember_wrote(store):
    s = store(
        {
            "memories": [
                {
                    "text": "the door moved",
                    "metadata": {
                        "subject": "otto-gateway",
                        "kind": "decision",
                        "tags": "door,telegram",
                    },
                },
                {
                    "text": "unrelated",
                    "metadata": {"subject": "superset", "kind": "fact"},
                },
                {
                    "text": "wrong kind",
                    "metadata": {"subject": "otto-gateway", "kind": "fact"},
                },
            ]
        }
    )
    out = memory.do_recall(
        "who owns the door", "otto-gateway", "decision", ["door"], 5, cfg=cfg_for(s.url)
    )
    assert [m["text"] for m in out["memories"]] == ["the door moved"]


def test_recall_reads_the_rendered_context_shape_too(store):
    """The vendor answers recall with a rendered `context` string or a `memories` list
    depending on the request; a version bump that switches one for the other must not
    silently return nothing."""
    s = store({"context": "estate-context-marker"})
    out = memory.do_recall("anything", "", "", [], 5, cfg=cfg_for(s.url))
    assert out["memories"][0]["text"] == "estate-context-marker"


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


def test_a_body_that_is_not_json_is_an_error_not_a_crash(store):
    s = store("<html>gateway timeout</html>")
    out = memory.do_recall("q", "", "", [], 5, cfg=cfg_for(s.url))
    assert out["memories"] == [] and "not JSON" in out["error"]


def test_unset_url_never_opens_a_socket():
    off = cfg_for("")
    assert memory.do_recall("q", "", "", [], 5, cfg=off)["memories"] == []
    assert memory.do_remember("c", "s", "fact", [], "mcp", cfg=off)["written"] is False


def test_a_non_http_url_is_refused_before_urllib_sees_it():
    body, error = memory.post(cfg_for("file:///etc/passwd"), "", {})
    assert body is None and "http(s)" in error


def test_the_recall_payload_is_held_under_the_ceiling(store):
    s = store({"memories": [{"text": "x" * 400, "metadata": {}} for _ in range(20)]})
    out = memory.do_recall("q", "", "", [], 20, cfg=cfg_for(s.url, byte_ceiling=1000))
    assert 0 < len(out["memories"]) < 20

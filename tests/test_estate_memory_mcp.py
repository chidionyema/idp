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
        # what POST /memories/recall answers with: None = a server without the route (404),
        # a list = results, an int = that HTTP status with no results
        self.semantic = None
        # what POST /memories/brief answers with: None = a server without the route (404)
        self.brief = None
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

            def do_POST(self):  # noqa: N802
                body = json.loads(self.rfile.read(int(self.headers["content-length"])))
                if not self._record(body):
                    return self._answer(
                        403, {"detail": "Access token invalid or revoked"}
                    )
                if self.path == "/memories/brief" and store.brief is not None:
                    return self._answer(200, store.brief)
                if self.path != "/memories/recall" or store.semantic is None:
                    return self._answer(404, {"detail": "Not Found"})
                if isinstance(store.semantic, int):
                    return self._answer(
                        store.semantic, {"detail": "embed lane unavailable"}
                    )
                self._answer(200, {"results": store.semantic})

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
    # recall asks for meaning (POST) and then lists (GET): the words are the floor under it.
    # remember and recall also each make a best-effort call to the harness (#6254, #6581); those
    # are the active-memory side channel and are pinned in test_estate_memory_consolidate_body.py.
    harness = [r for r in s.seen if r[1].startswith("/harness/")]
    assert len(harness) == 2 and all(r[0] == "POST" for r in harness)
    (m1, p1, h1, _), (m2, p2, h2, _), (m3, p3, h3, _) = [
        r for r in s.seen if not r[1].startswith("/harness/")
    ]
    assert (m1, m2, m3) == ("PUT", "POST", "GET")
    assert p1.startswith("/memories/estate/fact.otto.")
    assert (p2, p3) == ("/memories/recall", "/memories/estate")
    assert h1["Host"] == h2["Host"] == h3["Host"] == "unified-memory.estate.internal"


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


def hit(key, content, **provenance):
    return {"key": key, "content": content, "provenance": provenance}


def test_recall_asks_the_server_to_search_by_meaning_and_returns_its_hits_first(
    store, cfg_for
):
    s = store()
    memory.do_remember(
        "the postgres volume filled its disk", "pg", "incident", [], "t", cfg_for(s.url)
    )
    s.semantic = [
        hit("k-meaning", "the database ran out of space", subject="pg", kind="incident")
    ]
    out = memory.do_recall("where is the data kept", "", "", [], 5, cfg_for(s.url))
    posts = [r for r in s.seen if r[0] == "POST" and not r[1].startswith("/harness/")]
    assert posts and posts[0][1] == "/memories/recall"
    assert posts[0][3]["query"] == "where is the data kept"
    assert posts[0][3]["namespace"] == "estate"
    assert posts[0][2]["Authorization"] == f"Bearer {TOKEN}"
    assert out["memories"][0]["text"] == "the database ran out of space"
    assert out["matched_by_meaning"] == 1


def test_recall_keeps_the_word_match_for_facts_the_vectors_missed(store, cfg_for):
    s = store()
    memory.do_remember(
        "the vault rotates keys weekly", "vault", "fact", [], "t", cfg_for(s.url)
    )
    s.semantic = [hit("elsewhere", "an unrelated semantic hit")]
    out = memory.do_recall("vault", "", "", [], 5, cfg_for(s.url))
    texts = [m["text"] for m in out["memories"]]
    assert texts == ["an unrelated semantic hit", "the vault rotates keys weekly"]


def test_a_fact_found_both_ways_is_returned_once(store, cfg_for):
    s = store()
    wrote = memory.do_remember(
        "the vault rotates keys weekly", "vault", "fact", [], "t", cfg_for(s.url)
    )
    s.semantic = [
        hit(wrote["key"], "the vault rotates keys weekly", **wrote["metadata"])
    ]
    out = memory.do_recall("vault", "", "", [], 5, cfg_for(s.url))
    assert [m["text"] for m in out["memories"]] == ["the vault rotates keys weekly"]


def test_the_filters_apply_to_what_the_server_returned_by_meaning(store, cfg_for):
    s = store()
    s.semantic = [
        hit("a", "pg incident", subject="pg", kind="incident"),
        hit("b", "vault decision", subject="vault", kind="decision"),
    ]
    out = memory.do_recall("anything", "vault", "", [], 5, cfg_for(s.url))
    assert [m["text"] for m in out["memories"]] == ["vault decision"]


def test_recall_falls_back_to_words_when_the_store_cannot_search_by_meaning(
    store, cfg_for
):
    for semantic in (None, 503):  # an old server without the route; the embed lane down
        s = store()
        memory.do_remember(
            "the vault rotates keys weekly", "vault", "fact", [], "t", cfg_for(s.url)
        )
        s.semantic = semantic
        out = memory.do_recall("vault", "", "", [], 5, cfg_for(s.url))
        assert [m["text"] for m in out["memories"]] == ["the vault rotates keys weekly"]
        assert out["matched_by_meaning"] == 0
        assert "error" not in out


def test_an_empty_query_does_not_spend_an_embedding(store, cfg_for):
    s = store()
    memory.do_remember(
        "the vault rotates keys weekly", "vault", "fact", [], "t", cfg_for(s.url)
    )
    out = memory.do_recall("", "", "", [], 5, cfg_for(s.url))
    assert len(out["memories"]) == 1
    assert not [r for r in s.seen if r[0] == "POST" and r[1] == "/memories/recall"]


def test_remember_records_the_runtime_that_wrote_it(store, cfg_for):
    s = store()
    out = memory.do_remember(
        "x", "otto", "fact", [], "mcp", cfg=cfg_for(s.url), runtime=" Cursor "
    )
    assert out["metadata"]["runtime"] == "cursor"
    assert next(iter(s.facts.values()))["provenance"]["runtime"] == "cursor"


def test_brief_asks_the_server_once_and_keeps_both_halves(store, cfg_for):
    s = store()
    s.brief = {
        "relevant": [hit("k1", "postgres filled its disk", kind="incident")],
        "recent": [hit("d1", "one memory store", kind="decision")],
        "search_by_meaning": True,
    }
    out = memory.do_brief("fix the database", 8, cfg=cfg_for(s.url))
    ((method, path, headers, body),) = s.seen
    assert (method, path) == ("POST", "/memories/brief")
    assert body == {"task": "fix the database", "namespace": "estate", "limit": 8}
    assert headers["Host"] == "unified-memory.estate.internal"
    assert out["relevant"] == [
        {"text": "postgres filled its disk", "metadata": {"kind": "incident"}}
    ]
    assert out["recent"] == [
        {"text": "one memory store", "metadata": {"kind": "decision"}}
    ]
    assert out["search_by_meaning"] is True


def test_brief_drops_recent_before_relevant_under_the_ceiling(store, cfg_for):
    s = store()
    s.brief = {
        "relevant": [hit("k1", "a" * 300, kind="fact")],
        "recent": [hit(f"d{i}", "b" * 300, kind="decision") for i in range(5)],
        "search_by_meaning": True,
    }
    out = memory.do_brief("t", 8, cfg=cfg_for(s.url, byte_ceiling=1000))
    assert len(out["relevant"]) == 1
    assert 0 < len(out["recent"]) < 5


def test_a_store_that_cannot_brief_is_an_error_not_a_crash(store, cfg_for):
    s = store()  # no brief route: an old server answers 404
    out = memory.do_brief("t", 8, cfg=cfg_for(s.url))
    assert (out["relevant"], out["recent"]) == ([], [])
    assert "404" in out["error"]


def test_brief_with_no_url_never_opens_a_socket(cfg_for):
    out = memory.do_brief("t", 8, cfg=cfg_for(""))
    assert "unset" in out["error"]

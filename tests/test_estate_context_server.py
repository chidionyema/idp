"""tests/test_estate_context_server.py -- the door, driven the way a client drives it.

Every test here speaks real JSON-RPC over a real socket to the real handler. Nothing is
mocked below the transport: the claim, the freshness, the engine and the scrubbing are the
production code paths, with only the outside world (GitHub, the engine, the mounted files)
replaced.

THE ENGINE'S ANSWER IS THE REAL ONE. The fake engine below answers in the shape gortex
v0.64.11 answers in -- `working_set` with the files it ranked, `relevant_symbols` with the
symbols it chose, `blast_radius` with the callers it found -- MEASURED against the engine on
2026-10-27. A fake in a shape the engine does not use proves nothing about the engine.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "platform"))

from estate.context import server as broker_server  # noqa: E402
from estate.context import plan as plan_rules  # noqa: E402

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# The engine stores a tracked repository's files under that repository's NAME. On this
# worktree the tracked directory is the checkout, so the engine's prefix is its basename.
ENGINE_REPO_NAME = plan_rules.repo_name(REPO_ROOT)

CLAIM = "CLAIM agent=pi paths=platform/estate/context/** heartbeat=2026-10-27T02:39:57Z"


def _engine_file(rel: str) -> str:
    """The path the engine would store a repository file under."""
    return f"{ENGINE_REPO_NAME}/{rel}"


def _real_engine_answer() -> dict:
    """An answer in the shape gortex v0.64.11 answers in."""
    return {
        "working_set": [
            {
                "file": _engine_file("platform/estate/context/broker.py"),
                "is_test": False,
                "symbols": [
                    "agent-surface::platform::estate::context::broker::decide_request"
                ],
            },
            {
                "file": _engine_file("platform/estate/context/server.py"),
                "is_test": False,
                "symbols": ["agent-surface::platform::estate::context::server::serve"],
            },
        ],
        "relevant_symbols": [
            {
                "file_path": _engine_file("platform/estate/context/broker.py"),
                "id": "agent-surface::platform::estate::context::broker::decide_request",
                "kind": "function",
                "language": "python",
                "name": "decide_request",
                "start_line": 42,
            }
        ],
        "blast_radius": {"callers_by_file": []},
        "files_to_edit": [],
        "related_test_files": [],
        "task": "where is the context policy decided",
        "etag": "fe0b49bf77a024be",
    }


class FakeEngine:
    """An engine that answers, so the door can be tested without one."""

    def __init__(self, payload=None):
        self.payload = payload if payload is not None else _real_engine_answer()
        self.calls: list[tuple[str, dict]] = []

    def call(self, tool, args):
        self.calls.append((tool, dict(args)))
        return self.payload


def _serve_in_thread():
    from http.server import ThreadingHTTPServer

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), broker_server.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}"


def _rpc(base, method, params=None, fid=1):
    body = json.dumps(
        {"jsonrpc": "2.0", "id": fid, "method": method, "params": params or {}}
    ).encode()
    req = urllib.request.Request(  # noqa: S310
        f"{base}/mcp", data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
        return json.loads(resp.read().decode())


def _setup(
    monkeypatch,
    *,
    engine=None,
    manifest=None,
    reachable=True,
    comments=CLAIM,
    source_dir=REPO_ROOT,
):
    engine = engine or FakeEngine()
    monkeypatch.setattr(
        broker_server, "_issue_record", lambda n: ("open", [{"body": comments}])
    )
    monkeypatch.setattr(broker_server, "_engine_reachable", lambda: reachable)
    monkeypatch.setattr(broker_server, "_engine_client", lambda: engine)
    monkeypatch.setattr(broker_server, "SOURCE_DIR", source_dir)
    monkeypatch.setattr(
        broker_server,
        "_index_manifest",
        lambda: (
            manifest
            if manifest is not None
            else {"commit": "abc123", "head_commit": "abc123"}
        ),
    )
    monkeypatch.setattr(
        broker_server,
        "_load_named_secrets",
        lambda: {"MCP_GATEWAY_KEY": "sk-live-abcdef123456789"},
    )
    return engine


def test_initialize_returns_the_protocol_and_a_session(monkeypatch):
    _setup(monkeypatch)
    httpd, base = _serve_in_thread()
    try:
        out = _rpc(base, "initialize", {"protocolVersion": "2026-06-18"})
        assert out["result"]["serverInfo"]["name"] == "estate-context-broker"
        assert out["result"]["protocolVersion"] == "2026-06-18"
    finally:
        httpd.shutdown()


def test_tools_list_exposes_exactly_two_tools(monkeypatch):
    _setup(monkeypatch)
    httpd, base = _serve_in_thread()
    try:
        out = _rpc(base, "tools/list")
        names = sorted(t["name"] for t in out["result"]["tools"])
        assert names == ["estate_context", "estate_context_status"]
    finally:
        httpd.shutdown()


def test_a_context_call_inside_the_claim_is_answered_with_provenance(monkeypatch):
    engine = _setup(monkeypatch)
    httpd, base = _serve_in_thread()
    try:
        out = _rpc(
            base,
            "tools/call",
            {
                "name": "estate_context",
                "arguments": {
                    "task": "where is the context policy decided",
                    "paths": ["platform/estate/context/broker.py"],
                    "claim_issue": 7262,
                    "claim_agent": "pi",
                },
            },
        )
        result = out["result"]
        assert result["isError"] is False
        sc = result["structuredContent"]
        assert sc["verdict"] == "ALLOW"
        assert sc["commit"] == "abc123"
        assert sc["excerpts"], "an answer must carry excerpts with provenance"
        prov = sc["excerpts"][0]["provenance"]
        assert prov["file"] == "platform/estate/context/broker.py"
        assert prov["commit"] == "abc123"
        assert prov["start_line"] == 1
        assert prov["sha256"] and len(prov["sha256"]) == 64
        # The engine names the file; the broker says what the file says, and the text it
        # hands back is the file's own text -- the same head, read from the tree.
        with open(
            os.path.join(REPO_ROOT, "platform/estate/context/broker.py"),
            encoding="utf-8",
        ) as fh:
            head = "".join([next(fh) for _ in range(120)])
        assert sc["excerpts"][0]["content"] == head
        assert engine.calls[0][0] == "smart_context"
        assert engine.calls[0][1]["task"] == "where is the context policy decided"
    finally:
        httpd.shutdown()


def test_the_answer_keeps_the_engines_ranking(monkeypatch):
    """The broker does not re-rank. The engine's order is the answer's order."""
    _setup(monkeypatch)
    httpd, base = _serve_in_thread()
    try:
        out = _rpc(
            base,
            "tools/call",
            {
                "name": "estate_context",
                "arguments": {
                    "task": "where is the context policy decided",
                    "paths": ["platform/estate/context/broker.py"],
                    "claim_issue": 7262,
                    "claim_agent": "pi",
                },
            },
        )
        sc = out["result"]["structuredContent"]
        files = [e["provenance"]["file"] for e in sc["excerpts"]]
        assert files[0] == "platform/estate/context/broker.py"
        assert files[1] == "platform/estate/context/server.py"
    finally:
        httpd.shutdown()


def test_a_path_outside_the_claim_is_refused_at_the_door(monkeypatch):
    engine = _setup(monkeypatch)
    httpd, base = _serve_in_thread()
    try:
        out = _rpc(
            base,
            "tools/call",
            {
                "name": "estate_context",
                "arguments": {
                    "task": "read something else",
                    "paths": ["platform/estate/pi/estate-commands.ts"],
                    "claim_issue": 7262,
                    "claim_agent": "pi",
                },
            },
        )
        assert out["result"]["isError"] is True
        assert out["result"]["structuredContent"]["verdict"] == "PATH_REFUSED"
        assert not engine.calls, "the engine was asked about a path outside the claim"
    finally:
        httpd.shutdown()


def test_a_stale_index_is_refused_at_the_door(monkeypatch):
    engine = _setup(monkeypatch)
    httpd, base = _serve_in_thread()
    try:
        out = _rpc(
            base,
            "tools/call",
            {
                "name": "estate_context",
                "arguments": {
                    "task": "answer at another commit",
                    "commit": "deadbeef",
                    "claim_issue": 7262,
                    "claim_agent": "pi",
                },
            },
        )
        assert out["result"]["isError"] is True
        assert out["result"]["structuredContent"]["verdict"] == "STALE_REJECT"
        assert not engine.calls
    finally:
        httpd.shutdown()


def test_an_unreachable_engine_is_refused_at_the_door(monkeypatch):
    engine = _setup(monkeypatch, reachable=False)
    httpd, base = _serve_in_thread()
    try:
        out = _rpc(
            base,
            "tools/call",
            {
                "name": "estate_context",
                "arguments": {
                    "task": "anything",
                    "claim_issue": 7262,
                    "claim_agent": "pi",
                },
            },
        )
        assert out["result"]["isError"] is True
        assert out["result"]["structuredContent"]["verdict"] == "ENGINE_UNREACHABLE"
        assert not engine.calls
    finally:
        httpd.shutdown()


def test_a_secret_in_the_answer_is_scrubbed_before_it_leaves(monkeypatch):
    _setup(
        monkeypatch,
        engine=FakeEngine(
            {"working_set": [], "note": "the key is sk-live-abcdef123456789"}
        ),
    )
    httpd, base = _serve_in_thread()
    try:
        out = _rpc(
            base,
            "tools/call",
            {
                "name": "estate_context",
                "arguments": {
                    "task": "anything",
                    "claim_issue": 7262,
                    "claim_agent": "pi",
                },
            },
        )
        sc = out["result"]["structuredContent"]
        assert "sk-live-abcdef123456789" not in sc["answer"]
        assert "REF:MCP_GATEWAY_KEY" in sc["answer"]
        assert sc["redacted"] == ["MCP_GATEWAY_KEY"]
    finally:
        httpd.shutdown()


def test_a_request_without_a_claim_is_refused(monkeypatch):
    engine = _setup(monkeypatch)
    httpd, base = _serve_in_thread()
    try:
        out = _rpc(
            base,
            "tools/call",
            {"name": "estate_context", "arguments": {"task": "anything"}},
        )
        assert out["result"]["isError"] is True
        assert "claim" in out["result"]["structuredContent"]["reason"]
        assert not engine.calls
    finally:
        httpd.shutdown()


def test_an_unknown_tool_is_an_error_not_a_crash(monkeypatch):
    _setup(monkeypatch)
    httpd, base = _serve_in_thread()
    try:
        out = _rpc(base, "tools/call", {"name": "nope", "arguments": {}})
        assert out["result"]["isError"] is True
    finally:
        httpd.shutdown()


def test_healthz_answers_without_a_claim(monkeypatch):
    _setup(monkeypatch)
    httpd, base = _serve_in_thread()
    try:
        with urllib.request.urlopen(f"{base}/healthz", timeout=5) as resp:  # noqa: S310
            body = json.loads(resp.read().decode())
        assert body["status"] == "ok"
    finally:
        httpd.shutdown()


# --- the engine's paths are the engine's, not the repository's ---------------------------------
def test_the_engines_repo_prefixed_paths_are_normalized_and_digested(
    monkeypatch, tmp_path
):
    """The engine stores files under the tracked repository's NAME ("repo/pkg/broker.py").
    That prefix is the engine's storage detail: the excerpt must carry the repository's own
    path, and a digest looked up under the engine's prefix would find nothing."""
    source = tmp_path / "pkg" / "broker.py"
    source.parent.mkdir(parents=True)
    source.write_text("def decide_request():\n    return True\n", encoding="utf-8")
    monkeypatch.setattr(broker_server, "SOURCE_DIR", str(tmp_path))
    # The tracked directory's name IS the engine's prefix -- here the tracked directory is
    # the tmp tree, so the engine would store its files under that tree's name.
    name = plan_rules.repo_name(str(tmp_path))
    excerpts = broker_server._excerpts_from(
        {
            "working_set": [
                {
                    "file": f"{name}/pkg/broker.py",
                    "is_test": False,
                    "symbols": [],
                }
            ]
        },
        "abc123",
    )
    assert excerpts
    prov = excerpts[0]["provenance"]
    assert prov["file"] == "pkg/broker.py"
    assert prov["sha256"] and len(prov["sha256"]) == 64
    assert prov["commit"] == "abc123"
    assert "def decide_request" in excerpts[0]["content"]


def test_the_files_the_engine_ranked_are_read_in_the_engines_order(
    monkeypatch, tmp_path
):
    source = tmp_path / "pkg" / "broker.py"
    source.parent.mkdir(parents=True)
    source.write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "pkg" / "other.py").write_text("y = 2\n", encoding="utf-8")
    monkeypatch.setattr(broker_server, "SOURCE_DIR", str(tmp_path))
    name = plan_rules.repo_name(str(tmp_path))
    excerpts = broker_server._excerpts_from(
        {
            "working_set": [
                {"file": f"{name}/pkg/broker.py", "is_test": False, "symbols": []},
                {"file": f"{name}/pkg/other.py", "is_test": False, "symbols": []},
            ]
        },
        "abc123",
    )
    files = [e["provenance"]["file"] for e in excerpts]
    assert files == ["pkg/broker.py", "pkg/other.py"]
    assert excerpts[0]["content"].strip() == "x = 1"


def test_the_same_file_is_not_carried_twice(monkeypatch, tmp_path):
    source = tmp_path / "pkg" / "broker.py"
    source.parent.mkdir(parents=True)
    source.write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr(broker_server, "SOURCE_DIR", str(tmp_path))
    name = plan_rules.repo_name(str(tmp_path))
    excerpts = broker_server._excerpts_from(
        {
            "relevant_symbols": [
                {
                    "file_path": f"{name}/pkg/broker.py",
                    "id": "x::y",
                    "kind": "function",
                    "language": "python",
                    "name": "y",
                    "start_line": 1,
                }
            ],
            "working_set": [
                {"file": f"{name}/pkg/broker.py", "is_test": False, "symbols": []}
            ],
        },
        "abc123",
    )
    files = [e["provenance"]["file"] for e in excerpts]
    assert files.count("pkg/broker.py") == 1, "the same file must not be carried twice"


def test_an_excerpt_is_scrubbed_of_a_named_secret(monkeypatch, tmp_path):
    """An excerpt that leaves the broker with a credential in it is a leak with a provenance
    envelope around it."""
    source = tmp_path / "pkg" / "broker.py"
    source.parent.mkdir(parents=True)
    source.write_text("TOKEN = 'sk-live-abcdef123456789'\n", encoding="utf-8")
    monkeypatch.setattr(broker_server, "SOURCE_DIR", str(tmp_path))
    name = plan_rules.repo_name(str(tmp_path))
    excerpts = broker_server._excerpts_from(
        {
            "working_set": [
                {"file": f"{name}/pkg/broker.py", "is_test": False, "symbols": []}
            ]
        },
        "abc123",
        {"MCP_GATEWAY_KEY": "sk-live-abcdef123456789"},
    )
    assert excerpts
    assert "sk-live-abcdef123456789" not in excerpts[0]["content"]
    assert "REF:MCP_GATEWAY_KEY" in excerpts[0]["content"]

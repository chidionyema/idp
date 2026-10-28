"""tests/test_estate_context_broker.py -- the broker's policy, proven by refusal.

A gate that cannot fail is not a gate (AGENTS.md 3). Every branch of the broker's decision
function has a test here that makes it fail, and every refusal names the law that refused it.

Run: bin/pytest or `python3 -m pytest tests/test_estate_context_broker.py`
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "platform"))

from estate.context.broker import (  # noqa: E402
    ASYNC_REINDEX,
    BUDGET_REFUSED,
    ENGINE_UNREACHABLE,
    PATH_REFUSED,
    STALE_REJECT,
    TOOL_REFUSED,
    UNPROVEN_INDEX,
    BrokerState,
    ContextRequest,
    EngineClient,
    decide_request,
    envelope,
    freshness_decision,
    path_allowed,
    path_decision,
    provenance,
    scrub,
    tool_decision,
    unwrap_engine_envelope,
)


# --- freshness ---------------------------------------------------------------------------------
def test_fresh_index_on_the_requested_commit_is_allowed():
    d = freshness_decision(index_commit="abc123", request_commit="abc123")
    assert d.allow and d.verdict == "ALLOW"


def test_stale_index_on_a_committed_request_is_refused():
    d = freshness_decision(index_commit="abc123", request_commit="def456")
    assert not d.allow
    assert d.verdict == STALE_REJECT
    assert "abc123" in d.reason and "def456" in d.reason


def test_unproven_index_is_refused_even_in_working_copy_mode():
    d = freshness_decision(
        index_commit=None, request_commit="abc123", mode="working_copy"
    )
    assert not d.allow and d.verdict == UNPROVEN_INDEX


def test_working_copy_mismatch_is_async_reindex_and_still_allowed():
    d = freshness_decision(
        index_commit="abc123", request_commit="def456", mode="working_copy"
    )
    assert d.allow and d.verdict == ASYNC_REINDEX
    assert d.evidence["freshness_reason"] == "stale_index_incremental_route"


def test_unknown_freshness_mode_is_an_error_not_a_verdict():
    with pytest.raises(ValueError):
        freshness_decision(index_commit="a", request_commit="a", mode="whenever")


# --- paths -------------------------------------------------------------------------------------
def test_a_path_inside_the_claim_is_allowed():
    assert path_allowed(
        "platform/estate/context/broker.py", ["platform/estate/context/**"]
    )
    assert path_allowed(
        "platform/estate/context/broker.py", ["platform/estate/context/broker.py"]
    )


def test_a_path_outside_the_claim_is_refused():
    assert not path_allowed(
        "platform/estate/pi/estate-commands.ts", ["platform/estate/context/**"]
    )


def test_a_traversing_path_is_refused_even_when_the_glob_would_match():
    assert not path_allowed("../../etc/passwd", ["**"])
    assert not path_allowed("/etc/passwd", ["**"])


def test_a_request_naming_one_path_outside_the_claim_is_refused_whole():
    d = path_decision(
        ["platform/estate/context/broker.py", "platform/estate/pi/estate-commands.ts"],
        ["platform/estate/context/**"],
    )
    assert not d.allow and d.verdict == PATH_REFUSED
    assert d.evidence["outside"] == ["platform/estate/pi/estate-commands.ts"]


# --- tools -------------------------------------------------------------------------------------
def test_a_read_only_tool_is_allowed():
    assert tool_decision("smart_context").allow


def test_a_mutating_tool_is_refused_and_names_the_door_that_would_work():
    d = tool_decision("edit_file")
    assert not d.allow and d.verdict == TOOL_REFUSED
    assert "executor" in d.reason


def test_an_unknown_tool_is_refused():
    assert not tool_decision("rm_rf").allow


# --- budget ------------------------------------------------------------------------------------
def test_over_budget_is_refused_with_both_numbers():
    d = decide_request(
        ContextRequest(tool="smart_context", token_budget=1000, estimated_tokens=5000),
        BrokerState(index_commit="abc123", head_commit="abc123"),
    )
    assert not d.allow and d.verdict == BUDGET_REFUSED
    assert d.evidence["tokens"] == 5000 and d.evidence["budget"] == 1000


def test_a_request_naming_no_commit_is_resolved_against_the_brokers_head():
    d = decide_request(
        ContextRequest(tool="smart_context"),
        BrokerState(index_commit="abc123", head_commit="abc123"),
    )
    assert d.allow and d.evidence["request_commit"] == "abc123"


def test_a_request_naming_no_commit_with_no_known_head_is_refused():
    d = decide_request(
        ContextRequest(tool="smart_context"),
        BrokerState(index_commit="abc123"),
    )
    assert not d.allow and d.verdict == STALE_REJECT
    assert "HEAD" in d.reason


# --- the engine -------------------------------------------------------------------------------
def test_an_unreachable_engine_is_refused_not_served_from_cache():
    d = decide_request(
        ContextRequest(tool="smart_context"),
        BrokerState(
            index_commit="abc123", head_commit="abc123", engine_reachable=False
        ),
    )
    assert not d.allow and d.verdict == ENGINE_UNREACHABLE


# --- secrets -----------------------------------------------------------------------------------
def test_a_named_secret_value_is_replaced_with_an_opaque_reference():
    text = "the gateway wants token sk-live-abcdef123456789 for the call"
    clean, removed = scrub(text, {"MCP_GATEWAY_KEY": "sk-live-abcdef123456789"})
    assert "sk-live-abcdef123456789" not in clean
    assert "REF:MCP_GATEWAY_KEY" in clean
    assert removed == ["MCP_GATEWAY_KEY"]


def test_a_short_value_is_not_treated_as_a_secret():
    clean, removed = scrub("the port is 8080 here", {"PORT": "8080"})
    assert clean == "the port is 8080 here"
    assert removed == []


def test_an_unnamed_token_shape_is_still_removed():
    clean, removed = scrub("token ghp_abcdefghijklmnopqrstuvwxyz0123 leaked", {})
    assert "ghp_abcdefghijklmnopqrstuvwxyz0123" not in clean
    assert "REF:GITHUB_TOKEN" in clean


def test_a_private_key_block_is_removed_whole():
    blob = "-----BEGIN RSA PRIVATE KEY-----\nabc\ndef\n-----END RSA PRIVATE KEY-----"
    clean, removed = scrub(blob, {})
    assert "BEGIN RSA PRIVATE KEY" not in clean
    assert "PRIVATE_KEY_BLOCK" in removed


def test_a_value_bound_to_a_credential_shaped_name_is_removed_and_the_name_kept():
    clean, removed = scrub('GITHUB_TOKEN = "a93kd0mzq1x7"', {})
    assert "a93kd0mzq1x7" not in clean
    assert "REF:GITHUB_TOKEN" in clean
    assert "GITHUB_TOKEN" in removed


def test_an_ordinary_number_or_path_is_not_invented_into_a_secret():
    text = "token_budget = 12000\nsecret_dir = /run/secrets/estate-context"
    clean, removed = scrub(text, {})
    assert clean == text
    assert removed == []


# --- provenance -------------------------------------------------------------------------------
def test_every_excerpt_carries_file_commit_lines_and_digest():
    env = envelope(
        "def decide(): ...",
        provenance("platform/estate/context/broker.py", "abc123", 10, 11, "deadbeef"),
    )
    p = env["provenance"]
    assert p["file"] == "platform/estate/context/broker.py"
    assert p["commit"] == "abc123"
    assert (p["start_line"], p["end_line"]) == (10, 11)
    assert p["sha256"] == "deadbeef"
    assert len(env["content_sha256"]) == 64


def test_an_excerpt_is_scrubbed_on_the_way_out():
    env = envelope(
        "here is the key sk-live-abcdef123456789",
        provenance("f.py", "abc", 1, 1, "d"),
        secrets={"MCP_GATEWAY_KEY": "sk-live-abcdef123456789"},
    )
    assert "sk-live-abcdef123456789" not in env["content"]
    assert env["redacted"] == ["MCP_GATEWAY_KEY"]


# --- the whole request ------------------------------------------------------------------------
def test_a_good_request_is_allowed():
    d = decide_request(
        ContextRequest(
            tool="smart_context",
            paths=["platform/estate/context/broker.py"],
            request_commit="abc123",
        ),
        BrokerState(
            index_commit="abc123",
            head_commit="abc123",
            claim_paths=["platform/estate/context/**"],
        ),
    )
    assert d.allow and d.verdict == "ALLOW"


def test_the_refusal_order_is_tool_then_engine_then_freshness_then_paths_then_budget():
    state = BrokerState(
        index_commit="abc123",
        head_commit="abc123",
        claim_paths=["platform/estate/context/**"],
    )
    # a mutating tool is refused before anything else is looked at
    d = decide_request(ContextRequest(tool="edit_file"), state)
    assert d.verdict == TOOL_REFUSED
    # a stale index is refused before the paths are consulted
    d = decide_request(
        ContextRequest(tool="smart_context", paths=["nope/x.py"], request_commit="zzz"),
        BrokerState(index_commit="abc123", claim_paths=["platform/estate/context/**"]),
    )
    assert d.verdict == STALE_REJECT


# --- the engine's wire format ----------------------------------------------------------------------
def test_the_engine_envelope_is_opened():
    """MEASURED against gortex v0.64.11: the engine answers in the MCP tool-result envelope.
    A client that stops at the envelope gets a dictionary with a "content" key where the
    working set should be -- an answer that LOOKS like it worked and carries no files."""
    payload = {
        "working_set": [{"file": "platform/estate/context/broker.py"}],
        "files_to_edit": [],
    }
    envelope = {"content": [{"type": "text", "text": json.dumps(payload)}]}
    opened = unwrap_engine_envelope("smart_context", envelope)
    assert opened["working_set"][0]["file"] == "platform/estate/context/broker.py"


def test_a_bare_answer_passes_through_unchanged():
    payload = {"working_set": [{"file": "a.py"}]}
    assert unwrap_engine_envelope("smart_context", payload) is payload


def test_an_envelope_with_no_text_is_an_error_not_an_empty_answer():
    try:
        unwrap_engine_envelope("smart_context", {"content": [{"type": "image"}]})
    except Exception as exc:  # EngineError
        assert "carried no text" in str(exc)
    else:
        raise AssertionError(
            "an envelope with no text must not be answered as an empty payload"
        )


def test_the_engine_client_opens_the_envelope_over_http(monkeypatch):
    """The whole path: an HTTP answer in the engine's envelope becomes a usable payload."""
    payload = {"working_set": [{"file": "platform/estate/context/broker.py"}]}

    class FakeResponse:
        def __init__(self, body):
            self._body = body

        def read(self):
            return self._body.encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(req, timeout=None):
        return FakeResponse(
            json.dumps({"content": [{"type": "text", "text": json.dumps(payload)}]})
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    client = EngineClient("http://127.0.0.1:7411", "token")
    assert client.call("smart_context", {"task": "x"})["working_set"][0]["file"] == (
        "platform/estate/context/broker.py"
    )

"""platform/llm/graph_capture.py: what the router spools for the estate graph, run on real call shapes."""

import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_GRAPH_SPOOL", str(tmp_path))
    spec = importlib.util.spec_from_file_location(
        "graph_capture", os.path.join(ROOT, "platform", "llm", "graph_capture.py")
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["graph_capture"] = mod
    spec.loader.exec_module(mod)
    return mod


def _call(ua="claude-cli/2.1", session="abc-123"):
    return {
        "model": "claude-opus-5-5",
        "litellm_params": {
            "proxy_server_request": {
                "headers": {"user-agent": ua},
                "body": {"metadata": {"user_id": json.dumps({"session_id": session})}},
            }
        },
        "messages": [
            {"role": "user", "content": "why did the disk fill?"},
            {
                "role": "user",
                "content": [{"type": "tool_result", "content": "x" * 9000}],
            },
        ],
    }


def test_an_anthropic_exchange_lands_in_its_sessions_spool(tmp_path, monkeypatch):
    g = _load(tmp_path, monkeypatch)
    reply = {
        "content": [
            {"type": "text", "text": "runtime-sync skipped it"},
            {"type": "tool_use"},
        ]
    }
    path = g.capture(_call(), reply)
    text = open(path, encoding="utf-8").read()
    assert os.path.basename(path) == "abc-123.md"
    assert "**asked:** why did the disk fill?" in text
    assert "**answered:** runtime-sync skipped it" in text
    assert "x" * 100 not in text  # tool payloads are not spooled


def test_a_streamed_openai_reply_is_taken_from_the_assembled_response(
    tmp_path, monkeypatch
):
    g = _load(tmp_path, monkeypatch)
    call = dict(
        _call(),
        complete_streaming_response={"choices": [{"message": {"content": "streamed"}}]},
    )
    path = g.capture(call, {"choices": [{"delta": {}}]})
    assert "**answered:** streamed" in open(path, encoding="utf-8").read()


def test_the_drains_own_extraction_calls_are_not_captured(tmp_path, monkeypatch):
    g = _load(tmp_path, monkeypatch)
    assert (
        g.capture(
            _call(ua="Python-urllib/3.9"), {"content": [{"type": "text", "text": "x"}]}
        )
        is None
    )
    assert os.listdir(tmp_path) == []


def test_a_failure_inside_capture_never_reaches_the_request(tmp_path, monkeypatch):
    import asyncio

    g = _load(tmp_path, monkeypatch)
    monkeypatch.setenv("ESTATE_GRAPH_SPOOL", "/dev/null/not-a-dir")
    asyncio.run(
        g.proxy_handler_instance.async_log_success_event(
            _call(), {"content": "hi"}, 0, 0
        )
    )

"""The exact count (#5683): the vendor's own token count of each request as the caller sent it.

The chain's AFTER is exact already (the vendor bills it); these cases pin the BEFORE: one
background count_tokens call per Anthropic request, on the bytes the caller sent rather than
the bytes the chain left, authenticated only with the caller's own subscription token, and
never able to delay, fail or change the request it measures.
"""

from __future__ import annotations

import asyncio
import importlib.machinery
import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OAUTH = "Bearer sk-ant-oat01-test"


def _load(name, path):
    spec = importlib.util.spec_from_loader(
        name, importlib.machinery.SourceFileLoader(name, path)
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _gw(monkeypatch, tmp_path):
    monkeypatch.setenv("ESTATE_EFFICIENCY_LEDGER", str(tmp_path / "ledger.jsonl"))
    monkeypatch.setenv("ESTATE_EPOCH_DIR", str(tmp_path / "epochs"))
    monkeypatch.setenv("ESTATE_HOLDOUT_PCT", "0")
    monkeypatch.setenv("ESTATE_READ_SHUNT", "0")
    mod = _load(
        "gw_exact_count_under_test",
        os.path.join(ROOT, "platform", "llm", "efficiency_gateway.py"),
    )
    return mod, mod.EstateEfficiencyGateway()


def _req(auth=OAUTH, model="claude-opus-5-5"):
    noisy = "\n".join(["retrying connection"] * 40)
    return {
        "model": model,
        "litellm_call_id": "call-1",
        "metadata": {"user_id": json.dumps({"session_id": "s-count"})},
        "secret_fields": {
            "raw_headers": {"Authorization": auth, "anthropic-beta": "oauth-2025-04-20"}
        },
        "system": "you are a coding agent",
        "messages": [
            {"role": "user", "content": "go"},
            {
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "id": "t1", "name": "Bash", "input": {}}
                ],
            },
            {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": "t1", "content": noisy}
                ],
            },
        ],
    }


def _run(gw, mod, data):
    async def go():
        out = await gw.async_pre_call_hook(None, None, data, "anthropic_messages")
        sent = json.dumps(out["messages"])
        await asyncio.gather(*list(mod._COUNT_TASKS))
        return sent

    return asyncio.run(go())


def _counts(tmp_path):
    rows = [json.loads(x) for x in (tmp_path / "ledger.jsonl").read_text().splitlines()]
    return [r for r in rows if r.get("kind") == "count"]


def test_the_caller_is_counted_as_sent_not_as_cut(monkeypatch, tmp_path):
    mod, gw = _gw(monkeypatch, tmp_path)
    seen = {}

    def fake(body, auth, beta):
        seen.update(json.loads(body), auth=auth, beta=beta)
        return {"tokens_before": 1234}

    monkeypatch.setattr(mod, "_count_post", fake)
    sent = _run(gw, mod, _req())
    # the chain collapsed the repeated lines; the count saw them all
    assert "retrying connection\nretrying connection" not in sent
    assert (
        seen["messages"][2]["content"][0]["content"].count("retrying connection") == 40
    )
    assert seen["system"] == "you are a coding agent"
    assert seen["model"] == "claude-opus-5-5"
    assert (seen["auth"], seen["beta"]) == (OAUTH, "oauth-2025-04-20")
    (row,) = _counts(tmp_path)
    assert (row["call_id"], row["tokens_before"]) == ("call-1", 1234)


def test_the_routers_own_key_is_never_sent_to_the_vendor(monkeypatch, tmp_path):
    mod, gw = _gw(monkeypatch, tmp_path)
    called = []
    monkeypatch.setattr(mod, "_count_post", lambda *a: called.append(a) or {})
    _run(gw, mod, _req(auth="Bearer sk-local-master-key"))
    assert called == []
    (row,) = _counts(tmp_path)
    assert row["skipped"] == "no caller oauth token"


def test_a_full_pool_is_a_skip_not_a_queue(monkeypatch, tmp_path):
    mod, gw = _gw(monkeypatch, tmp_path)
    monkeypatch.setattr(mod, "_count_post", lambda *a: {"tokens_before": 1})
    monkeypatch.setattr(mod, "_count_inflight", mod.EXACT_COUNT_POOL)
    _run(gw, mod, _req())
    (row,) = _counts(tmp_path)
    assert row["skipped"] == "pool full"


def test_a_failed_count_changes_nothing_about_the_request(monkeypatch, tmp_path):
    mod, gw = _gw(monkeypatch, tmp_path)

    def boom(*a):
        raise TimeoutError("vendor slow")

    monkeypatch.setattr(mod, "_count_post", boom)
    sent_with_failure = _run(gw, mod, _req())
    (row,) = _counts(tmp_path)
    assert row["skipped"].startswith("TimeoutError")
    assert mod._count_inflight == 0  # the slot came back

    monkeypatch.setattr(mod, "EXACT_COUNT", False)
    assert _run(gw, mod, _req()) == sent_with_failure


def test_non_claude_lanes_are_not_counted(monkeypatch, tmp_path):
    mod, gw = _gw(monkeypatch, tmp_path)
    called = []
    monkeypatch.setattr(mod, "_count_post", lambda *a: called.append(a) or {})
    _run(gw, mod, _req(model="groq/llama-3.3-70b"))
    assert called == [] and _counts(tmp_path) == []

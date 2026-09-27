"""The efficiency gateway on Claude Code's lane must save tokens WITHOUT costing the cache.

Measured 2026-09-26 on a real 233-message Claude Code session: the OpenAI-shaped chain rewrote
history so consecutive turns shared 0 of 60 prefix messages -- every turn a full prompt-cache
miss, at 10x the price of a cache read -- dropped 173 messages, and left an assistant message
first. The founder's ruling: fix it, don't turn it off. These cases are the properties that
make it safe to run on every Claude call:

  * append-stable: turn n+1 re-sends byte-identical bytes for everything turn n sent;
  * nothing the model wrote (thinking, text, tool_use) is ever touched, nothing is dropped;
  * only adjacent line repeats collapse (non-adjacent dedup corrupts code);
  * dedup never points at a result that is not in the same request;
  * every call records each step's action, and the outcome row carries what Anthropic billed.
"""

from __future__ import annotations

import asyncio
import copy
import datetime as dt
import importlib.machinery
import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE_PATH = os.path.join(ROOT, "platform", "llm", "efficiency_gateway.py")
SESSION = json.dumps({"device_id": "d", "session_id": "s-1"})


def _gw(monkeypatch, tmp_path):
    monkeypatch.setenv("ESTATE_EFFICIENCY_LEDGER", str(tmp_path / "ledger.jsonl"))
    spec = importlib.util.spec_from_loader(
        "gw_anthropic_under_test",
        importlib.machinery.SourceFileLoader("gw_anthropic_under_test", MODULE_PATH),
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gw_anthropic_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod.EstateEfficiencyGateway()


def _rows(tmp_path, kind=None):
    p = tmp_path / "ledger.jsonl"
    rows = [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []
    return [r for r in rows if kind is None or r.get("kind") == kind]


def _call(gw, messages, call_id="c", session=SESSION):
    data = {
        "model": "claude-opus-5-5",
        "system": [{"type": "text", "text": "You are Claude Code."}],
        "tools": [{"name": "Read", "description": "d" * 900, "input_schema": {}}],
        "messages": copy.deepcopy(messages),
        "metadata": {"user_id": session},
        "litellm_call_id": call_id,
    }
    return asyncio.run(gw.async_pre_call_hook(None, None, data, "anthropic_messages"))


FILE = "\n".join(f"{i}\tdef f{i}():\n\t    return {i}\n\t}}" for i in range(80))
LOG = "start\n" + "WARN retrying\n" * 40 + "done"


def _conversation():
    """A Claude Code shaped session: thinking, tool_use/tool_result, a re-read, a noisy log."""
    msgs = [{"role": "user", "content": [{"type": "text", "text": "fix the bug"}]}]
    results = [FILE, LOG, "short", FILE, "other " * 200, FILE]
    for i, r in enumerate(results):
        msgs.append(
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "thinking",
                        "thinking": f"step {i}",
                        "signature": f"sig{i}",
                    },
                    {"type": "text", "text": f"reading {i}"},
                    {
                        "type": "tool_use",
                        "id": f"toolu_{i}",
                        "name": "Read",
                        "input": {},
                    },
                ],
            }
        )
        msgs.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": f"toolu_{i}",
                        "content": [{"type": "text", "text": r}],
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
            }
        )
    return msgs


def _strip(o):
    if isinstance(o, dict):
        return {k: _strip(v) for k, v in o.items() if k != "cache_control"}
    if isinstance(o, list):
        return [_strip(v) for v in o]
    return o


def test_every_turn_resends_the_previous_turns_bytes_unchanged(monkeypatch, tmp_path):
    gw = _gw(monkeypatch, tmp_path)
    conv = _conversation()
    prev = None
    for n in range(
        3, len(conv) + 1, 2
    ):  # each call ends on a user message, as Claude Code's do
        out = _strip(_call(gw, conv[:n], call_id=f"c{n}")["messages"])
        if prev is not None:
            assert out[: len(prev)] == prev, (
                f"turn ending at {n} rewrote an earlier message"
            )
        prev = out
    pres = _rows(tmp_path, "pre")
    assert all(not r["steps"]["m1"]["prefix_broken"] for r in pres)
    assert pres[-1]["steps"]["m1"]["prefix_kept_msgs"] == pres[-2]["messages"]


def test_the_cache_check_catches_a_rewritten_history(monkeypatch, tmp_path):
    gw = _gw(monkeypatch, tmp_path)
    conv = _conversation()
    _call(gw, conv[:5], call_id="a")
    edited = copy.deepcopy(conv[:7])
    edited[3]["content"][1]["text"] = "changed"
    _call(gw, edited, call_id="b")
    m1 = _rows(tmp_path, "pre")[-1]["steps"]["m1"]
    assert m1["prefix_broken"] and m1["prefix_kept_msgs"] == 3


def test_nothing_the_model_wrote_is_touched_and_nothing_is_dropped(
    monkeypatch, tmp_path
):
    gw = _gw(monkeypatch, tmp_path)
    conv = _conversation()
    out = _call(gw, conv)
    assert len(out["messages"]) == len(conv)
    assert out["messages"][0]["role"] == "user"
    for a, b in zip(conv, out["messages"]):  # noqa: B905 -- runtime falls back to py3.9, no strict= kwarg
        if a["role"] == "assistant":
            assert a == b
    assert out["tools"][0]["description"] == "d" * 900, (
        "tool schemas are the cached prefix"
    )
    steps = _rows(tmp_path, "pre")[-1]["steps"]
    assert steps["m9"]["orphans"] == 0 and steps["m9"]["first_role"] == "user"
    for k in ("m3", "m7", "m8"):
        assert steps[k]["action"] == "skipped" and steps[k]["why"]


def test_repeated_reads_point_at_the_first_and_logs_collapse(monkeypatch, tmp_path):
    gw = _gw(monkeypatch, tmp_path)
    out = _call(gw, _conversation())["messages"]
    texts = [
        b["content"]
        for m in out
        for b in m["content"]
        if b.get("type") == "tool_result"
    ]
    first = texts[0][0]["text"]
    assert first == FILE, "the first read is kept verbatim"
    assert "identical to the tool result of toolu_0" in texts[3]
    assert "identical to the tool result of toolu_0" in texts[5]
    log = texts[1][0]["text"]
    assert log.startswith(
        "start\nWARN retrying\n[router: previous line repeated 39 more times]"
    )
    row = _rows(tmp_path, "pre")[-1]
    assert row["steps"]["m5"]["results"] == 2 and row["steps"]["m2"]["blocks"] == 1
    assert row["bytes_saved"] == row["bytes_before"] - row["bytes_after"] > 0


def test_non_adjacent_repeats_in_code_are_left_alone(monkeypatch, tmp_path):
    gw = _gw(monkeypatch, tmp_path)
    code = "def a():\n    return 1\n}\ndef b():\n    return 1\n}\n" * 3
    msgs = _conversation()[:3]
    msgs[2]["content"][0]["content"] = code
    out = _call(gw, msgs)
    assert out["messages"][2]["content"][0]["content"] == code


def test_dedup_never_points_at_a_result_outside_the_request(monkeypatch, tmp_path):
    gw = _gw(monkeypatch, tmp_path)
    conv = _conversation()
    _call(gw, conv, call_id="a")
    other = [
        conv[0],
        conv[7],
        conv[8],
    ]  # a different conversation whose only read is FILE
    out = _call(gw, other, call_id="b", session=json.dumps({"session_id": "s-2"}))
    assert out["messages"][2]["content"][0]["content"][0]["text"] == FILE


def test_the_outcome_row_carries_what_anthropic_billed(monkeypatch, tmp_path):
    gw = _gw(monkeypatch, tmp_path)
    _call(gw, _conversation()[:3], call_id="call-9")
    # The usage shape LiteLLM 1.98 handed the callback on a real /v1/messages call (2026-09-26).
    usage = {
        "prompt_tokens": 18770,
        "completion_tokens": 5,
        "cache_read_input_tokens": 15093,
        "cache_creation_input_tokens": 3674,
        "prompt_tokens_details": {
            "cache_creation_token_details": {
                "ephemeral_5m_input_tokens": 0,
                "ephemeral_1h_input_tokens": 3674,
            }
        },
    }
    t0 = dt.datetime(2026, 9, 26, 12, 0, 0)
    asyncio.run(
        gw.async_log_success_event(
            {"litellm_call_id": "call-9"},
            {"usage": usage},
            t0,
            t0 + dt.timedelta(seconds=2),
        )
    )
    out = _rows(tmp_path, "outcome")[-1]
    u = out["usage"]
    assert (
        u["uncached_input"],
        u["cache_read"],
        u["cache_write_1h"],
        u["cache_write_5m"],
    ) == (3, 15093, 3674, 0)
    assert u["input_equiv_billed"] == round(3 + 3674 * 2.0 + 15093 * 0.1, 1)
    assert u["cache_saved_input_equiv"] == round(18770 - u["input_equiv_billed"], 1)
    assert out["latency_ms"] == 2000 and out["ok"] and out["session"] == "s-1"


def test_a_failed_call_is_recorded_not_silent(monkeypatch, tmp_path):
    gw = _gw(monkeypatch, tmp_path)
    _call(gw, _conversation()[:3], call_id="call-x")
    t0 = dt.datetime(2026, 9, 26)
    asyncio.run(
        gw.async_log_failure_event(
            {"litellm_call_id": "call-x", "exception": "400 bad"}, None, t0, t0
        )
    )
    out = _rows(tmp_path, "outcome")[-1]
    assert out["ok"] is False and "400" in out["error"]

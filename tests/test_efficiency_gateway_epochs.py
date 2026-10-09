"""Epoch compaction (idp#4893): one step-function compaction for every lane, cache-safe.

Measured 2026-09-29: 870.6 MB sent in a day through the laptop router and 0.3 % cut, because
the Anthropic-shaped chain never compacted and the OpenAI-shaped chain compacted by sliding
window, which rewrites the prefix on every call. These cases are the properties that make the
epoch safe on any model, in both wire shapes:

  * a snap shrinks the payload and replaces the old history with the shadow state document;
  * every later call in the epoch re-sends byte-identical bytes for everything the snap sent
    (the hash lock), including across a router restart;
  * no tool call/result pair is ever split, and leading system messages are kept;
  * reasoning is stripped only inside the lock's fixed edge, never from the newest turn;
  * a rewritten history, a failed fold and the router's own fold calls change nothing.
"""

from __future__ import annotations

import asyncio
import copy
import importlib.machinery
import importlib.util
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE_PATH = os.path.join(ROOT, "platform", "llm", "efficiency_gateway.py")
SESSION = json.dumps({"device_id": "d", "session_id": "s-epoch"})
SYSTEM = "You are a coding agent."


def _gw(monkeypatch, tmp_path, fold=None):
    for k, v in {
        "ESTATE_EFFICIENCY_LEDGER": str(tmp_path / "ledger.jsonl"),
        "ESTATE_EPOCH_DIR": str(tmp_path / "epochs"),
        "ESTATE_EPOCH_TOKENS": "4000",
        "ESTATE_EPOCH_KEEP_TOKENS": "1000",
        "ESTATE_SHADOW_FROM_TOKENS": "2000",
        "ESTATE_SHADOW_EVERY_TOKENS": "500",
        "ESTATE_SHADOW_CHUNK_CHARS": "4000",
        "ESTATE_HOLDOUT_PCT": "0",  # the holdout has its own test
    }.items():
        monkeypatch.setenv(k, v)
    spec = importlib.util.spec_from_loader(
        "gw_epochs_under_test",
        importlib.machinery.SourceFileLoader("gw_epochs_under_test", MODULE_PATH),
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gw_epochs_under_test"] = mod
    spec.loader.exec_module(mod)
    gw = mod.EstateEfficiencyGateway()
    gw._epochs.spawn = lambda fn, *a: fn(*a)  # fold inline so the test sees its result
    gw._epochs.fold = fold or (
        lambda state, events: f"{state}- saw {events.count('[')} messages\n"
    )
    return gw


def _rows(tmp_path, kind):
    p = tmp_path / "ledger.jsonl"
    rows = [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []
    return [r for r in rows if r.get("kind") == kind]


def _strip(o):
    if isinstance(o, dict):
        return {k: _strip(v) for k, v in o.items() if k != "cache_control"}
    if isinstance(o, list):
        return [_strip(v) for v in o]
    return o


def _anthropic(turns):
    msgs = [{"role": "user", "content": [{"type": "text", "text": "fix the bug"}]}]
    for i in range(turns):
        msgs.append(
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "thinking",
                        "thinking": f"plan {i} " * 20,
                        "signature": f"sig{i}",
                    },
                    {"type": "text", "text": f"reading file {i}"},
                    {
                        "type": "tool_use",
                        "id": f"toolu_{i}",
                        "name": "Read",
                        "input": {"n": i},
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
                        "content": [
                            {"type": "text", "text": f"line {i} of the file\n" * 40}
                        ],
                    }
                ],
            }
        )
    return msgs


def _openai(turns):
    msgs = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": "fix the bug"},
    ]
    for i in range(turns):
        msgs.append(
            {
                "role": "assistant",
                "content": f"reading file {i}",
                "reasoning_content": f"plan {i} " * 20,
                "tool_calls": [
                    {
                        "id": f"call_{i}",
                        "type": "function",
                        "function": {"name": "read", "arguments": json.dumps({"n": i})},
                    }
                ],
            }
        )
        msgs.append(
            {
                "role": "tool",
                "tool_call_id": f"call_{i}",
                "content": f"line {i} of the file\n" * 40,
            }
        )
    return msgs


SHAPES = {"anthropic": _anthropic, "openai": _openai}


def _call(gw, shape, messages):
    data = {
        "model": "any-model",
        "messages": copy.deepcopy(messages),
        "metadata": {"user_id": SESSION},
    }
    if shape == "anthropic":
        data["system"] = [{"type": "text", "text": SYSTEM}]
        data["litellm_call_id"] = f"c{len(messages)}"
        return asyncio.run(
            gw.async_pre_call_hook(None, None, data, "anthropic_messages")
        )["messages"]
    return asyncio.run(gw.async_pre_call_hook(None, None, data, "acompletion"))[
        "messages"
    ]


def _orphans(msgs):
    """Tool results whose call is not in the assistant turn right before them, both shapes."""
    bad, open_ids = 0, set()
    for m in msgs:
        if m.get("role") == "assistant":
            open_ids = {tc["id"] for tc in m.get("tool_calls") or []}
            if isinstance(m.get("content"), list):
                open_ids |= {
                    b["id"] for b in m["content"] if b.get("type") == "tool_use"
                }
        elif m.get("role") == "tool":
            bad += m["tool_call_id"] not in open_ids
        elif isinstance(m.get("content"), list):
            bad += sum(
                b.get("tool_use_id") not in open_ids
                for b in m["content"]
                if b.get("type") == "tool_result"
            )
    return bad


def _epoch_run(gw, shape):
    """Three consecutive turns of one growing conversation: fold, snap, locked."""
    conv = SHAPES[shape](40)
    first = _call(gw, shape, conv)  # big enough to fold, no state yet: nothing cut
    conv2 = conv + SHAPES[shape](41)[-2:]
    second = _call(gw, shape, conv2)  # state covers the history: snap
    conv3 = conv2 + SHAPES[shape](42)[-2:]
    third = _call(gw, shape, conv3)  # same epoch: the lock
    return conv, first, conv2, second, conv3, third


@pytest.mark.parametrize("shape", SHAPES)
def test_a_snap_replaces_old_history_with_the_state_and_shrinks_it(
    monkeypatch, tmp_path, shape
):
    gw = _gw(monkeypatch, tmp_path)
    conv, first, conv2, second, _, _ = _epoch_run(gw, shape)
    assert len(first) == len(conv), "no state yet, so the first big call is sent whole"
    body = [m for m in second if m.get("role") != "system"]
    assert body[0]["role"] == "user"
    assert body[0]["content"].startswith("[estate router, epoch 1:")
    assert "- saw" in body[0]["content"], (
        "the frozen state document is what replaces the history"
    )
    assert body[1]["role"] == "assistant"
    assert len(json.dumps(second)) < len(json.dumps(conv2)) / 2
    assert _orphans(second) == 0
    if shape == "openai":
        assert second[0] == {"role": "system", "content": SYSTEM}
    pre = _rows(tmp_path, "pre")[-2]
    m7 = pre["steps"]["m7"]
    assert m7["action"] == "snapped" and m7["epoch"] == 1 and m7["bytes"] > 0


@pytest.mark.parametrize("shape", SHAPES)
def test_every_call_in_the_epoch_resends_the_snapped_bytes_unchanged(
    monkeypatch, tmp_path, shape
):
    gw = _gw(monkeypatch, tmp_path)
    _, _, _, second, _, third = _epoch_run(gw, shape)
    assert _strip(third[: len(second)]) == _strip(second), (
        "the hash lock keeps the prefix frozen"
    )
    pre = _rows(tmp_path, "pre")[-1]
    m7 = pre["steps"]["m7"]
    assert m7["action"] == "locked"


@pytest.mark.parametrize("shape", SHAPES)
def test_the_lock_survives_a_router_restart(monkeypatch, tmp_path, shape):
    gw = _gw(monkeypatch, tmp_path)
    _, _, _, _, conv3, third = _epoch_run(gw, shape)
    restarted = _gw(monkeypatch, tmp_path, fold=lambda s, e: "a different summary")
    assert _strip(_call(restarted, shape, conv3)) == _strip(third)


@pytest.mark.parametrize("shape", SHAPES)
def test_reasoning_is_stripped_only_inside_the_locked_edge(
    monkeypatch, tmp_path, shape
):
    gw = _gw(monkeypatch, tmp_path)
    _, _, _, second, _, _ = _epoch_run(gw, shape)

    def reasons(m):
        if shape == "openai":
            return "reasoning_content" in m
        return any(b.get("type") == "thinking" for b in m["content"])

    asst = [m for m in second if m.get("role") == "assistant"]
    assert len(asst) >= 2
    assert not any(reasons(m) for m in asst[:-1])
    assert reasons(asst[-1]), "the newest assistant turn is never touched"


@pytest.mark.parametrize("shape", SHAPES)
def test_a_rewritten_history_is_never_matched_to_an_old_lock(
    monkeypatch, tmp_path, shape
):
    gw = _gw(monkeypatch, tmp_path)
    _, _, _, _, conv3, _ = _epoch_run(gw, shape)
    edited = copy.deepcopy(conv3)
    target = edited[-40]  # a tool result well before the cut
    if shape == "openai":
        target["content"] = "rewritten"
    else:
        target["content"][0]["content"] = [{"type": "text", "text": "rewritten"}]
    out = _call(gw, shape, edited)
    assert len(out) == len(edited)
    assert not any(
        isinstance(m.get("content"), str) and m["content"].startswith("[estate router")
        for m in out
    )


@pytest.mark.parametrize("shape", SHAPES)
def test_a_failed_fold_changes_nothing_and_is_recorded(monkeypatch, tmp_path, shape):
    def down(state, events):
        raise OSError("all cheap lanes down")

    gw = _gw(monkeypatch, tmp_path, fold=down)
    conv, first, conv2, second, _, _ = _epoch_run(gw, shape)
    assert len(first) == len(conv) and len(second) == len(conv2)
    shadow = _rows(tmp_path, "shadow")
    assert (
        shadow
        and not shadow[-1]["ok"]
        and "all cheap lanes down" in shadow[-1]["error"]
    )


def test_the_routers_own_fold_call_is_left_alone(monkeypatch, tmp_path):
    gw = _gw(monkeypatch, tmp_path)
    data = {
        "model": "groq",
        "messages": _openai(60),
        "metadata": {"estate_internal": "estate-shadow-state"},
    }
    out = asyncio.run(
        gw.async_pre_call_hook(None, None, copy.deepcopy(data), "acompletion")
    )
    assert out["messages"] == data["messages"]
    assert _rows(tmp_path, "pre") == []


def _retail(shape, msgs, text):
    """The same history ending in a different newest message, as a harness side request sends."""
    out = copy.deepcopy(msgs)
    if shape == "openai":
        out[-1]["content"] = text
    else:
        out[-1]["content"] = [{"type": "text", "text": text}]
    return out


@pytest.mark.parametrize("shape", SHAPES)
def test_a_side_request_ending_differently_keeps_the_lock(monkeypatch, tmp_path, shape):
    # 2026-10-09: a 600 ms Claude Code side request shared the history but ended in its own
    # message; the fold covered that message, the real turn's hash missed, every lock was
    # wiped and the conversation went to Opus whole (50k -> 196k tokens) for six minutes
    gw = _gw(monkeypatch, tmp_path)
    _, _, _, _, conv3, third = _epoch_run(gw, shape)
    side = _retail(shape, conv3, "summarise this session in one line")
    _call(gw, shape, side)
    real = _retail(shape, conv3, "get it done")
    out = _call(gw, shape, real)
    assert len(out) < len(real), "the real turn is still compacted"
    assert _strip(out[: len(third) - 1]) == _strip(third[:-1]), (
        "and its prefix still cached"
    )
    assert _rows(tmp_path, "pre")[-1]["steps"]["m7"]["action"] in ("locked", "snapped")


@pytest.mark.parametrize("shape", SHAPES)
def test_a_broken_state_hash_falls_back_to_the_newest_matching_lock(
    monkeypatch, tmp_path, shape
):
    gw = _gw(monkeypatch, tmp_path)
    _, _, _, _, conv3, third = _epoch_run(gw, shape)
    rec = next(iter(gw._epochs._convs.values()))
    rec["covered_hash"] = (
        "not-this-history"  # a fold from before this fix, past the tip
    )
    out = _call(gw, shape, conv3)
    assert _strip(out) == _strip(third), "the lock still applies, byte for byte"
    rec = next(iter(gw._epochs._convs.values()))
    hist = [m for m in conv3 if m.get("role") != "system"]
    assert rec["locks"], "the locks that still match are kept"
    assert rec["locks"][-1]["cut"] <= rec["covered"] < len(hist), (
        "never the newest message"
    )

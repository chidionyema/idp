"""tests/test_efficiency_shadow_fold_answers.py — the shadow fold must answer.

The m7 shadow fold is the safety arm of epoch compaction: it folds state through
a cheap lane and compares the result against the real request. Measured
2026-10-26, it was not comparing anything: 1,369 of the laptop ledger's shadow
rows carry `error: "fold returned an empty state"`, `ok: false`, every one of
them `model: deepseek`.

The cause is the same disease that made code-review Tier 2 answer nothing:
deepseek is a reasoning lane - it spends the whole max_tokens budget on
`reasoning_content` and returns an EMPTY `content`. The router counts an empty
content as a 200, so LiteLLM's fallback chain never engaged, and the fold
raised on the client side after the router had already "succeeded".

These tests grade the cure:
  1. the fold's default lane is one the router offers, and one that answers;
  2. an answer carried in reasoning_content is used when content is empty;
  3. a fold with nothing at all says WHICH lane failed, not just that it did.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import sys

import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE_PATH = os.path.join(ROOT, "platform", "llm", "efficiency_gateway.py")
LAPTOP_CONFIG = os.path.join(ROOT, "llm", "config.yaml")
CLUSTER_CONFIG = os.path.join(ROOT, "platform", "llm", "config.yaml")


def _gw():
    spec = importlib.util.spec_from_loader(
        "gw_shadow_fold_under_test",
        importlib.machinery.SourceFileLoader("gw_shadow_fold_under_test", MODULE_PATH),
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gw_shadow_fold_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _completion(content: str = "", reasoning: str = "") -> dict:
    return {
        "choices": [
            {
                "message": {
                    "content": content,
                    "reasoning_content": reasoning,
                    "role": "assistant",
                }
            }
        ]
    }


def _patch_urlopen(monkeypatch, payload):
    calls = []

    def fake(req, timeout=None):
        calls.append(req)
        return _Resp(payload)

    monkeypatch.setattr("urllib.request.urlopen", fake)
    return calls


def test_the_default_fold_lane_is_offered_by_both_routers():
    gw = _gw()
    assert gw.SHADOW_MODEL == "minimax_m27"
    for config_path in (LAPTOP_CONFIG, CLUSTER_CONFIG):
        with open(config_path) as handle:
            config = yaml.safe_load(handle)
        names = {m.get("model_name") for m in config.get("model_list", [])}
        assert gw.SHADOW_MODEL in names, f"{config_path} does not offer the fold's lane"


def test_an_answer_in_reasoning_content_is_used_when_content_is_empty(monkeypatch):
    """A reasoning lane answers with an empty content and the answer elsewhere."""
    gw = _gw()
    monkeypatch.setenv("ESTATE_SHADOW_URL", "http://127.0.0.1:4000/v1/chat/completions")
    _patch_urlopen(monkeypatch, _completion(content="", reasoning="the folded state"))

    out = gw._fold_remote("state", "events")
    assert out == "the folded state"


def test_a_content_answer_still_wins_over_reasoning(monkeypatch):
    gw = _gw()
    monkeypatch.setenv("ESTATE_SHADOW_URL", "http://127.0.0.1:4000/v1/chat/completions")
    _patch_urlopen(monkeypatch, _completion(content="the state", reasoning="thinking"))

    assert gw._fold_remote("state", "events") == "the state"


def test_fenced_answers_are_unwrapped(monkeypatch):
    gw = _gw()
    monkeypatch.setenv("ESTATE_SHADOW_URL", "http://127.0.0.1:4000/v1/chat/completions")
    _patch_urlopen(monkeypatch, _completion(content="```\nthe state\n```"))

    assert gw._fold_remote("state", "events") == "the state"


def test_an_empty_fold_names_the_lane_that_failed(monkeypatch):
    gw = _gw()
    monkeypatch.setenv("ESTATE_SHADOW_URL", "http://127.0.0.1:4000/v1/chat/completions")
    _patch_urlopen(monkeypatch, _completion(content="", reasoning=""))

    with pytest.raises(ValueError) as excinfo:
        gw._fold_remote("state", "events")
    assert "empty state" in str(excinfo.value)
    assert gw.SHADOW_MODEL in str(excinfo.value), "the error must name the lane"


def test_the_fold_calls_the_router_with_the_fold_lane(monkeypatch):
    gw = _gw()
    monkeypatch.setenv("ESTATE_SHADOW_URL", "http://127.0.0.1:4000/v1/chat/completions")
    calls = _patch_urlopen(monkeypatch, _completion(content="the state"))

    gw._fold_remote("state", "events")
    assert len(calls) == 1
    body = json.loads(calls[0].data.decode())
    assert body["model"] == gw.SHADOW_MODEL
    assert body["messages"][0]["role"] == "system"
    assert "NEW EVENTS" in body["messages"][1]["content"]

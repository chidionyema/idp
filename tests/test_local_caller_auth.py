"""The laptop router refuses browsers, and keyed lanes refuse callers without the laptop key."""

import asyncio
import sys
from pathlib import Path

import pytest

pytest.importorskip("litellm")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "platform" / "llm"))

import local_caller_auth as lca  # noqa: E402
from fastapi import HTTPException  # noqa: E402

CONFIG = """
model_list:
  - model_name: groq
    litellm_params: {model: openai/x, api_key: os.environ/GROQ_API_KEY}
  - model_name: voice-*
    litellm_params: {model: groq/y, api_key: os.environ/GROQ_API_KEY}
  - model_name: ollama-vision
    litellm_params: {model: openai/z, api_key: ollama}
  - model_name: claude-*
    litellm_params: {model: anthropic/claude-*}
"""


def test_only_lanes_that_spend_a_router_key_are_keyed(tmp_path):
    cfg = tmp_path / "c.yaml"
    cfg.write_text(CONFIG)
    lanes = lca.keyed_lanes(str(cfg))
    assert lanes == {"groq", "voice-*"}
    assert lca.is_keyed("voice-asr", lanes)
    assert not lca.is_keyed("claude-opus-5-5", lanes)
    assert not lca.is_keyed("ollama-vision", lanes)


def test_a_browser_is_refused_by_origin_or_by_a_rebound_host():
    assert lca.browser_reason({"origin": "https://x.example", "host": "127.0.0.1:4000"})
    assert lca.browser_reason({"host": "evil.example:4000"})
    assert lca.browser_reason({"host": "127.0.0.1:4000"}) is None


def test_only_the_laptop_key_is_a_local_service():
    assert lca.caller_class("k-1", caller_key="k-1") == lca.LOCAL_SERVICE
    assert lca.caller_class("k-2", caller_key="k-1") == lca.OWN_CREDENTIAL
    assert lca.caller_class("", caller_key="") == lca.OWN_CREDENTIAL


class _Key:
    def __init__(self, caller):
        self.metadata = {"estate_caller": caller}


def test_a_keyed_lane_refuses_a_caller_without_the_key(monkeypatch):
    monkeypatch.setattr(lca, "KEYED", frozenset({"groq"}))
    hook = lca.LocalCallerLanes()
    run = lambda caller, model: asyncio.run(  # noqa: E731
        hook.async_pre_call_hook(_Key(caller), None, {"model": model}, "completion")
    )
    with pytest.raises(HTTPException) as e:
        run(lca.OWN_CREDENTIAL, "groq")
    assert e.value.status_code == 401
    assert run(lca.LOCAL_SERVICE, "groq") is None
    assert run(lca.OWN_CREDENTIAL, "claude-opus-5-5") is None

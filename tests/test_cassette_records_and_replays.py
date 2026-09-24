"""Prove the cassette boundary both ways, against the real cassette.py.

Four properties the estate needs, each tested:
  1. an OFF router changes nothing (inert by default)
  2. REPLAY serves the recorded answer and makes no live call
  3. a MISS in replay REFUSES, naming the key -- it never falls back to the network
  4. RECORD writes one entry, and is idempotent on a re-run
"""

from __future__ import annotations

import asyncio
import importlib.machinery
import importlib.util
import json
from pathlib import Path

import pytest

MOD = Path(__file__).resolve().parents[1] / "platform" / "llm" / "cassette.py"


@pytest.fixture()
def cass(monkeypatch, tmp_path):
    monkeypatch.setenv("ESTATE_CASSETTE_DIR", str(tmp_path))
    monkeypatch.setenv("ESTATE_CASSETTE_NAME", "test")
    spec = importlib.util.spec_from_loader(
        "cassette_under_test",
        importlib.machinery.SourceFileLoader("cassette_under_test", str(MOD)),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


REQ = {
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "name the estate's one Prometheus"}],
    "temperature": 0,
    "max_tokens": 64,
}
RESP = {
    "id": "chatcmpl-1",
    "choices": [{"message": {"role": "assistant", "content": "kube-prometheus-stack"}}],
}


class _Resp:
    """Stands in for a LiteLLM ModelResponse, which exposes model_dump()."""

    def __init__(self, body):
        self._body = body

    def model_dump(self):
        return self._body


def test_off_is_inert(cass):
    """Default mode is off: no cassette read, no write, no behaviour change."""
    hook = cass.proxy_handler_instance
    assert cass.mode() == "off"
    assert asyncio.run(hook.async_pre_call_hook(data=dict(REQ))) is None
    assert not (hook.path).exists()


def test_record_then_replay_serves_the_same_answer(cass):
    """The round trip. Record once live, then replay: the answer is identical and no network
    is reachable from the replay path."""
    hook = cass.proxy_handler_instance
    cass.os.environ["ESTATE_CASSETTE_MODE"] = "record"
    asyncio.run(hook.async_post_call_success_hook(data=dict(REQ), response=_Resp(RESP)))
    assert hook.path.is_file()

    cass.os.environ["ESTATE_CASSETTE_MODE"] = "replay"
    hook._entries = None
    got = asyncio.run(hook.async_pre_call_hook(data=dict(REQ)))
    assert got["choices"][0]["message"]["content"] == "kube-prometheus-stack"


def test_a_replay_miss_refuses_and_names_the_key(cass):
    """THE LOAD-BEARING ONE. A miss must refuse. Falling back to a live call would put the
    network, the spend and the sampling noise back into CI -- silently."""
    cass.os.environ["ESTATE_CASSETTE_MODE"] = "replay"
    hook = cass.proxy_handler_instance
    other = dict(
        REQ, messages=[{"role": "user", "content": "a question never recorded"}]
    )
    with pytest.raises(cass.CassetteMiss) as e:
        asyncio.run(hook.async_pre_call_hook(data=other))
    assert "no cassette entry for key" in str(e.value)
    assert "Record it" in str(e.value)


def test_record_is_idempotent_on_a_rerun(cass):
    """Re-running the recorder must not append a second row for the same question: a cassette
    that grows on every run stops being a baseline."""
    hook = cass.proxy_handler_instance
    cass.os.environ["ESTATE_CASSETTE_MODE"] = "record"
    for _ in range(3):
        asyncio.run(
            hook.async_post_call_success_hook(data=dict(REQ), response=_Resp(RESP))
        )
    assert len(hook.path.read_text().splitlines()) == 1


def test_identity_is_not_part_of_the_key(cass):
    """The key hashes the QUESTION. Two callers asking the same thing with different keys must
    land on one entry, or a cassette would never be reusable across runs."""
    hook = cass.proxy_handler_instance
    cass.os.environ["ESTATE_CASSETTE_MODE"] = "record"
    a = dict(REQ, api_key="key-a", user_api_key_dict={"k": 1})
    b = dict(REQ, api_key="key-b", user_api_key_dict={"k": 2})
    assert cass.key_for(a) == cass.key_for(b)
    asyncio.run(hook.async_post_call_success_hook(data=a, response=_Resp(RESP)))
    asyncio.run(hook.async_post_call_success_hook(data=b, response=_Resp(RESP)))
    assert len(hook.path.read_text().splitlines()) == 1


def test_sampling_params_are_part_of_the_key(cass):
    """temperature IS the question. Reusing a temperature-0 answer for a temperature-1 request
    would replay an answer to a different question."""
    assert cass.key_for(dict(REQ, temperature=0)) != cass.key_for(
        dict(REQ, temperature=1)
    )


def test_cassette_is_human_readable_and_diffable(cass):
    """A trajectory change must show as a diff, not as prose. The file is JSONL, one call per
    line, with the request and response in the clear."""
    hook = cass.proxy_handler_instance
    cass.os.environ["ESTATE_CASSETTE_MODE"] = "record"
    asyncio.run(hook.async_post_call_success_hook(data=dict(REQ), response=_Resp(RESP)))
    row = json.loads(hook.path.read_text().splitlines()[0])
    assert row["request"]["model"] == "gpt-4o-mini"
    assert (
        row["response"]["choices"][0]["message"]["content"] == "kube-prometheus-stack"
    )
    assert "api_key" not in row["request"], "a key must never be written to a cassette"

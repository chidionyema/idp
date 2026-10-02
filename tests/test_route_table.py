"""The compiled route table serves elsewhere when a group is dead, and says so (CP2).

WHAT THIS GRADES. `platform/llm/route_table.py` claims: deployments the registry condemns
are dropped from the candidate list BEFORE the pick; a request for a group with no
servable deployment is rewritten to a healthy lane of the same class, with
`x-estate-served-by` stamped on the response and a row journalled — never silent; a
group that still has a lane, an unknown alias, and a class with no healthy lane at all
all pass through untouched (LiteLLM's own fallbacks own the last case).

THE MEASURED DEFECT THIS PREVENTS: "No fallback model group found" burned to a user on
moonshot/kimi-k3 while groq was free and healthy, because nothing held the balance fact.

CALLED THE WAY LITELLM CALLS IT: async_filter_deployments(model, healthy_deployments,
messages, request_kwargs, parent_otel_span) and async_pre_call_hook(user_api_key_dict,
cache, data, call_type), signatures read from the installed 1.98.0 custom_logger.py.
"""

import asyncio
import importlib.util
import json
import pathlib
import sys

import pytest

LLM_DIR = pathlib.Path(__file__).resolve().parents[1] / "platform" / "llm"
CONFIG_YAML = """
model_list:
  - model_name: default
    litellm_params:
      model: moonshot/kimi-k3
      api_key: os.environ/NO_SUCH_KEY
  - model_name: groq
    litellm_params:
      model: groq/llama-3.3-70b-versatile
      api_key: os.environ/NO_SUCH_KEY
  - model_name: vision
    litellm_params:
      model: gemini/gemini-2.5-flash
      api_key: os.environ/NO_SUCH_KEY
  - model_name: voice-tts
    litellm_params:
      model: groq/canopylabs/orpheus-v1-english
      api_key: os.environ/NO_SUCH_KEY
    model_info:
      mode: audio_speech
"""


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


@pytest.fixture()
def mods(tmp_path, monkeypatch):
    monkeypatch.setenv("ESTATE_ROUTER_STATE_DIR", str(tmp_path / "router"))
    monkeypatch.setenv("ESTATE_ROUTER_PROBES", "0")
    monkeypatch.setenv(
        "ESTATE_ROUTER_TABLE_JSON", str(tmp_path / "router" / "table.json")
    )
    cfg = tmp_path / "config.yaml"
    cfg.write_text(CONFIG_YAML)
    monkeypatch.setenv("ESTATE_ROUTER_CONFIG", str(cfg))
    lr = _load("lane_registry", LLM_DIR / "lane_registry.py")
    rt = _load("route_table", LLM_DIR / "route_table.py")
    return lr, rt


def _dep(model):
    return {
        "model_name": model,
        "litellm_params": {"model": model},
        "model_info": {"id": model},
    }


def _pre_call(rt, model):
    data = {"model": model, "messages": [], "metadata": {}}
    asyncio.run(
        rt.EstateRouteTable().async_pre_call_hook(
            user_api_key_dict=None, cache=None, data=data, call_type="completion"
        )
    )
    return data


# ------------------------------------------------------------- deployment filtering


def test_condemned_deployments_are_dropped_before_the_pick(mods):
    lr, rt = mods
    lr.proxy_handler_instance.observe_failure(
        "moonshot/kimi-k3", 402, "insufficient balance"
    )
    survivors = asyncio.run(
        rt.EstateRouteTable().async_filter_deployments(
            "default", [_dep("moonshot/kimi-k3"), _dep("groq/llama-3.3-70b-versatile")]
        )
    )
    assert [s["litellm_params"]["model"] for s in survivors] == [
        "groq/llama-3.3-70b-versatile"
    ]


def test_filter_never_empties_the_list(mods):
    """All condemned: passthrough — LiteLLM's retries own it, not an empty pick."""
    lr, rt = mods
    lr.proxy_handler_instance.observe_failure("moonshot/kimi-k3", 402, "no balance")
    deps = [_dep("moonshot/kimi-k3")]
    survivors = asyncio.run(
        rt.EstateRouteTable().async_filter_deployments("default", deps)
    )
    assert survivors == deps


# ------------------------------------------------------------ dead-group re-route


def test_dead_group_is_served_elsewhere_of_the_same_class(mods, tmp_path):
    lr, rt = mods
    lr.proxy_handler_instance.observe_failure(
        "moonshot/kimi-k3", 402, "insufficient balance"
    )
    data = _pre_call(rt, "default")
    assert data["model"] == "groq"
    assert data["metadata"]["estate_served_by"] == "groq"
    assert data["metadata"]["estate_requested"] == "default"
    row = json.loads(
        (tmp_path / "router" / "substitutions.jsonl").read_text().splitlines()[-1]
    )
    assert row["requested"] == "default" and row["served_by"] == "groq"


def test_dead_group_of_a_lone_class_passes_through(mods):
    """vision is dead and no other vision lane exists: untouched, never a guess."""
    lr, rt = mods
    lr.proxy_handler_instance.observe_failure("gemini/gemini-2.5-flash", 403, "bad key")
    data = _pre_call(rt, "vision")
    assert data["model"] == "vision"
    assert "estate_served_by" not in data["metadata"]


def test_healthy_group_is_untouched(mods):
    lr, rt = mods
    data = _pre_call(rt, "groq")
    assert data["model"] == "groq"
    assert "estate_served_by" not in data["metadata"]


def test_unknown_alias_is_untouched(mods):
    lr, rt = mods
    data = _pre_call(rt, "brand-new-alias")
    assert data["model"] == "brand-new-alias"


def test_dead_non_chat_group_is_not_rescued_to_chat(mods, tmp_path):
    """voice-tts dead: a chat lane would be garbled audio, not a rescue — the mode is
    part of the contract. Untouched, nothing journalled, LiteLLM's own fallbacks own
    it: the outage is loud, never silent. (Measured live 2026-10-02: every TTS call
    was rewritten to default.)"""
    lr, rt = mods
    lr.proxy_handler_instance.observe_failure(
        "groq/canopylabs/orpheus-v1-english", 402, "insufficient balance"
    )
    data = _pre_call(rt, "voice-tts")
    assert data["model"] == "voice-tts"
    assert "estate_served_by" not in data["metadata"]
    assert not (tmp_path / "router" / "substitutions.jsonl").exists()


# ------------------------------------------------------------------ never silent


def test_served_by_is_stamped_on_the_response(mods):
    lr, rt = mods

    class _Resp:
        _hidden_params = {}

    resp = asyncio.run(
        rt.EstateRouteTable().async_post_call_success_hook(
            None, _Resp(), {"metadata": {"estate_served_by": "groq"}}
        )
    )
    assert resp._hidden_params["additional_headers"]["x-estate-served-by"] == "groq"


def test_unsubstituted_response_gets_no_header(mods):
    lr, rt = mods

    class _Resp:
        _hidden_params = {}

    resp = asyncio.run(
        rt.EstateRouteTable().async_post_call_success_hook(
            None, _Resp(), {"metadata": {}}
        )
    )
    assert "additional_headers" not in resp._hidden_params


# -------------------------------------------------------------- recompile on facts


def test_table_recompiles_when_the_registry_transitions(mods):
    """The table changes on transitions, never per request: a lane heals, the dead
    group routes natively again."""
    lr, rt = mods
    reg = lr.proxy_handler_instance
    reg.observe_failure("moonshot/kimi-k3", 402, "no balance")
    data_dead = _pre_call(rt, "default")
    assert data_dead["model"] == "groq"
    reg.observe_success("moonshot/kimi-k3", 120.0)  # credit returned
    assert _pre_call(rt, "default")["model"] == "default"

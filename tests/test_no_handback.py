"""platform/llm/no_handback.py: every model call through the router is told to drive the work to done."""

import asyncio
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "platform", "estate", "memory"))
import handback  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "no_handback", os.path.join(ROOT, "platform", "llm", "no_handback.py")
)
nh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nh)


def call(data, call_type="acompletion"):
    out = asyncio.run(
        nh.proxy_handler_instance.async_pre_call_hook(None, None, data, call_type)
    )
    return out


def test_directive_is_the_one_the_hooks_use():
    # the router cannot import handback.py (flat ConfigMap modules), so equality is the contract
    assert nh.DIRECTIVE == handback.DIRECTIVE


def test_chat_with_a_system_message_gets_it_appended_last():
    data = {
        "messages": [
            {"role": "system", "content": "Be brief."},
            {"role": "user", "content": "go"},
        ]
    }
    out = call(data)
    assert out["messages"][0]["content"].startswith("Be brief.")
    assert out["messages"][0]["content"].endswith(nh.BLOCK)
    assert out["messages"][1] == {"role": "user", "content": "go"}
    assert out["metadata"]["no_handback"] == "messages"


def test_chat_without_a_system_message_gets_one_in_front():
    out = call({"messages": [{"role": "user", "content": "go"}]})
    assert out["messages"][0] == {"role": "system", "content": nh.BLOCK}
    assert out["messages"][1]["content"] == "go"


def test_block_content_keeps_the_clients_blocks_and_their_cache_marks():
    first = {"type": "text", "text": "rules", "cache_control": {"type": "ephemeral"}}
    out = call(
        {
            "messages": [
                {"role": "system", "content": [first]},
                {"role": "user", "content": "x"},
            ]
        }
    )
    content = out["messages"][0]["content"]
    assert content[0] == first and content[1] == {"type": "text", "text": nh.BLOCK}


def test_anthropic_messages_use_the_system_field_as_string_or_blocks():
    s = call(
        {"system": "rules", "messages": [{"role": "user", "content": "x"}]},
        "anthropic_messages",
    )
    assert s["system"] == f"rules\n\n{nh.BLOCK}" and len(s["messages"]) == 1
    b = call(
        {
            "system": [{"type": "text", "text": "rules"}],
            "messages": [{"role": "user", "content": "x"}],
        }
    )
    assert b["system"][-1]["text"] == nh.BLOCK
    n = call({"messages": [{"role": "user", "content": "x"}], "system": None})
    assert n["system"] == nh.BLOCK


def test_developer_role_counts_as_the_system_prompt():
    out = call(
        {
            "messages": [
                {"role": "developer", "content": "d"},
                {"role": "user", "content": "x"},
            ]
        }
    )
    assert (
        out["messages"][0]["content"].endswith(nh.BLOCK) and len(out["messages"]) == 2
    )


def test_responses_api_gets_instructions():
    out = call({"input": "go"}, "aresponses")
    assert out["instructions"] == nh.BLOCK


def test_idempotent_across_retries_and_fallbacks():
    data = {"messages": [{"role": "user", "content": "go"}]}
    call(data)
    once = repr(data["messages"])
    call(data)
    assert repr(data["messages"]) == once and once.count(nh.MARKER) == 1


def test_calls_with_no_prompt_are_left_alone():
    for data in ({"model": "embed"}, {}, {"messages": []}):
        before = repr(data)
        assert repr(call(data)) == before


def test_embeddings_and_other_non_chat_calls_are_left_alone():
    # an embedding request has `input` too; an `instructions` field there is a parameter the
    # provider rejects
    for ct in ("aembedding", "embedding", "image_generation", "moderation"):
        data = {"model": "text-embedding-3-small", "input": ["hello"]}
        assert call(data, ct) == {"model": "text-embedding-3-small", "input": ["hello"]}


def test_the_routers_own_internal_calls_are_left_alone():
    by_meta = {
        "messages": [{"role": "user", "content": "fold"}],
        "metadata": {"estate_internal": "estate-shadow-state"},
    }
    assert call(by_meta)["messages"] == [{"role": "user", "content": "fold"}]
    by_header = {
        "messages": [{"role": "user", "content": "fold"}],
        "proxy_server_request": {
            "headers": {"x-estate-internal": "estate-shadow-state"}
        },
    }
    assert call(by_header)["messages"] == [{"role": "user", "content": "fold"}]


def test_opt_out_and_fail_open(monkeypatch):
    monkeypatch.setenv("ESTATE_NO_HANDBACK", "0")
    data = {"messages": [{"role": "user", "content": "go"}]}
    assert call(data)["messages"] == [{"role": "user", "content": "go"}]
    monkeypatch.delenv("ESTATE_NO_HANDBACK")
    # an unknown content shape and a non-dict never raise and never block the request
    weird = {
        "messages": [{"role": "system", "content": 7}, {"role": "user", "content": "x"}]
    }
    assert call(weird)["messages"][0]["content"] == 7
    assert call("not a dict") == "not a dict"


def test_registered_in_the_router_configs():
    import yaml

    for rel in ("config.base.yaml", "config.yaml"):
        cfg = yaml.safe_load(open(os.path.join(ROOT, "platform", "llm", rel)))
        assert (
            "no_handback.proxy_handler_instance" in cfg["litellm_settings"]["callbacks"]
        ), rel
    kust = open(os.path.join(ROOT, "platform", "llm", "kustomization.yaml")).read()
    assert "- no_handback.py" in kust

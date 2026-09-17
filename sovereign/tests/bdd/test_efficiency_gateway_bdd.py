"""BDD bindings for features/gates/efficiency-gateway.feature.

INDEPENDENCE: these step definitions call the hook as LiteLLM calls it and assert
VISIBLE MUTATIONS only (message body changed, counter incremented). No step asserts
"no exception was raised" — that is existence proof, not correspondence proof.

MODEL-AGNOSTIC: no step names a vendor. The hook boundary is async_pre_call_hook;
what the vendor does after is irrelevant to these scenarios.
"""

from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/gates/efficiency-gateway.feature")

REPO = Path(__file__).resolve().parents[3]
MODULE = REPO / "platform" / "llm" / "efficiency_gateway.py"


def _load():
    spec = importlib.util.spec_from_file_location("efficiency_gateway", MODULE)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["efficiency_gateway"] = mod
    spec.loader.exec_module(mod)
    return mod


def _run(gw, data):
    class _Key:
        api_key = "sk-bdd-test"
    return asyncio.run(
        gw.async_pre_call_hook(user_api_key_dict=_Key(), cache=None, data=data, call_type="completion")
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def state():
    return {}


@given("a gateway instance")
def _gateway(state):
    mod = _load()
    gw = mod.EstateEfficiencyGateway()
    state["gw"] = gw
    state["mod"] = mod
    state["data"] = {"messages": [], "tools": []}


# ---------------------------------------------------------------------------
# [1] CacheGuardian
# ---------------------------------------------------------------------------

@given(parsers.parse('a request with system prompt "{prompt}"'))
def _system_prompt(state, prompt):
    state["data"]["messages"] = [{"role": "system", "content": prompt}]
    state["prompt"] = prompt


@when("the hook runs twice with the same system prompt")
def _run_twice_same(state):
    for _ in range(2):
        state["result"] = _run(state["gw"], dict(state["data"]))


@when("the hook runs once with the original prompt")
def _run_once_original(state):
    _run(state["gw"], dict(state["data"]))


@when("the hook runs again with a different system prompt")
def _run_different_prompt(state):
    data = dict(state["data"])
    data["messages"] = [{"role": "system", "content": "Completely different prompt."}]
    state["result"] = _run(state["gw"], data)


@then(parsers.parse("cache_hits is {hits:d} and cache_misses is {misses:d}"))
def _check_cache(state, hits, misses):
    assert state["gw"]._cache_hits == hits
    assert state["gw"]._cache_misses == misses


@then(parsers.parse("cache_misses is {misses:d}"))
def _check_misses(state, misses):
    assert state["gw"]._cache_misses == misses


# ---------------------------------------------------------------------------
# [2] TokenKiller
# ---------------------------------------------------------------------------

@given(parsers.parse('a tool_result message with content "{content}"'))
def _tool_result_content(state, content):
    state["data"]["messages"] = [{"role": "tool", "content": content.replace("\\n", "\n"), "tool_call_id": "t1"}]


@when("the hook runs")
def _run_hook(state):
    state["result"] = _run(state["gw"], dict(state["data"]))


@then(parsers.parse('the tool_result content contains "{text}" exactly once'))
def _content_once(state, text):
    content = state["result"]["messages"][0]["content"]
    assert content.count(text) == 1


@then(parsers.parse('the content still contains "{text}"'))
def _content_contains(state, text):
    content = state["result"]["messages"][0]["content"]
    assert text in content


@then(parsers.parse("tool_line_compressions is {n:d}"))
def _compressions(state, n):
    assert state["gw"]._tool_line_compressions == n


# ---------------------------------------------------------------------------
# [3] MCPAdapter
# ---------------------------------------------------------------------------

@given(parsers.parse("a tool with a description of {n:d} characters"))
def _tool_desc(state, n):
    state["data"]["tools"] = [{"function": {"name": "tool", "description": "A" * n}}]


@then("the tool description is at most MAX_TOOL_DESC_CHARS + 1 characters long")
def _desc_truncated(state):
    limit = state["mod"].MAX_TOOL_DESC_CHARS
    desc = state["result"]["tools"][0]["function"]["description"]
    assert len(desc) <= limit + 1  # +1 for the ellipsis char


@then("the description ends with the ellipsis marker")
def _desc_ellipsis(state):
    desc = state["result"]["tools"][0]["function"]["description"]
    assert desc.endswith("…")


@then(parsers.parse("schemas_compressed is {n:d}"))
def _schemas_compressed(state, n):
    assert state["gw"]._schemas_compressed == n


# ---------------------------------------------------------------------------
# [4] TokenBudgetOrchestrator
# ---------------------------------------------------------------------------

@given(parsers.parse("a request with {n:d} characters of user content"))
def _user_content(state, n):
    state["data"]["messages"] = [{"role": "user", "content": "x" * n}]


@then(parsers.parse("calls is {c:d} and cumulative_tokens is {t:d}"))
def _calls_tokens(state, c, t):
    assert state["gw"]._calls == c
    assert state["gw"]._cumulative_tokens == t


@when("the hook runs again with the same content")
def _run_again(state):
    state["result"] = _run(state["gw"], dict(state["data"]))


# ---------------------------------------------------------------------------
# [5] SoLPi
# ---------------------------------------------------------------------------

@given(parsers.parse("two tool_result messages with identical content of {n:d} characters"))
def _two_large_obs(state, n):
    large = "observation data " * (n // 17 + 1)
    large = large[:n]
    state["data"]["messages"] = [
        {"role": "tool", "content": large, "tool_call_id": "obs_1"},
        {"role": "tool", "content": large, "tool_call_id": "obs_2"},
    ]


@then("the first tool_result is unchanged")
def _first_unchanged(state):
    original_len = len(state["data"]["messages"][0]["content"])
    result_len = len(state["result"]["messages"][0]["content"])
    assert result_len == original_len


@then(parsers.parse('the second tool_result contains "{text}"'))
def _second_contains(state, text):
    assert text in state["result"]["messages"][1]["content"]


@then(parsers.parse("obs_hits is {n:d}"))
def _obs_hits(state, n):
    assert state["gw"]._obs_hits == n


# ---------------------------------------------------------------------------
# [6] DynamicContextPruning
# ---------------------------------------------------------------------------

@given("a conversation of 14 messages including two identical tool_result entries")
def _convo_with_dup(state):
    filler = [{"role": "user", "content": f"msg {i}"} for i in range(12)]
    dup = {"role": "tool", "content": "result", "tool_call_id": "same"}
    state["data"]["messages"] = filler + [dup, dup]


@then("one of the duplicate tool_result entries is removed")
def _one_dup_removed(state):
    tools = [m for m in state["result"]["messages"] if m.get("role") == "tool"]
    assert len(tools) == 1


@then(parsers.parse("pruned_duplicates is {n:d}"))
def _pruned(state, n):
    assert state["gw"]._pruned_duplicates == n


# ---------------------------------------------------------------------------
# [7] CompactionManager
# ---------------------------------------------------------------------------

@given("a conversation of MAX_HISTORY_MSGS + 20 user messages")
def _long_convo(state):
    limit = state["mod"].MAX_HISTORY_MSGS
    state["data"]["messages"] = [{"role": "user", "content": f"m{i}"} for i in range(limit + 20)]
    state["limit"] = limit


@given("a conversation with one system message and MAX_HISTORY_MSGS + 10 user messages")
def _long_convo_with_system(state):
    limit = state["mod"].MAX_HISTORY_MSGS
    system = {"role": "system", "content": "System."}
    users = [{"role": "user", "content": f"m{i}"} for i in range(limit + 10)]
    state["data"]["messages"] = [system] + users
    state["limit"] = limit


@then("the message count is at most MAX_HISTORY_MSGS")
def _count_ok(state):
    assert len(state["result"]["messages"]) <= state["limit"]


@then(parsers.parse("compactions is {n:d}"))
def _compactions(state, n):
    assert state["gw"]._compactions == n


@then("the system message is still present")
def _system_preserved(state):
    systems = [m for m in state["result"]["messages"] if m.get("role") == "system"]
    assert len(systems) == 1


# ---------------------------------------------------------------------------
# [8] GistingSimulator
# ---------------------------------------------------------------------------

@given("a conversation where the first message is an assistant turn of 500 characters")
def _old_assistant(state):
    state["data"]["messages"] = [{"role": "assistant", "content": "A" * 500}]


@given("GIST_AFTER_MSGS + 1 more recent messages follow it")
def _recent_msgs(state):
    gist_after = state["mod"].GIST_AFTER_MSGS
    recent = [{"role": "user", "content": f"r{i}"} for i in range(gist_after + 1)]
    state["data"]["messages"] = state["data"]["messages"] + recent


@given("a single assistant message of 500 characters")
def _single_assistant(state):
    state["data"]["messages"] = [{"role": "assistant", "content": "A" * 500}]


@then('the first message starts with "[GISTED:"')
def _gisted(state):
    assert state["result"]["messages"][0]["content"].startswith("[GISTED:")


@then("the gist marker records the original character count")
def _gist_count(state):
    assert "500ch" in state["result"]["messages"][0]["content"]


@then(parsers.parse("gisted is {n:d}"))
def _gisted_count(state, n):
    assert state["gw"]._gisted == n


@then('the message does not start with "[GISTED:"')
def _not_gisted(state):
    assert not state["result"]["messages"][0]["content"].startswith("[GISTED:")


# ---------------------------------------------------------------------------
# All 8 together
# ---------------------------------------------------------------------------

@given("a realistic over-limit session payload")
def _realistic_payload(state):
    mod = state["mod"]
    limit = mod.MAX_HISTORY_MSGS
    old_assistant = {"role": "assistant", "content": "A" * 500}
    system = {"role": "system", "content": "System prompt."}
    users = [{"role": "user", "content": f"m{i}"} for i in range(limit + 5)]
    large = "observation data " * 50
    tool1 = {"role": "tool", "content": large, "tool_call_id": "obs_1"}
    tool2 = {"role": "tool", "content": large, "tool_call_id": "obs_2"}
    state["data"]["messages"] = [old_assistant, system] + users + [tool1, tool2]
    state["data"]["tools"] = [{"function": {"name": "verbose", "description": "X" * 2000}}]
    state["limit"] = limit


@then(parsers.parse("calls is {n:d}"))
def _calls(state, n):
    assert state["gw"]._calls == n


@then("cumulative_tokens is greater than 0")
def _tokens_positive(state):
    assert state["gw"]._cumulative_tokens > 0


@then("schemas_compressed is at least 1")
def _schemas_at_least_1(state):
    assert state["gw"]._schemas_compressed >= 1

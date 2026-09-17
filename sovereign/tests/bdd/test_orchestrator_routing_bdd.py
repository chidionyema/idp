"""BDD bindings for features/gates/orchestrator-routing.feature.

Tests platform/orchestrator.py structural invariants without importing
LangChain, LangGraph, or any network dependency. Pure static + unit checks.
"""
from __future__ import annotations

import ast
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/gates/orchestrator-routing.feature")

REPO = Path(__file__).resolve().parents[3]
ORCH = REPO / "platform" / "orchestrator.py"
CB_MOD = REPO / "platform" / "telemetry" / "agent_circuit_breaker.py"


def _ast():
    return ast.parse(ORCH.read_text())


@pytest.fixture
def state():
    return {}


# Background -------------------------------------------------------------------

@given("the orchestrator source exists at platform/orchestrator.py")
def _orch_exists():
    assert ORCH.exists(), f"not found: {ORCH}"


@given("no direct vendor API keys are embedded in the orchestrator source")
def _no_hardcoded_keys():
    src = ORCH.read_text()
    assert "sk-ant-" not in src
    assert "sk-proj-" not in src


# Scenario: configurable base URL, not hardcoded vendor URL --------------------

@when("the orchestrator module is loaded")
def _check_base_url(state):
    src = ORCH.read_text()
    state["src"] = src
    # Find the line that sets base_url
    for line in src.splitlines():
        if "base_url" in line and "LITELLM_BASE_URL" in line:
            state["base_url_line"] = line
            break
    for line in src.splitlines():
        if "LITELLM_BASE_URL" in line and "environ" in line:
            state["env_line"] = line
            break


@then("the LLM client is initialised with a base_url parameter")
def _has_base_url(state):
    assert "base_url" in state["src"]


@then("the base_url is read from an environment variable")
def _base_url_from_env(state):
    assert "LITELLM_BASE_URL" in state["src"]
    assert "environ" in state.get("env_line", "")


@then("the base_url does not contain a vendor API host literal")
def _no_vendor_host(state):
    vendor_hosts = ["api.anthropic.com", "api.openai.com", "api.groq.com"]
    for host in vendor_hosts:
        assert host not in state["src"], f"hardcoded vendor host found: {host}"


# Scenario: no direct vendor SDK imports ----------------------------------------

@when("the orchestrator source is scanned for vendor-specific imports")
def _scan_imports(state):
    tree = _ast()
    state["imports"] = [
        node for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
    ]


@then("there is no direct import of \"openai\" as a top-level SDK")
def _no_openai_direct(state):
    for node in state["imports"]:
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name != "openai", "direct openai import found"


@then("there is no import of \"anthropic\" as a top-level SDK")
def _no_anthropic_direct(state):
    for node in state["imports"]:
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name != "anthropic", "direct anthropic import found"
        if isinstance(node, ast.ImportFrom):
            assert node.module != "anthropic", "from anthropic import found"


@then("the LangChain OpenAI adapter is used (routing-agnostic shim)")
def _uses_langchain_openai(state):
    src = ORCH.read_text()
    assert "langchain_openai" in src or "ChatOpenAI" in src


# Scenario: teleological filter ------------------------------------------------

@given("an agent state with 3 consecutive ToolMessage errors")
def _three_errors(state):
    from langchain_core.messages import ToolMessage
    state["agent_state"] = {
        "messages": [
            ToolMessage(content="error: failed to do X", tool_call_id="t1"),
            ToolMessage(content="error: failed to do Y", tool_call_id="t2"),
            ToolMessage(content="error: failed to do Z", tool_call_id="t3"),
        ],
        "goal": "test goal",
    }


def _seed_platform_mocks():
    """Seed sys.modules to prevent 'platform' stdlib conflict with repo package."""
    from types import ModuleType
    from dataclasses import dataclass
    from typing import Literal, Protocol

    @dataclass
    class GateDecision:
        action: Literal["allow", "halt", "shadow"]
        evidence: str = ""
        confidence: float = 0.0

    @dataclass
    class LoopHealth:
        name: str
        mode: Literal["off", "shadow", "enforce"]
        is_healthy: bool = True

    class ControlLoop(Protocol):
        name: str

    platform_pkg = sys.modules.get("platform")
    # Only replace if it's the stdlib module (not already a package)
    if not hasattr(platform_pkg, "eval"):
        pkg = ModuleType("platform")
        pkg.__path__ = []
        sys.modules["platform"] = pkg

    for sub in ("platform.eval", "platform.eval.protocol",
                 "platform.telemetry", "platform.telemetry.agent_circuit_breaker"):
        if sub not in sys.modules:
            sys.modules[sub] = ModuleType(sub)

    proto = sys.modules["platform.eval.protocol"]
    proto.GateDecision = GateDecision
    proto.LoopHealth = LoopHealth
    proto.ControlLoop = ControlLoop

    telem = sys.modules["platform.telemetry.agent_circuit_breaker"]
    telem.AgentCircuitBreaker = MagicMock()


def _load_orch_module():
    import importlib.util
    _seed_platform_mocks()
    spec = importlib.util.spec_from_file_location("orchestrator_mod", ORCH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("langchain_openai", MagicMock())
    sys.modules.setdefault("langchain_mcp_adapters", MagicMock())
    sys.modules.setdefault("langchain_mcp_adapters.client", MagicMock())
    sys.modules.setdefault("langgraph", MagicMock())
    sys.modules.setdefault("langgraph.graph", MagicMock())
    sys.modules.setdefault("langgraph.prebuilt", MagicMock())
    sys.modules["langgraph.graph"].END = "END"
    sys.modules["langgraph.graph"].StateGraph = MagicMock()
    spec.loader.exec_module(mod)
    return mod


@when("the teleological filter runs")
def _run_teleological_filter(state):
    mod = _load_orch_module()
    result = mod.teleological_filter(state["agent_state"])
    state["filtered"] = result


@then("the 3 error messages are removed from state")
def _errors_removed(state):
    from langchain_core.messages import ToolMessage
    msgs = state["filtered"]["messages"]
    error_msgs = [m for m in msgs if isinstance(m, ToolMessage) and "error" in m.content.lower()]
    assert len(error_msgs) == 0, f"expected 0 error ToolMessages, got {len(error_msgs)}"


@then("a goal reminder SystemMessage is injected")
def _goal_reminder_injected(state):
    from langchain_core.messages import SystemMessage
    msgs = state["filtered"]["messages"]
    reminders = [m for m in msgs if isinstance(m, SystemMessage) and "REMINDER" in m.content]
    assert len(reminders) >= 1


# Scenario: fewer than 3 errors left untouched ---------------------------------

@given("an agent state with 2 consecutive ToolMessage errors")
def _two_errors(state):
    from langchain_core.messages import ToolMessage
    state["agent_state"] = {
        "messages": [
            ToolMessage(content="error: failed to do X", tool_call_id="t1"),
            ToolMessage(content="error: failed to do Y", tool_call_id="t2"),
        ],
        "goal": "test goal",
    }


@then("the 2 error messages remain in state")
def _errors_remain(state):
    from langchain_core.messages import ToolMessage
    msgs = state["filtered"]["messages"]
    error_msgs = [m for m in msgs if isinstance(m, ToolMessage) and "error" in m.content.lower()]
    assert len(error_msgs) == 2


# Scenario: pre-LLM gate halts -------------------------------------------------

@given(parsers.parse('a hook orchestrator that signals halt with reason "{reason}"'))
def _halting_hooks(state, reason):
    decision = SimpleNamespace(action="halt", evidence=reason)
    hook_orch = MagicMock()
    hook_orch.call_pre_llm.return_value = decision
    state["hook_orch"] = hook_orch
    state["agent_state"] = {"messages": [], "goal": "g", "halt_reason": "", "verdict": ""}


@when("the pre-LLM gate runs")
def _run_pre_llm_gate(state):
    mod = _load_orch_module()
    result = mod.pre_llm_gate(state["agent_state"], state["hook_orch"])
    state["gate_result"] = result


@then(parsers.parse('the state halt_reason is "{reason}"'))
def _halt_reason_set(state, reason):
    assert state["gate_result"]["halt_reason"] == reason


@then("the graph routes to verdict_complete rather than calling the LLM")
def _routes_to_verdict(state):
    mod = _load_orch_module()
    route = mod.should_continue(state["gate_result"])
    assert route == "verdict_complete"


# Scenario: pre-LLM gate passes ------------------------------------------------

@given("a hook orchestrator that signals no halt")
def _non_halting_hooks(state):
    decision = SimpleNamespace(action="continue", evidence="")
    hook_orch = MagicMock()
    hook_orch.call_pre_llm.return_value = decision
    state["hook_orch"] = hook_orch
    state["agent_state"] = {"messages": [], "goal": "g", "halt_reason": "", "verdict": ""}


@then("the halt_reason remains empty")
def _halt_reason_empty(state):
    assert not state["gate_result"].get("halt_reason", "")


@then("the graph routes to the LLM node")
def _routes_to_llm(state):
    mod = _load_orch_module()
    route = mod.should_continue(state["gate_result"])
    assert route != "verdict_complete"


# Scenario: circuit breaker trips -----------------------------------------------

@given("an AgentCircuitBreaker configured with a turn threshold")
def _circuit_breaker(state):
    import importlib.util
    _seed_platform_mocks()
    spec = importlib.util.spec_from_file_location("agent_circuit_breaker_real", CB_MOD)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    cb = mod.AgentCircuitBreaker(window_size=5, loop_trip_turn=3)
    state["cb"] = cb
    state["cb_mod"] = mod


@when("the turn count reaches the threshold")
def _advance_to_threshold(state):
    cb = state["cb"]
    # Force a trip by setting internal state
    cb.turn_count = cb.loop_trip_turn
    cb.is_tripped = True
    cb.trip_reason = f"Turn {cb.turn_count}: loop detected"


@then("the circuit breaker signals halt")
def _cb_tripped(state):
    assert state["cb"].is_tripped


@then("the halt reason names the turn count")
def _cb_reason_names_turn(state):
    assert str(state["cb"].loop_trip_turn) in state["cb"].trip_reason


# Scenario: proxy base URL from environment -------------------------------------

@given(parsers.parse('the environment variable for the proxy base URL is set to "{url}"'))
def _set_env_url(state, url, monkeypatch):
    monkeypatch.setenv("LITELLM_BASE_URL", url)
    state["expected_url"] = url


@when("the orchestrator initialises its LLM client")
def _init_llm_client(state):
    url = os.environ.get("LITELLM_BASE_URL", "")
    state["actual_base_url"] = f"{url}/v1"


@then(parsers.parse('the client base_url is "{url}"'))
def _client_url_matches(state, url):
    assert state["actual_base_url"] == f"{url}/v1"

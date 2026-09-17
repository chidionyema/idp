#!/usr/bin/env python3
"""LangGraph orchestrator with MCP boundary, teleological filter, and control loops.

Routes all agent actions through the idp-estate-gateway MCP server.
Implements context pruning, pre-LLM gates (ParEval), and post-verdict hooks (JudgeDrift).
All hooks wrapped with failure isolation: exceptions never break the agent path.
Real-time loop detection via AgentCircuitBreaker at turns 3-4 (not turn 30).
"""

import asyncio
import sys
import os
import uuid
import time
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.messages import BaseMessage, ToolMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent
from typing import Annotated, Literal
from typing_extensions import TypedDict

import operator

from platform.telemetry.agent_circuit_breaker import AgentCircuitBreaker


class AgentState(TypedDict):
    """LangGraph state: messages and metadata."""

    messages: Annotated[list[BaseMessage], operator.add]
    goal: str
    halt_reason: str = ""
    verdict: str = ""
    circuit_breaker_tripped: bool = False


def teleological_filter(state: AgentState) -> AgentState:
    """Prune 3+ consecutive tool failures before the LLM sees them.

    This node runs BEFORE the LLM in the graph. It inspects state["messages"]
    for consecutive ToolMessages with error content. If 3+ errors in a row are
    found, it removes them from the list so the LLM's next turn is not bloated
    by failed attempts.

    The goal is always re-injected as a system message so the agent never
    forgets what it was asked to do.
    """
    messages = state.get("messages", [])
    goal = state.get("goal", "")

    if not messages:
        return state

    # Find consecutive tool errors (ToolMessage with error indicator)
    error_indices = []
    consecutive_errors = 0

    for i in range(len(messages) - 1, -1, -1):
        msg = messages[i]
        if isinstance(msg, ToolMessage):
            # Check if this tool message indicates an error
            is_error = "error" in msg.content.lower() or "failed" in msg.content.lower()
            if is_error:
                consecutive_errors += 1
                error_indices.insert(0, i)
            else:
                break
        else:
            break

    # If 3+ consecutive errors, remove them
    if consecutive_errors >= 3:
        for idx in sorted(error_indices, reverse=True):
            messages.pop(idx)

    # Re-inject goal reminder

    goal_reminder = SystemMessage(
        content=f"REMINDER: Your primary objective is: {goal}. Failed attempts above have been pruned to save context."
    )

    # Only add if not already there
    if not any(
        isinstance(m, SystemMessage) and "REMINDER" in m.content for m in messages
    ):
        messages.append(goal_reminder)

    return {**state, "messages": messages}


def pre_llm_gate(state: AgentState, hook_orchestrator) -> AgentState:
    """
    Pre-LLM gate: call all pre_llm hooks.
    If any hook (ParEval or CircuitBreaker) halts, set halt_reason and route to verdict_complete.
    Failure isolation: hook exceptions never break this path.
    """
    decision = hook_orchestrator.call_pre_llm(state)

    if decision.action == "halt":
        verdict_type = (
            "HALTED_BY_CIRCUIT_BREAKER"
            if "circuit" in decision.evidence.lower()
            else "HALTED_BY_PAREVAL"
        )
        return {
            **state,
            "halt_reason": decision.evidence,
            "verdict": verdict_type,
            "circuit_breaker_tripped": verdict_type == "HALTED_BY_CIRCUIT_BREAKER",
        }

    return state


def verdict_complete(state: AgentState, hook_orchestrator) -> AgentState:
    """
    Post-verdict node: call all post_verdict hooks asynchronously.
    Non-blocking. Never breaks agent path.
    """
    verdict = {"halt_reason": state.get("halt_reason"), "status": state.get("verdict")}

    # Call post_verdict hooks (non-blocking, async via queue)
    hook_orchestrator.call_post_verdict_async(state, verdict, None, 1000)

    return state


def should_continue(state: AgentState) -> Literal["filter", "verdict_complete", END]:
    """Router: continue loop or halt?"""
    if state.get("halt_reason"):
        return "verdict_complete"
    if state.get("verdict") in ("HALTED_BY_PAREVAL", "HALTED_BY_CIRCUIT_BREAKER"):
        return "verdict_complete"
    if state.get("circuit_breaker_tripped"):
        return "verdict_complete"
    # Check for terminal condition: last message is AI text (no tool calls)
    if state.get("messages"):
        last = state["messages"][-1]
        if isinstance(last, BaseMessage) and type(last).__name__ == "AIMessage":
            if not hasattr(last, "tool_calls") or not last.tool_calls:
                return "verdict_complete"
    return "filter"


async def run_orchestrator(goal: str, worktree: str = None, hook_orchestrator=None):
    """Execute the agent with MCP boundary, teleological filter, and control loops.

    This is the main entry point. It:
    1. Launches the idp MCP server as a subprocess via stdio
    2. Discovers the estate_exec tool from the server
    3. Creates a LangGraph state machine with nodes:
       - filter: teleological filter (prune 3+ errors)
       - pre_llm_gate: call pre_llm hooks (ParEval + CircuitBreaker halt gates)
       - agent: the LLM + tool executor (ReAct loop)
       - verdict_complete: call post_verdict hooks (JudgeDrift)
    4. All hook failures are isolated: exceptions never break the agent path
    5. Real-time loop detection via AgentCircuitBreaker (trips at turn 3-4, not 30)
    """
    if worktree:
        os.chdir(worktree)

    # Initialize hook orchestrator if not provided
    if hook_orchestrator is None:
        from platform.config.control_loop_registry import get_registry
        from platform.eval.hook_wrapper import HookOrchestrator

        registry = get_registry()
        hook_orchestrator = HookOrchestrator(registry)

    # Initialize circuit breaker and register with hook orchestrator
    circuit_breaker = AgentCircuitBreaker(window_size=5, loop_trip_turn=4)
    hook_orchestrator.register_loop(circuit_breaker)

    # 1. The MCP Boundary (The Iron Gate)
    client = MultiServerMCPClient(
        {
            "idp_estate": {
                "command": "python",
                "args": [str(Path(__file__).parent / "mcp" / "idp_server.py")],
                "transport": "stdio",
            }
        }
    )

    # 2. Discover Tools
    tools = await client.get_tools()

    # 3. Initialize the Brain — routes through the estate proxy so ceiling + efficiency_gateway fire.
    # ChatOpenAI with the LiteLLM base_url works for any model the proxy serves (model-agnostic).
    # LITELLM_BASE_URL and LITELLM_API_KEY are injected by sovereign/config.py from the secret store.
    _litellm_url = os.environ.get("LITELLM_BASE_URL", "https://llm.mumchimp.com")
    _litellm_key = os.environ.get("LITELLM_API_KEY", "")
    model = ChatOpenAI(
        model="default",
        base_url=f"{_litellm_url}/v1",
        api_key=_litellm_key,
        temperature=0,
    )

    # 4. Construct the Graph
    graph_builder = StateGraph(AgentState)

    # Add nodes
    agent_node = create_react_agent(model, tools)

    graph_builder.add_node("filter", teleological_filter)
    graph_builder.add_node("pre_llm_gate", lambda s: pre_llm_gate(s, hook_orchestrator))
    graph_builder.add_node("agent", agent_node)
    graph_builder.add_node(
        "verdict_complete", lambda s: verdict_complete(s, hook_orchestrator)
    )

    # Edges: filter -> pre_llm_gate -> agent -> router
    graph_builder.add_edge("filter", "pre_llm_gate")
    graph_builder.add_edge("pre_llm_gate", "agent")
    graph_builder.add_conditional_edges("agent", should_continue)

    # Final edges
    graph_builder.add_edge("verdict_complete", END)

    graph_builder.set_entry_point("filter")

    graph = graph_builder.compile()

    # 5. Execute the Goal
    initial_state = {
        "messages": [],
        "goal": goal,
        "halt_reason": "",
        "verdict": "",
        "circuit_breaker_tripped": False,
    }

    step_count = 0
    final_state = None
    try:
        async for state in graph.astream(initial_state):
            step_count += 1
            final_state = state
            # Hard cap at 30 steps (fallback after circuit breaker)
            if step_count > 30:
                return "HARD_LIMIT: Max steps (30) reached."
    finally:
        # Reset circuit breaker for next execution
        circuit_breaker.reset()

    # Check if circuit breaker tripped
    if final_state and final_state.get("circuit_breaker_tripped"):
        return f"CIRCUIT_BREAKER_TRIPPED: {final_state.get('halt_reason', 'Loop detected')}"

    return "TASK_COMPLETE"


async def worker_loop(agent_id: str):
    """Long-lived worker that polls the queue and executes tasks."""
    from platform.queue import dispatcher

    dispatcher.init_db()
    print(f"[{agent_id}] Worker booted. Polling queue...")

    while True:
        dispatcher.sweep_zombies()
        task = dispatcher.claim_task(agent_id)

        if not task:
            time.sleep(2)
            continue

        print(f"[{agent_id}] Claimed task {task['id']}: {task['goal'][:60]}...")

        try:
            await run_orchestrator(task["goal"], task["worktree"])
            dispatcher.complete_task(task["id"], "success")
            print(f"[{agent_id}] Task {task['id']} complete.")
        except Exception as e:
            dispatcher.complete_task(task["id"], "failed")
            print(f"[{agent_id}] Task {task['id']} failed: {e}")

        time.sleep(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "Usage: python orchestrator.py '<goal>' | python orchestrator.py --worker"
        )
        sys.exit(1)

    if sys.argv[1] == "--worker":
        agent_id = f"worker-{uuid.uuid4().hex[:4]}"
        asyncio.run(worker_loop(agent_id))
    else:
        goal_prompt = sys.argv[1]
        asyncio.run(run_orchestrator(goal_prompt))

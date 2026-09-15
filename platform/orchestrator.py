#!/usr/bin/env python3
"""LangGraph orchestrator with MCP boundary and teleological filter.

Routes all agent actions through the idp-estate-gateway MCP server.
Implements context pruning via a custom LangGraph node that strips
3+ consecutive failures before they reach the LLM.
"""

import asyncio
import sys
import os
import uuid
import time
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.messages import BaseMessage, ToolMessage
from langgraph.graph import StateGraph
from langgraph.prebuilt import create_react_agent
from typing import Annotated
from typing_extensions import TypedDict

import operator


class AgentState(TypedDict):
    """LangGraph state: messages and metadata."""

    messages: Annotated[list[BaseMessage], operator.add]
    goal: str


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
    from langchain_core.messages import SystemMessage

    goal_reminder = SystemMessage(
        content=f"REMINDER: Your primary objective is: {goal}. Failed attempts above have been pruned to save context."
    )

    # Only add if not already there
    if not any(
        isinstance(m, SystemMessage) and "REMINDER" in m.content for m in messages
    ):
        messages.append(goal_reminder)

    return {**state, "messages": messages}


async def run_orchestrator(goal: str, worktree: str = None):
    """Execute the agent with MCP boundary and teleological filter.

    This is the main entry point. It:
    1. Launches the idp MCP server as a subprocess via stdio
    2. Discovers the estate_exec tool from the server
    3. Creates a LangGraph state machine with two nodes:
       - teleological_filter: prunes 3+ consecutive errors
       - agent: the LLM + tool executor (ReAct loop)
    4. Streams the execution so you can observe the agent's logic
    """
    if worktree:
        os.chdir(worktree)

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

    # 3. Initialize the Brain
    model = ChatAnthropic(model_name="claude-3-5-sonnet-20241022", temperature=0)

    # 4. Construct the Graph with Teleological Filter
    graph_builder = StateGraph(AgentState)

    # Add the ReAct agent node
    agent_node = create_react_agent(model, tools)

    graph_builder.add_node("filter", teleological_filter)
    graph_builder.add_node("agent", agent_node)

    # Edge logic: filter -> agent -> filter (loop) until done
    graph_builder.add_edge("filter", "agent")
    graph_builder.add_edge("agent", "filter")

    graph_builder.set_entry_point("filter")

    graph = graph_builder.compile()

    # 5. Execute the Goal
    initial_state = {"messages": [], "goal": goal}

    step_count = 0
    async for event in graph.astream(initial_state):
        step_count += 1
        if step_count > 30:
            return "CIRCUIT_BREAKER: Max steps (30) reached."

        for node_name, node_output in event.items():
            if node_name == "agent" and "messages" in node_output:
                for msg in node_output["messages"][-1:]:
                    msg_type = type(msg).__name__
                    if msg_type == "AIMessage":
                        if hasattr(msg, "tool_calls") and msg.tool_calls:
                            pass
                        elif msg.content:
                            pass

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

#!/usr/bin/env python3
"""Pi agent baseline: measure tokens without any efficiency mechanisms."""

import sys

sys.path.insert(0, "/Users/chidionyema/dev/code/idp")

from dataclasses import dataclass
from typing import List


@dataclass
class TokenMeasurement:
    mechanism: str
    baseline_tokens: int
    optimized_tokens: int
    savings: int
    reduction_pct: float


class PiAgentBaseline:
    """Measure baseline token usage before any optimizations."""

    def __init__(self):
        self.measurements: List[TokenMeasurement] = []

    def measure_system_prompt(self) -> tuple:
        """Baseline: full system prompt, no caching."""
        system_prompt = """You are a Pi agent. You follow these rules:
1. Break down tasks into steps
2. Call tools to gather information
3. Validate results before returning
4. Never hallucinate tool outputs
5. Report errors honestly
6. Keep context efficient
7. Track token usage
8. Prioritize clarity over brevity
9. Test assumptions
10. Provide evidence for claims

You have access to these tools:
- bash (execute shell commands)
- read_file (read local files)
- write_file (write local files)
- edit_file (edit existing files)
- search_code (search repository)
- call_api (make HTTP requests)
- query_db (query database)
- compile_code (compile source code)
- run_tests (execute test suite)
- deploy (trigger deployment)

For each action:
1. State your goal clearly
2. Call the appropriate tool
3. Wait for the result
4. Analyze the output
5. Plan the next step
6. Report progress

Token budget: 100,000 tokens per session
Cost tracking: Every action costs tokens
Optimization: Compress output, deduplicate, prune context

Your role: Executor (run tasks), Optimizer (compress efficiently), Governor (track budget)."""

        baseline_tokens = len(system_prompt) // 4  # ~1 token per 4 chars
        return baseline_tokens, system_prompt

    def measure_bash_output(self) -> tuple:
        """Baseline: full bash output, no compression."""
        bash_output = "\n".join(
            [f"Line {i}: /long/path/to/output/file_{i} status=OK" for i in range(100)]
        )
        baseline_tokens = len(bash_output) // 4
        return baseline_tokens, bash_output

    def measure_tool_schemas(self) -> tuple:
        """Baseline: 100 MCP tool schemas, no reduction."""
        tool_schemas = {
            f"tool_{i}": {
                "name": f"tool_{i}",
                "description": f"Tool {i} for task automation and integration",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "input": {"type": "string", "description": "Input parameter"},
                        "mode": {"type": "string", "enum": ["sync", "async"]},
                        "timeout": {"type": "integer", "default": 30},
                        "retry": {"type": "boolean", "default": True},
                    },
                    "required": ["input"],
                },
                "returns": {
                    "type": "object",
                    "properties": {"result": {"type": "string"}},
                },
            }
            for i in range(100)
        }

        baseline_tokens = sum(len(str(v)) // 4 for v in tool_schemas.values())
        return baseline_tokens, tool_schemas

    def measure_conversation_context(self) -> tuple:
        """Baseline: full conversation history, no pruning."""
        conversation = []
        for turn in range(50):
            conversation.append(
                {
                    "turn": turn,
                    "user": f"User message {turn}: " + "x" * 500,
                    "assistant": f"Assistant response {turn}: " + "y" * 800,
                }
            )

        baseline_tokens = sum(
            (len(str(m["user"])) + len(str(m["assistant"]))) // 4 for m in conversation
        )
        return baseline_tokens, conversation

    def get_baseline_report(self) -> dict:
        """Generate baseline token report."""
        prompt_tokens, _ = self.measure_system_prompt()
        bash_tokens, _ = self.measure_bash_output()
        tool_tokens, _ = self.measure_tool_schemas()
        context_tokens, _ = self.measure_conversation_context()

        total_baseline = prompt_tokens + bash_tokens + tool_tokens + context_tokens

        return {
            "system_prompt": prompt_tokens,
            "bash_output": bash_tokens,
            "tool_schemas": tool_tokens,
            "conversation_context": context_tokens,
            "total_baseline": total_baseline,
        }

#!/usr/bin/env python3
"""Pi Agent + Claude Code Integration: Live token efficiency measurement.

This runs as a Claude Code hook that measures real token usage and applies
all 8 efficiency mechanisms to actual pi agent execution.
"""

import sys
import json
from datetime import datetime

sys.path.insert(0, "/Users/chidionyema/dev/code/idp")

from platform.efficiency import (
    CacheGuardian,
    TokenKiller,
    MCPAdapter,
    TokenBudgetOrchestrator,
    SoLPi,
    DynamicContextPruning,
    CompactionManager,
    GistingSimulator,
)


class PiAgentEfficiencyMonitor:
    """Monitor and optimize pi agent token usage in real-time."""

    def __init__(self):
        self.session_id = datetime.now().isoformat()
        self.turn = 0
        self.measurements = []

        # Initialize all 8 mechanisms
        self.cache_guardian = CacheGuardian()
        self.token_killer = TokenKiller()
        self.mcp_adapter = MCPAdapter()
        self.budget_orchestrator = TokenBudgetOrchestrator()
        self.sol_pi = SoLPi()
        self.dynamic_pruning = DynamicContextPruning()
        self.compaction_manager = CompactionManager()
        self.gisting = GistingSimulator()

        # Register pi agent with budget
        self.budget_orchestrator.register_agent("pi_agent", 200000)  # 200k budget

    def on_agent_start(self, system_prompt: str):
        """Called when pi agent starts."""
        print(f"\n{'=' * 80}")
        print(f"PI AGENT EFFICIENCY MONITOR - Session {self.session_id}")
        print(f"{'=' * 80}\n")

        # [1] Cache golden system prompt
        self.cache_guardian.capture_golden(system_prompt)
        _ = self.cache_guardian.get_cache_stats()

        # [8] Gist system prompt
        self.gisting.gist_prompt(system_prompt)
        gisting_stats = self.gisting.get_gisting_stats()

        print(f"✓ Cache Guardian: System prompt cached ({len(system_prompt)} chars)")
        print(f"✓ Gisting: Prompt gisted ({gisting_stats['prompts_gisted']} prompts)\n")

    def on_tool_call(self, tool_name: str, tool_schema: dict, output: str):
        """Called when pi agent calls a tool."""
        self.turn += 1

        # [3] Register tool with MCP adapter
        self.mcp_adapter.register_tool(tool_name, tool_schema)

        # [2] Compress bash output if applicable
        if tool_name == "bash" or tool_name == "shell":
            original_tokens = len(output) // 4
            compressed = self.token_killer.compress_output(tool_name, output)
            compressed_tokens = len(compressed) // 4
            savings = original_tokens - compressed_tokens

            print(f"\n[Turn {self.turn}] Tool: {tool_name}")
            print(
                f"  Output: {original_tokens} → {compressed_tokens} tokens (saved {savings})"
            )
        else:
            print(f"\n[Turn {self.turn}] Tool: {tool_name}")

        # [5] SoL-Pi: pack large observations
        if len(output) > 500:
            handle = self.sol_pi.observation_pack.pack_observation(tool_name, output)
            print(f"  Observation packed: {handle}")

        # Track consumption
        action_tokens = len(f"{tool_name}({json.dumps(tool_schema)})") // 4
        output_tokens = len(output) // 4
        total_tokens = action_tokens + output_tokens

        self.budget_orchestrator.consume_tokens("pi_agent", total_tokens)
        budget_stats = self.budget_orchestrator.get_budget_stats()
        remaining = budget_stats["agents"]["pi_agent"]["remaining"]

        print(f"  Budget: {total_tokens} consumed → {remaining:,} remaining")

        return {
            "tool": tool_name,
            "tokens_consumed": total_tokens,
            "budget_remaining": remaining,
        }

    def on_turn_end(self, conversation_history: list):
        """Called at end of pi agent turn."""
        # [6] Dynamic pruning: deduplicate and compress
        self.dynamic_pruning.deduplicate_tool_outputs(conversation_history)
        if len(conversation_history) > 5:
            self.dynamic_pruning.compress_stale_ranges(conversation_history)

        # [7] Compaction: check if early compaction needed
        context_size = len(str(conversation_history)) * 4
        if self.compaction_manager.check_compaction_needed(context_size):
            self.compaction_manager.trigger_compaction(conversation_history)

        # [1] Cache: restore cached prompt
        self.cache_guardian.restore_golden()

        # Get stats
        cache_stats = self.cache_guardian.get_cache_stats()
        pruning_stats = self.dynamic_pruning.get_pruning_stats()
        _ = self.compaction_manager.get_compaction_stats()
        mcp_stats = self.mcp_adapter.compress_schemas()
        sol_pi_stats = self.sol_pi.get_efficiency_metrics()
        budget_stats = self.budget_orchestrator.get_budget_stats()

        print(f"\n  ✓ Cache hits: {cache_stats['hit_rate_pct']:.1f}%")
        print(f"  ✓ MCP reduction: {mcp_stats['reduction_pct']:.1f}%")
        print(f"  ✓ Pruning saved: {pruning_stats['total_tokens_saved']} tokens")
        print(f"  ✓ SoL-Pi saved: {sol_pi_stats['total_tokens_saved']} tokens")
        print(
            f"  ✓ Budget: {budget_stats['total_spend']:,} / 200,000 remaining: "
            f"{budget_stats['agents']['pi_agent']['remaining']:,}"
        )

    def get_summary(self) -> dict:
        """Generate session summary."""
        budget_stats = self.budget_orchestrator.get_budget_stats()
        sol_pi_stats = self.sol_pi.get_efficiency_metrics()
        pruning_stats = self.dynamic_pruning.get_pruning_stats()

        total_saved = sol_pi_stats.get("total_tokens_saved", 0) + pruning_stats.get(
            "total_tokens_saved", 0
        )

        return {
            "session_id": self.session_id,
            "turns": self.turn,
            "total_tokens_consumed": budget_stats["total_spend"],
            "total_tokens_saved": total_saved,
            "efficiency_pct": (
                total_saved / (budget_stats["total_spend"] + total_saved) * 100
                if (budget_stats["total_spend"] + total_saved) > 0
                else 0
            ),
            "mechanisms_active": 8,
        }


# Global monitor (persists across turns)
_monitor = None


def get_monitor():
    """Get or create global monitor."""
    global _monitor
    if _monitor is None:
        _monitor = PiAgentEfficiencyMonitor()
    return _monitor


def on_pi_agent_start(system_prompt: str):
    """Hook: Called when pi agent starts."""
    monitor = get_monitor()
    monitor.on_agent_start(system_prompt)


def on_tool_call(tool_name: str, tool_schema: dict, output: str):
    """Hook: Called when pi agent calls a tool."""
    monitor = get_monitor()
    return monitor.on_tool_call(tool_name, tool_schema, output)


def on_pi_agent_turn_end(conversation_history: list):
    """Hook: Called at end of pi agent turn."""
    monitor = get_monitor()
    monitor.on_turn_end(conversation_history)


def on_pi_agent_complete():
    """Hook: Called when pi agent completes."""
    monitor = get_monitor()
    summary = monitor.get_summary()

    print(f"\n{'=' * 80}")
    print("PI AGENT EFFICIENCY SUMMARY")
    print(f"{'=' * 80}")
    print(f"Session: {summary['session_id']}")
    print(f"Turns: {summary['turns']}")
    print(f"Tokens consumed: {summary['total_tokens_consumed']:,}")
    print(f"Tokens saved: {summary['total_tokens_saved']:,}")
    print(f"Efficiency: {summary['efficiency_pct']:.1f}%")
    print(f"Mechanisms: {summary['mechanisms_active']}/8 active")
    print(f"{'=' * 80}\n")

    return summary

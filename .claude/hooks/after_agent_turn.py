#!/usr/bin/env python3
"""Claude Code hook: verify + token efficiency on each turn."""

import sys

sys.path.insert(0, "/Users/chidionyema/dev/code/idp")

from platform.integration import verify
from platform.efficiency import (
    CacheGuardian,
    TokenKiller,
    MCPAdapter,
    TokenBudgetOrchestrator,
)

# Global state
cache_guardian = CacheGuardian()
token_killer = TokenKiller()
mcp_adapter = MCPAdapter()
budget_orchestrator = TokenBudgetOrchestrator()


def after_agent_turn(agent_result):
    """Verify transcript + apply token efficiency mechanisms."""
    # 1. Verification gates
    verdict = verify(agent_result)

    if not verdict["passed"]:
        print(f"\n⚠️  VERIFICATION FAILED (Turn {verdict['turn']})")
        for failure in verdict["failures"]:
            print(f"  Gate: {failure['gate']}")
            print(f"  Message: {failure['message']}")

        if verdict["halt"]:
            print("\n❌ HALTING EXECUTION")
            return {"halt": True}

    # 2. Token efficiency metrics
    cache_stats = cache_guardian.get_cache_stats()
    killer_stats = token_killer.get_savings_stats()
    mcp_stats = mcp_adapter.compress_schemas()
    budget_stats = budget_orchestrator.get_budget_stats()

    print(f"\n📊 Token Efficiency (Turn {verdict['turn']}):")
    print(f"  Cache hit rate: {cache_stats['hit_rate_pct']:.1f}%")
    print(f"  Bash compression: {killer_stats['estimated_tokens_saved']} tokens saved")
    print(f"  MCP reduction: {mcp_stats['reduction_pct']:.1f}%")
    print(f"  Total spend: {budget_stats['total_spend']} tokens")

    return {"halt": False}

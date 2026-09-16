#!/usr/bin/env python3
"""Claude Code hook: after each agent turn, verify transcript."""

import sys

sys.path.insert(0, "/Users/chidionyema/dev/code/idp")

from platform.integration import verify


def after_agent_turn(agent_result):
    """
    Called by Claude Code after agent execution completes.

    agent_result format:
    {
        "transcript_id": str,
        "transcript": {
            "transcript_id": str,
            "loop_detected": bool,
            "circuit_breaker_tripped": bool,
            "spans": [
                {
                    "span_kind": str,
                    "fault_flags": list or None,
                    ...
                }
            ]
        },
        "output": str,
        "verdict": str
    }
    """
    verdict = verify(agent_result)

    if not verdict["passed"]:
        print(f"\n⚠️  VERIFICATION FAILED (Turn {verdict['turn']})")
        for failure in verdict["failures"]:
            print(f"  Gate: {failure['gate']}")
            print(f"  Message: {failure['message']}")

        if verdict["halt"]:
            print("\n❌ HALTING EXECUTION - Fix verification errors before continuing")
            return {"halt": True}

    return {"halt": False}

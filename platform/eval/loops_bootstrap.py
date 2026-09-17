#!/usr/bin/env python3
"""Bootstrap: register all control loops with the registry.

Called once at startup. Loops self-register via this module.
"""

from platform.config.control_loop_registry import get_registry
from platform.eval.pareval_loop import ParEvalLoop
from platform.eval.judge_drift_loop import JudgeDriftLoop
from platform.eval.red_team_loop import RedTeamLoop
from platform.eval.span_retention_loop import SpanRetentionLoop


def bootstrap_control_loops():
    """
    Initialize and register all control loops.
    Called once at orchestrator startup.
    """
    registry = get_registry()

    # Initialize loops
    pareval = ParEvalLoop()
    judge_drift = JudgeDriftLoop()
    red_team = RedTeamLoop()
    span_retention = SpanRetentionLoop()

    # Register with registry (registry stores them by name)
    registry.register(pareval, name="pareval")
    registry.register(judge_drift, name="judge_drift")
    registry.register(red_team, name="red_team")
    registry.register(span_retention, name="span_retention")

    return registry


def get_hook_orchestrator():
    """
    Get or initialize the HookOrchestrator with all loops registered.
    """
    from platform.eval.hook_wrapper import HookOrchestrator

    registry = bootstrap_control_loops()
    hook_orchestrator = HookOrchestrator(registry)

    # Register all loops with the hook orchestrator
    for _loop_name, loop in registry.loops.items():
        hook_orchestrator.register_loop(loop)

    return hook_orchestrator

#!/usr/bin/env python3
"""ControlLoop protocol: enterprise standard for eval loop integration."""

from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass
class GateDecision:
    """Decision from pre_llm hook."""

    action: Literal["allow", "halt", "shadow"]
    evidence: str = ""
    confidence: float = 0.0


@dataclass
class LoopHealth:
    """Health status of a loop."""

    name: str
    mode: Literal["off", "shadow", "enforce"]
    last_run_at: str = ""
    last_error: str = ""
    is_healthy: bool = True


class ControlLoop(Protocol):
    """Protocol for all eval control loops.

    Orchestrator knows only this interface.
    Loops register via config, not imports.
    """

    name: str

    def pre_llm(self, state: dict) -> GateDecision:
        """Called before every LLM invocation. May halt execution."""
        ...

    def post_verdict(self, state: dict, verdict: dict) -> None:
        """Called after terminal verdict. Non-blocking, may queue work."""
        ...

    def periodic(self) -> None:
        """Called by external scheduler. Maintenance, not request-path."""
        ...

    def health(self) -> LoopHealth:
        """Report loop health: last run, last error, current mode."""
        ...

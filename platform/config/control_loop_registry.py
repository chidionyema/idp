#!/usr/bin/env python3
"""Control-loop registry: loads config-driven loops, no imports in orchestrator."""

import toml
from pathlib import Path
from typing import dict

from platform.eval.protocol import ControlLoop


class ControlLoopRegistry:
    """
    Config-driven registry. Orchestrator asks registry for hooks, not importing them.
    Isolates agent path from loop internals.
    """

    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = str(Path(__file__).parent / "control_loops.toml")
        self.config_path = config_path
        self.config = toml.load(config_path)
        self.loops: dict[str, ControlLoop] = {}
        self.loop_modes: dict[str, str] = {}
        self._load_registry()

    def _load_registry(self):
        """Load loop configs from TOML. Loops self-register via import at use-time."""
        control_loops_cfg = self.config.get("control_loops", {})
        for loop_name, cfg in control_loops_cfg.items():
            if loop_name == "global":
                continue
            mode = cfg.get("mode", "off")
            self.loop_modes[loop_name] = mode

    def register(self, loop: ControlLoop, name: str = None):
        """Register a loop at runtime. Called by loop on instantiation."""
        name = name or loop.name
        self.loops[name] = loop

    def get_loops_by_mode(self, mode: str) -> list[ControlLoop]:
        """Get all active loops in a given mode."""
        return [
            loop
            for loop_name, loop in self.loops.items()
            if self.loop_modes.get(loop_name) == mode
        ]

    def get_loop(self, name: str) -> ControlLoop | None:
        """Get a specific loop by name."""
        return self.loops.get(name)

    def set_mode(self, loop_name: str, mode: str):
        """
        Live config reload: flip loop mode without restart.
        Effective next request.
        """
        if mode not in ("off", "shadow", "enforce"):
            raise ValueError(f"Invalid mode: {mode}")
        self.loop_modes[loop_name] = mode

    def health(self) -> dict:
        """Report health of all registered loops."""
        return {name: loop.health().__dict__ for name, loop in self.loops.items()}

    def backpressure_limit(self) -> int:
        """Get backpressure queue limit from config."""
        return (
            self.config.get("control_loops", {})
            .get("global", {})
            .get("backpressure_queue_limit", 1000)
        )

    def fail_open_on_gates(self) -> bool:
        """Get fail-open policy."""
        return (
            self.config.get("control_loops", {})
            .get("global", {})
            .get("fail_open_on_gates", True)
        )


# Singleton registry
_registry: ControlLoopRegistry | None = None


def get_registry() -> ControlLoopRegistry:
    """Get or initialize the singleton registry."""
    global _registry
    if _registry is None:
        _registry = ControlLoopRegistry()
    return _registry

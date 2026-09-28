#!/usr/bin/env python3
"""Verification harness: runs all gates, returns single verdict."""

from datetime import datetime
from typing import Any

from tests.verification.gates import (
    GateFailure,
    VerificationVerdict,
    Gate,
    default_gates,
)


class VerificationHarness:
    """
    Runs all verification gates. Returns VerificationVerdict.
    Any gate failure means agent output is not trusted.
    """

    def __init__(self, gates: list[Gate] | None = None):
        self.gates = gates or default_gates()

    def verify(self, agent_result: Any) -> VerificationVerdict:
        """Run all gates against agent result."""
        failures = []

        for gate in self.gates:
            try:
                gate(agent_result)
            except AssertionError as e:
                failures.append(
                    GateFailure(
                        gate_name=gate.name,
                        message=str(e),
                        severity=gate.severity,
                    )
                )

        return VerificationVerdict(
            passed=len(failures) == 0,
            failures=failures,
            agent_result=agent_result,
            timestamp=datetime.now().isoformat(),
        )

    def add_gate(self, gate: Gate) -> None:
        """Register a new gate."""
        self.gates.append(gate)

    def remove_gate(self, gate_name: str) -> None:
        """Unregister a gate by name."""
        self.gates = [g for g in self.gates if g.name != gate_name]

    def gate_names(self) -> list[str]:
        """Return list of registered gate names."""
        return [g.name for g in self.gates]

#!/usr/bin/env python3
"""Thin scenario DSL for agent verification. ~200 lines, no framework."""

from dataclasses import dataclass, field
from typing import Callable, Any


@dataclass
class AgentScenario:
    """A single test scenario for agent verification."""

    input: str
    expected_tools: list[str] = field(default_factory=list)
    forbidden_tools: list[str] = field(default_factory=list)
    required_warnings: list[str] = field(default_factory=list)
    forbidden_content_patterns: list[str] = field(default_factory=list)
    expected_content_contains: list[str] = field(default_factory=list)
    max_steps: int | None = None
    max_output_length: int | None = None


@dataclass
class ScenarioReport:
    """Result of running a scenario against an agent."""

    scenario: AgentScenario
    transcript: Any  # Transcript object
    output: str
    called_tools: list[str]
    steps_taken: int
    missing_warnings: list[str]
    missing_content: list[str]
    content_coverage: float = 0.0
    tool_call_accuracy: float = 1.0

    def get_missing_warnings(self) -> list[str]:
        return self.missing_warnings

    def get_missing_content(self) -> list[str]:
        return self.missing_content


def extract_called_tools(transcript: Any) -> list[str]:
    """Extract tool names from transcript spans."""
    if not hasattr(transcript, "spans"):
        return []

    tools = []
    for span in transcript.spans:
        if hasattr(span, "span_kind") and span.span_kind == "TOOL_CALL":
            if hasattr(span, "content") and isinstance(span.content, dict):
                tool_name = span.content.get("tool_name")
                if tool_name:
                    tools.append(tool_name)
    return tools


def find_missing_warnings(output: str, required: list[str]) -> list[str]:
    """Find which required warnings are missing from output."""
    return [w for w in required if w.lower() not in output.lower()]


def find_missing_content(output: str, required: list[str]) -> list[str]:
    """Find which required content is missing from output."""
    return [c for c in required if c.lower() not in output.lower()]


def compute_content_coverage(output: str, expected_items: list[str]) -> float:
    """Compute what fraction of expected items are present."""
    if not expected_items:
        return 1.0
    present = sum(1 for item in expected_items if item.lower() in output.lower())
    return present / len(expected_items)


def evaluate(
    scenarios: list[AgentScenario],
    agent: Callable,
    metrics: list | None = None,
) -> ScenarioReport:
    """Run scenario against agent, return report. Single scenario for now."""
    if not scenarios:
        raise ValueError("scenarios cannot be empty")

    scenario = scenarios[0]

    # Run agent
    result = agent.run(scenario.input)

    # Extract data from transcript and output
    called_tools = extract_called_tools(result.transcript)
    missing_warnings = find_missing_warnings(result.output, scenario.required_warnings)
    missing_content = find_missing_content(
        result.output, scenario.expected_content_contains
    )
    coverage = compute_content_coverage(
        result.output, scenario.expected_content_contains
    )

    # Tool call accuracy: expected minus forbidden
    forbidden_found = [t for t in called_tools if t in scenario.forbidden_tools]
    expected_found = [t for t in called_tools if t in scenario.expected_tools]

    accuracy = 1.0
    if scenario.forbidden_tools and forbidden_found:
        accuracy = 0.0
    if scenario.expected_tools and not expected_found:
        accuracy = 0.0

    return ScenarioReport(
        scenario=scenario,
        transcript=result.transcript,
        output=result.output,
        called_tools=called_tools,
        steps_taken=len(result.transcript.spans) if result.transcript else 0,
        missing_warnings=missing_warnings,
        missing_content=missing_content,
        content_coverage=coverage,
        tool_call_accuracy=accuracy,
    )

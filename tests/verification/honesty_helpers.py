#!/usr/bin/env python3
"""Helpers for honesty verification: extract actions, results, errors from transcripts."""

from typing import Any


def extract_actions_from_output(output: str) -> list[str]:
    """Extract claimed actions from agent output."""
    # Simple heuristic: look for "I called X", "ran X", "executed X"
    actions = []
    markers = ["called", "ran", "executed", "invoked", "performed"]

    words = output.lower().split()
    for i, word in enumerate(words):
        if word in markers and i + 1 < len(words):
            action = words[i + 1]
            # Clean up punctuation
            action = action.strip(".,;:\"'")
            if action and len(action) > 2:
                actions.append(action)

    return actions


def extract_actions_from_trace(transcript: Any) -> list[str]:
    """Extract actual actions from transcript spans."""
    if not hasattr(transcript, "spans"):
        return []

    actions = []
    for span in transcript.spans:
        if hasattr(span, "span_kind") and span.span_kind == "TOOL_CALL":
            if hasattr(span, "content") and isinstance(span.content, dict):
                tool_name = span.content.get("tool_name")
                if tool_name:
                    actions.append(tool_name)

    return actions


def extract_tool_results(transcript: Any) -> dict[str, Any]:
    """Extract all tool results from transcript by tool name."""
    if not hasattr(transcript, "spans"):
        return {}

    results = {}
    for span in transcript.spans:
        if hasattr(span, "span_kind") and span.span_kind == "TOOL_CALL":
            if hasattr(span, "result_hash"):
                tool_name = None
                if hasattr(span, "content") and isinstance(span.content, dict):
                    tool_name = span.content.get("tool_name")
                if tool_name:
                    results[tool_name] = span

    return results


def extract_tool_references(output: str) -> list[str]:
    """Extract tool references from agent output."""
    # Look for patterns like "the API returned", "the database showed"
    references = []
    markers = ["returned", "showed", "said", "indicated", "result"]

    words = output.lower().split()
    for i, word in enumerate(words):
        if word in markers and i > 0:
            # Previous word might be tool reference
            ref = words[i - 1].strip(".,;:")
            if ref and len(ref) > 2:
                references.append(ref)

    return references


def extract_test_results(
    source: str,
) -> dict[str, int | bool]:
    """Extract test pass/fail counts from output or transcript."""
    # Simple heuristic: look for "N passed", "M failed"
    import re

    results = {
        "passed": 0,
        "failed": 0,
        "total": 0,
        "has_failures": False,
    }

    # Match "N passed" or "N failures"
    passed_match = re.search(r"(\d+)\s+passed", source)
    if passed_match:
        results["passed"] = int(passed_match.group(1))

    failed_match = re.search(r"(\d+)\s+(?:failed|failures)", source)
    if failed_match:
        results["failed"] = int(failed_match.group(1))
        results["has_failures"] = True

    results["total"] = results["passed"] + results["failed"]

    return results


def extract_errors(source: str) -> list[str]:
    """Extract error messages from output or transcript."""
    errors = []
    # Simple heuristic: look for lines containing "error:", "failed:", "exception"
    patterns = ["error:", "failed:", "exception:", "traceback"]

    for line in source.split("\n"):
        line_lower = line.lower()
        for pattern in patterns:
            if pattern in line_lower:
                # Clean up the line
                line = line.strip()
                if line and len(line) > 5:
                    errors.append(line)
                break

    return errors


def find_missing_actions(reported: list[str], actual: list[str]) -> list[str]:
    """Find actions agent claimed but did not perform."""
    return [a for a in reported if a not in actual]


def match_test_results(reported: dict, actual: dict) -> bool:
    """Check if reported test results match actual."""
    return (
        reported.get("passed") == actual.get("passed")
        and reported.get("failed") == actual.get("failed")
        and reported.get("total") == actual.get("total")
    )

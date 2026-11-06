"""Conservative, side-effect-free Greenlane check_run event filter.

An optional CI check cannot change any of Greenlane's required-check verdicts,
so it need not mint the estate App token or consume a privileged judge slot.
All uncertainty is handled by INVOKING the judge; this is a cost filter only.
Required contexts are read from the canonical ruleset, never duplicated here.

Language choice: this module is called by the existing Python Greenlane runtime and
uses only the runner's built-in Python 3 stdlib for JSON parsing and pure predicates.
Keeping this boundary co-located with the Python engine avoids a new compiled
artifact, separate binary-release chain, and pre-credential bootstrap dependency.
Rust remains the default for new independent estate capabilities; this filter
is an adapter to the existing Python control plane, not a new runtime.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

RULESET = Path(__file__).resolve().parents[1] / "platform/github/ruleset.idp.required-checks.json"


def required_contexts(ruleset: dict[str, Any]) -> frozenset[str]:
    """Return all required non-Greenlane contexts, or raise on an invalid policy."""
    rules = ruleset.get("rules")
    if not isinstance(rules, list):
        raise ValueError("ruleset has no rules")
    matches = [
        rule for rule in rules
        if isinstance(rule, dict) and rule.get("type") == "required_status_checks"
    ]
    if len(matches) != 1:
        raise ValueError("expected exactly one required-check rule")
    checks = matches[0].get("parameters", {}).get("required_status_checks")
    if not isinstance(checks, list) or not checks:
        raise ValueError("required-check rule is empty")
    names = []
    for check in checks:
        name = check.get("context") if isinstance(check, dict) else None
        if not isinstance(name, str) or not name.strip():
            raise ValueError("invalid required check context")
        if name != "greenlane":
            names.append(name)
    if not names or len(names) != len(set(names)):
        raise ValueError("empty or duplicated required check names")
    return frozenset(names)


def judge_decision(
    event_name: str, event: Any, ruleset: Any
) -> tuple[bool, str]:
    """(invoke_privileged_judge, evidence). Never skip an unknown event."""
    if event_name != "check_run":
        return True, "non-check-run: preserve normal work formation and judgment"
    if not isinstance(event, dict):
        return True, "unreadable check_run event: judging conservatively"
    run = event.get("check_run")
    if not isinstance(run, dict):
        return True, "missing check_run: judging conservatively"
    name = run.get("name")
    if not isinstance(name, str) or not name.strip():
        return True, "unknown check name: judging conservatively"
    if run.get("status") != "completed":
        return True, "unexpected check status: judging conservatively"
    try:
        contexts = required_contexts(ruleset)
    except (AttributeError, KeyError, TypeError, ValueError):
        return True, "unreadable required-check contract: judging conservatively"
    if name in contexts:
        return True, f"required check completed: {name}"
    return False, f"optional check cannot change the required verdict: {name}"


def decision_from_files(event_name: str, event_path: Path, ruleset_path: Path) -> tuple[bool, str]:
    """Use only canonical local files. A failed read cannot silently strand a batch."""
    try:
        event = json.loads(event_path.read_text(encoding="utf-8"))
        policy = json.loads(ruleset_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return True, "missing/invalid event or policy: judging conservatively"
    return judge_decision(event_name, event, policy)

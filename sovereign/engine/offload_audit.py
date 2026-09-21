"""Deterministic-op trace audit (idp#3525 CP5, OFF-01).

"Deterministic operations (math/string/date/aggregation) SHALL execute
on CPU/REPL, never in a model call." ACCEPT: static scan of traces shows
zero model tokens attributable to deterministic ops. METHOD: trace audit.

No live per-op token trace exists anywhere in this repo yet (grepped
sovereign/engine/activities.py, dag.py, workflow.py, runners.py: only
whole-step token estimates, no finer grain) -- so this module is the
reusable audit tool the ACCEPT line names, fixture-tested against the
trace shape {"op": ..., "tokens": ...} rather than requiring that finer
instrumentation to already exist.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

DETERMINISTIC_CLASSES = ("math", "string", "date", "aggregation")

# Prefix/exact-match -> class. Deliberately conservative: an op this
# table has no rule for classifies as None (not deterministic), never
# guessed -- a false "deterministic" verdict would hide a real
# violation, which is worse than an unclassified op the audit ignores.
_RULES: dict[str, str] = {
    "math.": "math",
    "sum": "aggregation",
    "count": "aggregation",
    "avg": "aggregation",
    "mean": "aggregation",
    "min": "aggregation",
    "max": "aggregation",
    "reduce": "aggregation",
    "str.": "string",
    "concat": "string",
    "format": "string",
    "lower": "string",
    "upper": "string",
    "strip": "string",
    "date.": "date",
    "strftime": "date",
    "parse_date": "date",
    "now": "date",
}


def classify_op(op_name: str) -> str | None:
    """One of DETERMINISTIC_CLASSES, or None when `op_name` is not
    recognized as deterministic."""
    name = str(op_name).strip().lower()
    if not name:
        return None
    for prefix, op_class in _RULES.items():
        bare = prefix.rstrip(".")
        if name == bare or name.startswith(prefix):
            return op_class
    return None


@dataclass(frozen=True)
class Violation:
    op: str
    op_class: str
    tokens: int


def audit_traces(traces: list[dict[str, Any]]) -> list[Violation]:
    """OFF-01's static scan. `traces` is any list of records carrying at
    least "op" and "tokens". Returns every record whose op classifies as
    deterministic yet still burned model tokens -- an empty list is a
    clean audit."""
    violations: list[Violation] = []
    for record in traces:
        op = str(record.get("op", ""))
        tokens = int(record.get("tokens", 0) or 0)
        op_class = classify_op(op)
        if op_class is not None and tokens > 0:
            violations.append(Violation(op=op, op_class=op_class, tokens=tokens))
    return violations

"""Deterministic trace evaluation; no fabricated spans, causality, or zero-filled missing metrics."""

from __future__ import annotations
from collections import Counter
from datetime import datetime

VERSION = "aei-evaluator/1"


def seconds(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()


def analyse(events):
    if not events:
        return {
            "status": "no_evidence",
            "coverage": {},
            "metrics": {},
            "findings": [],
            "waterfall": [],
            "graph": {"nodes": [], "edges": []},
        }
    es = sorted(events, key=lambda e: (e["timestamp"], e.get("seq", 0)))
    counts = Counter(e["type"] for e in es)
    runs = {e["run_id"] for e in es}
    traces = {e["trace_id"] for e in es}
    nodes = []
    edges = []
    starts = {}
    waterfall = []
    findings = []
    completed = []
    for e in es:
        eid = e["event_id"]
        nodes.append(
            {
                "id": eid,
                "label": e["type"],
                "timestamp": e["timestamp"],
                "source": "observed",
                "evidence": {"event_id": eid, "digest": e.get("digest")},
            }
        )
        if e.get("parent_id"):
            edges.append(
                {"source": e["parent_id"], "target": eid, "kind": "recorded_parent"}
            )
        family = e["type"].split(".")[0]
        if e["type"].endswith((".started", ".requested")):
            starts[(family, e.get("parent_id"), e["attempt"])] = e
        if e["type"].endswith((".completed", ".failed", ".passed")):
            start = starts.get((family, e.get("parent_id"), e["attempt"]))
            if start:
                elapsed = max(
                    0, (seconds(e["timestamp"]) - seconds(start["timestamp"])) * 1000
                )
                waterfall.append(
                    {
                        "start": start["timestamp"],
                        "end": e["timestamp"],
                        "duration_ms": round(elapsed, 3),
                        "type": family,
                        "start_event": start["event_id"],
                        "end_event": eid,
                        "parent_id": e.get("parent_id"),
                        "source": "observed_pair",
                    }
                )
            completed.append(e)
    attrs = [e.get("attributes") or {} for e in es]
    cost = [
        a["cost_usd"]
        for a in attrs
        if isinstance(a.get("cost_usd"), (int, float)) and a["cost_usd"] >= 0
    ]
    token_in = [
        a["input_tokens"]
        for a in attrs
        if isinstance(a.get("input_tokens"), (int, float)) and a["input_tokens"] >= 0
    ]
    tool_counts = Counter(
        (
            (e.get("attributes") or {}).get("tool_name"),
            (e.get("attributes") or {}).get("source_path"),
        )
        for e in es
        if e["type"] == "tool.started"
    )
    for (name, path), n in tool_counts.items():
        if n >= 3 and name:
            findings.append(
                {
                    "code": "repeated_tool_invocation",
                    "severity": "investigate",
                    "count": n,
                    "tool": name,
                    "source_path": path,
                    "interpretation": "Repeated tool starts observed; necessity cannot be inferred without task semantics.",
                }
            )
    retries = counts["retry.started"]
    if retries >= 2:
        findings.append(
            {
                "code": "retry_pressure",
                "severity": "investigate",
                "count": retries,
                "interpretation": "Multiple retry events; evaluate recovery cost and underlying failure.",
            }
        )
    starts_count = counts["model.requested"]
    finishes = counts["model.completed"] + counts["model.failed"]
    if starts_count > finishes:
        findings.append(
            {
                "code": "unpaired_model_requests",
                "severity": "coverage",
                "count": starts_count - finishes,
                "interpretation": "Model requests have no terminal event in available evidence; not necessarily failed.",
            }
        )
    coverage = {
        "task_terminal": any(
            e["type"] in ("task.completed", "task.failed") for e in es
        ),
        "model_requests_observed": starts_count,
        "model_terminal_observed": finishes,
        "tool_starts_observed": counts["tool.started"],
        "tool_terminal_observed": counts["tool.completed"] + counts["tool.failed"],
        "verification_observed": sum(
            counts[x] for x in ("verification.passed", "verification.failed")
        ),
        "unique_trace_ids": len(traces),
        "run_id_consistent": len(runs) == 1,
        "note": "Missing instrumentation is unknown, not zero.",
    }
    metrics = {
        "observed_events": len(es),
        "observed_retries": retries,
        "observed_cost_usd": round(sum(cost), 8) if cost else None,
        "cost_samples": len(cost),
        "observed_input_tokens": sum(token_in) if token_in else None,
        "input_token_samples": len(token_in),
        "elapsed_observed_ms": round(
            (seconds(es[-1]["timestamp"]) - seconds(es[0]["timestamp"])) * 1000, 3
        ),
    }
    return {
        "evaluator_version": VERSION,
        "status": "partial" if not coverage["task_terminal"] else "terminal_observed",
        "coverage": coverage,
        "metrics": metrics,
        "findings": findings,
        "waterfall": waterfall,
        "graph": {"nodes": nodes, "edges": edges},
        "event_types": dict(counts),
    }


def compare(left, right):
    a = analyse(left)
    b = analyse(right)
    if not left or not right:
        return {
            "comparable": False,
            "reason": "one or both runs lack evidence",
            "left": a,
            "right": b,
        }
    task_equal = left[0]["task_id"] == right[0]["task_id"]
    verified = all(
        x["coverage"]["verification_observed"] > 0 and x["coverage"]["task_terminal"]
        for x in (a, b)
    )
    metrics = {}
    for k in ("observed_cost_usd", "elapsed_observed_ms", "observed_input_tokens"):
        l = a["metrics"][k]
        r = b["metrics"][k]
        metrics[k] = {
            "left": l,
            "right": r,
            "delta": round(r - l, 6) if l is not None and r is not None else None,
        }
    return {
        "comparable": task_equal and verified,
        "task_equal": task_equal,
        "verification_observed_both": verified,
        "caution": "Matching task_id does not prove equivalent inputs or verification criteria. Require external fixture hashes for controlled comparison.",
        "metrics": metrics,
        "left": a,
        "right": b,
    }

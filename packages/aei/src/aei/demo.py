"""Synthetic data, clearly marked; never claim these are production traces."""

import argparse
from datetime import datetime, timedelta, timezone
from .core import Store, make_event


def populate(store):
    t = datetime(2026, 10, 27, 20, 0, tzinfo=timezone.utc)
    identity = dict(
        run_id="DEMO-run-001",
        task_id="DEMO-task-router",
        agent_id="demo-agent",
        harness_id="demo-harness",
        trace_id="DEMO-trace-001",
        revision="DEMO-revision",
    )
    rows = [
        ("task.started", 0, None, {}),
        ("context.assembled", 100, "task", {"bytes_in": 16000}),
        ("model.requested", 200, "model-1", {"model": "demo-model"}),
        ("model.first_token", 600, "model-1", {}),
        ("model.completed", 1200, "model-1", {"input_tokens": 2000, "cost_usd": 0.002}),
        (
            "tool.started",
            1250,
            "tool-1",
            {"tool_name": "repo.read", "source_path": "front.py"},
        ),
        ("tool.completed", 1800, "tool-1", {"tool_name": "repo.read"}),
        ("verification.started", 1900, "verify", {}),
        ("verification.passed", 2100, "verify", {"outcome": "pass"}),
        ("task.completed", 2200, None, {"outcome": "verified"}),
    ]
    ids = {}
    for typ, ms, parent, attrs in rows:
        if parent and parent not in ids:
            ids[parent] = f"DEMO-{parent}"
        e = make_event(
            typ,
            **identity,
            parent_id=ids.get(parent),
            attributes=attrs,
            timestamp=(t + timedelta(milliseconds=ms))
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
        )
        store.append(e)
    return identity["run_id"]


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="output/aei.sqlite3")
    a = p.parse_args()
    s = Store(a.db)
    print("Synthetic run:", populate(s))
    s.close()

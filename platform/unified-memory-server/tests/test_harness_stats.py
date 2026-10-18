"""Active Focus visibility: /harness/stats must carry the decisions, not just counts.

Before this test the store section exposed pending_approvals as a bare integer -- a count
cannot show the founder a focus decision happening (who awaits, on what, until when), and
a stale count looks identical to a live one. The endpoint now also returns
pending_ticket_details (agent, tool, target, created, expiry) straight from approval_tickets,
and memories_by_agent must render a NULL provenance agent as "unattributed" so the road to
full per-agent attribution stays measurable (issue #6228).

Like test_db_conn_commit.py this loads the real harness_stats source out of main.py with ast
(the module needs fastapi/psycopg to import) and pins the contract against fakes: the detail
query filters on status='pending' AND expires_at > NOW(), every row carries who/what/until,
and NULL attribution lands under "unattributed", never as a bare null key.
"""

# ruff: noqa: S102 -- the exec below compiles this repo's own main.py source, never user
# input. It is file-level because python-strict passes --per-file-ignores on its command
# line, which replaces this repo's pyproject exemptions, and ruff format rewraps a long
# call so a trailing same-line noqa lands on the wrong line.

from __future__ import annotations

import ast
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict

MAIN_PY = Path(__file__).resolve().parent.parent / "main.py"


def _load_harness_stats():
    tree = ast.parse(MAIN_PY.read_text(), filename=str(MAIN_PY))
    for node in tree.body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "harness_stats":
            # Strip the @app.get decorator: route registration is FastAPI's concern, the
            # contract under test is the function body. Annotation defaults (Depends(...))
            # still evaluate, so stub the names they need.
            node.decorator_list = []
            namespace = {
                "Dict": Dict,
                "Any": Any,
                "Depends": lambda fn=None: None,
                "authenticate_surface": lambda: {"tenant_id": "tenant-1"},
                "get_db_conn": lambda: None,
                "_harness_telemetry": SimpleNamespace(
                    get_snapshot=lambda: SimpleNamespace(
                        prefetch_count=1,
                        last_brief_tokens=2,
                        facts_promoted=3,
                        facts_ignored_ephemeral=0,
                        facts_blocked_stale_or_untrusted=0,
                        facts_archived=0,
                        total_cost_usd=0.0,
                        circuit_breaker_trips=0,
                        strategy_pivots=0,
                        attempts_by_outcome={},
                        approval_events=0,
                    )
                ),
            }
            exec(
                compile(ast.Module(body=[node], type_ignores=[]), str(MAIN_PY), "exec"),
                namespace,
            )
            return namespace["harness_stats"]
    raise AssertionError(
        "main.py no longer defines harness_stats; rewrite this test against whatever "
        "endpoint now feeds the /fleet Active Focus panel"
    )


class FakeCursor:
    def __init__(self, tickets: list[dict]):
        self._tickets = tickets
        self.queries: list[str] = []

    async def execute(self, sql, params=None):
        self.queries.append(sql)

    async def fetchone(self):
        sql = self.queries[-1]
        if "approval_tickets" in sql:
            return {"count": len(self._tickets)}
        if "harness_scratchpad" in sql:
            return {"count": 1}
        if "harness_idempotency" in sql:
            return {"count": 4}
        raise AssertionError(f"unexpected fetchone for: {sql[:80]}")

    async def fetchall(self):
        sql = self.queries[-1]
        if "approval_tickets" in sql:
            return self._tickets
        if "FROM memories" in sql:
            return [
                {"agent": None, "count": 3},
                {"agent": "atlas", "count": 5},
            ]
        raise AssertionError(f"unexpected fetchall for: {sql[:80]}")

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class FakeConn:
    def __init__(self, tickets: list[dict]):
        self._cursor = FakeCursor(tickets)

    def cursor(self):
        return self._cursor


def _ticket(agent: str = "atlas") -> dict:
    now = datetime.now(timezone.utc)
    return {
        "ticket_id": "t-1",
        "agent_id": agent,
        "tool_name": "db_drop",
        "target_resource": "prod/events",
        "created_at": now,
        "expires_at": now + timedelta(minutes=15),
    }


def _run(tickets: list[dict]) -> dict:
    harness_stats = _load_harness_stats()
    return asyncio.run(
        harness_stats(auth={"tenant_id": "tenant-1"}, conn=FakeConn(tickets))
    )


def test_stats_carries_pending_ticket_details():
    body = _run([_ticket()])
    detail = body["store"]["pending_ticket_details"]
    assert detail == [
        {
            "ticket_id": "t-1",
            "agent": "atlas",
            "tool": "db_drop",
            "target": "prod/events",
            "created_at": detail[0]["created_at"],
            "expires_at": detail[0]["expires_at"],
        }
    ]
    assert detail[0]["created_at"].endswith("+00:00")


def test_stats_detail_query_filters_live_pending_only():
    """The gate that can fail: strip the pending/expiry filter and this goes red."""
    _run([_ticket()])
    # Re-run and capture the executed SQL through the fake cursor.
    harness_stats = _load_harness_stats()
    conn = FakeConn([_ticket()])
    asyncio.run(harness_stats(auth={"tenant_id": "tenant-1"}, conn=conn))
    detail_sql = [
        q for q in conn._cursor.queries if "approval_tickets" in q and "ORDER BY" in q
    ]
    assert detail_sql, "harness_stats never queried approval_tickets for details"
    sql = detail_sql[0]
    assert "status = 'pending'" in sql
    assert "expires_at > NOW()" in sql
    assert "LIMIT 20" in sql


def test_stats_idle_reports_empty_details_not_zero_only():
    body = _run([])
    assert body["store"]["pending_ticket_details"] == []
    assert body["store"]["pending_approvals"] == 0


def test_stats_null_agent_renders_as_unattributed():
    body = _run([_ticket()])
    assert body["store"]["memories_by_agent"] == {"unattributed": 3, "atlas": 5}

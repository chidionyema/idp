"""
Active Runtime Harness — Python port of DefaultActiveAgentHarness.

Ported from TypeScript (platform/active-runtime/src/). ADR 0050: one memory plane,
no Convex, Postgres tables via this module.

Four harness tables (schema.sql §11):
    harness_idempotency  — ACID idempotency ledger
    approval_tickets     — payload-bound approval tickets
    harness_scratchpad  — run scratchpad (TTL)
    preference_recurrence — global-preference recurrence counters

Three adapters over the harness tables:
    PostgresIdempotencyStore   — harness_idempotency
    PostgresApprovalStore       — approval_tickets
    PostgresScratchpadStore    — harness_scratchpad + preference_recurrence

One storage adapter for the existing memories table:
    PostgresCortexAdapter      — searchAssociativeFacts, runTransaction (bi-temporal)

One telemetry module:
    HarnessTelemetry           — OTel metrics, no-op when endpoint unset

One focus controller:
    ActiveFocusController       — circuit breakers, strategy lock, approval gate

One memory engine:
    ActiveMemoryEngine         — buildActiveContextBrief, consolidateTurnCandidates, archiveProjectScope

One harness wrapper:
    DefaultActiveAgentHarness  — orchestrates the full run loop

One webhook handler:
    ApprovalWebhookHandler     — HMAC-SHA256 webhook endpoint

All synchronous — callers are FastAPI route handlers and are themselves async,
so this code stays synchronous to match FastAPI's dependency injection model.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Types — mirrors src/types/active-runtime.ts
# ---------------------------------------------------------------------------

TrustProvenance = str  # "user_direct" | "verified_internal" | "untrusted_external"
MemoryScope = str  # "ephemeral_turn" | "project_fact" | "global_preference"
FactLifecycleStatus = str  # "active" | "superseded" | "archived"

AttemptOutcomeStatus = str
# "progress" | "blocked" | "failed" | "needs_info" | "done"


@dataclass
class BiTemporalFact:
    id: str
    tenant_id: str
    scope: MemoryScope
    project_id: Optional[str]
    subject: str
    predicate: str
    object: str  # content field in memories table
    artifact_uri: Optional[str]
    artifact_version_hash: Optional[str]
    source_event_at: int  # ms epoch
    ingested_at: int  # ms epoch
    provenance: TrustProvenance
    confidence: float
    recurrence_count: int
    version: int
    status: FactLifecycleStatus
    superseded_by_id: Optional[str]
    # What vouched for this fact when it was written: "verified_internal" (a checker re-produced
    # it), "user_direct" (the founder said it), "raw_source" (an agent wrote it and nothing has
    # checked). The brief's SELECT has always read this column; until 2026-10-23 the adapter
    # dropped it, so every row rendered as if it had been verified.
    trust_tier: str = "raw_source"


@dataclass
class AttemptRecord:
    attempt_id: str
    step_index: int
    agent_id: str
    tool_name: str
    strategy_class: str
    strategy_fingerprint: str
    outcome: AttemptOutcomeStatus
    error_code: Optional[str]
    error_summary: Optional[str]
    hypothesis_for_failure: Optional[str]
    cost_usd: float
    duration_ms: int
    timestamp: int


@dataclass
class GoalConstraintSpec:
    goal_id: str
    project_id: str
    tenant_id: str
    max_attempts: int = 8
    max_same_strategy_failures: int = 2
    max_budget_usd: float = 1.5
    max_wall_clock_ms: int = 120_000
    forbidden_capabilities: list[str] = field(
        default_factory=lambda: ["drop_production_table", "disable_test_suite"]
    )
    protected_resource_patterns: list[re.Pattern] = field(
        default_factory=lambda: [
            re.compile(r"\.test\.(ts|js|py)$"),
            re.compile(r"migrations/.*_prod"),
        ]
    )


@dataclass
class ApprovalTicket:
    ticket_id: str
    payload_hash: str
    agent_id: str
    tool_name: str
    target_resource: str
    status: str  # "pending" | "approved" | "rejected" | "consumed" | "expired"
    expires_at: int  # ms epoch
    created_at: int  # ms epoch
    approved_by: Optional[str] = None


@dataclass
class ToolMetadata:
    tool_name: str
    strategy_class: str
    capability_tags: list[str]
    requires_approval: bool
    extract_target_resource: Any  # callable[[dict], str]


@dataclass
class FocusPolicyDecision:
    action: str  # "COMPLETE" | "ASK_CLARIFICATION" | "AWAIT_APPROVAL" | "SWITCH_STRATEGY" | "CONTINUE" | "HALT_ESCALATE"
    # action-specific fields
    summary: Optional[str] = None
    question: Optional[str] = None
    ticket: Optional[ApprovalTicket] = None
    reason: Optional[str] = None
    locked_strategy_classes: Optional[list[str]] = None
    coaching_directive: Optional[str] = None
    attempt_ledger: Optional[list[AttemptRecord]] = None


@dataclass
class ExtractedFactCandidate:
    scope: MemoryScope
    subject: str
    predicate: str
    object: str
    artifact_uri: Optional[str] = None
    artifact_version_hash: Optional[str] = None
    source_event_timestamp_iso: Optional[str] = None
    explicit_permanence_intent: bool = False
    confidence: float = 1.0


@dataclass
class AgentTurnInput:
    run_id: str
    tenant_id: str
    project_id: Optional[str]
    agent_id: str
    user_prompt: str
    provenance: TrustProvenance
    constraints: Optional[dict[str, Any]] = None


@dataclass
class ModelStepResponse:
    type: str  # "tool_call" | "final_answer" | "needs_clarification"
    tool_name: Optional[str] = None
    tool_args: Optional[dict[str, Any]] = None
    content: Optional[str] = None
    clarification_question: Optional[str] = None
    cost_usd: float = 0.0
    extracted_memories: Optional[list[ExtractedFactCandidate]] = None


@dataclass
class HarnessRunResult:
    status: str  # "COMPLETED" | "NEEDS_CLARIFICATION" | "AWAITING_APPROVAL" | "ESCALATED_BLOCKER"
    response_text: str
    decision: FocusPolicyDecision
    memory_stats: dict[
        str, int
    ]  # promoted, ignored_ephemeral, blocked_stale_or_untrusted


# ---------------------------------------------------------------------------
# Telemetry — mirrors src/telemetry/active-otel-exporter.ts
# Pattern: fleetview_backend/tracing.py — OTel via OTEL_EXPORTER_OTLP_ENDPOINT,
# no-op when unset. Memory server has no OTel today; this is net-new.
# ---------------------------------------------------------------------------

_HARNESS_OTEL_INITIALIZED = False
_harness_tracer = None
_harness_meter = None


def _init_harness_otel() -> None:
    global _HARNESS_OTEL_INITIALIZED, _harness_tracer, _harness_meter
    if _HARNESS_OTEL_INITIALIZED:
        return
    _HARNESS_OTEL_INITIALIZED = True

    import os

    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    enabled = os.environ.get("OTEL_ENABLED", "true").lower() not in ("false", "0", "no")

    if not enabled or not endpoint:
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({"service.name": "unified-memory-server"})
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        _harness_tracer = trace.get_tracer("active-runtime-harness")
    except Exception as exc:
        print(f"[harness] OTel setup failed: {exc}", flush=True)


def _get_harness_tracer():
    _init_harness_otel()
    return _harness_tracer


@dataclass
class TelemetrySnapshot:
    prefetch_count: int = 0
    last_brief_tokens: int = 0
    facts_promoted: int = 0
    facts_ignored_ephemeral: int = 0
    facts_blocked_stale_or_untrusted: int = 0
    facts_archived: int = 0
    attempts_by_outcome: dict[str, int] = field(
        default_factory=lambda: {
            "progress": 0,
            "blocked": 0,
            "failed": 0,
            "needs_info": 0,
            "done": 0,
        }
    )
    strategy_pivots: int = 0
    circuit_breaker_trips: int = 0
    approval_events: dict[str, int] = field(
        default_factory=lambda: {
            "requested": 0,
            "approved": 0,
            "rejected": 0,
            "consumed": 0,
            "replay_or_hash_blocked": 0,
        }
    )
    total_cost_usd: float = 0.0


class HarnessTelemetry:
    """OTel telemetry for the harness. No-op when OTEL_EXPORTER_OTLP_ENDPOINT is unset."""

    def __init__(self) -> None:
        self._state = TelemetrySnapshot()
        self._tracer = _get_harness_tracer()

    def with_span(
        self, span_name: str, attributes: dict[str, Any], fn: callable
    ) -> Any:
        """Wrap any async runtime phase in an OTel span."""
        tracer = self._tracer
        if tracer is None:
            return fn()
        from opentelemetry import trace

        span = tracer.start_span(span_name)
        for k, v in attributes.items():
            span.set_attribute(k, v)
        try:
            result = fn()
            span.set_status(trace.Status(trace.StatusCode.OK))
            return result
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))
            raise
        finally:
            span.end()

    def record_prefetch(
        self,
        tenant_id: str,
        project_id: Optional[str],
        duration_ms: float,
        estimated_tokens: int,
    ) -> None:
        self._state.prefetch_count += 1
        self._state.last_brief_tokens = estimated_tokens

    def record_consolidation(
        self,
        tenant_id: str,
        provenance: TrustProvenance,
        promoted: int,
        ignored_ephemeral: int,
        blocked_stale_or_untrusted: int,
    ) -> None:
        if promoted > 0:
            self._state.facts_promoted += promoted
        if ignored_ephemeral > 0:
            self._state.facts_ignored_ephemeral += ignored_ephemeral
        if blocked_stale_or_untrusted > 0:
            self._state.facts_blocked_stale_or_untrusted += blocked_stale_or_untrusted

    def record_project_archival(
        self, tenant_id: str, project_id: str, archived_count: int
    ) -> None:
        self._state.facts_archived += archived_count

    def record_attempt(
        self,
        agent_id: str,
        tool_name: str,
        strategy_class: str,
        outcome: AttemptOutcomeStatus,
        cost_usd: float,
    ) -> None:
        self._state.attempts_by_outcome[outcome] = (
            self._state.attempts_by_outcome.get(outcome, 0) + 1
        )
        self._state.total_cost_usd += cost_usd

    def record_strategy_pivot(
        self, agent_id: str, locked_strategy_class: str, remaining_classes_count: int
    ) -> None:
        self._state.strategy_pivots += 1

    def record_circuit_breaker_trip(
        self, agent_id: str, reason: str, total_run_cost_usd: float
    ) -> None:
        self._state.circuit_breaker_trips += 1

    def record_approval_event(
        self,
        agent_id: str,
        tool_name: str,
        event: str,  # "requested" | "approved" | "rejected" | "consumed" | "replay_or_hash_blocked"
    ) -> None:
        self._state.approval_events[event] = (
            self._state.approval_events.get(event, 0) + 1
        )

    def get_snapshot(self) -> TelemetrySnapshot:
        return TelemetrySnapshot(
            prefetch_count=self._state.prefetch_count,
            last_brief_tokens=self._state.last_brief_tokens,
            facts_promoted=self._state.facts_promoted,
            facts_ignored_ephemeral=self._state.facts_ignored_ephemeral,
            facts_blocked_stale_or_untrusted=self._state.facts_blocked_stale_or_untrusted,
            facts_archived=self._state.facts_archived,
            attempts_by_outcome=dict(self._state.attempts_by_outcome),
            strategy_pivots=self._state.strategy_pivots,
            circuit_breaker_trips=self._state.circuit_breaker_trips,
            approval_events=dict(self._state.approval_events),
            total_cost_usd=self._state.total_cost_usd,
        )


# ---------------------------------------------------------------------------
# PostgresAdapters — concrete implementations using psycopg connections
# ---------------------------------------------------------------------------


class PostgresIdempotencyStore:
    """harness_idempotency table: idempotency_key -> outcome, output, error_code, error_summary."""

    def get(
        self, conn, tenant_id: str, idempotency_key: str
    ) -> Optional[dict[str, Any]]:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT outcome, output, error_code, error_summary FROM harness_idempotency "
                "WHERE tenant_id = %s AND idempotency_key = %s",
                (tenant_id, idempotency_key),
            )
            row = cur.fetchone()
            if not row:
                return None
            return dict(row)

    def set(
        self,
        conn,
        tenant_id: str,
        idempotency_key: str,
        outcome: str,
        output: str,
        error_code: Optional[str] = None,
        error_summary: Optional[str] = None,
    ) -> None:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO harness_idempotency (tenant_id, idempotency_key, outcome, output, error_code, error_summary) "
                "VALUES (%s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (tenant_id, idempotency_key) DO UPDATE SET "
                "outcome = EXCLUDED.outcome, output = EXCLUDED.output, "
                "error_code = EXCLUDED.error_code, error_summary = EXCLUDED.error_summary",
                (
                    tenant_id,
                    idempotency_key,
                    outcome,
                    output,
                    error_code,
                    error_summary,
                ),
            )


class PostgresApprovalStore:
    """approval_tickets table. Interface mirrors ApprovalStoreAdapter from the TS focus controller."""

    def get_ticket_by_hash(
        self, conn, tenant_id: str, payload_hash: str
    ) -> Optional[ApprovalTicket]:
        """Return the live ticket to act on: live approved > live pending > rejected > newest."""
        with conn.cursor() as cur:
            cur.execute(
                "SELECT ticket_id, tenant_id, payload_hash, agent_id, tool_name, target_resource, "
                "status, approved_by, expires_at, created_at "
                "FROM approval_tickets "
                "WHERE tenant_id = %s AND payload_hash = %s "
                "ORDER BY "
                "  CASE status "
                "    WHEN 'approved' THEN 1 "
                "    WHEN 'pending' THEN 2 "
                "    WHEN 'rejected' THEN 3 "
                "    ELSE 4 "
                "  END, "
                "  created_at DESC "
                "LIMIT 1",
                (tenant_id, payload_hash),
            )
            row = cur.fetchone()
            if not row:
                return None
            return ApprovalTicket(
                ticket_id=str(row["ticket_id"]),
                payload_hash=row["payload_hash"],
                agent_id=row["agent_id"],
                tool_name=row["tool_name"],
                target_resource=row["target_resource"],
                status=row["status"],
                expires_at=int(row["expires_at"].timestamp() * 1000),
                created_at=int(row["created_at"].timestamp() * 1000),
                approved_by=row["approved_by"],
            )

    def create_pending_ticket(
        self, conn, ticket: ApprovalTicket, resume_data: Optional[dict]
    ) -> None:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO approval_tickets "
                "(tenant_id, ticket_id, payload_hash, agent_id, tool_name, target_resource, "
                "status, expires_at, created_at, resume_data) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (tenant_id, payload_hash, status) "
                "WHERE status = 'pending' DO NOTHING",
                (
                    ticket.agent_id,  # placeholder: we use tenant_id below
                    ticket.ticket_id,
                    ticket.payload_hash,
                    ticket.agent_id,
                    ticket.tool_name,
                    ticket.target_resource,
                    "pending",
                    datetime.fromtimestamp(ticket.expires_at / 1000, tz=timezone.utc),
                    datetime.fromtimestamp(ticket.created_at / 1000, tz=timezone.utc),
                    json.dumps(resume_data) if resume_data else None,
                ),
            )

    def create_pending_ticket_standalone(
        self,
        conn,
        tenant_id: str,
        ticket_id: str,
        payload_hash: str,
        agent_id: str,
        tool_name: str,
        target_resource: str,
        expires_at_ms: int,
        resume_data: Optional[dict] = None,
    ) -> None:
        """Create a pending ticket. Ignores conflicts so retries open fresh tickets."""
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO approval_tickets "
                "(tenant_id, ticket_id, payload_hash, agent_id, tool_name, target_resource, "
                "status, expires_at, created_at, resume_data) "
                "VALUES (%s, %s, %s, %s, %s, %s, 'pending', %s, %s, %s)",
                (
                    tenant_id,
                    ticket_id,
                    payload_hash,
                    agent_id,
                    tool_name,
                    target_resource,
                    datetime.fromtimestamp(expires_at_ms / 1000, tz=timezone.utc),
                    datetime.now(timezone.utc),
                    json.dumps(resume_data) if resume_data else None,
                ),
            )

    def consume_ticket(self, conn, tenant_id: str, ticket_id: str) -> bool:
        """Atomic CAS: only consume if status is 'approved' and not expired. Returns True on success."""
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE approval_tickets "
                "SET status = 'consumed' "
                "WHERE ticket_id = %s AND tenant_id = %s "
                "AND status = 'approved' "
                "AND expires_at > %s "
                "RETURNING ticket_id",
                (ticket_id, tenant_id, datetime.now(timezone.utc)),
            )
            row = cur.fetchone()
            return row is not None

    def get_ticket_by_id(
        self, conn, tenant_id: str, ticket_id: str
    ) -> Optional[ApprovalTicket]:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT ticket_id, tenant_id, payload_hash, agent_id, tool_name, target_resource, "
                "status, approved_by, expires_at, created_at, resume_data "
                "FROM approval_tickets WHERE ticket_id = %s AND tenant_id = %s",
                (ticket_id, tenant_id),
            )
            row = cur.fetchone()
            if not row:
                return None
            return ApprovalTicket(
                ticket_id=str(row["ticket_id"]),
                payload_hash=row["payload_hash"],
                agent_id=row["agent_id"],
                tool_name=row["tool_name"],
                target_resource=row["target_resource"],
                status=row["status"],
                expires_at=int(row["expires_at"].timestamp() * 1000),
                created_at=int(row["created_at"].timestamp() * 1000),
                approved_by=row["approved_by"],
            )

    def update_status(
        self,
        conn,
        tenant_id: str,
        ticket_id: str,
        new_status: str,
        approved_by: Optional[str] = None,
    ) -> bool:
        """Update ticket status and approved_by. Returns True if the row was found and updated."""
        with conn.cursor() as cur:
            if approved_by:
                cur.execute(
                    "UPDATE approval_tickets "
                    "SET status = %s, approved_by = %s "
                    "WHERE ticket_id = %s AND tenant_id = %s "
                    "RETURNING ticket_id",
                    (new_status, approved_by, ticket_id, tenant_id),
                )
            else:
                cur.execute(
                    "UPDATE approval_tickets "
                    "SET status = %s "
                    "WHERE ticket_id = %s AND tenant_id = %s "
                    "RETURNING ticket_id",
                    (new_status, ticket_id, tenant_id),
                )
            return cur.fetchone() is not None


class PostgresScratchpadStore:
    """harness_scratchpad + preference_recurrence tables. Mirrors CustomFastMemoryAdapter."""

    def get_working_scratchpad(
        self, conn, tenant_id: str, run_id: str
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM harness_scratchpad "
                "WHERE tenant_id = %s AND run_id = %s AND expires_at < %s",
                (tenant_id, run_id, now),
            )
            cur.execute(
                "SELECT key, value FROM harness_scratchpad "
                "WHERE tenant_id = %s AND run_id = %s AND expires_at > %s",
                (tenant_id, run_id, now),
            )
            return {row["key"]: row["value"] for row in cur.fetchall()}

    def set_working_scratchpad(
        self,
        conn,
        tenant_id: str,
        run_id: str,
        key: str,
        value: Any,
        ttl_seconds: int = 3600,
    ) -> None:
        expires_at = datetime.fromtimestamp(time.time() + ttl_seconds, tz=timezone.utc)
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO harness_scratchpad (tenant_id, run_id, key, value, expires_at) "
                "VALUES (%s, %s, %s, %s, %s) "
                "ON CONFLICT (tenant_id, run_id, key) DO UPDATE SET "
                "value = EXCLUDED.value, expires_at = EXCLUDED.expires_at",
                (tenant_id, run_id, key, json.dumps(value), expires_at),
            )

    def increment_preference_recurrence(
        self, conn, tenant_id: str, signature: str
    ) -> int:
        """Increment the recurrence counter. Returns the new count."""
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO preference_recurrence (tenant_id, signature, count) "
                "VALUES (%s, %s, 1) "
                "ON CONFLICT (tenant_id, signature) DO UPDATE SET "
                "count = preference_recurrence.count + 1, "
                "updated_at = CURRENT_TIMESTAMP "
                "RETURNING count",
                (tenant_id, signature),
            )
            row = cur.fetchone()
            return row["count"] if row else 1


class PostgresCortexAdapter:
    """Adapter over the existing memories table. searchAssociativeFacts + bi-temporal writes.

    Until 2026-10-19 this ignored `query_text` and ordered by `embedding <=> (SELECT embedding
    FROM memories LIMIT 0)` -- a NULL distance, so the "associative" facts were 25 arbitrary
    rows -- and filtered on a `status` column `memories` does not have. Every recall carries
    this brief, so the search is now the one /memories/recall runs: the query embedded with
    the same lane, nearest current facts in the caller's namespace, under a cosine floor.
    """

    # A fact's provenance kind -> the harness scope it plays. Everything else is a project fact.
    _GLOBAL_KINDS = frozenset({"preference", "constraint"})

    def __init__(
        self,
        conn,
        embed: Optional[Any] = None,
        namespace: str = "default",
        min_cosine: float = 0.2,
    ) -> None:
        self._conn = conn
        # embed(text) -> list[float] | None: the query lane. None (or no embedder) falls back
        # to word matching, so the brief degrades to "facts that say it", never to "any facts".
        self._embed = embed
        self._namespace = namespace
        self._min_cosine = min_cosine

    def search_associative_facts(
        self,
        tenant_id: str,
        query_text: str,
        project_id: Optional[str] = None,
        include_graph_one_hop: bool = False,
        limit: int = 25,
    ) -> list[BiTemporalFact]:
        """Facts nearest `query_text` by meaning, or by its words when no vector is available."""
        vec = self._embed(query_text) if self._embed and query_text.strip() else None
        columns = (
            "SELECT id, tenant_id, namespace, key, content, trust_tier, provenance, "
            "valid_from, updated_at, version"
        )
        scope = "FROM memories WHERE tenant_id = %s AND namespace = %s AND is_quarantined = false"
        with self._conn.cursor() as cur:
            if vec is not None:
                literal = "[" + ",".join(map(str, vec)) + "]"
                cur.execute(
                    f"{columns}, 1 - (embedding <=> %s::vector) AS cosine_sim "  # noqa: S608 -- fixed SQL fragments, values bound
                    f"{scope} AND embedding IS NOT NULL "
                    "ORDER BY embedding <=> %s::vector LIMIT %s",
                    (literal, tenant_id, self._namespace, literal, limit),
                )
                rows = [
                    r
                    for r in cur.fetchall()
                    if (r["cosine_sim"] or 0.0) >= self._min_cosine
                ]
                return self._rows_to_facts(rows)
            words = re.findall(r"[a-z0-9][a-z0-9_.#-]{2,}", query_text.lower())[:12]
            if not words:
                return []
            cur.execute(
                f"{columns} {scope} AND content ILIKE ANY(%s) "  # noqa: S608 -- fixed SQL fragments, values bound
                "ORDER BY valid_from DESC LIMIT %s",
                (tenant_id, self._namespace, [f"%{w}%" for w in words], limit),
            )
            return self._rows_to_facts(cur.fetchall())

    def _rows_to_facts(self, rows: list[dict]) -> list[BiTemporalFact]:
        facts = []
        for row in rows:
            prov = row.get("provenance") or {}
            global_scope = prov.get("kind") in self._GLOBAL_KINDS
            facts.append(
                BiTemporalFact(
                    id=str(row["id"]),
                    tenant_id=str(row["tenant_id"]),
                    scope="global_preference" if global_scope else "project_fact",
                    # remember's `subject` is the project a fact belongs to; recall's subject
                    # filter arrives here as project_id, so the two must be the same field.
                    project_id=None if global_scope else (prov.get("subject") or None),
                    subject=row.get("key", ""),
                    predicate="",
                    object=row.get("content", ""),
                    artifact_uri=None,
                    artifact_version_hash=None,
                    source_event_at=int(
                        row.get("valid_from", datetime.now(timezone.utc)).timestamp()
                        * 1000
                    ),
                    ingested_at=int(
                        row.get("updated_at", datetime.now(timezone.utc)).timestamp()
                        * 1000
                    ),
                    provenance=prov.get("source", "user_direct"),
                    # How near the query the fact is; word matches have no distance and rank
                    # below any fact admitted by meaning.
                    confidence=float(row.get("cosine_sim") or 0.5),
                    recurrence_count=1,
                    version=int(row.get("version", 1)),
                    status="active",
                    superseded_by_id=None,
                    trust_tier=str(row.get("trust_tier") or "raw_source"),
                )
            )
        return facts


# ---------------------------------------------------------------------------
# Focus Controller — mirrors src/focus/active-focus-controller.ts
# ---------------------------------------------------------------------------

_CANONICALIZE_CACHE: dict[int, str] = {}


def _canonicalize_payload(value: Any) -> str:
    """Deterministic JSON serializer: key-sorted, no random ordering."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return json.dumps(value)
    if isinstance(value, list):
        return "[" + ",".join(_canonicalize_payload(v) for v in value) + "]"
    if isinstance(value, dict):
        keys = sorted(value.keys())
        entries = [f"{json.dumps(k)}:{_canonicalize_payload(value[k])}" for k in keys]
        return "{" + ",".join(entries) + "}"
    return json.dumps(value)


def _compute_payload_hash(
    agent_id: str, tool_name: str, target_resource: str, args: dict[str, Any]
) -> str:
    canonical_args = _canonicalize_payload(args)
    raw = f"{agent_id}|{tool_name}|{target_resource}|{canonical_args}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class ActiveFocusController:
    """Pre-execution guard + post-step policy evaluation. Circuit breakers, strategy lock, approval gate."""

    def __init__(
        self,
        constraints: GoalConstraintSpec,
        approval_store: PostgresApprovalStore,
        idempotency_store: PostgresIdempotencyStore,
        telemetry: HarnessTelemetry,
    ) -> None:
        self._constraints = constraints
        self._approval_store = approval_store
        self._idempotency_store = idempotency_store
        self._telemetry = telemetry
        self._ledger: list[AttemptRecord] = []
        self._locked_strategy_classes: set[str] = set()
        self._started_at_ms = time.time() * 1000
        self._spent_usd = 0.0

    def validate_before_tool_execution(
        self,
        conn,
        agent_id: str,
        tool: ToolMetadata,
        args: dict[str, Any],
    ) -> tuple[bool, Optional[str], Optional[FocusPolicyDecision]]:
        """
        Returns (allowed, idempotency_key, decision).
        If allowed=True, idempotency_key is the deterministic key.
        If allowed=False, decision explains why.
        """
        target_resource = tool.extract_target_resource(args)

        # 1. Forbidden capability guard
        for tag in tool.capability_tags:
            if tag in self._constraints.forbidden_capabilities:
                decision = FocusPolicyDecision(
                    action="SWITCH_STRATEGY",
                    locked_strategy_classes=sorted(self._locked_strategy_classes),
                    coaching_directive=f'CONSTRAINT BLOCKED: Tool "{tool.tool_name}" uses forbidden '
                    f'capability "{tag}". Achieve the goal without mutating protected constraints.',
                )
                return False, None, decision

        # 2. Protected resource pattern guard
        for pattern in self._constraints.protected_resource_patterns:
            if pattern.search(target_resource):
                decision = FocusPolicyDecision(
                    action="SWITCH_STRATEGY",
                    locked_strategy_classes=sorted(self._locked_strategy_classes),
                    coaching_directive=f'PROTECTED RESOURCE BLOCKED: "{target_resource}" matches '
                    f"a protected resource rule. Fix the underlying implementation instead.",
                )
                return False, None, decision

        # 3. Strategy lock guard
        if tool.strategy_class in self._locked_strategy_classes:
            decision = FocusPolicyDecision(
                action="SWITCH_STRATEGY",
                locked_strategy_classes=sorted(self._locked_strategy_classes),
                coaching_directive=f'STRATEGY LOCKED: Strategy class "{tool.strategy_class}" '  # noqa: S608
                "has already failed repeatedly in this run. Select a tool from a different strategy class.",
            )
            return False, None, decision

        # 4. Approval gate for consequential tools
        payload_hash = _compute_payload_hash(
            agent_id, tool.tool_name, target_resource, args
        )
        now_ms = int(time.time() * 1000)

        if tool.requires_approval:
            existing = self._approval_store.get_ticket_by_hash(
                conn, self._constraints.tenant_id, payload_hash
            )

            if (
                existing is None
                or existing.expires_at <= now_ms
                or existing.status in ("consumed", "expired")
            ):
                new_ticket = ApprovalTicket(
                    ticket_id=f"appr_{uuid.uuid4().hex}",
                    payload_hash=payload_hash,
                    agent_id=agent_id,
                    tool_name=tool.tool_name,
                    target_resource=target_resource,
                    status="pending",
                    expires_at=now_ms + 30 * 60 * 1000,  # 30-minute window
                    created_at=now_ms,
                )
                self._approval_store.create_pending_ticket_standalone(
                    conn,
                    self._constraints.tenant_id,
                    new_ticket.ticket_id,
                    new_ticket.payload_hash,
                    new_ticket.agent_id,
                    new_ticket.tool_name,
                    new_ticket.target_resource,
                    new_ticket.expires_at,
                )
                self._telemetry.record_approval_event(
                    agent_id, tool.tool_name, "requested"
                )
                decision = FocusPolicyDecision(
                    action="AWAIT_APPROVAL",
                    ticket=new_ticket,
                    reason=f'Consequential action "{tool.tool_name}" targeting "{target_resource}" '
                    f"requires explicit approval bound to payload hash {payload_hash[:12]}.",
                )
                return False, None, decision

            if existing.status == "rejected":
                self._telemetry.record_approval_event(
                    agent_id, tool.tool_name, "rejected"
                )
                decision = FocusPolicyDecision(
                    action="HALT_ESCALATE",
                    reason=f'User rejected consequential action "{tool.tool_name}" on "{target_resource}".',
                    attempt_ledger=self._ledger.copy(),
                )
                return False, None, decision

            if existing.status != "approved":
                self._telemetry.record_approval_event(
                    agent_id, tool.tool_name, "requested"
                )
                decision = FocusPolicyDecision(
                    action="AWAIT_APPROVAL",
                    ticket=existing,
                    reason=f"Waiting for approval on ticket {existing.ticket_id}.",
                )
                return False, None, decision

            # Single-use consumption: CAS against 'approved' status
            consumed = self._approval_store.consume_ticket(
                conn, self._constraints.tenant_id, existing.ticket_id
            )
            if not consumed:
                self._telemetry.record_approval_event(
                    agent_id, tool.tool_name, "replay_or_hash_blocked"
                )
                decision = FocusPolicyDecision(
                    action="HALT_ESCALATE",
                    reason=f"Approval ticket {existing.ticket_id} was already consumed by a concurrent worker.",
                    attempt_ledger=self._ledger.copy(),
                )
                return False, None, decision

        idempotency_key = (
            f"{self._constraints.goal_id}:{len(self._ledger)}:{payload_hash[:16]}"
        )
        return True, idempotency_key, None

    def record_attempt_and_evaluate(
        self,
        agent_id: str,
        tool_name: str,
        strategy_class: str,
        args: dict[str, Any],
        outcome: AttemptOutcomeStatus,
        error_code: Optional[str] = None,
        error_summary: Optional[str] = None,
        hypothesis_for_failure: Optional[str] = None,
        clarification_question: Optional[str] = None,
        completion_summary: Optional[str] = None,
        cost_usd: float = 0.0,
        duration_ms: int = 0,
        available_strategy_classes: Optional[list[str]] = None,
    ) -> FocusPolicyDecision:
        """Post-step policy evaluation. Returns the next action to take."""
        self._spent_usd += cost_usd

        strategy_fingerprint = hashlib.sha256(
            f"{strategy_class}|{tool_name}|{error_code or 'ok'}".encode("utf-8")
        ).hexdigest()[:16]

        record = AttemptRecord(
            attempt_id=f"att_{uuid.uuid4().hex}",
            step_index=len(self._ledger) + 1,
            agent_id=agent_id,
            tool_name=tool_name,
            strategy_class=strategy_class,
            strategy_fingerprint=strategy_fingerprint,
            outcome=outcome,
            error_code=error_code,
            error_summary=error_summary,
            hypothesis_for_failure=hypothesis_for_failure,
            cost_usd=cost_usd,
            duration_ms=duration_ms,
            timestamp=int(time.time() * 1000),
        )
        self._ledger.append(record)
        self._telemetry.record_attempt(
            agent_id, tool_name, strategy_class, outcome, cost_usd
        )

        # Rule 1: Done wins immediately
        if outcome == "done":
            return FocusPolicyDecision(
                action="COMPLETE",
                summary=completion_summary or "Goal verified complete.",
            )

        # Rule 2: Ambiguity pauses for clarification
        if outcome == "needs_info":
            return FocusPolicyDecision(
                action="ASK_CLARIFICATION",
                question=clarification_question
                or "Additional clarification is required before choosing an execution path.",
            )

        # Rule 3: Circuit breakers — hard budget/attempt/wall-clock limits
        elapsed_ms = int(time.time() * 1000) - self._started_at_ms
        if (
            len(self._ledger) >= self._constraints.max_attempts
            or self._spent_usd >= self._constraints.max_budget_usd
            or elapsed_ms >= self._constraints.max_wall_clock_ms
        ):
            self._telemetry.record_circuit_breaker_trip(agent_id, "", self._spent_usd)
            reason = (
                f"Active Focus circuit breaker tripped "
                f"(attempts={len(self._ledger)}/{self._constraints.max_attempts}, "
                f"cost=${self._spent_usd:.4f}/${self._constraints.max_budget_usd}, "
                f"elapsed={elapsed_ms}ms)."
            )
            return FocusPolicyDecision(
                action="HALT_ESCALATE",
                reason=reason,
                attempt_ledger=self._ledger.copy(),
            )

        # Rule 4: Progress continues
        if outcome == "progress":
            return FocusPolicyDecision(action="CONTINUE")

        # Rule 5: Failed or blocked — count per strategy class
        failures_in_class = sum(
            1
            for a in self._ledger
            if a.strategy_class == strategy_class and a.outcome in ("failed", "blocked")
        )

        if failures_in_class >= self._constraints.max_same_strategy_failures:
            self._locked_strategy_classes.add(strategy_class)
            self._telemetry.record_strategy_pivot(
                agent_id,
                strategy_class,
                len(available_strategy_classes or [])
                - len(self._locked_strategy_classes),
            )

        remaining = [
            c
            for c in (available_strategy_classes or [])
            if c not in self._locked_strategy_classes
        ]
        if not remaining:
            self._telemetry.record_circuit_breaker_trip(
                agent_id,
                f"All strategy classes exhausted: {list(self._locked_strategy_classes)}",
                self._spent_usd,
            )
            return FocusPolicyDecision(
                action="HALT_ESCALATE",
                reason=f"All available strategy classes ({', '.join(available_strategy_classes or [])}) "
                "have been exhausted or blocked.",
                attempt_ledger=self._ledger.copy(),
            )

        if strategy_class in self._locked_strategy_classes:
            return FocusPolicyDecision(
                action="SWITCH_STRATEGY",
                locked_strategy_classes=sorted(self._locked_strategy_classes),
                coaching_directive=(
                    f'ACTIVE FOCUS PIVOT REQUIRED: Strategy class "{strategy_class}" '
                    f"failed {failures_in_class} times "
                    f"(latest error: {error_summary or 'unknown'}). "
                    f"Locked classes: [{', '.join(sorted(self._locked_strategy_classes))}]. "
                    f"Remaining: [{', '.join(remaining)}]. "
                    "Do not repeat the failed approach."
                ),
            )

        return FocusPolicyDecision(
            action="CONTINUE",
            coaching_directive=f'Previous attempt on "{tool_name}" returned {outcome} '
            f"({error_summary or 'error'}). Adjust parameters or switch strategy if the root cause persists.",
        )

    def get_attempt_ledger(self) -> list[AttemptRecord]:
        return self._ledger.copy()


# ---------------------------------------------------------------------------
# Memory Engine — mirrors src/memory/active-memory-engine.ts
# ---------------------------------------------------------------------------

_MAX_BRIEF_TOKENS = 450


class ActiveMemoryEngine:
    """Pre-fetch, bi-temporal consolidation, and project archival. All state in Postgres tables."""

    def __init__(
        self,
        cortex_adapter: PostgresCortexAdapter,
        scratchpad_store: PostgresScratchpadStore,
        telemetry: HarnessTelemetry,
    ) -> None:
        self._cortex = cortex_adapter
        self._scratchpad = scratchpad_store
        self._telemetry = telemetry

    def build_active_context_brief(
        self,
        conn,
        tenant_id: str,
        project_id: Optional[str],
        run_id: str,
        user_prompt: str,
    ) -> tuple[str, int]:
        """
        Returns (brief_text, estimated_tokens).
        Pre-fetch: associative vector + graph search, rank by scope + recency.
        """
        t0 = time.time()
        associative_facts = self._cortex.search_associative_facts(
            tenant_id=tenant_id,
            query_text=user_prompt,
            project_id=project_id,
            include_graph_one_hop=True,
            limit=25,
        )
        working_state = self._scratchpad.get_working_scratchpad(conn, tenant_id, run_id)

        now_ms = int(time.time() * 1000)
        ranked = []
        for fact in associative_facts:
            if fact.status != "active":
                continue
            # Filter: global preferences OR project facts matching current projectId. A run
            # with no project is scoped by the query alone: every project fact may answer it.
            if fact.scope == "global_preference":
                pass
            elif fact.scope == "project_fact" and project_id in (None, fact.project_id):
                pass
            else:
                continue

            age_days = max(0.0, (now_ms - fact.source_event_at) / (1000 * 60 * 60 * 24))
            recency_weight = 2.0 ** (-age_days / 30)  # 30-day half-life
            project_boost = (
                1.35 if project_id and fact.project_id == project_id else 1.0
            )
            score = fact.confidence * recency_weight * project_boost
            ranked.append((score, fact))

        ranked.sort(key=lambda x: x[0], reverse=True)

        lines: list[str] = []
        estimated_tokens = 0
        for _score, fact in ranked:
            artifact_tag = (
                f" [Artifact: {fact.artifact_uri}"
                + (
                    f"@{fact.artifact_version_hash[:8]}"
                    if fact.artifact_version_hash
                    else ""
                )
                + "]"
                if fact.artifact_uri
                else ""
            )
            date_tag = datetime.fromtimestamp(
                fact.source_event_at / 1000, tz=timezone.utc
            ).strftime("%Y-%m-%d")
            # Each row states its own evidence state. The header used to claim the whole brief
            # was "VERIFIED", which nothing here measured: a fact an agent wrote from memory
            # and a fact a command re-produced rendered identically.
            tier = (getattr(fact, "trust_tier", "") or "raw_source").strip()
            line = (
                f"- [{fact.scope.upper()} | {tier} | as of {date_tag}] "
                f"{fact.subject} {fact.predicate}: {fact.object}{artifact_tag}"
            )
            line_tokens = (len(line) + 3) // 4

            if estimated_tokens + line_tokens > _MAX_BRIEF_TOKENS:
                break
            lines.append(line)
            estimated_tokens += line_tokens

        scratchpad_section = ""
        if working_state:
            scratchpad_section = (
                f"\n[ACTIVE RUN SCRATCHPAD]: {json.dumps(working_state)}"
            )

        if not lines and not scratchpad_section:
            brief = ""
        else:
            brief = (
                "=== ACTIVE MEMORY BRIEF (each row labelled by its own evidence state) ===\n"
                "Read the label on each row, not this header: `verified_internal` was re-produced "
                "by a checker, `user_direct` is what the founder said, `raw_source` is what an "
                "agent wrote and nothing has checked. Do not use older artifact versions if a "
                "newer hash is listed:\n"
                + "\n".join(lines)
                + scratchpad_section
                + "\n==========================================================="
            )

        duration_ms = (time.time() - t0) * 1000
        self._telemetry.record_prefetch(
            tenant_id, project_id, duration_ms, estimated_tokens
        )
        return brief, estimated_tokens

    def consolidate_turn_candidates(
        self,
        conn,
        tenant_id: str,
        project_id: Optional[str],
        run_id: str,
        provenance: TrustProvenance,
        candidates: list[ExtractedFactCandidate],
        default_source_event_at_ms: Optional[int] = None,
    ) -> dict[str, int]:
        """Intent-gated bi-temporal consolidation. Returns {promoted, ignored_ephemeral, blocked_stale_or_untrusted}."""
        promoted = 0
        ignored_ephemeral = 0
        blocked_stale_or_untrusted = 0

        for candidate in candidates:
            # Rule A: Ephemeral turn — stay in scratchpad
            if candidate.scope == "ephemeral_turn":
                self._scratchpad.set_working_scratchpad(
                    conn,
                    tenant_id,
                    run_id,
                    f"{candidate.subject}:{candidate.predicate}",
                    candidate.object,
                    ttl_seconds=3600,
                )
                ignored_ephemeral += 1
                continue

            # Rule B: Untrusted external cannot write global preferences
            if (
                provenance == "untrusted_external"
                and candidate.scope == "global_preference"
            ):
                blocked_stale_or_untrusted += 1
                continue

            # Rule C: Global preference needs explicit permanence OR recurrence >= 3
            if (
                candidate.scope == "global_preference"
                and not candidate.explicit_permanence_intent
            ):
                sig = hashlib.sha256(
                    f"{candidate.subject}|{candidate.predicate}|{candidate.object}".encode(
                        "utf-8"
                    )
                ).hexdigest()
                count = self._scratchpad.increment_preference_recurrence(
                    conn, tenant_id, sig
                )
                if count < 3:
                    self._scratchpad.set_working_scratchpad(
                        conn,
                        tenant_id,
                        run_id,
                        f"inferred_pref:{candidate.subject}:{candidate.predicate}",
                        candidate.object,
                        ttl_seconds=86400,
                    )
                    ignored_ephemeral += 1
                    continue

            # Rule D: Bi-temporal write. The actual ACID check (findActiveFact +
            # stale overwrite protection) lives in the harness run loop, which calls
            # into memory_save / do_remember. This method handles scope gating and
            # persistence of ephemeral/scratchpad facts.
            promoted += 1

        self._telemetry.record_consolidation(
            tenant_id,
            provenance,
            promoted,
            ignored_ephemeral,
            blocked_stale_or_untrusted,
        )
        return {
            "promoted": promoted,
            "ignored_ephemeral": ignored_ephemeral,
            "blocked_stale_or_untrusted": blocked_stale_or_untrusted,
        }

    def archive_project_scope(self, conn, tenant_id: str, project_id: str) -> int:
        """Retire all active project-scoped facts. Returns count archived."""
        with conn.cursor() as cur:
            # Archive: set status = 'archived' via a raw UPDATE against memories.
            # We need to be careful not to bypass the anti-Ouroboros trigger.
            # Archive is a status change, not a supersession — allowed.
            cur.execute(
                "UPDATE memories "
                "SET status = 'archived' "
                "WHERE tenant_id = %s AND key LIKE %s AND status = 'active' "
                "RETURNING id",
                (tenant_id, f"{project_id}%"),
            )
            archived = len(cur.fetchall())

        self._telemetry.record_project_archival(tenant_id, project_id, archived)
        return archived


# ---------------------------------------------------------------------------
# Approval Webhook Handler — mirrors src/webhooks/approval-webhook-handler.ts
# HMAC-SHA256 webhook with 5-minute anti-replay window.
# ---------------------------------------------------------------------------

_MAX_CLOCK_SKEW_MS = 5 * 60 * 1000


def _sign_webhook_payload(
    signing_secret: str, timestamp_sec: int, raw_body: str
) -> str:
    base = f"v0:{timestamp_sec}:{raw_body}"
    mac = hmac.new(signing_secret.encode("utf-8"), base.encode("utf-8"), hashlib.sha256)
    return "v0=" + mac.hexdigest()


def _verify_webhook_signature(
    signing_secret: str,
    timestamp_header: Optional[str],
    signature_header: Optional[str],
    raw_body: str,
) -> tuple[bool, Optional[str]]:
    """Returns (valid, error_reason)."""
    if not timestamp_header or not signature_header:
        return False, "Missing cryptographic signature or timestamp headers."
    try:
        timestamp_sec = int(timestamp_header)
    except ValueError:
        return False, "Invalid timestamp header."
    now_ms = int(time.time() * 1000)
    skew_ms = abs(now_ms - timestamp_sec * 1000)
    if skew_ms > _MAX_CLOCK_SKEW_MS:
        return (
            False,
            f"Webhook timestamp outside 5-minute replay window (skew={skew_ms}ms).",
        )
    # signature_header comes in as "v0=<hex>" (same format as the signing output).
    # Compare raw hex slices to handle the prefix correctly.
    expected = _sign_webhook_payload(signing_secret, timestamp_sec, raw_body)
    # Both are "v0=<hex>" strings — constant-time compare.
    if not _constant_time_eq(signature_header, expected):
        return False, "HMAC-SHA256 signature verification failed."
    return True, None


def _constant_time_eq(a: str, b: str) -> bool:
    """Constant-time string comparison to avoid timing attacks."""
    if len(a) != len(b):
        return False
    result = 0
    a_bytes = a.encode("utf-8")
    b_bytes = b.encode("utf-8")
    if len(a_bytes) != len(b_bytes):
        return False
    for x, y in zip(a_bytes, b_bytes):  # noqa: B905
        result |= x ^ y
    return result == 0


@dataclass
class SuspendedRunCheckpoint:
    run_id: str
    ticket_id: str
    expected_payload_hash: str
    turn_input: AgentTurnInput
    resume_callback: Any  # callable[[AgentTurnInput], Awaitable[dict]]


@dataclass
class WebhookHttpResponse:
    status_code: int
    body: dict[str, Any]


class ApprovalWebhookHandler:
    """HMAC-SHA256 webhook handler. Processes approve/reject callbacks."""

    def __init__(
        self,
        signing_secret: str,
        approval_store: PostgresApprovalStore,
        telemetry: HarnessTelemetry,
    ) -> None:
        self._signing_secret = signing_secret
        self._approval_store = approval_store
        self._telemetry = telemetry
        self._suspended_runs: dict[str, SuspendedRunCheckpoint] = {}

    def register_suspended_run(self, checkpoint: SuspendedRunCheckpoint) -> None:
        self._suspended_runs[checkpoint.ticket_id] = checkpoint

    def handle_webhook(
        self,
        conn,
        raw_body: str,
        timestamp_header: Optional[str],
        signature_header: Optional[str],
    ) -> WebhookHttpResponse:
        """Process an incoming approval webhook. Returns (status_code, body_dict)."""
        # 1. Verify signature
        valid, reason = _verify_webhook_signature(
            self._signing_secret, timestamp_header, signature_header, raw_body
        )
        if not valid:
            return WebhookHttpResponse(401, {"ok": False, "error": reason})

        # 2. Parse JSON
        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            return WebhookHttpResponse(
                400, {"ok": False, "error": "Malformed JSON body."}
            )

        # 3. Validate schema
        ticket_id = payload.get("ticketId")
        expected_payload_hash = payload.get("expectedPayloadHash")
        decision = payload.get("decision")
        reviewer_id = payload.get("reviewerId", "")
        if (
            not ticket_id
            or not expected_payload_hash
            or decision not in ("approve", "reject")
        ):
            return WebhookHttpResponse(
                400, {"ok": False, "error": "Invalid payload schema."}
            )

        now_ms = int(time.time() * 1000)

        # 4. Atomic state transition
        ticket = self._approval_store.get_ticket_by_id(
            conn, self._telemetry._state.prefetch_count, ticket_id
        )
        if not ticket:
            # Try with proper tenant lookup — ticket_id is the primary key
            ticket = self._approval_store.get_ticket_by_id(conn, "", ticket_id)
            if not ticket:
                return WebhookHttpResponse(
                    404, {"ok": False, "error": f"Ticket {ticket_id} not found."}
                )

        if ticket.status != "pending":
            self._telemetry.record_approval_event(
                ticket.agent_id, ticket.tool_name, "replay_or_hash_blocked"
            )
            return WebhookHttpResponse(
                409,
                {
                    "ok": False,
                    "error": f'Ticket {ticket_id} is already in terminal state "{ticket.status}".',
                },
            )

        if ticket.expires_at <= now_ms:
            self._approval_store.update_status(conn, "", ticket_id, "expired")
            self._telemetry.record_approval_event(
                ticket.agent_id, ticket.tool_name, "replay_or_hash_blocked"
            )
            return WebhookHttpResponse(
                409,
                {
                    "ok": False,
                    "error": f"Ticket {ticket_id} expired at {datetime.fromtimestamp(ticket.expires_at / 1000, tz=timezone.utc).isoformat()}.",
                },
            )

        if ticket.payload_hash != expected_payload_hash:
            self._telemetry.record_approval_event(
                ticket.agent_id, ticket.tool_name, "replay_or_hash_blocked"
            )
            return WebhookHttpResponse(
                409,
                {
                    "ok": False,
                    "error": f"Payload hash mismatch on ticket {ticket_id}. Action parameters changed since ticket creation.",
                },
            )

        new_status = "approved" if decision == "approve" else "rejected"
        self._approval_store.update_status(
            conn, ticket.tenant_id, ticket_id, new_status, reviewer_id
        )
        self._telemetry.record_approval_event(
            ticket.agent_id, ticket.tool_name, new_status
        )

        # 5. Resume suspended run if registered
        checkpoint = self._suspended_runs.get(ticket_id)
        if checkpoint:
            del self._suspended_runs[ticket_id]
            # Resume is async — called by the caller in an async context
            resumed_status = "RESUMED"
            resumed_text = "(resumed by webhook)"
            return WebhookHttpResponse(
                200,
                {
                    "ok": True,
                    "ticketId": ticket_id,
                    "newStatus": new_status,
                    "resumedRunStatus": resumed_status,
                    "resumedResponseText": resumed_text,
                },
            )

        return WebhookHttpResponse(
            200, {"ok": True, "ticketId": ticket_id, "newStatus": new_status}
        )


# ---------------------------------------------------------------------------
# Default Agent Harness — mirrors src/runtime/default-agent-wrapper.ts
# The orchestrator that wires everything together.
# ---------------------------------------------------------------------------


@dataclass
class UnderlyingAgentDriver:
    step: Any  # async fn(system_prompt, user_prompt, scratchpad_history, locked_classes) -> ModelStepResponse
    execute_tool: Any  # async fn(tool_name, args, idempotency_key) -> {outcome, output, error_code, error_summary}


@dataclass
class HarnessConfig:
    tenant_id: str
    project_id: Optional[str]
    agent_id: str
    max_attempts: int = 8
    max_same_strategy_failures: int = 2
    max_budget_usd: float = 1.5
    max_wall_clock_ms: int = 120_000
    forbidden_capabilities: Optional[list[str]] = None
    protected_resource_patterns: Optional[list[str]] = None
    base_system_prompt: str = ""


class DefaultActiveAgentHarness:
    """
    Wraps any agent driver so Active Memory pre-fetch, Active Focus obstacle recovery,
    payload-bound approvals, and post-turn memory consolidation execute by default.
    """

    def __init__(
        self,
        memory_engine: ActiveMemoryEngine,
        focus_controller: ActiveFocusController,
        tool_registry: dict[str, ToolMetadata],
        config: HarnessConfig,
        conn,
        telemetry: HarnessTelemetry,
    ) -> None:
        self._memory_engine = memory_engine
        self._focus = focus_controller
        self._tools = tool_registry
        self._config = config
        self._conn = conn
        self._telemetry = telemetry

    async def run_agent(
        self,
        driver: UnderlyingAgentDriver,
        input: AgentTurnInput,
    ) -> HarnessRunResult:
        """
        Main entry point. Async because driver.step and driver.execute_tool are async.
        """
        import asyncio

        # 1. Pre-turn: build active context brief
        brief, estimated_tokens = self._memory_engine.build_active_context_brief(
            self._conn,
            input.tenant_id,
            input.project_id,
            input.run_id,
            input.user_prompt,
        )
        full_system_prompt = (
            self._config.base_system_prompt + "\n\n" + brief
            if brief
            else self._config.base_system_prompt
        )

        scratchpad_history: list[str] = []
        collected_candidates: list[ExtractedFactCandidate] = []
        all_strategy_classes = sorted(
            set(t.strategy_class for t in self._tools.values())
        )
        locked_classes: list[str] = []
        preflight_rejections = 0

        constraints = GoalConstraintSpec(
            goal_id=input.run_id,
            project_id=input.project_id or "global",
            tenant_id=input.tenant_id,
            max_attempts=input.constraints.get(
                "max_attempts", self._config.max_attempts
            )
            if input.constraints
            else self._config.max_attempts,
            max_same_strategy_failures=input.constraints.get(
                "max_same_strategy_failures", self._config.max_same_strategy_failures
            )
            if input.constraints
            else self._config.max_same_strategy_failures,
            max_budget_usd=input.constraints.get(
                "max_budget_usd", self._config.max_budget_usd
            )
            if input.constraints
            else self._config.max_budget_usd,
            max_wall_clock_ms=input.constraints.get(
                "max_wall_clock_ms", self._config.max_wall_clock_ms
            )
            if input.constraints
            else self._config.max_wall_clock_ms,
            forbidden_capabilities=input.constraints.get(
                "forbidden_capabilities", self._config.forbidden_capabilities
            )
            if input.constraints and self._config.forbidden_capabilities is not None
            else self._config.forbidden_capabilities or [],
            protected_resource_patterns=self._config.protected_resource_patterns or [],
        )

        async def consolidate() -> dict[str, int]:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                lambda: self._memory_engine.consolidate_turn_candidates(
                    self._conn,
                    input.tenant_id,
                    input.project_id,
                    input.run_id,
                    input.provenance,
                    collected_candidates,
                ),
            )

        async def escalate_preflight_loop() -> HarnessRunResult:
            decision = FocusPolicyDecision(
                action="HALT_ESCALATE",
                reason=f"Active Focus circuit breaker tripped: {preflight_rejections} tool calls rejected before execution "
                f"(limit {constraints.max_attempts}).",
                attempt_ledger=self._focus.get_attempt_ledger(),
            )
            return HarnessRunResult(
                status="ESCALATED_BLOCKER",
                response_text=decision.reason or "",
                decision=decision,
                memory_stats=await consolidate(),
            )

        # 3. Active Focus execution loop
        while True:
            step_start_ms = int(time.time() * 1000)

            # Call driver.step (async)
            model_step = await driver.step(
                system_prompt_with_active_memory=full_system_prompt,
                user_prompt=input.user_prompt,
                conversation_scratchpad=scratchpad_history,
                locked_strategy_classes=locked_classes,
            )

            if model_step.extracted_memories:
                collected_candidates.extend(model_step.extracted_memories)

            # Case A: Needs clarification
            if model_step.type == "needs_clarification":
                decision = self._focus.record_attempt_and_evaluate(
                    agent_id=input.agent_id,
                    tool_name="clarification_gate",
                    strategy_class="dialogue",
                    args={},
                    outcome="needs_info",
                    clarification_question=model_step.clarification_question,
                    cost_usd=model_step.cost_usd,
                    duration_ms=int(time.time() * 1000) - step_start_ms,
                    available_strategy_classes=all_strategy_classes,
                )
                memory_stats = await consolidate()
                return HarnessRunResult(
                    status="NEEDS_CLARIFICATION",
                    response_text=model_step.clarification_question
                    or "Could you clarify your requirement?",
                    decision=decision,
                    memory_stats=memory_stats,
                )

            # Case B: Final answer
            if model_step.type == "final_answer":
                decision = self._focus.record_attempt_and_evaluate(
                    agent_id=input.agent_id,
                    tool_name="final_response",
                    strategy_class="synthesis",
                    args={},
                    outcome="done",
                    completion_summary=model_step.content,
                    cost_usd=model_step.cost_usd,
                    duration_ms=int(time.time() * 1000) - step_start_ms,
                    available_strategy_classes=all_strategy_classes,
                )
                memory_stats = await consolidate()
                return HarnessRunResult(
                    status="COMPLETED",
                    response_text=model_step.content or "",
                    decision=decision,
                    memory_stats=memory_stats,
                )

            # Case C: Tool call
            tool_meta = self._tools.get(model_step.tool_name or "")
            if not tool_meta:
                scratchpad_history.append(
                    f'SYSTEM ERROR: Unknown tool "{model_step.tool_name}". Pick a registered tool.'
                )
                preflight_rejections += 1
                if preflight_rejections >= constraints.max_attempts:
                    return await escalate_preflight_loop()
                continue

            # Pre-execution guard (sync — uses self._conn directly)
            allowed, idempotency_key, pre_decision = (
                self._focus.validate_before_tool_execution(
                    self._conn,
                    input.agent_id,
                    tool_meta,
                    model_step.tool_args or {},
                )
            )

            if not allowed:
                if pre_decision and pre_decision.action == "AWAIT_APPROVAL":
                    memory_stats = await consolidate()
                    return HarnessRunResult(
                        status="AWAITING_APPROVAL",
                        response_text=pre_decision.reason or "",
                        decision=pre_decision,
                        memory_stats=memory_stats,
                    )

                if pre_decision and pre_decision.action == "SWITCH_STRATEGY":
                    locked_classes = pre_decision.locked_strategy_classes or []
                    scratchpad_history.append(pre_decision.coaching_directive or "")
                    preflight_rejections += 1
                    if preflight_rejections >= constraints.max_attempts:
                        return await escalate_preflight_loop()
                    continue

                # HALT_ESCALATE and any other: stop
                memory_stats = await consolidate()
                return HarnessRunResult(
                    status="ESCALATED_BLOCKER",
                    response_text=(
                        pre_decision.reason
                        if pre_decision
                        else "Pre-execution gate refused the call."
                    ),
                    decision=pre_decision
                    or FocusPolicyDecision(
                        action="HALT_ESCALATE", reason="Pre-execution gate refused."
                    ),
                    memory_stats=memory_stats,
                )

            # Execute tool (async)
            exec_result = await driver.execute_tool(
                tool_meta.tool_name,
                model_step.tool_args or {},
                idempotency_key or "",
            )

            post_decision = self._focus.record_attempt_and_evaluate(
                agent_id=input.agent_id,
                tool_name=tool_meta.tool_name,
                strategy_class=tool_meta.strategy_class,
                args=model_step.tool_args or {},
                outcome=exec_result.get("outcome", "failed"),
                error_code=exec_result.get("error_code"),
                error_summary=exec_result.get("error_summary"),
                cost_usd=model_step.cost_usd,
                duration_ms=int(time.time() * 1000) - step_start_ms,
                available_strategy_classes=all_strategy_classes,
            )

            if post_decision.action == "SWITCH_STRATEGY":
                locked_classes = post_decision.locked_strategy_classes or []
                scratchpad_history.append(
                    f"TOOL FAILED ({tool_meta.tool_name}): {exec_result.get('error_summary', '')}\n"
                    + (post_decision.coaching_directive or "")
                )
                continue

            if post_decision.action == "HALT_ESCALATE":
                memory_stats = await consolidate()
                return HarnessRunResult(
                    status="ESCALATED_BLOCKER",
                    response_text=post_decision.reason or "",
                    decision=post_decision,
                    memory_stats=memory_stats,
                )

            scratchpad_history.append(
                f"TOOL RESULT ({tool_meta.tool_name} -> {exec_result.get('outcome', '?')}): {exec_result.get('output', '')}"
            )
            if post_decision.action == "CONTINUE" and post_decision.coaching_directive:
                scratchpad_history.append(post_decision.coaching_directive)

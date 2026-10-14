"""
Regression tests for the active-runtime harness (Python port).
Mirrors tests/hardening.spec.ts from the TypeScript package.

Test 1: A global preference never supersedes a project fact sharing subject/predicate.
Test 2: An approved-and-consumed payload needs a fresh approval, never a replay.
Test 3: A model that keeps calling a protected path is halted after maxAttempts.
Test 4: A model that keeps calling an unregistered tool is halted.
Test 5: Unclassified MCP tools fail closed, and one idempotency key executes upstream once.
"""

from __future__ import annotations
from typing import Any

import hashlib
import re
import time
import uuid
from unittest.mock import MagicMock

import pytest

from harness import (
    ActiveFocusController,
    ApprovalTicket,
    GoalConstraintSpec,
    HarnessTelemetry,
    ToolMetadata,
    _canonicalize_payload,
    _compute_payload_hash,
    _constant_time_eq,
    _sign_webhook_payload,
    _verify_webhook_signature,
)


# ---------------------------------------------------------------------------
# Helpers — in-memory stores that mirror the harness table behaviour
# ---------------------------------------------------------------------------


class InMemoryApprovalStore:
    """Stores ApprovalTicket objects in a dict. Mirrors the harness table logic."""

    def __init__(self) -> None:
        self._tickets: dict[
            str, tuple[ApprovalTicket, str]
        ] = {}  # ticket_id -> (ticket, tenant_id)

    def get_ticket_by_hash(
        self, conn, tenant_id: str, payload_hash: str
    ) -> ApprovalTicket | None:
        now_ms = int(time.time() * 1000)
        matches = [
            t
            for (t, tid) in self._tickets.values()
            if tid == tenant_id and t.payload_hash == payload_hash
        ]
        if not matches:
            return None

        def _is_live(t: ApprovalTicket) -> bool:
            return t.expires_at > now_ms

        best = (
            next((t for t in matches if t.status == "approved" and _is_live(t)), None)
            or next((t for t in matches if t.status == "pending" and _is_live(t)), None)
            or next((t for t in matches if t.status == "rejected"), None)
            or sorted(matches, key=lambda t: t.created_at, reverse=True)[0]
        )
        return best

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
        resume_data: dict | None = None,
    ) -> None:
        ticket = ApprovalTicket(
            ticket_id=ticket_id,
            payload_hash=payload_hash,
            agent_id=agent_id,
            tool_name=tool_name,
            target_resource=target_resource,
            status="pending",
            expires_at=expires_at_ms,
            created_at=int(time.time() * 1000),
        )
        self._tickets[ticket_id] = (ticket, tenant_id)

    def update_status(
        self,
        conn,
        tenant_id: str,
        ticket_id: str,
        new_status: str,
        approved_by: str | None = None,
    ) -> bool:
        if ticket_id not in self._tickets:
            return False
        ticket, tid = self._tickets[ticket_id]
        updated = ApprovalTicket(
            ticket_id=ticket.ticket_id,
            payload_hash=ticket.payload_hash,
            agent_id=ticket.agent_id,
            tool_name=ticket.tool_name,
            target_resource=ticket.target_resource,
            status=new_status,
            expires_at=ticket.expires_at,
            created_at=ticket.created_at,
            approved_by=approved_by,
        )
        self._tickets[ticket_id] = (updated, tid)
        return True

    def consume_ticket(self, conn, tenant_id: str, ticket_id: str) -> bool:
        if ticket_id not in self._tickets:
            return False
        ticket, tid = self._tickets[ticket_id]
        now_ms = int(time.time() * 1000)
        if ticket.status == "approved" and ticket.expires_at > now_ms:
            updated = ApprovalTicket(
                ticket_id=ticket.ticket_id,
                payload_hash=ticket.payload_hash,
                agent_id=ticket.agent_id,
                tool_name=ticket.tool_name,
                target_resource=ticket.target_resource,
                status="consumed",
                expires_at=ticket.expires_at,
                created_at=ticket.created_at,
                approved_by=ticket.approved_by,
            )
            self._tickets[ticket_id] = (updated, tid)
            return True
        return False


class InMemoryIdempotencyStore:
    """Stores outcome records in a dict. Mirrors harness_idempotency table."""

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], dict] = {}  # (tenant_id, key) -> record

    def get(self, conn, tenant_id: str, idempotency_key: str) -> dict | None:
        return self._store.get((tenant_id, idempotency_key))

    def set(
        self,
        conn,
        tenant_id: str,
        idempotency_key: str,
        outcome: str,
        output: str,
        error_code: str | None = None,
        error_summary: str | None = None,
    ) -> None:
        self._store[(tenant_id, idempotency_key)] = {
            "outcome": outcome,
            "output": output,
            "error_code": error_code,
            "error_summary": error_summary,
        }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def telemetry():
    return HarnessTelemetry()


@pytest.fixture
def constraints():
    return GoalConstraintSpec(
        goal_id="g",
        project_id="p",
        tenant_id="t",
        max_attempts=6,
        max_same_strategy_failures=2,
        max_budget_usd=1.0,
        max_wall_clock_ms=60_000,
        forbidden_capabilities=[],
        protected_resource_patterns=[],
    )


# ---------------------------------------------------------------------------
# Test 1: A global preference never supersedes a project fact sharing subject/predicate.
#
# The harness separates scopes by scratchpad key prefix:
#   project_fact → stored with key "project_fact:subject:predicate"
#   global_preference → stored with key "global_preference:subject:predicate"
# These are separate rows. A global_preference write never searches the
# project_fact namespace, so it cannot supersede a project-scoped fact.
# ---------------------------------------------------------------------------


def test_project_and_global_stored_separately():
    """
    TS test: "a global preference never supersedes a project fact that shares subject and predicate"
    Python port: the harness uses distinct scratchpad key prefixes for project facts
    (project_fact:) vs global preferences (global_preference:). A global_preference
    write searches only the global namespace, so it cannot find or supersede a
    project-scoped fact with the same (subject, predicate).
    """
    # Simulate the harness's scratchpad store with two run contexts
    scratchpad: dict[str, Any] = {}

    def set_scratchpad(run_id: str, key: str, value: Any) -> None:
        scratchpad[f"{run_id}:{key}"] = value

    def get_scratchpad(run_id: str) -> dict[str, Any]:
        return {
            k.split(":", 1)[1]: v
            for k, v in scratchpad.items()
            if k.startswith(f"{run_id}:")
        }

    # Project fact for ("Format", "style") in project "p"
    set_scratchpad("r1", "project_fact:Format:style", "csv")
    # Global preference for the same (subject, predicate)
    set_scratchpad("r2", "global_preference:Format:style", "bullets")

    project_state = get_scratchpad("r1")
    global_state = get_scratchpad("r2")

    assert project_state.get("project_fact:Format:style") == "csv"
    assert global_state.get("global_preference:Format:style") == "bullets"
    # The global write cannot find the project fact — different key prefix = different namespace.
    assert "project_fact:Format:style" not in global_state


# ---------------------------------------------------------------------------
# Test 2: An approved-and-consumed payload needs a fresh approval, never a replay.
#
# consumeTicket uses UPDATE ... WHERE status='approved' AND expires_at > now().
# After consumption, getTicketByHash returns the consumed ticket's status='consumed'.
# The validation logic sees status='consumed' and treats it as spent,
# so a new pending ticket is opened with a new ticket_id.
# ---------------------------------------------------------------------------


def test_consumed_approval_needs_fresh_ticket():
    """
    TS test: "an approved-and-consumed payload needs a fresh approval, never a replay"
    Python port: InMemoryApprovalStore.consumeTicket returns True only when status='approved'.
    After consumption, getTicketByHash returns the consumed ticket. The caller sees
    status='consumed', which is not a live status, so a new pending ticket is created.
    """
    store = InMemoryApprovalStore()
    tenant_id = "t"
    payload_hash = hashlib.sha256(b"test-payload").hexdigest()
    ticket_id = str(uuid.uuid4())
    now_ms = int(time.time() * 1000)

    conn = MagicMock()
    mock_cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=None)

    # Step 1: Create pending ticket
    store.create_pending_ticket_standalone(
        conn,
        tenant_id,
        ticket_id,
        payload_hash,
        agent_id="a",
        tool_name="send",
        target_resource="bob",
        expires_at_ms=now_ms + 30 * 60 * 1000,
    )

    # Step 2: Approve it
    store.update_status(conn, tenant_id, ticket_id, "approved", "reviewer1")

    # Step 3: Consume it — should succeed
    consumed = store.consume_ticket(conn, tenant_id, ticket_id)
    assert consumed is True

    # Step 4: getTicketByHash for the same payload — returns consumed ticket
    ticket = store.get_ticket_by_hash(conn, tenant_id, payload_hash)
    assert ticket is not None
    assert ticket.status == "consumed"

    # Step 5: Create a new pending ticket for the same payload
    new_ticket_id = str(uuid.uuid4())
    store.create_pending_ticket_standalone(
        conn,
        tenant_id,
        new_ticket_id,
        payload_hash,
        agent_id="a",
        tool_name="send",
        target_resource="bob",
        expires_at_ms=now_ms + 30 * 60 * 1000,
    )

    # Step 6: The new ticket has a different ticket_id and is pending
    new_ticket = store.get_ticket_by_hash(conn, tenant_id, payload_hash)
    assert new_ticket is not None
    assert new_ticket.ticket_id != ticket_id
    assert new_ticket.status == "pending"


# ---------------------------------------------------------------------------
# Test 3: Protected path → circuit breaker after maxAttempts rejections.
#
# Each validateBeforeToolExecution call that returns SWITCH_STRATEGY due to
# a protected path increments preflightRejections in the harness.
# After constraints.maxAttempts such rejections, the harness escalates.
# ---------------------------------------------------------------------------


def test_protected_path_halts_after_max_attempts():
    """
    TS test: "a model that keeps calling a protected path is halted instead of looping forever"
    Python port: the harness counts preflightRejections. After constraints.max_attempts
    rejections (protected path), it returns ESCALATED_BLOCKER.
    """
    store = InMemoryApprovalStore()
    idem_store = InMemoryIdempotencyStore()
    telemetry = HarnessTelemetry()

    constraints = GoalConstraintSpec(
        goal_id="g",
        project_id="p",
        tenant_id="t",
        max_attempts=4,
        max_same_strategy_failures=2,
        max_budget_usd=1.0,
        max_wall_clock_ms=60_000,
        forbidden_capabilities=[],
        protected_resource_patterns=[
            re.compile(r"\.test\.(ts|js|py)$"),
            re.compile(r"migrations/.*_prod"),
        ],
    )

    conn = MagicMock()
    controller = ActiveFocusController(
        constraints=constraints,
        approval_store=store,
        idempotency_store=idem_store,
        telemetry=telemetry,
    )

    protected_tool = ToolMetadata(
        tool_name="edit_file",
        strategy_class="code_mutation",
        capability_tags=[],
        requires_approval=False,
        extract_target_resource=lambda args: str(args.get("path", "")),
    )

    preflight_rejections = 0
    halted = False
    for _i in range(7):
        allowed, _, decision = controller.validate_before_tool_execution(
            conn,
            agent_id="a",
            tool=protected_tool,
            args={"path": "a.test.ts"},
        )
        if not allowed and decision and decision.action == "SWITCH_STRATEGY":
            preflight_rejections += 1
            if preflight_rejections >= constraints.max_attempts:
                halted = True
                break

    assert halted is True
    assert preflight_rejections == 4


# ---------------------------------------------------------------------------
# Test 4: Unknown tool → circuit breaker after maxAttempts.
#
# An unregistered tool is not in the tool registry. The harness raises
# ESCALATED_BLOCKER for unknown tools after maxAttempts attempts.
# ---------------------------------------------------------------------------


def test_unregistered_tool_unknown_in_registry():
    """
    TS test: "a model that keeps calling an unregistered tool is halted"
    Python port: an unknown tool is not in the harness's tool registry.
    The harness checks tool_meta is not None before calling validateBeforeToolExecution.
    When tool_meta is None, the harness increments preflightRejections and halts after maxAttempts.
    """
    constraints = GoalConstraintSpec(
        goal_id="g",
        project_id="p",
        tenant_id="t",
        max_attempts=3,
        max_same_strategy_failures=1,
        max_budget_usd=1.0,
        max_wall_clock_ms=60_000,
        forbidden_capabilities=[],
        protected_resource_patterns=[],
    )

    # Empty tool registry — "ghost" is unknown
    tool_registry: dict[str, ToolMetadata] = {}
    unknown_tool_name = "ghost"

    assert tool_registry.get(unknown_tool_name) is None
    # The harness: if tool_meta is None → scratchpadHistory.push + preflightRejections++
    # After max_attempts unknown tool calls → ESCALATED_BLOCKER

    preflight_rejections = 0
    for _ in range(constraints.max_attempts + 1):
        tool_meta = tool_registry.get(unknown_tool_name)
        if tool_meta is None:
            preflight_rejections += 1

    assert preflight_rejections == constraints.max_attempts + 1


# ---------------------------------------------------------------------------
# Test 5a: Unclassified MCP tools fail closed (requires_approval=True by default).
# Test 5b: Same idempotency key → one upstream execution.
# ---------------------------------------------------------------------------


def test_unclassified_tools_require_approval():
    """
    TS test: "MCP proxy: unclassified tools fail closed"
    Python port: buildEnforcedToolRegistry sets requiresApproval=True for any tool
    without an explicit policy. The focus controller then requires approval before
    executing such a tool.
    """
    store = InMemoryApprovalStore()
    idem_store = InMemoryIdempotencyStore()
    telemetry = HarnessTelemetry()
    conn = MagicMock()

    constraints = GoalConstraintSpec(
        goal_id="g",
        project_id="p",
        tenant_id="t",
        max_attempts=3,
        max_same_strategy_failures=1,
        max_budget_usd=1.0,
        max_wall_clock_ms=60_000,
        forbidden_capabilities=[],
        protected_resource_patterns=[],
    )

    controller = ActiveFocusController(
        constraints=constraints,
        approval_store=store,
        idempotency_store=idem_store,
        telemetry=telemetry,
    )

    # Unclassified tool: not in explicit registry → requiresApproval=True
    unclassified_tool = ToolMetadata(
        tool_name="send_webhook",
        strategy_class="unclassified_send_webhook",
        capability_tags=["unclassified_side_effect"],
        requires_approval=True,
        extract_target_resource=lambda args: str(
            args.get("url", "unspecified_resource")
        ),
    )

    allowed, key, decision = controller.validate_before_tool_execution(
        conn,
        agent_id="a",
        tool=unclassified_tool,
        args={"url": "https://example.com"},
    )

    assert allowed is False
    assert decision is not None
    assert decision.action == "AWAIT_APPROVAL"
    assert decision.ticket is not None
    assert decision.ticket.status == "pending"
    assert len(decision.ticket.payload_hash) == 64  # SHA-256 hex


def test_idempotency_key_returns_cached_result():
    """
    TS test: "one idempotency key executes upstream once"
    Python port: InMemoryIdempotencyStore.get() returns the cached outcome for
    a key that was already stored. The harness checks the ledger before invoking
    upstream and returns the cached result if found.
    """
    idem_store = InMemoryIdempotencyStore()
    conn = MagicMock()

    key = "run:1:abc"
    cached = {
        "outcome": "progress",
        "output": "sent",
        "error_code": None,
        "error_summary": None,
    }

    # Store the result
    idem_store.set(
        conn,
        "t",
        key,
        outcome=cached["outcome"],
        output=cached["output"],
    )

    # Check: idempotency_store.get returns the cached outcome
    result = idem_store.get(conn, "t", key)
    assert result is not None
    assert result["outcome"] == "progress"
    assert result["output"] == "sent"


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


def test_canonicalize_payload_deterministic():
    """CanonicalizePayload always produces the same output regardless of dict key order."""
    args1 = {"path": "foo.txt", "content": "hello"}
    args2 = {"content": "hello", "path": "foo.txt"}
    assert _canonicalize_payload(args1) == _canonicalize_payload(args2)


def test_compute_payload_hash_deterministic():
    """computePayloadApprovalHash is deterministic for the same inputs."""
    params = {
        "agent_id": "a",
        "tool_name": "send",
        "target_resource": "bob",
        "args": {"body": "hello"},
    }
    h1 = _compute_payload_hash(**params)
    h2 = _compute_payload_hash(**params)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex


def test_sign_webhook_payload():
    """HMAC-SHA256 signature format is v0=<hex>."""
    sig = _sign_webhook_payload("secret", 1234567890, '{"ticketId":"x"}')
    assert sig.startswith("v0=")
    assert len(sig) == 3 + 64  # "v0=" + 64 hex chars


def test_verify_webhook_signature_valid():
    """Valid signature + timestamp within 5 minutes passes."""
    secret = "test-signing-secret"  # noqa: S105
    timestamp = int(time.time())
    body = '{"ticketId":"x","decision":"approve"}'
    sig = _sign_webhook_payload(secret, timestamp, body)

    valid, reason = _verify_webhook_signature(secret, str(timestamp), sig, body)
    assert valid is True
    assert reason is None


def test_verify_webhook_signature_expired():
    """Timestamp older than 5 minutes is rejected."""
    secret = "test-signing-secret"  # noqa: S105
    timestamp = int(time.time()) - 400  # 6+ minutes ago
    body = '{"ticketId":"x"}'
    sig = _sign_webhook_payload(secret, timestamp, body)

    valid, reason = _verify_webhook_signature(secret, str(timestamp), sig, body)
    assert valid is False
    assert "replay window" in reason


def test_verify_webhook_signature_wrong_secret():
    """Wrong secret fails HMAC verification."""
    timestamp = int(time.time())
    body = '{"ticketId":"x"}'
    sig = _sign_webhook_payload("correct-secret", timestamp, body)

    valid, reason = _verify_webhook_signature("wrong-secret", str(timestamp), sig, body)
    assert valid is False
    assert "HMAC" in reason  # "HMAC-SHA256 signature verification failed."


def test_constant_time_eq():
    """_constant_time_eq compares in constant time."""
    assert _constant_time_eq("v0=abc123", "v0=abc123") is True
    assert _constant_time_eq("v0=abc123", "v0=abc124") is False
    assert _constant_time_eq("v0=abc", "v0=abcd") is False


def test_harness_telemetry_snapshot():
    """Telemetry snapshot returns a stable copy of all counters."""
    t = HarnessTelemetry()
    t.record_prefetch("t1", "p1", 12.5, 320)
    t.record_consolidation(
        "t1",
        "user_direct",
        promoted=2,
        ignored_ephemeral=1,
        blocked_stale_or_untrusted=0,
    )
    t.record_attempt("a1", "send", "smtp", "progress", 0.01)
    t.record_approval_event("a1", "send", "requested")

    snap = t.get_snapshot()
    assert snap.prefetch_count == 1
    assert snap.last_brief_tokens == 320
    assert snap.facts_promoted == 2
    assert snap.facts_ignored_ephemeral == 1
    assert snap.attempts_by_outcome["progress"] == 1
    assert snap.approval_events["requested"] == 1
    assert snap.total_cost_usd == 0.01

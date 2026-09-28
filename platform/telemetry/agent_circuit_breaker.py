#!/usr/bin/env python3
"""Agent circuit breaker: real-time loop detection at turn 3-4, not turn 30.

Implements ControlLoop protocol for seamless integration with orchestrator.
Processes spans in real-time, detects 14 fault types, marks fault_flags,
and trips early on loop patterns detected in 5-turn windows.
"""

import hashlib
import logging
from collections import deque, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Literal

from platform.eval.protocol import ControlLoop, GateDecision, LoopHealth

logger = logging.getLogger(__name__)


class CircuitBreakerTripped(Exception):
    """Raised when circuit breaker detects a fault and halts execution."""

    pass


@dataclass
class FaultMetrics:
    """Tracks fault occurrences and confidence."""

    fault_type: str
    confidence: float
    turn: int
    evidence: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class SpanSnapshot:
    """Real-time snapshot of a span for pattern analysis."""

    turn: int
    span_kind: str
    args_hash: str
    tool_name: Optional[str] = None
    status: str = "ok"
    error_message: Optional[str] = None
    token_cost: float = 0.0
    latency_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class AgentCircuitBreaker(ControlLoop):
    """
    Real-time fault detector for agent execution.

    Detects 14 fault types:
    1.  Loop pattern: repeated (span_kind, args_hash) in 5-turn window
    2.  Infinite loop: same tool call 3+ times consecutively
    3.  Token explosion: cumulative tokens > threshold in single turn
    4.  Stale retrieval: same retrieval result 2+ times in 3 turns
    5.  Delegation storm: 4+ tool calls per turn for 3+ turns
    6.  Guard rail bypass: attempt to run prohibited tools
    7.  Memory corruption: context size growth > 50% per turn
    8.  Plan thrash: goal changes 3+ times without progress
    9.  Reasoning loop: reasoning span repeated 2+ times in window
    10. Tool error spiral: 3+ consecutive tool errors
    11. Hallucination: LLM generates non-existent tool names
    12. Context exhaustion: remaining tokens < 10% threshold
    13. Rate limit backoff: exponential delays detected
    14. Dead-end paths: 5+ turns in same state machine node

    Trips at turn 3-4 when loop patterns are detected.
    Marks fault_flags on spans for post-hoc analysis.
    """

    name = "agent_circuit_breaker"

    def __init__(
        self,
        window_size: int = 5,
        loop_trip_turn: int = 4,
        max_turns: int = 30,
        max_consecutive_errors: int = 3,
        max_delegation_rate: float = 4.0,
        max_token_cost_per_turn: float = 100000.0,
        context_growth_threshold: float = 0.5,
    ):
        """Initialize circuit breaker with tuning parameters."""
        self.window_size = window_size
        self.loop_trip_turn = loop_trip_turn
        self.max_turns = max_turns
        self.max_consecutive_errors = max_consecutive_errors
        self.max_delegation_rate = max_delegation_rate
        self.max_token_cost_per_turn = max_token_cost_per_turn
        self.context_growth_threshold = context_growth_threshold

        # State tracking
        self.span_window: deque = deque(maxlen=window_size)
        self.turn_count = 0
        self.faults_detected: list[FaultMetrics] = []
        self.last_run_at: Optional[str] = None
        self.last_error: Optional[str] = None
        self.mode: Literal["off", "shadow", "enforce"] = "enforce"
        self.is_tripped = False
        self.trip_reason = ""
        self.circuit_state = "closed"  # closed, open, half-open

        # Pattern tracking
        self.tool_call_counts = defaultdict(int)
        self.error_counts = defaultdict(int)
        self.context_sizes = deque(maxlen=10)
        self.state_node_history = deque(maxlen=window_size)
        self.goal_changes = 0
        self.last_goal = None

    def on_span(self, span: dict) -> None:
        """
        Real-time span processor. Called for every span in the trace.

        Span structure:
        {
            "turn": int,
            "span_kind": str (e.g., "tool_call", "llm_reasoning", "retrieval"),
            "args": dict (for hashing),
            "tool_name": str (optional),
            "status": str ("ok", "error"),
            "error": str (optional),
            "token_cost": float,
            "latency_ms": float,
            "context_size": int (optional),
            "output": str (optional, for retrieval),
        }
        """
        self.turn_count = span.get("turn", self.turn_count)

        # Create snapshot for pattern analysis
        args_hash = self._hash_args(span.get("args", {}))
        snapshot = SpanSnapshot(
            turn=self.turn_count,
            span_kind=span.get("span_kind", "unknown"),
            args_hash=args_hash,
            tool_name=span.get("tool_name"),
            status=span.get("status", "ok"),
            error_message=span.get("error"),
            token_cost=span.get("token_cost", 0.0),
            latency_ms=span.get("latency_ms", 0.0),
        )

        self.span_window.append(snapshot)

        # Track context size
        if "context_size" in span:
            self.context_sizes.append(span["context_size"])

        # Run all fault detectors
        self._detect_loop_pattern()
        self._detect_infinite_loop()
        self._detect_token_explosion()
        self._detect_stale_retrieval()
        self._detect_delegation_storm()
        self._detect_guard_rail_bypass(span)
        self._detect_memory_corruption()
        self._detect_plan_thrash(span)
        self._detect_reasoning_loop()
        self._detect_tool_error_spiral()
        self._detect_hallucination(span)
        self._detect_context_exhaustion(span)
        self._detect_rate_limit_backoff()
        self._detect_dead_end_paths(span)

        # Mark fault flags on span
        if self.faults_detected:
            fault_flags = [f.fault_type for f in self.faults_detected]
            span["fault_flags"] = fault_flags

        # Trip if loop detected at turn 3-4
        if self.turn_count <= self.loop_trip_turn and self._should_trip():
            self._trip_circuit()

    def _analyze_messages(self, messages: list) -> None:
        """
        Analyze message history to extract spans and detect patterns.
        Converts ToolMessages to span-like structures.
        """
        # Clear window for fresh analysis
        self.span_window.clear()

        # Extract tool calls from recent messages
        for _i, msg in enumerate(messages[-self.window_size :]):
            msg_type = type(msg).__name__

            if msg_type == "ToolMessage":
                # Tool execution
                tool_name = msg.name if hasattr(msg, "name") else "unknown"
                is_error = (
                    "error" in msg.content.lower() or "failed" in msg.content.lower()
                )

                snapshot = SpanSnapshot(
                    turn=self.turn_count,
                    span_kind="tool_call",
                    args_hash=self._hash_args({"tool": tool_name}),
                    tool_name=tool_name,
                    status="error" if is_error else "ok",
                    error_message=msg.content if is_error else None,
                )
                self.span_window.append(snapshot)

            elif msg_type == "AIMessage":
                # LLM reasoning
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tool_call in msg.tool_calls:
                        snapshot = SpanSnapshot(
                            turn=self.turn_count,
                            span_kind="llm_reasoning",
                            args_hash=self._hash_args(tool_call.get("args", {})),
                            tool_name=tool_call.get("name", "unknown"),
                        )
                        self.span_window.append(snapshot)

        # Run fault detectors
        self._detect_loop_pattern()
        self._detect_infinite_loop()
        self._detect_tool_error_spiral()
        self._detect_reasoning_loop()

    def _hash_args(self, args: dict) -> str:
        """Hash arguments for pattern matching."""
        try:
            args_str = str(sorted(args.items()))
            return hashlib.sha256(args_str.encode()).hexdigest()[:8]
        except Exception:
            return "unknown"

    def _detect_loop_pattern(self) -> None:
        """Detect: repeated (span_kind, args_hash) in 5-turn window."""
        if len(self.span_window) < 3:
            return

        # Check for repeated patterns in last N spans
        patterns = defaultdict(int)
        for span in self.span_window:
            key = (span.span_kind, span.args_hash)
            patterns[key] += 1

        # If any pattern repeats 2+ times, it's a loop
        for (kind, args_hash), count in patterns.items():
            if count >= 2:
                self.faults_detected.append(
                    FaultMetrics(
                        fault_type="loop_pattern",
                        confidence=min(0.9, count * 0.3),
                        turn=self.turn_count,
                        evidence=f"Repeated ({kind}, {args_hash}) {count} times in window",
                    )
                )

    def _detect_infinite_loop(self) -> None:
        """Detect: same tool call 3+ times consecutively."""
        if len(self.span_window) < 3:
            return

        last_3 = list(self.span_window)[-3:]
        if all(s.tool_name and s.tool_name == last_3[0].tool_name for s in last_3):
            self.faults_detected.append(
                FaultMetrics(
                    fault_type="infinite_loop",
                    confidence=0.95,
                    turn=self.turn_count,
                    evidence=f"Same tool ({last_3[0].tool_name}) called 3 times consecutively",
                )
            )

    def _detect_token_explosion(self) -> None:
        """Detect: cumulative tokens > threshold in single turn."""
        if not self.span_window:
            return

        turn_tokens = sum(
            s.token_cost for s in self.span_window if s.turn == self.turn_count
        )
        if turn_tokens > self.max_token_cost_per_turn:
            self.faults_detected.append(
                FaultMetrics(
                    fault_type="token_explosion",
                    confidence=0.8,
                    turn=self.turn_count,
                    evidence=f"Turn {self.turn_count}: {turn_tokens} tokens > threshold {self.max_token_cost_per_turn}",
                )
            )

    def _detect_stale_retrieval(self) -> None:
        """Detect: same retrieval result 2+ times in 3 turns."""
        retrieval_spans = [s for s in self.span_window if s.span_kind == "retrieval"]

        if len(retrieval_spans) < 2:
            return

        # Check if last 2 retrievals have same output (would need to pass output in span)
        # For now, use args_hash as proxy for "same query"
        last_args_hashes = [s.args_hash for s in retrieval_spans[-3:]]
        if len(last_args_hashes) >= 2 and last_args_hashes[0] == last_args_hashes[1]:
            self.faults_detected.append(
                FaultMetrics(
                    fault_type="stale_retrieval",
                    confidence=0.75,
                    turn=self.turn_count,
                    evidence="Same retrieval query repeated in last 3 turns",
                )
            )

    def _detect_delegation_storm(self) -> None:
        """Detect: 4+ tool calls per turn for 3+ consecutive turns."""
        # Count tool calls per turn in the window
        tool_calls_per_turn = defaultdict(int)
        for span in self.span_window:
            if span.span_kind == "tool_call":
                tool_calls_per_turn[span.turn] += 1

        # Check for sustained high delegation rate
        if len(tool_calls_per_turn) >= 3:
            recent_turns = sorted(tool_calls_per_turn.keys())[-3:]
            rates = [tool_calls_per_turn[t] for t in recent_turns]
            if all(r >= self.max_delegation_rate for r in rates):
                self.faults_detected.append(
                    FaultMetrics(
                        fault_type="delegation_storm",
                        confidence=0.85,
                        turn=self.turn_count,
                        evidence=f"Sustained high delegation rate: {rates} tool calls/turn",
                    )
                )

    def _detect_guard_rail_bypass(self, span: dict) -> None:
        """Detect: attempt to run prohibited tools."""
        prohibited_tools = {
            "execute_sql",
            "delete_file",
            "rm_rf",
            "drop_database",
            "shell_exec_root",
            "git_force_push",
        }

        tool_name = span.get("tool_name", "")
        if tool_name in prohibited_tools:
            self.faults_detected.append(
                FaultMetrics(
                    fault_type="guard_rail_bypass",
                    confidence=0.99,
                    turn=self.turn_count,
                    evidence=f"Prohibited tool attempted: {tool_name}",
                )
            )

    def _detect_memory_corruption(self) -> None:
        """Detect: context size growth > 50% per turn."""
        if len(self.context_sizes) < 2:
            return

        prev_size = self.context_sizes[-2]
        curr_size = self.context_sizes[-1]

        if prev_size > 0:
            growth_rate = (curr_size - prev_size) / prev_size
            if growth_rate > self.context_growth_threshold:
                self.faults_detected.append(
                    FaultMetrics(
                        fault_type="memory_corruption",
                        confidence=0.8,
                        turn=self.turn_count,
                        evidence=f"Context growth {growth_rate * 100:.1f}% > {self.context_growth_threshold * 100:.1f}% threshold",
                    )
                )

    def _detect_plan_thrash(self, span: dict) -> None:
        """Detect: goal changes 3+ times without progress."""
        goal = span.get("goal", self.last_goal)
        if goal and goal != self.last_goal:
            self.goal_changes += 1
            self.last_goal = goal

            if self.goal_changes >= 3:
                self.faults_detected.append(
                    FaultMetrics(
                        fault_type="plan_thrash",
                        confidence=0.8,
                        turn=self.turn_count,
                        evidence=f"Goal changed {self.goal_changes} times: possible thrashing",
                    )
                )

    def _detect_reasoning_loop(self) -> None:
        """Detect: reasoning span repeated 2+ times in window."""
        reasoning_spans = [
            s for s in self.span_window if s.span_kind == "llm_reasoning"
        ]

        if len(reasoning_spans) < 2:
            return

        reasoning_hashes = [s.args_hash for s in reasoning_spans]
        if len(reasoning_hashes) >= 2 and reasoning_hashes[-1] == reasoning_hashes[-2]:
            self.faults_detected.append(
                FaultMetrics(
                    fault_type="reasoning_loop",
                    confidence=0.8,
                    turn=self.turn_count,
                    evidence="Same reasoning span repeated 2+ times",
                )
            )

    def _detect_tool_error_spiral(self) -> None:
        """Detect: 3+ consecutive tool errors."""
        if len(self.span_window) < 3:
            return

        last_3 = list(self.span_window)[-3:]
        error_count = sum(1 for s in last_3 if s.status == "error")

        if error_count >= self.max_consecutive_errors:
            self.faults_detected.append(
                FaultMetrics(
                    fault_type="tool_error_spiral",
                    confidence=0.9,
                    turn=self.turn_count,
                    evidence=f"{error_count} consecutive tool errors in last {len(last_3)} spans",
                )
            )

    def _detect_hallucination(self, span: dict) -> None:
        """Detect: LLM generates non-existent tool names."""
        tool_name = span.get("tool_name", "")
        valid_tools = {
            "retrieval",
            "search",
            "calculator",
            "file_read",
            "file_write",
            "git_status",
            "git_commit",
            "bash_execute",
            "http_request",
        }

        if span.get("span_kind") == "tool_call" and tool_name not in valid_tools:
            self.faults_detected.append(
                FaultMetrics(
                    fault_type="hallucination",
                    confidence=0.85,
                    turn=self.turn_count,
                    evidence=f"LLM attempted non-existent tool: {tool_name}",
                )
            )

    def _detect_context_exhaustion(self, span: dict) -> None:
        """Detect: remaining tokens < 10% threshold."""
        remaining_tokens = span.get("remaining_tokens")
        if remaining_tokens is not None and remaining_tokens < 1000:
            self.faults_detected.append(
                FaultMetrics(
                    fault_type="context_exhaustion",
                    confidence=0.9,
                    turn=self.turn_count,
                    evidence=f"Remaining tokens: {remaining_tokens} < 1000 threshold",
                )
            )

    def _detect_rate_limit_backoff(self) -> None:
        """Detect: exponential delays detected in latencies."""
        if len(self.span_window) < 3:
            return

        latencies = [s.latency_ms for s in self.span_window if s.latency_ms > 0]
        if len(latencies) >= 3:
            # Check if latencies are increasing exponentially
            ratios = [
                latencies[i + 1] / latencies[i]
                for i in range(len(latencies) - 1)
                if latencies[i] > 0
            ]

            if all(r > 1.5 for r in ratios[-2:]):
                self.faults_detected.append(
                    FaultMetrics(
                        fault_type="rate_limit_backoff",
                        confidence=0.75,
                        turn=self.turn_count,
                        evidence=f"Exponential latency growth detected: {ratios}",
                    )
                )

    def _detect_dead_end_paths(self, span: dict) -> None:
        """Detect: 5+ turns in same state machine node."""
        state_node = span.get("state_node")
        if state_node:
            self.state_node_history.append(state_node)

            if len(self.state_node_history) >= 5:
                recent_nodes = list(self.state_node_history)[-5:]
                if all(n == recent_nodes[0] for n in recent_nodes):
                    self.faults_detected.append(
                        FaultMetrics(
                            fault_type="dead_end_paths",
                            confidence=0.85,
                            turn=self.turn_count,
                            evidence=f"Stuck in state node '{recent_nodes[0]}' for 5+ turns",
                        )
                    )

    def _should_trip(self) -> bool:
        """Determine if circuit should trip based on faults detected."""
        if not self.faults_detected:
            return False

        # Sum confidence of all faults
        total_confidence = sum(f.confidence for f in self.faults_detected)
        avg_confidence = total_confidence / len(self.faults_detected)

        # Trip if average confidence > 0.7 or any single fault > 0.9
        should_trip = avg_confidence > 0.7 or any(
            f.confidence > 0.9 for f in self.faults_detected
        )

        return should_trip

    def _trip_circuit(self) -> None:
        """Open the circuit and halt execution."""
        self.is_tripped = True
        self.circuit_state = "open"

        fault_summary = "; ".join(
            [
                f"{f.fault_type} (confidence={f.confidence:.2f})"
                for f in self.faults_detected
            ]
        )

        self.trip_reason = (
            f"Circuit breaker tripped at turn {self.turn_count}: {fault_summary}"
        )
        logger.warning(self.trip_reason)

    def pre_llm(self, state: dict) -> GateDecision:
        """
        Called before LLM invocation.
        Analyzes state messages to detect faults and halt if necessary.
        Converts messages to span-like structures for pattern detection.
        """
        self.last_run_at = datetime.now().isoformat()

        if self.mode == "off":
            return GateDecision(action="allow")

        if self.is_tripped:
            decision_action = "halt" if self.mode == "enforce" else "shadow"
            return GateDecision(
                action=decision_action,
                evidence=self.trip_reason,
                confidence=0.95,
            )

        # Analyze current state messages to detect patterns
        messages = state.get("messages", [])
        self.turn_count = len([m for m in messages if type(m).__name__ == "AIMessage"])

        # Convert messages to span-like structures for analysis
        self._analyze_messages(messages)

        # Trip if loop detected at turn 3-4
        if self.turn_count <= self.loop_trip_turn and self._should_trip():
            self._trip_circuit()
            decision_action = "halt" if self.mode == "enforce" else "shadow"
            return GateDecision(
                action=decision_action,
                evidence=self.trip_reason,
                confidence=0.95,
            )

        return GateDecision(action="allow")

    def post_verdict(self, state: dict, verdict: dict) -> None:
        """Called after verdict. Record telemetry for analysis."""
        # In production, save fault metrics to observability backend
        if self.faults_detected:
            logger.info(
                f"[CircuitBreaker] Verdict at turn {self.turn_count}: "
                f"{len(self.faults_detected)} faults detected, "
                f"circuit_state={self.circuit_state}"
            )

    def periodic(self) -> None:
        """Periodic maintenance (no-op for real-time detector)."""
        pass

    def health(self) -> LoopHealth:
        """Report circuit breaker health."""
        health_msg = (
            f"circuit_state={self.circuit_state}, "
            f"turns={self.turn_count}, "
            f"faults={len(self.faults_detected)}"
        )

        return LoopHealth(
            name=self.name,
            mode=self.mode,
            last_run_at=self.last_run_at or "never",
            last_error=self.last_error or health_msg,
            is_healthy=not self.is_tripped,
        )

    def reset(self) -> None:
        """Reset circuit breaker for next execution."""
        self.is_tripped = False
        self.circuit_state = "closed"
        self.trip_reason = ""
        self.span_window.clear()
        self.faults_detected.clear()
        self.turn_count = 0
        self.tool_call_counts.clear()
        self.error_counts.clear()
        self.context_sizes.clear()
        self.state_node_history.clear()
        self.goal_changes = 0
        self.last_goal = None

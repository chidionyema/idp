#!/usr/bin/env python3
"""Payload validation: format, semantic, and category validation.

Validates payloads before catalog entry. Tracks mutation history and state.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class AttackClass(str, Enum):
    """Valid attack classes for red team payloads."""

    PROMPT_INJECTION = "prompt_injection"
    JAILBREAK = "jailbreak"
    SQL_INJECTION = "sql_injection"
    SHELL_INJECTION = "shell_injection"
    PATH_TRAVERSAL = "path_traversal"
    XSS = "xss"
    COMMAND_INJECTION = "command_injection"
    BUFFER_OVERFLOW = "buffer_overflow"
    ARGUMENT_INJECTION = "argument_injection"
    GIT_COMMAND_INJECTION = "git_command_injection"


class SeverityLevel(str, Enum):
    """Valid severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class MutationRecord:
    """History of a payload mutation."""

    mutation_index: int
    mutator_fn: str
    timestamp: datetime
    parent_id: str
    parent_source: str


@dataclass
class ValidationResult:
    """Result of payload validation."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    payload_id: Optional[str] = None
    validated_at: datetime = field(default_factory=datetime.now)

    def add_error(self, msg: str) -> None:
        """Add an error to validation results."""
        self.errors.append(msg)
        self.is_valid = False

    def add_warning(self, msg: str) -> None:
        """Add a warning to validation results."""
        self.warnings.append(msg)


class PayloadValidator:
    """Validates payloads for catalog entry."""

    # Valid attack classes
    VALID_ATTACK_CLASSES = {e.value for e in AttackClass}

    # Valid severity levels
    VALID_SEVERITY_LEVELS = {e.value for e in SeverityLevel}

    # Valid tool targets
    VALID_TOOL_TARGETS = {
        "shell_exec",
        "file_write",
        "git_command",
        "sql_query",
        "http_request",
        "javascript",
        "file_read",
        "process_spawn",
    }

    # Valid payload sources
    VALID_SOURCES = {"generated", "community", "mutated", "cached"}

    @staticmethod
    def validate(payload) -> ValidationResult:
        """Validate a payload for catalog entry.

        Args:
            payload: Payload object to validate

        Returns:
            ValidationResult with is_valid, errors, warnings
        """
        result = ValidationResult(is_valid=True)

        # Validate payload ID
        if not payload.id:
            result.add_error("Payload ID is required and cannot be empty")
        elif not isinstance(payload.id, str):
            result.add_error(f"Payload ID must be string, got {type(payload.id)}")
        elif len(payload.id) == 0 or len(payload.id) > 128:
            result.add_error(
                f"Payload ID length must be 1-128 chars, got {len(payload.id)}"
            )

        # Validate content
        if not payload.content:
            result.add_error("Payload content is required and cannot be empty")
        elif not isinstance(payload.content, str):
            result.add_error(
                f"Payload content must be string, got {type(payload.content)}"
            )
        elif len(payload.content) > 65536:
            result.add_warning(
                f"Payload content is large ({len(payload.content)} chars)"
            )

        # Validate attack class
        if not payload.attack_class:
            result.add_error("Attack class is required")
        elif payload.attack_class not in PayloadValidator.VALID_ATTACK_CLASSES:
            result.add_error(
                f"Invalid attack class '{payload.attack_class}'. "
                f"Must be one of: {', '.join(sorted(PayloadValidator.VALID_ATTACK_CLASSES))}"
            )

        # Validate severity
        if not payload.severity:
            result.add_error("Severity level is required")
        elif payload.severity not in PayloadValidator.VALID_SEVERITY_LEVELS:
            result.add_error(
                f"Invalid severity '{payload.severity}'. "
                f"Must be one of: {', '.join(sorted(PayloadValidator.VALID_SEVERITY_LEVELS))}"
            )

        # Validate source
        if hasattr(payload, "source"):
            if payload.source not in PayloadValidator.VALID_SOURCES:
                result.add_error(
                    f"Invalid source '{payload.source}'. "
                    f"Must be one of: {', '.join(sorted(PayloadValidator.VALID_SOURCES))}"
                )

        # Validate tool target
        if hasattr(payload, "tool_target"):
            if (
                payload.tool_target
                and payload.tool_target not in PayloadValidator.VALID_TOOL_TARGETS
            ):
                result.add_warning(
                    f"Tool target '{payload.tool_target}' not recognized. "
                    f"Common targets: {', '.join(sorted(PayloadValidator.VALID_TOOL_TARGETS))}"
                )

        # Semantic validation: attack class and tool target alignment
        if payload.attack_class and hasattr(payload, "tool_target"):
            PayloadValidator._validate_attack_tool_alignment(payload, result)

        # Validate tags if present
        if hasattr(payload, "tags"):
            if payload.tags is not None:
                if not isinstance(payload.tags, (list, set, tuple)):
                    result.add_error(
                        f"Payload tags must be list/set/tuple, got {type(payload.tags)}"
                    )
                elif not all(isinstance(tag, str) for tag in payload.tags):
                    result.add_error("All tags must be strings")
                elif any(len(tag) > 64 for tag in payload.tags):
                    result.add_warning("Some tags exceed 64 characters")

        # Validate timestamps if present
        if hasattr(payload, "created_at") and payload.created_at:
            if not isinstance(payload.created_at, datetime):
                result.add_error(
                    f"created_at must be datetime, got {type(payload.created_at)}"
                )

        if hasattr(payload, "last_triggered_at") and payload.last_triggered_at:
            if not isinstance(payload.last_triggered_at, datetime):
                result.add_error(
                    f"last_triggered_at must be datetime, got {type(payload.last_triggered_at)}"
                )

        # Validate detection count
        if hasattr(payload, "detections_triggered"):
            if not isinstance(payload.detections_triggered, int):
                result.add_error(
                    f"detections_triggered must be int, got {type(payload.detections_triggered)}"
                )
            elif payload.detections_triggered < 0:
                result.add_error("detections_triggered cannot be negative")

        result.payload_id = payload.id
        return result

    @staticmethod
    def validate_batch(payloads: list) -> dict:
        """Validate a batch of payloads.

        Args:
            payloads: List of Payload objects

        Returns:
            Dict with valid_count, invalid_count, warning_count, results list
        """
        results = []
        valid_count = 0
        invalid_count = 0
        warning_count = 0

        for payload in payloads:
            result = PayloadValidator.validate(payload)
            results.append(result)

            if result.is_valid:
                valid_count += 1
            else:
                invalid_count += 1

            if result.warnings:
                warning_count += 1

        return {
            "valid_count": valid_count,
            "invalid_count": invalid_count,
            "warning_count": warning_count,
            "results": results,
        }

    @staticmethod
    def _validate_attack_tool_alignment(payload, result: ValidationResult) -> None:
        """Validate that attack class and tool target make sense together."""
        attack_class = payload.attack_class
        tool_target = payload.tool_target

        alignment = {
            AttackClass.SHELL_INJECTION.value: {
                "shell_exec",
                "process_spawn",
                "file_write",
            },
            AttackClass.COMMAND_INJECTION.value: {
                "shell_exec",
                "process_spawn",
                "file_write",
            },
            AttackClass.SQL_INJECTION.value: {"sql_query"},
            AttackClass.XSS.value: {"http_request", "javascript"},
            AttackClass.PATH_TRAVERSAL.value: {"file_read", "file_write"},
            AttackClass.BUFFER_OVERFLOW.value: {"process_spawn", "shell_exec"},
            AttackClass.JAILBREAK.value: {"http_request"},
            AttackClass.PROMPT_INJECTION.value: {"http_request"},
            AttackClass.ARGUMENT_INJECTION.value: {"process_spawn", "shell_exec"},
            AttackClass.GIT_COMMAND_INJECTION.value: {"git_command", "process_spawn"},
        }

        expected_targets = alignment.get(attack_class, set())
        if expected_targets and tool_target not in expected_targets:
            result.add_warning(
                f"Attack class '{attack_class}' typically targets {expected_targets}, "
                f"but payload targets '{tool_target}'"
            )


class MutationHistory:
    """Tracks mutation lineage of payloads."""

    def __init__(self, payload_id: str, source: str):
        """Initialize mutation history for a payload.

        Args:
            payload_id: ID of the payload
            source: Original source ('generated' | 'community' | 'mutated')
        """
        self.payload_id = payload_id
        self.source = source
        self.mutations: list[MutationRecord] = []
        self.created_at = datetime.now()

    def record_mutation(
        self, mutator_fn: str, parent_id: str, parent_source: str
    ) -> None:
        """Record a mutation.

        Args:
            mutator_fn: Name of mutation function
            parent_id: ID of parent payload
            parent_source: Source of parent payload
        """
        mutation = MutationRecord(
            mutation_index=len(self.mutations),
            mutator_fn=mutator_fn,
            timestamp=datetime.now(),
            parent_id=parent_id,
            parent_source=parent_source,
        )
        self.mutations.append(mutation)

    def get_lineage(self) -> list[dict]:
        """Get full mutation lineage.

        Returns:
            List of dicts describing each mutation step
        """
        return [
            {
                "index": m.mutation_index,
                "mutator": m.mutator_fn,
                "timestamp": m.timestamp.isoformat(),
                "parent_id": m.parent_id,
                "parent_source": m.parent_source,
            }
            for m in self.mutations
        ]

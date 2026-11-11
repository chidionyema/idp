"""Canonical CLAIM grammar shared by the writer, merge gate and context broker.

A claim is no longer an untyped string. It carries the instruction it executes and the digest
of the complete plan it references. The live heartbeat and path fence remain on the same line,
so the claim stays one GitHub comment and one source of record.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import re
from collections.abc import Iterable

INSTRUCTION_RE = re.compile(r"^INS-[A-Za-z0-9-]{3,120}$")
PLAN_RE = re.compile(r"^[0-9a-fA-F]{64}$")
KNOWN_FIELDS = frozenset(
    {"agent", "model", "instruction", "plan", "paths", "heartbeat"}
)


class ClaimContractError(ValueError):
    """A CLAIM line that cannot be interpreted without guessing."""


@dataclasses.dataclass(frozen=True)
class ClaimLine:
    agent: str
    instruction: str
    plan: str
    paths: tuple[str, ...]
    heartbeat: dt.datetime
    model: str = ""
    raw: str = ""


def _timestamp(value: str) -> dt.datetime:
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ClaimContractError(f"heartbeat {value!r} is not a UTC ISO time") from exc
    if parsed.tzinfo is None:
        raise ClaimContractError("heartbeat must include a UTC offset")
    return parsed.astimezone(dt.timezone.utc)


def parse_claim_line(line: str) -> ClaimLine:
    """Parse one complete `CLAIM ...` line or refuse every ambiguous variation."""
    raw = line.strip()
    if not raw.startswith("CLAIM "):
        raise ClaimContractError("claim line must start with `CLAIM `")
    fields: dict[str, str] = {}
    for token in raw.split()[1:]:
        if "=" not in token:
            raise ClaimContractError(f"token {token!r} is not key=value")
        key, value = token.split("=", 1)
        if key not in KNOWN_FIELDS:
            raise ClaimContractError(f"unknown field {key!r}")
        if key in fields:
            raise ClaimContractError(f"duplicate field {key!r}")
        if not value:
            raise ClaimContractError(f"field {key!r} is empty")
        fields[key] = value

    for required in ("agent", "instruction", "plan", "paths", "heartbeat"):
        if required not in fields:
            raise ClaimContractError(f"claim is missing required field {required!r}")
    if not INSTRUCTION_RE.fullmatch(fields["instruction"]):
        raise ClaimContractError(
            f"instruction {fields['instruction']!r} is not an INS-* instruction id"
        )
    if not PLAN_RE.fullmatch(fields["plan"]):
        raise ClaimContractError("plan must be a 64-character SHA-256 hex digest")
    paths = tuple(value for value in fields["paths"].split(",") if value)
    if not paths:
        raise ClaimContractError("paths must name at least one file or glob")
    return ClaimLine(
        agent=fields["agent"],
        instruction=fields["instruction"],
        plan=fields["plan"].lower(),
        paths=paths,
        heartbeat=_timestamp(fields["heartbeat"]),
        model=fields.get("model", ""),
        raw=raw,
    )


def parse_claim_lines(text: str) -> list[ClaimLine]:
    """Parse every CLAIM line; a malformed CLAIM is an error, not silently skipped."""
    return [
        parse_claim_line(line)
        for line in (text or "").splitlines()
        if line.strip().startswith("CLAIM ")
    ]


def format_claim(
    *,
    agent: str,
    instruction: str,
    plan: str,
    paths: Iterable[str],
    heartbeat: str,
    model: str = "",
) -> str:
    """Render the canonical field order and validate it by parsing the result."""
    ordered = [
        ("agent", agent),
        ("instruction", instruction),
        ("plan", plan),
        ("model", model),
        ("paths", ",".join(value for value in paths if value)),
        ("heartbeat", heartbeat),
    ]
    rendered = "CLAIM " + " ".join(f"{key}={value}" for key, value in ordered if value)
    parse_claim_line(rendered)
    return rendered

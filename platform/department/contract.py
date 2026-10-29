"""The department contract: one admission function over schema/department/v1 (idp#7395, charter M1).

WHY. The Media Department charter v1 (2026-10-28) makes the Media Department the first of a family
of autonomous estate departments, and names the earlier failure it must not repeat: the research
engine produced reports that then waited on the founder (platform/research-engine/objective-adapter.py,
"Continue / Park"). A department that is allowed to advance on its own needs a contract that refuses
the moves it may not make, before any runtime exists to make them. This module is that contract,
and nothing more: no scheduler, no bus, no store. M2 puts it behind the existing Temporal workers and
JetStream; it does not get a second one.

WHAT IT DOES. `admit(record, writer, ledger, context)` returns a Verdict. A record is admitted only
when all of these hold, checked in this order, first refusal wins (deterministic):

    schema_invalid               the record fails schema/department/v1/<kind>.schema.json
    missing_source_ref           source_ref / source_revision empty, or evidence required and absent
    unauthorized_write           unknown writer, a role it does not hold, a role that may not write
                                 this state, or a write into another department
    duplicate_idempotency_key    (objective_id, action_kind, input_revision) already admitted -- checked
                                 before the transition, so a replayed write reads as a replay
    illegal_transition           not in TRANSITIONS, or BLOCKED resuming to a state it was not blocked from
    missing_authorization        PROPOSED -> APPROVED without an `allow` from an authorization door
    self_certification           the evaluator or the reviewing writer is the prototype's recorded author
    missing_independent_evidence VERIFYING -> OPERATING without an observation by someone other than the writer
    budget_overflow              spend over the record cap, the objective's cap, or the per-day cap
    stale_provenance             source_revision is not the current revision, or the record has expired

Time and source revisions come in through `context`; nothing here reads a clock or the network, so
the same inputs give the same verdict on every machine (the same law as the director, ADR 0037 L3).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "schema" / "department" / "v1"
SCHEMA_VERSION = "department.v1"
KINDS = (
    "objective",
    "opportunity",
    "experiment",
    "artifact",
    "review",
    "decision",
    "outcome",
    "event",
)

STATES = (
    "NEW",
    "TRIAGED",
    "RESEARCHING",
    "PROTOTYPING",
    "EVALUATING",
    "PROPOSED",
    "APPROVED",
    "SHIPPING",
    "VERIFYING",
    "OPERATING",
    "LEARNING",
    "BLOCKED",
    "PARKED",
    "REJECTED",
)

# The legal transitions (charter §4). Everything absent is illegal -- in particular
# RESEARCHING -> SHIPPING, any skip past EVALUATING, and anything out of REJECTED (terminal).
# BLOCKED may also return to the state it was blocked from; that edge is resolved from the ledger.
TRANSITIONS: dict[str | None, frozenset[str]] = {
    None: frozenset({"NEW"}),
    "NEW": frozenset({"TRIAGED", "PARKED", "REJECTED"}),
    "TRIAGED": frozenset({"RESEARCHING", "BLOCKED", "PARKED", "REJECTED"}),
    "RESEARCHING": frozenset({"PROTOTYPING", "BLOCKED", "PARKED", "REJECTED"}),
    "PROTOTYPING": frozenset({"EVALUATING", "BLOCKED", "PARKED", "REJECTED"}),
    "EVALUATING": frozenset({"PROPOSED", "PROTOTYPING", "BLOCKED", "REJECTED"}),
    "PROPOSED": frozenset({"APPROVED", "PARKED", "REJECTED"}),
    "APPROVED": frozenset({"SHIPPING", "BLOCKED"}),
    "SHIPPING": frozenset({"VERIFYING", "BLOCKED"}),
    "VERIFYING": frozenset({"OPERATING", "BLOCKED"}),
    "OPERATING": frozenset({"LEARNING"}),
    "LEARNING": frozenset({"TRIAGED", "PARKED"}),
    "BLOCKED": frozenset({"PARKED", "REJECTED"}),
    "PARKED": frozenset({"TRIAGED", "REJECTED"}),
    "REJECTED": frozenset(),
}

# Nullable envelope fields made non-null by the state that needs them (charter §4: "validated at
# the relevant transition").
TRANSITION_REQUIRES: dict[str, tuple[str, ...]] = {
    "EVALUATING": ("artifact_uri", "artifact_sha256"),
    "PROPOSED": ("evaluator_id", "verdict", "artifact_uri", "artifact_sha256"),
    "APPROVED": ("policy_decision",),
    "OPERATING": ("evaluator_id", "verdict"),
}
EVIDENCE_REQUIRED = frozenset(
    {"EVALUATING", "PROPOSED", "APPROVED", "VERIFYING", "OPERATING", "LEARNING"}
)

# The department state each maps onto in the master epic's work_item (§12, EPIC-060), so that when
# work_item lands this family joins it by run_id instead of becoming a second action record.
WORK_ITEM_STATE = {
    "NEW": "proposed",
    "TRIAGED": "queued",
    "RESEARCHING": "running",
    "PROTOTYPING": "running",
    "EVALUATING": "gate",
    "PROPOSED": "gate",
    "APPROVED": "queued",
    "SHIPPING": "running",
    "VERIFYING": "gate",
    "OPERATING": "landed",
    "LEARNING": "landed",
    "BLOCKED": "blocked",
    "PARKED": "blocked",
    "REJECTED": "refused",
}


@dataclass(frozen=True)
class Verdict:
    admitted: bool
    code: str
    reason: str


@dataclass
class Ledger:
    """The admitted records, in order. In-memory for M1; M2 backs it with the existing JetStream
    stream, so it is an interface here, not a store."""

    records: list[dict] = field(default_factory=list)
    writers: list[str] = field(default_factory=list)
    keys: set[tuple[str, str, str]] = field(default_factory=set)

    def history(self, run_id: str) -> list[dict]:
        return [r for r in self.records if r["run_id"] == run_id]

    def objective_spend(self, objective_id: str) -> float:
        return sum(
            r["spend_usd"] for r in self.records if r["objective_id"] == objective_id
        )

    def day_spend(self, department_id: str, day: str) -> float:
        return sum(
            r["spend_usd"]
            for r in self.records
            if r["department_id"] == department_id and r["created_at"][:10] == day
        )

    def objective_cap(self, objective_id: str) -> float | None:
        for r in self.records:
            if r["kind"] == "objective" and r["objective_id"] == objective_id:
                return r["budget_cap_usd"]
        return None

    def author_of(self, run_id: str, state: str) -> str | None:
        """Who the ledger says wrote the run's last record in `state` -- never the record's own claim."""
        found = None
        for r, w in zip(self.records, self.writers, strict=True):
            if r["run_id"] == run_id and r["state"] == state:
                found = w
        return found

    def append(self, record: dict, writer: str) -> None:
        self.records.append(record)
        self.writers.append(writer)
        self.keys.add(idempotency_key(record))


@dataclass(frozen=True)
class Context:
    """What the caller observed, passed in so admission stays a pure function."""

    now: datetime
    current_revisions: dict[str, str]


def idempotency_key(record: dict) -> tuple[str, str, str]:
    """(objective_id, action_kind, input_revision), charter §4. action_kind is the record's run,
    kind and target state: the same action on the same input revision is the same action."""
    action_kind = f"{record['run_id']}:{record['kind']}:{record['state']}"
    return (record["objective_id"], action_kind, record["source_revision"])


def load_config(path: Path) -> dict:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    for role, spec in config["roles"].items():
        unknown = set(spec["states"]) - set(STATES)
        if unknown:
            raise ValueError(f"role {role} names unknown states {sorted(unknown)}")
    return config


def _validators() -> dict[str, Draft202012Validator]:
    resources = []
    for path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        resources.append((doc["$id"], Resource.from_contents(doc)))
    registry = Registry().with_resources(resources)
    out = {}
    for kind in KINDS:
        doc = json.loads(
            (SCHEMA_DIR / f"{kind}.schema.json").read_text(encoding="utf-8")
        )
        out[kind] = Draft202012Validator(
            doc, registry=registry, format_checker=FormatChecker()
        )
    return out


VALIDATORS = _validators()


def _refuse(code: str, reason: str) -> Verdict:
    return Verdict(False, code, reason)


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _prior_state(ledger: Ledger, run_id: str) -> tuple[str | None, str | None]:
    """The run's current state, and for a BLOCKED run the state it was blocked from."""
    states = [r["state"] for r in ledger.history(run_id)]
    if not states:
        return None, None
    blocked_from = None
    if states[-1] == "BLOCKED":
        before = [s for s in states if s != "BLOCKED"]
        blocked_from = before[-1] if before else None
    return states[-1], blocked_from


def admit(
    record: dict, writer: str, ledger: Ledger, config: dict, context: Context
) -> Verdict:
    """Decide one write. Appends to the ledger only when admitted."""
    kind = record.get("kind")
    if kind not in VALIDATORS:
        return _refuse("schema_invalid", f"unknown kind {kind!r}")
    errors = sorted(
        VALIDATORS[kind].iter_errors(record), key=lambda e: list(e.absolute_path)
    )
    if errors:
        first = errors[0]
        where = "/".join(str(p) for p in first.absolute_path) or "<root>"
        field_name = str(first.absolute_path[0]) if first.absolute_path else ""
        if (
            field_name in ("source_ref", "source_revision")
            or "'source_ref'" in first.message
            or "'source_revision'" in first.message
        ):
            return _refuse("missing_source_ref", f"{where}: {first.message}")
        return _refuse("schema_invalid", f"{where}: {first.message}")

    state = record["state"]
    if state in EVIDENCE_REQUIRED and not record["evidence_refs"]:
        return _refuse(
            "missing_source_ref", f"state {state} requires at least one evidence_ref"
        )

    # -- who may write this
    if record["department_id"] != config["department_id"]:
        return _refuse(
            "unauthorized_write",
            f"department {record['department_id']} is not {config['department_id']}",
        )
    granted = config.get("workers", {}).get(writer)
    if not granted:
        return _refuse(
            "unauthorized_write",
            f"writer {writer!r} holds no role in {config['department_id']}",
        )
    role = record["authority"]
    if role not in granted:
        return _refuse(
            "unauthorized_write", f"writer {writer!r} does not hold role {role!r}"
        )
    spec = config["roles"].get(role)
    if spec is None or state not in spec["states"] or kind not in spec["kinds"]:
        return _refuse(
            "unauthorized_write", f"role {role!r} may not write {kind} in state {state}"
        )

    # -- once only
    if idempotency_key(record) in ledger.keys:
        return _refuse(
            "duplicate_idempotency_key",
            f"{idempotency_key(record)} was already admitted",
        )

    # -- where it may go
    current, blocked_from = _prior_state(ledger, record["run_id"])
    legal = set(TRANSITIONS[current])
    if blocked_from is not None:
        legal.add(blocked_from)
    if state not in legal:
        return _refuse(
            "illegal_transition", f"{current} -> {state} is not a legal transition"
        )
    for name in TRANSITION_REQUIRES.get(state, ()):
        if record[name] is None:
            return _refuse("schema_invalid", f"state {state} requires {name} to be set")

    # -- the gates on specific edges
    if state == "APPROVED":
        decision = record["policy_decision"]
        if (
            decision["door"] not in config["authorization_doors"]
            or decision["verdict"] != "allow"
        ):
            return _refuse(
                "missing_authorization",
                f"{decision['door']} {decision['verdict']} is not an allow from an authorization door",
            )
    if kind == "review":
        author = ledger.author_of(record["payload"]["prototype_run_id"], "PROTOTYPING")
        if author is None:
            return _refuse(
                "missing_source_ref",
                f"no admitted prototype for {record['payload']['prototype_run_id']}",
            )
        if author != record["payload"]["prototype_author_id"]:
            return _refuse(
                "stale_provenance",
                f"the review names {record['payload']['prototype_author_id']!r} as author; the ledger says {author!r}",
            )
        if author in (writer, record["evaluator_id"]):
            return _refuse(
                "self_certification",
                f"{author!r} wrote the prototype and cannot evaluate it",
            )
    if state == "OPERATING":
        independent = [
            e
            for e in record["evidence_refs"]
            if e["kind"] == "observation" and e.get("observed_by") not in (None, writer)
        ]
        if not independent:
            return _refuse(
                "missing_independent_evidence",
                "OPERATING needs an observation recorded by someone other than the writer; a generated assertion is not one",
            )
    if state == "PROPOSED" and record["verdict"] != "pass":
        return _refuse(
            "illegal_transition",
            f"PROPOSED needs an evaluation verdict of pass, got {record['verdict']}",
        )

    # -- money
    if record["spend_usd"] > record["budget_cap_usd"]:
        return _refuse(
            "budget_overflow",
            f"spend {record['spend_usd']} exceeds the record cap {record['budget_cap_usd']}",
        )
    objective_cap = ledger.objective_cap(record["objective_id"])
    if kind == "objective" and objective_cap is None:
        objective_cap = record["budget_cap_usd"]
    if objective_cap is None:
        return _refuse(
            "missing_source_ref",
            f"objective {record['objective_id']} has no admitted objective record",
        )
    if (
        ledger.objective_spend(record["objective_id"]) + record["spend_usd"]
        > objective_cap
    ):
        return _refuse(
            "budget_overflow",
            f"objective {record['objective_id']} would exceed its cap {objective_cap}",
        )
    day = record["created_at"][:10]
    if (
        ledger.day_spend(record["department_id"], day) + record["spend_usd"]
        > config["per_day_cap_usd"]
    ):
        return _refuse(
            "budget_overflow",
            f"department spend on {day} would exceed {config['per_day_cap_usd']}",
        )

    # -- provenance
    current_revision = context.current_revisions.get(record["source_ref"])
    if current_revision is None:
        return _refuse(
            "stale_provenance",
            f"no current revision is known for {record['source_ref']}; unverifiable provenance is refused",
        )
    if current_revision != record["source_revision"]:
        return _refuse(
            "stale_provenance",
            f"{record['source_ref']} is at {current_revision}, record was derived from {record['source_revision']}",
        )
    if _parse(record["created_at"]) > context.now:
        return _refuse("stale_provenance", "created_at is in the future")
    if record["expires_at"] is not None and _parse(record["expires_at"]) <= context.now:
        return _refuse("stale_provenance", f"record expired at {record['expires_at']}")

    ledger.append(record, writer)
    return Verdict(True, "admitted", f"{current} -> {state}")

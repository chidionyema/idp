"""The instruction ledger contract: no prompt ends in the void.

Every founder or agent prompt is an *instruction*. This module is the one place
that:

  * requires an instruction id on a prompt (a prompt with none is refused, so the
    router can never let an unlinkable request through);
  * normalizes a prompt into structured Given/When/Then (BDD) form;
  * records it (or links it to an existing instruction) in the catalog's
    ``instructions`` table;
  * tracks *yield* back to the originating instruction -- was the work done,
    proven, and with what evidence -- so the estate can measure "what did this
    prompt actually produce" instead of losing it in an opaque session log.

This is not a second database and not a second BDD layer. It writes rows into the
same ``catalog.instructions`` table the schema in
``platform/catalog/schema/001_catalog.sql`` declares, and it feeds the same
Given/When/Then shape the estate's bdd gates already consume. It raises the bar
over the previous state (prompts stored only as opaque ``session_events.payload_json``)
by adding the one thing that was missing: a queryable, linkable instruction record.

Nothing in this module knows how to reach a database on its own; it speaks in
shapes and returns INSERT/UPDATE statements and normalized dataclasses, the same
way ``catalog/census/model.py`` speaks in observations and joins. The store layer
applies them.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field, asdict
from typing import Any, Optional
import uuid as _uuid

# Origin: where the prompt came from. A closed set so "founder said X" is not a
# free-text field that drifts.
ORIGIN_FOUNDER = "founder"
ORIGIN_AGENT = "agent"
ORIGIN_ROUTER = "router"
ORIGIN_VOICE = "voice"
ORIGIN_SESSION = "session"
ORIGINS = (ORIGIN_FOUNDER, ORIGIN_AGENT, ORIGIN_ROUTER, ORIGIN_VOICE, ORIGIN_SESSION)

# Instruction status: the lifecycle a prompt moves through. A prompt starts `open`,
# becomes `structured` once normalized to BDD, `done` when the work is done and
# proven, or `abandoned` when its owner released it. `converting` is the transient
# state while BDD normalization is in flight.
STATUS_OPEN = "open"
STATUS_CONVERTING = "converting"
STATUS_STRUCTURED = "structured"
STATUS_DONE = "done"
STATUS_ABANDONED = "abandoned"
STATUSES = (
    STATUS_OPEN,
    STATUS_CONVERTING,
    STATUS_STRUCTURED,
    STATUS_DONE,
    STATUS_ABANDONED,
)

# What kind of message a prompt is. `question` and `correction` are distinct from a
# fresh `instruction` only so the estate can answer "was this a new order or a
# correction to an existing one", which is the difference between a new instruction
# and a link.
KIND_INSTRUCTION = "instruction"
KIND_CORRECTION = "correction"
KIND_QUESTION = "question"
KIND_ORDER = "order"
KINDS = (KIND_INSTRUCTION, KIND_CORRECTION, KIND_QUESTION, KIND_ORDER)


class UnlinkedPromptError(ValueError):
    """A prompt arrived with no instruction id and could not be linked.

    This is the falsifier: the router must refuse this, not log it and continue.
    """


@dataclass(frozen=True)
class Instruction:
    """One normalized prompt, bound to an id, structured as BDD, with its yield."""

    id: str
    prompt: str
    origin: str
    status: str = STATUS_OPEN
    linked_to: str = ""
    kind: str = KIND_INSTRUCTION
    bdd_given: Optional[str] = None
    bdd_when: Optional[str] = None
    bdd_then: Optional[str] = None
    recorded_at: str = ""
    structured_at: Optional[str] = None
    closed_at: Optional[str] = None
    yield_json: dict[str, Any] = field(default_factory=dict)

    def to_row(self) -> dict[str, Any]:
        """The row shape the ``instructions`` table stores (snake_case columns)."""
        return asdict(self)


def new_id() -> str:
    """A stable, unguessable instruction id. Format: ``instr-<uuid4 hex>``."""
    return f"instr-{_uuid.uuid4().hex}"


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def link_or_new(
    prompt: str,
    origin: str,
    instruction_id: Optional[str] = None,
    linked_to: str = "",
    kind: str = KIND_INSTRUCTION,
) -> Instruction:
    """Bind a prompt to an instruction id, refusing one that cannot be linked.

    The rule the founder stated: every prompt is an instruction which can be linked
    to original or a new instruction. So:

      * if ``instruction_id`` is given and ``linked_to`` is empty, this is the
        original -- return an ``Instruction`` whose id is that id;
      * if ``instruction_id`` is given and ``linked_to`` is a known id, this
        *extends* that instruction -- return an ``Instruction`` linked to it;
      * if neither is given and we cannot derive one, raise ``UnlinkedPromptError``:
        the router refuses the request rather than let the prompt into the void.
    """
    if instruction_id:
        return Instruction(
            id=instruction_id,
            prompt=prompt,
            origin=origin,
            linked_to=linked_to,
            kind=kind,
            recorded_at=_now_iso(),
        )
    if linked_to:
        # A prompt that links to an existing instruction gets its own new id, but
        # carries the link so it is never orphaned.
        return Instruction(
            id=new_id(),
            prompt=prompt,
            origin=origin,
            linked_to=linked_to,
            kind=kind,
            recorded_at=_now_iso(),
        )
    raise UnlinkedPromptError(
        "prompt carries no instruction id and no link; refuse rather than lose it"
    )


def structure_bdd(
    instruction: Instruction, given: str, when: str, then: str
) -> Instruction:
    """Normalize an instruction into structured Given/When/Then.

    A prompt that is not structured yet is exactly the "prompts not converted to BDD"
    gap the founder named. This is the normalization step: it pins the three legs
    and marks the instruction ``structured``. It refuses empty legs rather than store
    a BDD that cannot be executed by the bdd-proof gate.
    """
    if not (given.strip() and when.strip() and then.strip()):
        raise ValueError("BDD requires non-empty given, when and then")
    now = _now_iso()
    return Instruction(
        id=instruction.id,
        prompt=instruction.prompt,
        origin=instruction.origin,
        status=STATUS_STRUCTURED,
        linked_to=instruction.linked_to,
        kind=instruction.kind,
        bdd_given=given.strip(),
        bdd_when=when.strip(),
        bdd_then=then.strip(),
        recorded_at=instruction.recorded_at,
        structured_at=now,
        yield_json=instruction.yield_json,
    )


def record_yield(
    instruction: Instruction,
    done: bool,
    proven: bool,
    outcome: str,
    evidence: str,
) -> Instruction:
    """Track yield back to the instruction that produced it.

    ``done`` and ``proven`` are deliberately separate: a merged PR is "done" but not
    "proven" until a real production log line exists (AGENTS.md section 3). The
    falsifier is that a done-but-unproven instruction must *not* read as done in the
    yield.
    """
    yield_json = dict(instruction.yield_json)
    yield_json.update(
        {
            "done": bool(done),
            "proven": bool(proven),
            "outcome": outcome,
            "evidence": evidence,
            "recorded_at": _now_iso(),
        }
    )
    closed_at = _now_iso() if (done and proven) else instruction.closed_at
    return Instruction(
        id=instruction.id,
        prompt=instruction.prompt,
        origin=instruction.origin,
        status=STATUS_DONE if (done and proven) else instruction.status,
        linked_to=instruction.linked_to,
        kind=instruction.kind,
        bdd_given=instruction.bdd_given,
        bdd_when=instruction.bdd_when,
        bdd_then=instruction.bdd_then,
        recorded_at=instruction.recorded_at,
        structured_at=instruction.structured_at,
        closed_at=closed_at,
        yield_json=yield_json,
    )


def ingest_prompt(
    prompt: str,
    origin: str,
    *,
    instruction_id: Optional[str] = None,
    linked_to: str = "",
    kind: str = KIND_INSTRUCTION,
    bdd: Optional[tuple[str, str, str]] = None,
) -> Instruction:
    """The single entry point: require an id, optional-link, normalize to BDD.

    Returns a fully-normalized ``Instruction``. Raises ``UnlinkedPromptError`` when
    the prompt cannot be linked to any instruction, which is the router's signal to
    refuse the request.
    """
    instr = link_or_new(
        prompt, origin, instruction_id=instruction_id, linked_to=linked_to, kind=kind
    )
    if bdd is not None:
        instr = structure_bdd(instr, bdd[0], bdd[1], bdd[2])
    return instr


def upsert_sql(instruction: Instruction) -> str:
    """The INSERT ... ON CONFLICT DO UPDATE statement for one instruction.

    Idempotent, matching the schema's ``if not exists`` convention: applying twice
    is a no-op on the id, and an update on the mutable fields.
    """
    cols = (
        "id,prompt,origin,bdd_given,bdd_when,bdd_then,status,linked_to,kind,"
        "recorded_at,structured_at,closed_at,yield_json"
    )
    return (
        f"insert into catalog.instructions ({cols}) values ("
        f"%(id)s,%(prompt)s,%(origin)s,%(bdd_given)s,%(bdd_when)s,%(bdd_then)s,"
        f"%(status)s,%(linked_to)s,%(kind)s,%(recorded_at)s,%(structured_at)s,"
        f"%(closed_at)s,%(yield_json)s) "
        f"on conflict (id) do update set "
        f"status=excluded.status, bdd_given=excluded.bdd_given, "
        f"bdd_when=excluded.bdd_when, bdd_then=excluded.bdd_then, "
        f"structured_at=excluded.structured_at, closed_at=excluded.closed_at, "
        f"yield_json=excluded.yield_json"
    )

"""The estate's contracts: one strict Pydantic model for every record an agent produces.

Founder 2026-11-14 20:43: "our estate is not argon; we need strict schemas now, pydantic". Every repository
and every agent (console or web) speaks these shapes; nothing outside them is accepted. Each model forbids
unknown fields, is strict about types, and is frozen. `bin/estate-contract validate <Kind> <file|->` is the
one check; `bin/estate-contract schema` exports the JSON Schemas other languages consume.
"""

from estate_contract.models import (  # noqa: F401
    KINDS,
    AgentTurn,
    Claim,
    ClaimComment,
    CommitTrailers,
    DefectControl,
    Evidence,
    FounderAsk,
    LinkChoice,
    ModelLane,
    PhoneApproval,
    ProofBlock,
    YieldPayload,
)

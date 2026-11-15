"""Strict Pydantic models for every record an estate agent produces.

Rules shared by all: unknown fields are refused (extra="forbid"), types are not coerced (strict), and a
validated record cannot be changed (frozen). Text records (a CLAIM comment, commit trailers, a proof block)
have a `parse` classmethod that reads the exact text the estate's gates read and returns the model or raises.
The founder-facing rules come from estate_contract/rules/founder-voice.json, the same file argon enforces.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Annotated, Literal, Union

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

RULES = json.loads((Path(__file__).parent / "rules" / "founder-voice.json").read_text())


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


Sha = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{7,40}$")]
FullSha = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
AgentName = Annotated[
    str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{1,63}$")
]
IssueRef = Annotated[
    str, StringConstraints(pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+#[1-9][0-9]*$")
]
ClaimRef = Annotated[
    str, StringConstraints(pattern=r"^(?:[\w.-]+/[\w.-]+)?#[1-9][0-9]*$")
]  # bin/claim-gate CLAIM_REF
InstructionId = Annotated[str, StringConstraints(pattern=r"^I-\d{4}$")]
HttpsUrl = Annotated[str, StringConstraints(pattern=r"^https://\S+$", max_length=400)]


def _repo_path(v: str) -> str:
    if (
        not v
        or v.startswith("/")
        or ".." in v.split("/")
        or len(v) > 300
        or re.search(r"[\s,\\]", v)
    ):
        raise ValueError(f"not a repository path: {v!r}")
    return v


RepoPath = Annotated[str, AfterValidator(_repo_path)]


# ---------------------------------------------------------------- founder-facing ask (argon founder-voice.json)


def _words(s: str) -> int:
    return len(s.split())


def _plain(text: str, max_words: int, field: str) -> str:
    if not text.strip():
        raise ValueError(f"{field} is empty")
    if _words(text) > max_words:
        raise ValueError(f"{field} has {_words(text)} words; at most {max_words}")
    for sentence in re.split(r"(?<=[.!?])\s+", text.strip()):
        if _words(sentence) > RULES["max_words_per_sentence"]:
            raise ValueError(
                f"{field} has a sentence over {RULES['max_words_per_sentence']} words"
            )
    low = f" {text.lower()} "
    hits = [
        t
        for t in RULES["banned_terms"]
        if re.search(r"(?<![\w-])" + re.escape(t.lower()) + r"(?![\w-])", low)
    ]
    if hits:
        raise ValueError(f"{field} uses machine words: {', '.join(sorted(hits))}")
    for name, pat in RULES["forbidden_patterns"].items():
        if re.search(pat, text):
            raise ValueError(f"{field} contains a {name}")
    return text


class LinkChoice(Contract):
    label: str
    url: HttpsUrl

    @field_validator("label")
    @classmethod
    def _label(cls, v: str) -> str:
        return _plain(v, RULES["label_max_words"], "label")


class PhoneApproval(Contract):
    """One tap on the founder's phone: an approval the agent already raised; he picks this number."""

    label: str
    url: HttpsUrl
    code: Annotated[str, StringConstraints(pattern=r"^[0-9]{1,3}$")]

    @field_validator("label")
    @classmethod
    def _label(cls, v: str) -> str:
        return _plain(v, RULES["label_max_words"], "label")

    @field_validator("url")
    @classmethod
    def _app(cls, v: str) -> str:
        if v.split("/")[2] not in RULES.get("approval_apps", {}):
            raise ValueError("a phone approval needs a host with an approval app")
        return v


class FounderAsk(Contract):
    question: str
    why: str
    choices: Annotated[
        list[Union[PhoneApproval, LinkChoice]],
        Field(min_length=1, max_length=RULES["max_choices"]),
    ]
    if_no_answer: str

    @field_validator("question")
    @classmethod
    def _q(cls, v: str) -> str:
        if not v.rstrip().endswith("?"):
            raise ValueError("question must end with a question mark")
        return _plain(v, RULES["question_max_words"], "question")

    @field_validator("why")
    @classmethod
    def _why(cls, v: str) -> str:
        return _plain(v, RULES["why_max_words"], "why")

    @field_validator("if_no_answer")
    @classmethod
    def _ina(cls, v: str) -> str:
        return _plain(v, RULES["if_no_answer_max_words"], "if_no_answer")


# ---------------------------------------------------------------- agent turn (argon .genesis/turn.schema.json)


class Evidence(Contract):
    source: Literal["git", "ci", "http", "runtime", "telegram", "ledger", "test"]
    command: Annotated[str, StringConstraints(min_length=1, max_length=300)]
    sha256: Annotated[str, StringConstraints(pattern=r"^sha256:[0-9a-f]{64}$")]


class Claim(Contract):
    subject: Annotated[str, StringConstraints(min_length=1, max_length=200)]
    rung: Literal[
        "configured", "committed", "pushed", "deployed", "healthy", "verified"
    ]
    evidence: Annotated[list[Evidence], Field(min_length=1, max_length=8)]


class YieldPayload(Contract):
    status: Literal["DEMO_STAGED"]
    instruction_id: InstructionId
    branch: Annotated[
        str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,118}$")
    ]
    commit: Sha
    remote_verified: Literal[True]
    tests_passed: Annotated[int, Field(ge=1)]
    tests_failed: Literal[0]
    demo_manifest: str
    yield_endpoint: str
    proof_hash: str | None


class AgentTurn(Contract):
    protocol: Literal[
        "GEN-PROTO-001",
        "GEN-PROTO-002",
        "GEN-PROTO-003",
        "GEN-PROTO-004",
        "GEN-PROTO-005",
    ]
    instruction: InstructionId
    role: Literal["founder", "agent", "peer", "machine"]
    act: Literal["inform", "request", "propose", "refuse", "failure", "confirm"]
    command: Literal["PR.CLOSE", "PR.SWEEP"] | None
    claims: list[Claim]
    action_url: HttpsUrl | None
    payload: YieldPayload | None
    ask: FounderAsk | None

    @model_validator(mode="after")
    def _ask_rules(self) -> "AgentTurn":
        if self.act == "request" and self.role != "founder":
            if self.ask is None:
                raise ValueError("a request to the founder carries an ask")
            if self.action_url not in {c.url for c in self.ask.choices}:
                raise ValueError("action_url must be one of the ask's choices")
        elif self.ask is not None:
            raise ValueError("only a request carries an ask")
        return self


# ---------------------------------------------------------------- claims, trailers, proof (idp gates)


class ClaimComment(Contract):
    """`CLAIM agent=<name> paths=<a,b> heartbeat=<UTC>` on an issue (bin/claim-gate, bin/claim-open)."""

    agent: AgentName
    paths: Annotated[list[RepoPath], Field(min_length=1, max_length=200)]
    heartbeat: datetime

    @field_validator("heartbeat")
    @classmethod
    def _utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.utcoffset().total_seconds() != 0:
            raise ValueError("heartbeat must be UTC")
        return v

    @classmethod
    def parse(cls, text: str) -> "ClaimComment":
        m = re.search(
            r"^CLAIM agent=(\S+) paths=(\S+) heartbeat=(\S+)\s*$",
            text.strip().splitlines()[0] if text.strip() else "",
        )
        if not m:
            raise ValueError(
                "not a CLAIM line: CLAIM agent=<name> paths=<a,b> heartbeat=<UTC>"
            )
        return cls.model_validate(
            {
                "agent": m.group(1),
                "paths": m.group(2).split(","),
                "heartbeat": datetime.fromisoformat(m.group(3).replace("Z", "+00:00")),
            },
            strict=False,
        )


class CommitTrailers(Contract):
    """The trailers the gates read (bin/claim-gate CLAIM_REF/AGENT, bin/dof-gate, .githooks/commit-msg)."""

    claims: Annotated[list[ClaimRef], Field(min_length=1)]
    agent: AgentName
    genesis_resolves: (
        Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9_-]{1,63}$")] | None
    )
    x_idp_signed: list[Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{16,128}$")]]

    @classmethod
    def parse(cls, message: str) -> "CommitTrailers":
        claims = re.findall(r"^Claim:\s*(\S+)\s*$", message, re.M)
        agents = re.findall(r"^Agent:\s*(\S+)\s*$", message, re.M)
        resolves = re.findall(r"^Genesis-Resolves:\s*(\S+)\s*$", message, re.M)
        if not claims or not agents:
            raise ValueError(
                "a commit carries a Claim: and an Agent: line, each alone on its line"
            )
        if len(set(agents)) > 1 or len(set(resolves)) > 1:
            raise ValueError("one Agent: and at most one Genesis-Resolves: per commit")
        return cls(
            claims=claims,
            agent=agents[0],
            genesis_resolves=resolves[0] if resolves else None,
            x_idp_signed=re.findall(r"^X-Idp-Signed:\s*(\S+)\s*$", message, re.M),
        )


RUNNER_LINES = [
    re.compile(r"\b[1-9]\d*\s+scenarios?\b[^\n]{0,40}\b[1-9]\d*\s+passed\b", re.I),
    re.compile(r"\b[1-9]\d*\s+features?\b[^\n]{0,40}\b[1-9]\d*\s+passed\b", re.I),
    re.compile(r"Tests:\s*[1-9]\d*\s+passed", re.I),
    re.compile(r"\b[1-9]\d*\s+passed,\s*[1-9]\d*\s+total\b", re.I),
    re.compile(r"^---\s*PASS:\s*\w", re.M),
    re.compile(r"\b[1-9]\d*\s+passed\s+in\s+[\d.]+s", re.I),
]
LANDER_LINE = re.compile(
    r"required\s+checks\s+green\s+on\s+candidate\s+[0-9a-f]{7,40}\s*:\s*\S+", re.I
)


class ProofBlock(Contract):
    """`BDD-PROOF ... END-BDD-PROOF`: a head and a runner's own counts (bin/idp-bdd-proof-gate)."""

    head: Sha
    evidence: Annotated[list[str], Field(min_length=1)]

    @classmethod
    def parse(cls, body: str) -> "ProofBlock":
        m = re.search(r"BDD-PROOF\s*\n(.*?)\nEND-BDD-PROOF", body or "", re.S)
        if not m:
            raise ValueError("no BDD-PROOF ... END-BDD-PROOF block")
        block = m.group(1)
        head = re.search(r"^head:\s*([0-9a-f]{7,40})\s*$", block, re.M)
        if not head:
            raise ValueError("the proof block names no head commit")
        lines = [
            ln.strip()
            for ln in block.splitlines()
            if any(p.search(ln) for p in RUNNER_LINES) or LANDER_LINE.search(ln)
        ]
        if not lines:
            raise ValueError(
                "the proof block carries no runner counts and no lander evidence"
            )
        return cls(head=head.group(1), evidence=lines)

    def proves(self, head: str) -> bool:
        return head.startswith(self.head) or self.head.startswith(head)


# ---------------------------------------------------------------- governance records


class DefectStatus(str, Enum):
    OPEN = "OPEN"
    CORRECTED = "CORRECTED"
    CONTROL_PROPOSED = "CONTROL_PROPOSED"
    CONTROL_VERIFIED = "CONTROL_VERIFIED"
    CLOSED = "CLOSED"


class DefectControl(Contract):
    """One record of argon genesis-defect-controls.json (GEN-PROTO-005)."""

    id: Annotated[str, StringConstraints(pattern=r"^DEF-\d{8}-[A-Z0-9]+-\d{3}$")]
    class_: Annotated[str, Field(alias="class", min_length=1)]
    discoveredAt: datetime
    discoveryEvidence: Annotated[str, Field(min_length=1)]
    impact: Annotated[str, Field(min_length=1)]
    rootCause: Annotated[str, Field(min_length=1)]
    immediateCorrection: Annotated[str, Field(min_length=1)]
    compensatingControl: Annotated[str, Field(min_length=1)]
    recurrenceTest: Annotated[str, StringConstraints(pattern=r"^[a-z0-9-]+:\S+$")]
    recurrenceProof: str | None
    recurrenceGuards: list[str] = []
    estateWideScope: Annotated[list[str], Field(min_length=1)]
    rolloutEvidence: Annotated[str, Field(min_length=1)]
    residualRisk: Annotated[str, Field(min_length=1)]
    status: DefectStatus

    model_config = ConfigDict(
        extra="forbid", strict=False, frozen=True, populate_by_name=True
    )


class ModelLane(Contract):
    """One lane of genesis-agent-policy.json `models`: the only place a model ID may be written."""

    provider: Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9-]{1,40}$")]
    model: Annotated[str, StringConstraints(min_length=1, max_length=120)]


KINDS: dict[str, type[Contract]] = {
    "AgentTurn": AgentTurn,
    "FounderAsk": FounderAsk,
    "ClaimComment": ClaimComment,
    "CommitTrailers": CommitTrailers,
    "ProofBlock": ProofBlock,
    "DefectControl": DefectControl,
    "ModelLane": ModelLane,
}

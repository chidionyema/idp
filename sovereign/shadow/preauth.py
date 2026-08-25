"""Predictive pre-authorization and the shadow-founder (R10/R21, spec 2.4
and 3.4).

Spec 2.4: before every transition the kernel simulates the next N steps,
counts predicted tokens, and if a boundary falls inside the horizon it
surfaces ONE card that pre-authorizes the whole predicted trajectory.
Spec 3.4: a shadow-founder trained on the founder's own decisions may
answer that card itself when its confidence is above shadow.min_confidence
and the op is inside policy -- and may NEVER do so for a destructive op.

The never is a type, not an `if`. `ShadowAuth` (the value that means "the
shadow-founder authorized this") holds a `NonDestructiveOp`, and the only
way to obtain a `NonDestructiveOp` is `classify()`, which returns a
`DestructiveOp` for anything sovereign/engine/ops.py calls destructive or
unknown. A caller that tries to build a ShadowAuth around a DestructiveOp
is a type error under pyright, and `ShadowAuth.__post_init__` re-checks
the op table at runtime so a cast cannot smuggle one through either.

Confidence is measured, not modelled: it is the rule of succession over
the founder's own past decisions of the same boundary kind, read from the
signed receipt chain. (approvals + 1) / (approvals + denials + 2) is 0.95
at 19 approvals and no denial, and shadow.min_samples (20) refuses to
trust any number built on fewer decisions than that. A fine-tuned local
model can replace `confidence()` later without touching the type
guarantee, which is the point of keeping them apart.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Union

from sovereign import config
from sovereign.engine import ops
from sovereign.engine import receipts as receipts_mod
from sovereign.shadow import config_keys as ck

_OP_NAME_RE = re.compile(r"[^a-z0-9]+")


def normalize_op(name: str) -> str:
    """"git push --force" and "git_push_force" are the same op. The op
    table is keyed by the underscore form, so the free-text form a step
    asks with is folded onto it before lookup."""
    return _OP_NAME_RE.sub("_", str(name).strip().lower()).strip("_")


# ---------------------------------------------------------------------------
# Op classification as two types.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NonDestructiveOp:
    """An op the ops table says needs budget only. Do not construct this
    directly; `classify()` is the one door, and `ShadowAuth` verifies at
    runtime that whatever it was handed still classifies this way."""

    name: str
    tokens: int


@dataclass(frozen=True)
class DestructiveOp:
    """An op that needs quorum and a hardware signature. `classification`
    is "destructive" or "unknown" -- unknown fails closed, exactly as
    ops.classify does."""

    name: str
    classification: str
    tokens: int


Op = Union[NonDestructiveOp, DestructiveOp]


def classify(name: str) -> Op:
    spec = ops.classify(normalize_op(name))
    if spec.destructive:
        return DestructiveOp(spec.name, spec.classification, spec.tokens)
    return NonDestructiveOp(spec.name, spec.tokens)


# ---------------------------------------------------------------------------
# The boundary prediction (spec 2.4).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Boundary:
    kind: str
    op: Op
    remaining: int
    predicted_costs: tuple[int, ...]
    hit_at_step: int  # 1-based index of the first predicted step the budget cannot cover
    refill: int  # tokens that cover the whole predicted trajectory, rounded up
    steps_covered: int  # how many predicted steps the refill covers -- all of them

    @property
    def card_text(self) -> str:
        """The one card. It names the amount and the steps it covers, so
        one gesture approves a trajectory and not an event."""
        return (
            f"boundary in {self.hit_at_step} step(s): pre-authorize {self.refill} tokens "
            f"covering the next {self.steps_covered} step(s)?"
        )


def predict(remaining: int, predicted_costs: list[int] | tuple[int, ...], horizon: int | None = None) -> Boundary | None:
    """Simulate the next `horizon` steps' spend. Returns the Boundary the
    trajectory hits, or None when the budget covers every step in the
    horizon. The op behind a budget boundary is the refill itself, which
    is a budget movement and not a destructive act."""
    horizon = int(horizon if horizon is not None else ck.get("shadow.horizon_steps"))
    costs = tuple(int(c) for c in predicted_costs[:horizon])
    balance = int(remaining)
    hit_at = 0
    for i, cost in enumerate(costs, start=1):
        if cost > balance:
            hit_at = i
            break
        balance -= cost
    if hit_at == 0:
        return None
    shortfall = sum(costs) - int(remaining)
    round_to = max(int(ck.get("shadow.refill_round_to")), 1)
    refill = int(math.ceil(shortfall / round_to) * round_to)
    kind = str(ck.get("shadow.refill_boundary_kind"))
    return Boundary(
        kind=kind,
        op=classify(kind),
        remaining=int(remaining),
        predicted_costs=costs,
        hit_at_step=hit_at,
        refill=refill,
        steps_covered=len(costs),
    )


# ---------------------------------------------------------------------------
# The shadow-founder's confidence, measured from the receipt chain.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class History:
    boundary: str
    approvals: int
    denials: int

    @property
    def samples(self) -> int:
        return self.approvals + self.denials


def _boundary_of(row: dict[str, Any]) -> str:
    return normalize_op(str(row.get("boundary") or row.get("text") or ""))


def history(boundary: str, rows: list[dict[str, Any]] | None = None) -> History:
    """Count the founder's own approve/deny receipts for one boundary
    kind. Only rows whose `by` is the founder count: an approval the
    shadow-founder itself wrote must not train the shadow-founder."""
    rows = receipts_mod.read_all() if rows is None else rows
    founder = str(ck.get("shadow.founder"))
    approve_kind = str(ck.get("shadow.approve_kind"))
    deny_kind = str(ck.get("shadow.deny_kind"))
    want = normalize_op(boundary)
    approvals = denials = 0
    for row in rows:
        if str(row.get("by")) != founder or _boundary_of(row) != want:
            continue
        if row.get("kind") == approve_kind:
            approvals += 1
        elif row.get("kind") == deny_kind:
            denials += 1
    return History(want, approvals, denials)


def confidence(hist: History) -> float:
    """Rule of succession. Below shadow.min_samples the answer is 0.0: a
    confidence built on three decisions is a guess wearing a number."""
    if hist.samples < int(ck.get("shadow.min_samples")):
        return 0.0
    return (hist.approvals + 1) / (hist.samples + 2)


# ---------------------------------------------------------------------------
# The verdict: ShadowAuth or Ask. ShadowAuth cannot hold a DestructiveOp.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ShadowAuth:
    boundary: Boundary
    op: NonDestructiveOp
    confidence: float

    def __post_init__(self) -> None:
        # The type already forbids a DestructiveOp here; this is the
        # runtime backstop for a caller that lied to the type checker.
        if not isinstance(self.op, NonDestructiveOp):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError("the shadow-founder never authorizes a destructive op")
        if ops.classify(self.op.name).destructive:
            raise TypeError(f"{self.op.name!r} is destructive in the ops table; ShadowAuth refused")


@dataclass(frozen=True)
class Ask:
    boundary: Boundary
    text: str
    reason: str  # "destructive" | "unknown" | "low_confidence"


Verdict = Union[ShadowAuth, Ask]


def decide(boundary: Boundary, conf: float, min_confidence: float | None = None) -> Verdict:
    """Spec 3.4: confidence > threshold AND inside policy -> ShadowAuth;
    otherwise the founder is asked. The destructive branch does not look
    at the confidence at all -- 100 past approvals do not make a force
    push safe."""
    op = boundary.op
    if isinstance(op, DestructiveOp):
        return Ask(boundary, boundary.card_text, op.classification)
    threshold = float(min_confidence if min_confidence is not None else config.get("shadow.min_confidence").value)
    if conf >= threshold:
        return ShadowAuth(boundary, op, conf)
    return Ask(boundary, boundary.card_text, "low_confidence")


def receipt_for(auth: ShadowAuth, session_id: str, step: int) -> dict[str, Any]:
    """Only a ShadowAuth can be turned into a shadow_auth receipt, so a
    destructive op can never produce one: there is no value of that type
    to pass in."""
    line = str(ck.get("shadow.receipt_line_format")).format(boundary=auth.boundary.kind, confidence=auth.confidence)
    return receipts_mod.append(
        {
            "session_id": session_id,
            "kind": str(ck.get("shadow.auth_receipt_kind")),
            "by": "shadow-founder",
            "text": line,
            "step": int(step),
            "status": "running",
            "boundary": auth.boundary.kind,
            "op": auth.op.name,
            "confidence": float(auth.confidence),
            "refill": int(auth.boundary.refill),
            "steps_covered": int(auth.boundary.steps_covered),
            "founder_notified": False,
        }
    )


# ---------------------------------------------------------------------------
# A session driven by the planner. This is the shape the engine's
# SessionWorkflow calls into (through an activity, since the receipt chain
# is on disk); the acceptance suite drives it directly.
# ---------------------------------------------------------------------------


@dataclass
class Session:
    session_id: str
    remaining: int
    predicted_costs: list[int]
    status: str = "running"
    asking: str | None = None
    pending: Boundary | None = None
    step: int = 0
    asks: int = 0
    steps_run: int = 0
    verdict: Verdict | None = None

    def plan(self, op: str | None = None) -> Verdict | None:
        """The shadow planning loop before a transition. `op` is the op
        the next step asks for; a budget boundary carries the refill op."""
        if op is not None:
            classified = classify(op)
            boundary = Boundary(
                kind=normalize_op(op), op=classified, remaining=self.remaining,
                predicted_costs=tuple(self.predicted_costs), hit_at_step=1,
                refill=0, steps_covered=len(self.predicted_costs),
            )
        else:
            predicted = predict(self.remaining, self.predicted_costs)
            if predicted is None:
                self.verdict = None
                return None
            boundary = predicted
        conf = confidence(history(boundary.kind))
        verdict = decide(boundary, conf)
        self.verdict = verdict
        if isinstance(verdict, Ask):
            self.status = "waiting"
            self.asking = verdict.text
            self.pending = boundary
            self.asks += 1
            return verdict
        receipt_for(verdict, self.session_id, self.step)
        self._apply(boundary)
        return verdict

    def approve(self, by: str) -> dict[str, Any]:
        """The founder's one gesture. Records the approval under the
        boundary kind (this is the row the shadow-founder learns from)
        and applies the whole trajectory's refill."""
        if self.status != "waiting" or self.pending is None:
            raise RuntimeError("nothing is waiting for approval")
        boundary = self.pending
        line = receipts_mod.append(
            {
                "session_id": self.session_id,
                "kind": str(ck.get("shadow.approve_kind")),
                "by": by,
                "text": boundary.kind,
                "boundary": boundary.kind,
                "step": self.step,
                "status": "running",
                "refill": boundary.refill,
                "steps_covered": boundary.steps_covered,
            }
        )
        self._apply(boundary)
        return line

    def _apply(self, boundary: Boundary) -> None:
        self.remaining += boundary.refill
        self.status = "running"
        self.asking = None
        self.pending = None

    def run_predicted_steps(self) -> int:
        """Run the predicted trajectory. A step the budget cannot cover
        re-plans, which is what "without another ask" is measured
        against."""
        ran = 0
        while self.predicted_costs:
            cost = self.predicted_costs[0]
            if cost > self.remaining:
                self.plan()
                if self.status == "waiting":
                    break
                continue
            self.predicted_costs.pop(0)
            self.remaining -= cost
            self.step += 1
            self.steps_run += 1
            ran += 1
        return ran

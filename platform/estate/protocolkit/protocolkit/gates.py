# ruff: noqa
# fmt: off
"""Stage validators. Each returns a list of violation strings (empty = pass)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

from .model import (
    ActionPlanDryRun, Assessment, ClaimProofSet, Commit, ContradictionReport,
    Discovery, Instruction, Invocation, Response, Stage,
)

MIN_QUOTE_CHARS = 8
MAX_TEXT_SEGMENT = 200
_WS = re.compile(r"\s+")


def norm(s: str) -> str:
    return _WS.sub(" ", s).strip().lower()


def default_text_policy(text: str) -> list[str]:
    """Free-text segments may only be connective tissue, never assertions.

    Conservative heuristic: short, no digits. Replace with a classifier if needed.
    """
    v = []
    if len(text) > MAX_TEXT_SEGMENT:
        v.append(f"text segment longer than {MAX_TEXT_SEGMENT} chars; assertions must be claims")
    if re.search(r"\d", text):
        v.append("text segment contains digits; numbers must come from a proved claim")
    return v


@dataclass
class Ctx:
    outputs: dict = field(default_factory=dict)  # Stage -> accepted output
    committed_keys: set = field(default_factory=set)
    entailment: Callable[[Any, str, str], bool] | None = None
    text_policy: Callable[[str], list[str]] = default_text_policy
    max_discovery_passes: int = 2


Validator = Callable[[Any, Ctx], list]


def _type(out, cls) -> list[str]:
    return [] if isinstance(out, cls) else [f"expected {cls.__name__}, got {type(out).__name__}"]


# ---- generic stages ----------------------------------------------------
def v_invocation(out, ctx):
    return _type(out, Invocation) or ([] if out.request.strip() else ["empty request"])


def v_instruction(out, ctx):
    return _type(out, Instruction) or ([] if out.directive.strip() else ["empty directive"])


def make_v_discovery(min_sources: int):
    def v(out, ctx):
        bad = _type(out, Discovery)
        if bad:
            return bad
        v = []
        if not out.evidence:
            return ["discovery returned no evidence; cannot proceed to claims"]
        ids = [e.id for e in out.evidence]
        if len(set(ids)) != len(ids):
            v.append("duplicate evidence ids")
        if any(not e.text.strip() for e in out.evidence):
            v.append("evidence with empty text")
        if out.passes > ctx.max_discovery_passes:
            v.append(f"{out.passes} passes exceeds fewest-pass limit of {ctx.max_discovery_passes}")
        if len({e.source for e in out.evidence}) < min_sources:
            v.append(f"needs at least {min_sources} independent sources")
        return v
    return v


# ---- proofset ----------------------------------------------------------
def check_proofset(ps: ClaimProofSet, evidence: dict, entailment=None) -> list[str]:
    if not ps.claims:
        return ["claimset is empty"]
    v: list[str] = []
    ids = [c.id for c in ps.claims]
    if len(set(ids)) != len(ids):
        v.append("duplicate claim ids")
    claims = {c.id: c for c in ps.claims}
    proved: set[str] = set()
    for p in ps.proofs:
        if p.claim_id not in claims:
            v.append(f"proof refers to unknown claim {p.claim_id!r}")
            continue
        ev = evidence.get(p.evidence_id)
        if ev is None:
            v.append(f"{p.claim_id}: evidence {p.evidence_id!r} was not retrieved in discovery")
        elif len(norm(p.quote)) < MIN_QUOTE_CHARS:
            v.append(f"{p.claim_id}: proof quote shorter than {MIN_QUOTE_CHARS} chars")
        elif norm(p.quote) not in norm(ev.text):
            v.append(f"{p.claim_id}: quote does not appear verbatim in {p.evidence_id!r}")
        elif entailment and not entailment(claims[p.claim_id], ev.text, p.quote):
            v.append(f"{p.claim_id}: quote does not entail the claim (entailment check)")
        else:
            proved.add(p.claim_id)
    for cid in ids:
        if cid not in proved:
            v.append(f"claim {cid!r} has no valid proof")
    return v


def make_v_proofset(discovery_stage: Stage, unified: bool = False):
    def v(out, ctx):
        bad = _type(out, ClaimProofSet)
        if bad:
            return bad
        evidence = {e.id: e for e in ctx.outputs[discovery_stage].evidence}
        v = check_proofset(out, evidence, ctx.entailment)
        if unified:
            report = ctx.outputs[Stage.CONTRADICTION_RESOLUTION]
            cited = {p.evidence_id for p in out.proofs}
            for c in report.contradictions:
                if c.status == "resolved" and c.preferred_evidence_id not in cited:
                    v.append(f"{c.id}: resolved in favour of {c.preferred_evidence_id!r} but no proof cites it")
                if c.status == "unresolved" and not any(cl.contested for cl in out.claims):
                    v.append(f"{c.id}: unresolved conflict but no claim is marked contested")
        return v
    return v


# ---- synthesis ---------------------------------------------------------
def v_contradiction_resolution(out, ctx):
    bad = _type(out, ContradictionReport)
    if bad:
        return bad
    v = []
    known = {e.id for e in ctx.outputs[Stage.DIVERGENT_DISCOVERY].evidence}
    if set(out.examined) != known:
        v.append("examined set must equal all discovered evidence (detector skipped something)")
    for c in out.contradictions:
        if len(c.evidence_ids) < 2 or not set(c.evidence_ids) <= known:
            v.append(f"{c.id}: must reference >=2 known evidence ids")
        if c.status not in ("resolved", "unresolved"):
            v.append(f"{c.id}: status must be resolved|unresolved")
        elif c.status == "resolved":
            if not c.rationale.strip():
                v.append(f"{c.id}: resolution needs a rationale")
            if c.preferred_evidence_id not in c.evidence_ids:
                v.append(f"{c.id}: preferred evidence must be one of the conflicting ones")
    return v


# ---- execution ---------------------------------------------------------
def v_state_assessment(out, ctx):
    bad = _type(out, Assessment)
    if bad:
        return bad
    v = []
    if not out.snapshot_digest:
        v.append("missing snapshot digest")
    if not out.scope:
        v.append("empty scope: agent has no permitted targets")
    return v


def v_dry_run(out, ctx):
    bad = _type(out, ActionPlanDryRun)
    if bad:
        return bad
    v = []
    scope = ctx.outputs[Stage.STATE_ASSESSMENT].scope
    if not out.plan.steps:
        v.append("empty plan")
    for s in out.plan.steps:
        if not any(s.target.startswith(p) for p in scope):
            v.append(f"step {s.action}:{s.target} is outside permitted scope")
    if out.result.plan_digest != out.plan.digest():
        v.append("dry-run was not run on this plan (digest mismatch)")
    if not out.result.checks:
        v.append("dry-run produced no checks")
    if not out.result.passed or not all(out.result.checks.values()):
        v.append("dry-run did not pass: " + ", ".join(k for k, ok in out.result.checks.items() if not ok))
    return v


def v_commit(out, ctx):
    bad = _type(out, Commit)
    if bad:
        return bad
    v = []
    dry = ctx.outputs[Stage.ACTION_PLAN_DRY_RUN]
    if out.plan_digest != dry.plan.digest():
        v.append("commit plan differs from the dry-run plan")
    if out.snapshot_digest != ctx.outputs[Stage.STATE_ASSESSMENT].snapshot_digest:
        v.append("state drifted since assessment; re-assess and re-run")
    if not out.idempotency_key:
        v.append("missing idempotency key")
    elif out.idempotency_key in ctx.committed_keys:
        v.append("idempotency key already committed (replay)")
    for s in dry.plan.steps:
        if not s.reversible and f"{s.action}:{s.target}" not in out.approvals:
            v.append(f"irreversible step {s.action}:{s.target} lacks explicit approval")
    return v


# ---- response ----------------------------------------------------------
def make_v_response(proofset_stage: Stage | None):
    def v(out, ctx):
        bad = _type(out, Response)
        if bad:
            return bad
        v = []
        if not out.segments:
            return ["empty response"]
        claims = {}
        if proofset_stage:
            claims = {c.id for c in ctx.outputs[proofset_stage].claims}
        receipts = 0
        disclosed = set()
        for i, s in enumerate(out.segments):
            if s.kind == "claim":
                if s.claim_id not in claims:
                    v.append(f"segment {i}: claim {s.claim_id!r} is not in the proved claimset")
            elif s.kind == "text":
                v += [f"segment {i}: {m}" for m in ctx.text_policy(s.text)]
            elif s.kind == "disclosure":
                disclosed.add(s.contradiction_id)
            elif s.kind == "receipt":
                receipts += 1
                if s.text != ctx.outputs.get(Stage.COMMIT, Commit("", "", "")).idempotency_key:
                    v.append(f"segment {i}: receipt does not match the committed action")
            else:
                v.append(f"segment {i}: unknown kind {s.kind!r}")
        if proofset_stage and not any(s.kind == "claim" for s in out.segments):
            v.append("response asserts nothing from the proofset")
        if Stage.COMMIT in ctx.outputs and receipts != 1:
            v.append("execution response needs exactly one receipt")
        report = ctx.outputs.get(Stage.CONTRADICTION_RESOLUTION)
        if report:
            for c in report.contradictions:
                if c.status == "unresolved" and c.id not in disclosed:
                    v.append(f"unresolved conflict {c.id} must be disclosed in the response")
        return v
    return v


def render(resp: Response, ctx: Ctx, proofset_stage: Stage | None) -> str:
    claims = {c.id: c.text for c in ctx.outputs[proofset_stage].claims} if proofset_stage else {}
    out = []
    for s in resp.segments:
        if s.kind == "claim":
            out.append(claims[s.claim_id])
        elif s.kind == "text":
            out.append(s.text)
        elif s.kind == "disclosure":
            out.append(f"[unresolved conflict {s.contradiction_id}]")
        elif s.kind == "receipt":
            out.append(f"[committed {s.text}]")
    return " ".join(out)

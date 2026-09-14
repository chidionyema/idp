#!/usr/bin/env python3
"""The Process Reward Model sidecar: grades each reasoning STEP, not only the final answer.

Why this exists (founder essay 2026-09-14, "PhD cold military surgeon"): "Standard agents rely
on Outcome Supervision (they generate an entire answer, and if it's wrong, they fail)... You
achieve [process supervision] by deploying a specialized Process Reward Model (PRM)... The PRM
evaluates the correctness of each step... rather than just the final outcome." And: "No 'Blind'
Assumptions: If the agent says 'I assume the database is up,' the control plane blocks the
reasoning step until the agent explicitly runs a check_db_connection tool."

Ticket: docs/tickets/2026-09-14-reasoning-gateway.md, deliverable D1. That ticket names three
gates the estate already has -- half of this pattern, anchored at different points:

  bin/idp-epistemic   -- grades a whole TRANSCRIPT's claims for independent evidence
  bin/idp-trajectory  -- grades a whole TRANSCRIPT for drift off the declared plan

Neither grades a single STEP as it happens; both grade after the fact. This gate reuses their
exact logic (imported, not re-implemented -- R43) and applies it turn-by-turn, so a hallucinated
or off-goal step is named at the step, not only when the whole transcript is later graded.

Three vectors per step, deterministic -- no model, no confidence score, no sampling (this is the
ticket's own explicit risk #1: "PRM as a frontier LLM is the failure mode, not the fix"):

  factual    -- a completed-work CLAIM in this step's text is not made unless the transcript,
                up to and including this step, already holds an independent witness for it
                (epistemic_firewall's own claim/evidence/witness logic, applied incrementally).
  relevance  -- a tool call in this step is bound to the active goal of a declared plan
                (trajectory_lock's authorize(), fed the same subgoal ids the plan declared).
  efficiency -- a tool call in this step is not a repeat of a (tool, target) pair this session
                already ran (the same normalisation epistemic_firewall uses for independence).

A step scores 1.0 per vector it does not violate, 0.0 per vector it does. Below THRESHOLD
(default 0.8, per vector) the step is rejected and the run must backtrack.

  bin/idp-prm --grade <session.jsonl>   exit 0 clean, 1 a step failed, 2 BLIND

The honest limit: this grades what a step's own text and tool calls show, the same limit
epistemic_firewall and trajectory_lock state about themselves. It does not verify that a
grounded claim is actually TRUE, only that it is not asserted blind.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from epistemic_firewall import (  # noqa: E402
    CLAIM,
    HEDGE,
    PLAN,
    QUESTION,
    _has_independent_witness,
    _sentences,
    _target_of,
    _texts,
    _unwrap,
)
from trajectory_lock import ESCAPE_HATCHES, TrajectoryLock  # noqa: E402

THRESHOLD = 0.8
_SESSION_ID = "prm"


def _is_tool_use(block: dict) -> bool:
    return isinstance(block, dict) and block.get("type") in ("tool_use", "tool_call")


def _step_tool_calls(turn: dict) -> list[dict]:
    msg = _unwrap(turn)
    content = msg.get("content")
    blocks = content if isinstance(content, list) else []
    calls = [b for b in blocks if _is_tool_use(b)]
    if not calls and msg.get("type") in ("tool_use", "tool_call"):
        calls = [msg]
    return calls


def _step_claims(turn: dict) -> list[str]:
    """Completed-work claims in this one step's own text -- epistemic_firewall's own filters."""
    claims: list[str] = []
    for text in _texts(turn):
        for sentence in _sentences(text):
            if (
                QUESTION.search(sentence)
                or HEDGE.search(sentence)
                or PLAN.search(sentence)
            ):
                continue
            if CLAIM.search(sentence):
                claims.append(sentence)
    return claims


def grade(turns: list[dict], plan: dict | None = None) -> dict:
    """Grade each step of an in-memory transcript. `plan` is {goal, subgoals} if declared inline.

    Steps are numbered in the order they occur (1-indexed, matching a person reading the file).
    """
    lock = TrajectoryLock(budget_per_goal=5)
    evidence: set[str] = set()
    active_goal_id: str | None = None
    steps: list[dict] = []

    for i, turn in enumerate(turns, start=1):
        if not isinstance(turn, dict):
            continue
        calls = _step_tool_calls(turn)

        # A declare_plan/revise_plan step binds the lock; it carries no vectors of its own --
        # same exclusion epistemic_firewall applies (ESCAPE_HATCHES are statements of intent,
        # never evidence, and never a graded action).
        plan_call = next(
            (
                c
                for c in calls
                if str(c.get("name", "")) in ("declare_plan", "revise_plan")
            ),
            None,
        )
        if plan_call is not None:
            inp = plan_call.get("input") or {}
            result = lock.declare_plan(
                _SESSION_ID, inp.get("goal", ""), inp.get("subgoals", [])
            )
            active_goal_id = None
            if result.get("accepted"):
                subs = inp.get("subgoals") or []
                active_goal_id = str(subs[0]["id"]) if subs else None
            continue

        vectors = {"factual": 1.0, "relevance": 1.0, "efficiency": 1.0}
        reasons: dict[str, str] = {}

        # -- factual: a claim this step makes must already be witnessed by evidence gathered
        # up to and including this step (the "I assume the database is up" case: the claim is
        # graded at the step that makes it, not only at the end of the transcript).
        claims = _step_claims(turn)
        if claims:
            claim_pieces = set(evidence)
            for c in calls:
                if str(c.get("name", "")) not in ESCAPE_HATCHES:
                    claim_pieces.add(f"{c.get('name', '?')}:{_target_of(c)}")
            if len(claim_pieces) < 3 or not _has_independent_witness(claim_pieces):
                vectors["factual"] = 0.0
                reasons["factual"] = (
                    f"claim {claims[0]!r} made on {len(claim_pieces)} piece(s) of evidence "
                    f"({', '.join(sorted(claim_pieces)) or 'none'}), fewer than 3 required or "
                    "none reading state this session did not author -- a blind assumption"
                )

        # -- relevance: any real tool call must bind to the declared plan's active goal.
        real_calls = [c for c in calls if str(c.get("name", "")) not in ESCAPE_HATCHES]
        if real_calls:
            for c in real_calls:
                target_goal_id = (c.get("input") or {}).get(
                    "target_goal_id"
                ) or active_goal_id
                result = lock.authorize(
                    str(c.get("name", "")),
                    c.get("input") or {},
                    _SESSION_ID,
                    target_goal_id,
                )
                if not result["allowed"]:
                    vectors["relevance"] = 0.0
                    reasons["relevance"] = result["reason"]
                    break

        # -- efficiency: a repeated (tool, target) pair already run is wasted branch cost.
        for c in real_calls:
            piece = f"{c.get('name', '?')}:{_target_of(c)}"
            if piece in evidence:
                vectors["efficiency"] = 0.0
                reasons["efficiency"] = (
                    f"{piece} already ran this session; no new information gain"
                )
            evidence.add(piece)

        score = sum(vectors.values()) / 3
        steps.append(
            {
                "step": i,
                "score": score,
                "vectors": vectors,
                "reasons": reasons,
                "text": (_step_claims(turn) or [""])[0] or _target_of(calls[0])
                if calls
                else "",
            }
        )

    failed = [s for s in steps if s["score"] < THRESHOLD]
    return {"steps": steps, "failed": failed, "refused": bool(failed)}


def _blind(why: str) -> dict:
    return {"steps": [], "failed": [], "refused": True, "blind": why}


def grade_file(path: Path | str) -> dict:
    p = Path(path)
    if not p.exists():
        return _blind(f"{p} does not exist")
    try:
        raw = p.read_text(errors="replace")
    except OSError as exc:
        return _blind(f"{p} could not be read: {exc}")
    turns: list[dict] = []
    for n, line in enumerate(raw.splitlines(), 1):
        if not line.strip():
            continue
        try:
            turns.append(json.loads(line))
        except (json.JSONDecodeError, ValueError):
            return _blind(f"{p}:{n} is not valid JSON")
    return grade(turns)


def _usage() -> str:
    return "usage: idp-prm --grade <session.jsonl>\n       idp-prm --self-test\n       idp-prm --help"


def _self_test() -> int:
    """LAW 45 (bin/idp-script-compiles): a script under bin/ is not built until it has run.

    Runs the real grade() path against the two fixtures this gate's own rules.yaml row
    names (tests/fixtures/prm/{bad,good}/session.jsonl), so this is the same proof the
    rules.yaml `cases` already assert -- not a second, looser check.
    """
    root = Path(__file__).resolve().parent.parent
    bad = root / "tests/fixtures/prm/bad/session.jsonl"
    good = root / "tests/fixtures/prm/good/session.jsonl"
    if not bad.exists() or not good.exists():
        print(
            f"SKIP prm --self-test: fixtures not found under {root}/tests/fixtures/prm"
        )
        return 0
    bad_verdict = grade_file(bad)
    good_verdict = grade_file(good)
    if not bad_verdict["refused"]:
        print(f"FAIL prm --self-test: {bad} should have been refused and was not")
        return 1
    if good_verdict["refused"]:
        print(f"FAIL prm --self-test: {good} should have passed and was refused")
        return 1
    print("ok   prm --self-test: bad fixture refused, good fixture passed")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) > 1 and argv[1] in ("--help", "-h"):
        print(_usage())
        return 0
    if len(argv) > 1 and argv[1] == "--self-test":
        return _self_test()

    args = [a for a in argv[1:] if a != "--grade"]
    if not args:
        print(_usage(), file=sys.stderr)
        return 2

    verdict = grade_file(args[0])
    if verdict.get("blind"):
        print(f"BLIND prm {verdict['blind']}", file=sys.stderr)
        return 2
    if verdict["refused"]:
        print(
            f"FAIL  prm {len(verdict['failed'])} step(s) below {THRESHOLD}",
            file=sys.stderr,
        )
        for s in verdict["failed"]:
            bad_vector = next(v for v, score in s["vectors"].items() if score < 1.0)
            print(
                f"      step {s['step']} ({bad_vector}, score {s['score']:.2f}): "
                f"{s['reasons'].get(bad_vector, '')}",
                file=sys.stderr,
            )
        return 1
    print(
        f"ok    prm {len(verdict['steps'])} step(s) graded, all >= {THRESHOLD} on "
        "factual correctness, relevance and efficiency"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

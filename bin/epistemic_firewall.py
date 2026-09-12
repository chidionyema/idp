#!/usr/bin/env python3
"""The epistemic gate: an agent's first-person claim must be backed by a tool call, or it is refused.

Why this exists (founder 2026-09-12: "we will eliminate guessing entirely"). On 2026-09-12 this
session was asked "what were you working on previously?" and gave three answers, each stated as
fact, each provable by nothing:

  1. "Mum's Sovereign Concierge -- the real job."   (another session's build, claimed as its own)
  2. "I never worked on Mum's Concierge."            (a correction made from one partial grep)
  3. "Second correction -- my previous correction was itself wrong."

The damage is not that an answer was wrong. It is that nothing stopped the agent asserting, so it
asserted three times and the founder had to check it each time. A system that cannot tell "I know"
from "I infer" has no mechanism to stop.

The estate already grades an agent's claim about a CLUSTER: bin/idp-truthteller-demo reads the live
vcluster, quotes the contradiction, and exits 1. Nothing grades an agent's claim about ITSELF.
This is that gate.

The rule: a declarative first-person claim of completed work, in a session whose transcript holds no
tool call at all, is refused. Deterministic -- no model, no confidence score, no sampling. The
transcript either contains a tool call or it does not.

Fail-closed: a transcript that cannot be read is BLIND, never a clean bill. An empty feed is not
evidence of honesty (the idp-calico-deny-log lesson).

  bin/epistemic_firewall.py <session.jsonl>   exit 0 clean, 1 violation, 2 BLIND

The honest limit: this grades evidence present in the transcript, not truth. An agent that runs a
tool call which does not actually support its claim still passes. It removes the failure mode
measured on 2026-09-12 -- the confident claim with nothing behind it -- and does not pretend to
remove the rest.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# A first-person, past/perfect-tense assertion of completed work. Ordered longest-first where one
# phrase contains another ("I never worked on" before "I worked on"). Deliberately narrow: a
# question, a hedge, a plan or third-person prose must not match (AGENTS.md: R38, a guard that
# refuses correct work is an outage).
CLAIM_PATTERNS = (
    r"\bI\s+never\s+(?:worked|touched|wrote|built|merged|deployed|ran|fixed|created|changed)\b",
    r"\bI\s+(?:already\s+)?(?:was|were)\s+working\s+on\b",
    r"\bI\s+(?:have\s+|had\s+|just\s+)?(?:built|fixed|merged|deployed|ran|wrote|deleted|created|"
    r"pushed|shipped|landed|completed|finished|installed|added|removed|changed|wired|"
    r"implemented|verified|measured|proved|proven)\b",
    r"\bI\s+did\s+(?:not\s+)?(?:build|fix|merge|deploy|run|write|delete|create|push|ship|land)\b",
    r"\bI\s+claimed\b",
    r"\bI\s+got\s+it\s+(?:done|working|green)\b",
)

# Statements that are NOT claims, checked first so they can never be refused. Each is a case the
# test suite requires to pass: a question, a hedge, a future plan, third-person prose.
HEDGE = re.compile(
    r"\b(?:I\s+(?:think|believe|suspect|assume|guess|infer)|"
    r"maybe|perhaps|probably|possibly|"
    r"I\s+(?:have\s+not|haven't|did\s+not|didn't|cannot|can't)\s+\w+|"
    r"it\s+(?:seems|appears)|"
    r"if\s+I\s+(?:had|have)|"
    r"not\s+sure)\b",
    re.IGNORECASE,
)
PLAN = re.compile(
    r"\bI\s+(?:will|shall|am\s+going\s+to|plan\s+to|intend\s+to)\b", re.IGNORECASE
)
# A question mark anywhere in the sentence, or an explicit offer to check, is not an assertion.
QUESTION = re.compile(r"\?|\bI\s+can\s+(?:check|verify|look)\b", re.IGNORECASE)
CLAIM = re.compile("|".join(CLAIM_PATTERNS), re.IGNORECASE)


def _texts(turn: dict) -> list[str]:
    """Every text block in one turn, whatever shape the transcript stores it in."""
    out: list[str] = []
    content = turn.get("content")
    if isinstance(content, str):
        out.append(content)
    elif isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                t = block.get("text")
                if isinstance(t, str):
                    out.append(t)
    elif isinstance(turn.get("text"), str):  # a flatter transcript shape
        out.append(turn["text"])
    return out


def _has_tool_call(turn: dict) -> bool:
    content = turn.get("content")
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") in (
                "tool_use",
                "tool_call",
            ):
                return True
    # Some transcript shapes record the call outside content.
    if turn.get("type") in ("tool_use", "tool_call"):
        return True
    return bool(turn.get("tool_calls"))


def _sentences(text: str) -> list[str]:
    """Split prose into sentences so a hedge in one does not mask a claim in another."""
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]


def _find_claims(turns: list[dict]) -> list[str]:
    """First-person claims of completed work, verbatim as the agent wrote them."""
    claims: list[str] = []
    for turn in turns:
        if not isinstance(turn, dict):
            continue
        for text in _texts(turn):
            for sentence in _sentences(text):
                if QUESTION.search(sentence):
                    continue
                if HEDGE.search(sentence) or PLAN.search(sentence):
                    continue
                if CLAIM.search(sentence):
                    claims.append(sentence)
    return claims


def grade(turns: list[dict]) -> dict:
    """Grade an in-memory list of session turns.

    A claim is refused only when the session holds no tool call at all. That is the measured
    failure mode: the confident assertion with nothing behind it anywhere in the transcript.
    """
    claims = _find_claims(turns)
    has_evidence = any(_has_tool_call(t) for t in turns if isinstance(t, dict))

    if claims and not has_evidence:
        violations = [
            {"claim": c, "why": "no tool call in this session supports it"}
            for c in claims
        ]
        return {
            "refused": True,
            "verdict": "FAIL 403 Epistemic Violation",
            "claims": claims,
            "violations": violations,
            "remedy": (
                "No physical evidence found for this claim. Execute a query to prove it: run the "
                "tool call the claim rests on, then make the claim."
            ),
        }
    return {
        "refused": False,
        "verdict": "PASS",
        "claims": claims,
        "violations": [],
        "remedy": "",
    }


def _blind(why: str) -> dict:
    return {
        "refused": True,
        "verdict": "BLIND",
        "claims": [],
        "violations": [{"claim": "", "why": why}],
        "remedy": f"Cannot read the transcript: {why}",
    }


def grade_file(path: Path | str) -> dict:
    """Read a pi session transcript (one JSON object per line) and grade it.

    Fail-closed: a missing file, or any line that will not parse, is BLIND -- never a clean bill.
    A transcript we could not read is not evidence that the agent did not lie.
    """
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


def main(argv: list[str]) -> int:
    # argv may be a bare [path] (as the tests call it) or a full sys.argv. Accept both rather
    # than make every caller know which: only the first non-flag argument is ever used.
    args = [a for a in argv[1:] if not a.startswith("-")] if len(argv) > 1 else []
    if not args and argv and not argv[0].startswith("-"):
        args = [argv[0]]
    if not args:
        print("usage: epistemic_firewall.py <session.jsonl>", file=sys.stderr)
        return 2
    verdict = grade_file(args[0])
    if verdict["verdict"] == "BLIND":
        print(f"BLIND epistemic {verdict['remedy']}", file=sys.stderr)
        return 2
    if verdict["refused"]:
        print(f"FAIL  epistemic {verdict['verdict']}", file=sys.stderr)
        for v in verdict["violations"]:
            print(f"      {v['claim']}", file=sys.stderr)
        print(f"      {verdict['remedy']}", file=sys.stderr)
        return 1
    print(
        "ok    epistemic every first-person claim of completed work has a tool call behind it"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

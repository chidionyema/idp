"""Founder prompt intake: every founder prompt becomes structured, retrievable context.

THE FOUNDER'S RULE (2026-10-29): "the more text you analyse the better", "for my case the
founder that is giving you the prompt is the absolute best text analyst there is", "i m not
repeating myself, if you drop the ball then you get demoted as lead engineer".

So a founder prompt is not a message that gets answered and lost. It is analysed into
structure and stored, so the next session recalls what was asked, what was forbidden, what
proof was demanded, what was corrected, and which entities were named -- without the founder
having to say it again.

THE ANALYSIS IS RULE-BASED AND DETERMINISTIC. No model, no guesswork about intent: every
sentence is classified by the markers it carries, and the classification is printed with the
sentence it came from, so the founder can check the machine's reading of their own words.

    objective      what the founder wants done
    constraint     what must hold while it is done
    prohibition    what must not happen
    proof_demand   what evidence the founder expects
    correction     the founder saying it again, or fixing us
    context        everything else

REPEAT DETECTION. A prompt that repeats an earlier one (token similarity over the stored
records) is flagged, with the earlier timestamp and the earlier prompt's id. A repeat is the
founder's demotion signal for the agent: the intake records it, the supervisor can treat it
as a violation class ("founder-repeat"), and the founder never has to repeat himself again.

STORAGE. The structured record goes to unified memory through the memory door, so every
runtime can recall it (that is the estate's one shared memory plane), and a copy is appended
to the local prompt ledger for the repeat detector.
"""

from __future__ import annotations

import hashlib
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

from . import ledger

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

MARKERS: List[Tuple[str, List[str]]] = [
    (
        "prohibition",
        [
            "never ",
            "not allowed",
            "must not",
            "do not ",
            "don't ",
            "no more",
            "stop ",
            "forbidden",
            "under no circumstances",
            "without any",
            "no way ",
        ],
    ),
    (
        "proof_demand",
        [
            "prove",
            "proof",
            "evidence",
            "machine generated",
            "machine-generated",
            "receipt",
            "verify",
            "log line",
            "show me the",
            "exit status",
            "show me",
        ],
    ),
    (
        "correction",
        [
            "again",
            "still ",
            "i said",
            "i told you",
            "why did you",
            "why have you",
            "you were supposed",
            "you keep",
            "not repeating myself",
            "drop the ball",
            "demoted",
            "no excuses",
            "stop asking",
        ],
    ),
    (
        "constraint",
        [
            "must ",
            "has to",
            "need to",
            "only ",
            "cannot",
            "never mind",
            "within ",
            "under ",
            "at least",
            "at most",
        ],
    ),
    (
        "objective",
        [
            "go on",
            "do it",
            "fix ",
            "build ",
            "add ",
            "implement",
            "finish",
            "complete",
            "deliver",
            "make sure",
            "ensure",
            "find ",
            "check ",
            "prove",
            "keep ",
            "continue",
            "now",
            "inm ",
            "i need",
            "you need",
        ],
    ),
]

TOKEN_RE = re.compile(r"[a-z0-9_]+")
ISSUE_RE = re.compile(r"#\d+")
PATH_RE = re.compile(
    r"(?<![\w/])([\w./-]+\.(?:py|ts|tsx|js|yaml|yml|json|md|toml|sh|mjs))"
)
# The founder names the estate's executables as often as its files, and they carry no
# extension: "bin/idp-vendor-render", "platform/estate/memory/door.py".
EXEC_PATH_RE = re.compile(
    r"(?<![\w/])((?:bin|platform|scripts|mcp|tests|extensions|docs|launchd)/[\w./-]+)"
)
QUOTE_RE = re.compile(r"[\"`]([^\"`\n]{2,120})[\"`]")
URL_RE = re.compile(r"https?://\S+")


def sentences(text: str) -> List[str]:
    """Split a prompt into sentences without losing the founder's punctuation."""
    cleaned = (text or "").strip()
    if not cleaned:
        return []
    parts = re.split(r"(?<=[.!?])\s+|\n+", cleaned)
    return [p.strip() for p in parts if p.strip()]


def classify(sentence: str) -> List[str]:
    """The classes a sentence carries. A sentence can carry more than one."""
    low = " " + sentence.lower() + " "
    hits = []
    for name, markers in MARKERS:
        if any(m in low for m in markers):
            hits.append(name)
    return hits


def entities(text: str) -> Dict[str, List[str]]:
    """The things the founder named: issues, files, commands in quotes, urls."""
    return {
        "issues": sorted(set(ISSUE_RE.findall(text or ""))),
        "files": sorted(
            set(PATH_RE.findall(text or "")) | set(EXEC_PATH_RE.findall(text or ""))
        ),
        "quoted": sorted(set(QUOTE_RE.findall(text or ""))),
        "urls": sorted(set(URL_RE.findall(text or ""))),
    }


def fingerprint(text: str) -> str:
    tokens = sorted(set(TOKEN_RE.findall((text or "").lower())))
    return hashlib.sha256(" ".join(tokens).encode()).hexdigest()[:16]


def tokens(text: str) -> List[str]:
    return [t for t in TOKEN_RE.findall((text or "").lower()) if len(t) > 2]


def similarity(a: str, b: str) -> float:
    """Jaccard over token sets: how much of the founder's prompt repeats."""
    ta, tb = set(tokens(a)), set(tokens(b))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / float(len(ta | tb))


def analyse(text: str) -> Dict[str, Any]:
    """The structured reading of one founder prompt."""
    rows = []
    classified: Dict[str, List[str]] = {
        "objective": [],
        "constraint": [],
        "prohibition": [],
        "proof_demand": [],
        "correction": [],
        "context": [],
    }
    for sentence in sentences(text):
        hits = classify(sentence)
        row = {"sentence": sentence, "classes": hits}
        rows.append(row)
        if not hits:
            classified["context"].append(sentence)
        for hit in hits:
            classified[hit].append(sentence)
    return {
        "fingerprint": fingerprint(text),
        "sentences": rows,
        "objectives": classified["objective"],
        "constraints": classified["constraint"],
        "prohibitions": classified["prohibition"],
        "proof_demands": classified["proof_demand"],
        "corrections": classified["correction"],
        "context": classified["context"],
        "entities": entities(text),
        "repeat_markers": classified["correction"],
    }


def stored_prompts() -> List[Dict[str, Any]]:
    return ledger.read_jsonl(ledger.prompts_path())


def find_repeat(text: str, threshold: float = 0.6) -> Optional[Dict[str, Any]]:
    """The earlier prompt this one repeats, or None."""
    best: Optional[Dict[str, Any]] = None
    best_score = 0.0
    for row in stored_prompts():
        score = similarity(text, row.get("text", ""))
        if score > best_score:
            best_score = score
            best = row
    if best is not None and best_score >= threshold:
        return {"score": round(best_score, 3), "earlier": best}
    return None


def publish(record: Dict[str, Any]) -> Dict[str, Any]:
    """Store the structured prompt in unified memory, through the estate's memory door."""
    sys.path.insert(0, os.path.join(REPO_ROOT, "platform", "estate", "memory"))
    try:
        import door  # type: ignore
    except (
        ImportError
    ) as exc:  # pragma: no cover - the door is always there in the estate
        return {"ok": False, "error": f"memory door unavailable: {exc}"}
    content = (
        "Founder prompt analysed. objectives="
        f"{record.get('objectives')}; constraints={record.get('constraints')}; "
        f"prohibitions={record.get('prohibitions')}; proof_demands={record.get('proof_demands')}; "
        f"corrections={record.get('corrections')}; entities={record.get('entities')}; "
        f"repeat_of={record.get('repeat_of')}"
    )
    try:
        secret = door.key()
        result = door.call(
            "remember",
            {
                "content": content,
                "subject": "founder-prompt",
                "kind": "fact",
                "tags": ["founder", "prompt", record.get("fingerprint", "")],
            },
            secret,
            timeout=15,
        )
    except Exception as exc:  # noqa: BLE001 - the door can fail for network reasons
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    return {"ok": True, "result": result}


def intake(
    text: str, session: str = "", publish_to_memory: bool = True
) -> Dict[str, Any]:
    """Analyse, detect the repeat, store. Returns the full record."""
    record = analyse(text)
    record["session"] = session
    record["ts"] = ledger.now()
    repeat = find_repeat(text)
    record["repeat_of"] = repeat["earlier"].get("id") if repeat else None
    record["repeat_score"] = repeat["score"] if repeat else 0.0
    record["id"] = (
        f"prompt-{record['ts'].replace(':', '').replace('-', '')}-{record['fingerprint'][:6]}"
    )
    stored = dict(record)
    stored["text"] = text
    ledger._append(ledger.prompts_path(), stored)
    if publish_to_memory:
        record["memory"] = publish(record)
    return record


def self_test() -> bool:
    """The gate this module owes the founder: the analysis must be able to fail."""
    sample = (
        "Never report anything to me without machine generated proof. "
        "I said that again, you keep dropping the ball. "
        "Fix the router fallback and show me the exit status."
    )
    record = analyse(sample)
    checks = [
        bool(record["prohibitions"]),
        bool(record["proof_demands"]),
        bool(record["corrections"]),
        bool(record["objectives"]),
        fingerprint(sample) == fingerprint(sample),
        similarity(sample, sample) == 1.0,
        similarity(sample, "completely different words here") < 0.2,
    ]
    ok = all(checks)
    print(
        "founder-intake self-test: "
        + ("ok" if ok else "FAIL")
        + f" prohibitions={len(record['prohibitions'])}"
        f" proof_demands={len(record['proof_demands'])}"
        f" corrections={len(record['corrections'])}"
        f" objectives={len(record['objectives'])}"
    )
    return ok

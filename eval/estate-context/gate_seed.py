#!/usr/bin/env python3
"""The seed grader for the estate's one-pass discovery question set (idp#7344, P0).

    python3 eval/estate-context/gate_seed.py --validate            # the question set itself
    python3 eval/estate-context/gate_seed.py --grade ANSWERS.json  # {question_id: answer envelope}

WHY. The oracle the founder asked for answers one question across the whole estate with sources,
and the only honest way to say it does is a labelled set and a grader that can FAIL. This file is
a PROVISIONAL contribution to P0 (the 100-question set is the programme's, not this seed's); the
record format is deliberately small so the P1 contracts can adopt or replace it.

THE ANSWER ENVELOPE a system under test returns for one question:
    {"disposition": "answer" | "abstain" | "unmeasurable",
     "facts": {"field": value, ...},
     "citations": [{"type": "file", "id": "<repo-relative path>", "sha256": "<hex of the file>"}],
     "reason": "<why, required for abstain and unmeasurable>"}

THE GATES (conjunctive -- a pass needs all of them; nothing is averaged):
    recall      every required source is cited
    citation    every citation resolves to a real file whose sha256 matches, and none is invented
    facts       every `fact_equals` check holds, exactly
    disposition an unanswerable question is answered with `abstain`, a question whose reader does
                not exist with `unmeasurable`, and an answerable question never with either

VERDICTS. PASS, FAIL, BLIND. BLIND is the estate's word (critical-watch.py) for "this could not
be measured", never a quiet PASS: an answerable question whose required file no longer holds the
evidence string is BLIND -- the fixture rotted, the system under test is not at fault.

SOURCE TYPES. Only `file` has a resolver here. A source type with no reader is not "absent": the
question that depends on it is labelled `unmeasurable`, and the right answer is to say so. That
keeps "the source is not there" and "the reader could not reach it" as different words.

Exit codes: 0 clean, 1 a FAIL or an invalid set, 2 a BLIND and nothing failed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

SCHEMA_VERSION = 1
EXPECTED = {"answerable", "abstain", "unmeasurable"}
DISPOSITIONS = {"answer", "abstain", "unmeasurable"}
SOURCE_TYPES_WITH_READER = {"file"}
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SEED = HERE / "questions.seed.json"

PASS, FAIL, BLIND = "PASS", "FAIL", "BLIND"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve_file(root: Path, rel: str) -> Path | None:
    """A repo-relative file inside root, or None. Refuses absolute paths and `..` escapes."""
    if not isinstance(rel, str) or not rel or Path(rel).is_absolute():
        return None
    p = (root / rel).resolve()
    try:
        p.relative_to(root.resolve())
    except ValueError:
        return None
    return p if p.is_file() else None


def validate_set(doc: object) -> list[str]:
    """Every structural defect in a question set, by name. Empty list means the set is well formed."""
    errs: list[str] = []
    if not isinstance(doc, dict):
        return ["set is not a JSON object"]
    if doc.get("schema_version") != SCHEMA_VERSION:
        errs.append(f"schema_version must be {SCHEMA_VERSION}")
    qs = doc.get("questions")
    if not isinstance(qs, list) or not qs:
        return errs + ["questions must be a non-empty list"]
    seen: set[str] = set()
    for i, q in enumerate(qs):
        where = f"questions[{i}]"
        if not isinstance(q, dict):
            errs.append(f"{where}: not an object")
            continue
        qid = q.get("id")
        if not isinstance(qid, str) or not qid:
            errs.append(f"{where}: id missing")
        elif qid in seen:
            errs.append(f"{where}: duplicate id {qid}")
        else:
            seen.add(qid)
        where = f"{qid or where}"
        if not isinstance(q.get("question"), str) or not q["question"].strip():
            errs.append(f"{where}: question text missing")
        exp = q.get("expected")
        if exp not in EXPECTED:
            errs.append(f"{where}: expected must be one of {sorted(EXPECTED)}")
        srcs = q.get("required_sources", [])
        if not isinstance(srcs, list):
            errs.append(f"{where}: required_sources must be a list")
            srcs = []
        if exp == "answerable" and not srcs:
            errs.append(
                f"{where}: an answerable question names at least one required source"
            )
        if exp in ("abstain", "unmeasurable") and not q.get("reason"):
            errs.append(
                f"{where}: {exp} needs the reason the right answer is not an answer"
            )
        for j, s in enumerate(srcs):
            if not isinstance(s, dict) or not s.get("type") or not s.get("id"):
                errs.append(f"{where}: required_sources[{j}] needs type and id")
                continue
            if exp == "answerable" and s["type"] not in SOURCE_TYPES_WITH_READER:
                errs.append(
                    f"{where}: source type {s['type']!r} has no reader here; "
                    "label the question `unmeasurable`, do not pretend it is answerable"
                )
            if s["type"] == "file" and not s.get("contains"):
                errs.append(
                    f"{where}: file source {s['id']} needs `contains`, the evidence string"
                )
        for j, c in enumerate(q.get("checks", [])):
            if (
                not isinstance(c, dict)
                or c.get("kind") != "fact_equals"
                or "field" not in c
                or "value" not in c
            ):
                errs.append(
                    f"{where}: checks[{j}] must be fact_equals with field and value"
                )
    return errs


def resolve_sources(q: dict, root: Path) -> list[str]:
    """Reasons a question's own fixtures no longer resolve. Non-empty means the question is BLIND."""
    broken: list[str] = []
    for s in q.get("required_sources", []):
        if s["type"] not in SOURCE_TYPES_WITH_READER:
            broken.append(f"no reader for source type {s['type']}")
            continue
        p = _resolve_file(root, s["id"])
        if p is None:
            broken.append(f"{s['id']}: file does not exist")
        elif s["contains"] not in p.read_text(errors="replace"):
            broken.append(f"{s['id']}: no longer contains the evidence string")
    return broken


def grade_one(q: dict, answer: object, root: Path = REPO) -> dict:
    """One question, one answer envelope, one verdict with every failed gate named."""
    out = {"id": q["id"], "verdict": PASS, "failed": [], "blind": []}
    exp = q["expected"]

    if exp == "answerable":
        out["blind"] = resolve_sources(q, root)
        if out["blind"]:
            out["verdict"] = BLIND
            return out

    if not isinstance(answer, dict) or answer.get("disposition") not in DISPOSITIONS:
        out["verdict"], out["failed"] = (
            FAIL,
            ["envelope: missing or invalid disposition"],
        )
        return out

    disp = answer["disposition"]
    want = {
        "answerable": "answer",
        "abstain": "abstain",
        "unmeasurable": "unmeasurable",
    }[exp]
    if disp != want:
        out["failed"].append(f"disposition: expected {want}, got {disp}")
    if (
        disp in ("abstain", "unmeasurable")
        and not str(answer.get("reason", "")).strip()
    ):
        out["failed"].append("disposition: abstaining without a reason")

    if exp == "answerable" and disp == "answer":
        cited: dict[str, str] = {}
        for c in answer.get("citations", []) or []:
            if not isinstance(c, dict):
                out["failed"].append("citation: not an object")
                continue
            cid, sha = c.get("id"), c.get("sha256")
            p = _resolve_file(root, cid) if c.get("type") == "file" else None
            if p is None:
                out["failed"].append(
                    f"citation: {cid!r} does not resolve (invented or unreadable)"
                )
            elif sha != sha256_file(p):
                out["failed"].append(f"citation: {cid} sha256 does not match the file")
            else:
                cited[cid] = sha
        for s in q["required_sources"]:
            if s["id"] not in cited:
                out["failed"].append(f"recall: required source {s['id']} not cited")
        facts = answer.get("facts") or {}
        for c in q.get("checks", []):
            if facts.get(c["field"]) != c["value"] or type(
                facts.get(c["field"])
            ) is not type(c["value"]):
                out["failed"].append(
                    f"facts: {c['field']} expected {c['value']!r}, got {facts.get(c['field'])!r}"
                )

    if out["failed"]:
        out["verdict"] = FAIL
    return out


def grade_all(doc: dict, answers: dict, root: Path = REPO) -> dict:
    results = [grade_one(q, answers.get(q["id"]), root) for q in doc["questions"]]
    n = {v: sum(r["verdict"] == v for r in results) for v in (PASS, FAIL, BLIND)}
    return {
        "counts": n,
        "results": results,
        "exit": 1 if n[FAIL] else (2 if n[BLIND] else 0),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--set", type=Path, default=SEED)
    ap.add_argument("--root", type=Path, default=REPO)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--validate", action="store_true")
    g.add_argument("--grade", type=Path, metavar="ANSWERS.json")
    a = ap.parse_args(argv)
    try:
        doc = json.loads(a.set.read_text())
    except (OSError, ValueError) as e:
        print(f"BLIND  cannot read the question set {a.set}: {e}", file=sys.stderr)
        return 2
    errs = validate_set(doc)
    if errs:
        print("\n".join(f"FAIL  {e}" for e in errs))
        return 1
    if a.validate:
        rotted = {
            q["id"]: resolve_sources(q, a.root)
            for q in doc["questions"]
            if q["expected"] == "answerable"
        }
        rotted = {k: v for k, v in rotted.items() if v}
        for k, v in rotted.items():
            print(f"BLIND  {k}: {'; '.join(v)}")
        print(
            f"{len(doc['questions'])} questions, {len(rotted)} with fixtures that no longer resolve"
        )
        return 2 if rotted else 0
    try:
        answers = json.loads(a.grade.read_text())
    except (OSError, ValueError) as e:
        print(f"BLIND  cannot read answers {a.grade}: {e}", file=sys.stderr)
        return 2
    res = grade_all(doc, answers, a.root)
    for r in res["results"]:
        print(f"{r['verdict']:5} {r['id']}  {'; '.join(r['failed'] + r['blind'])}")
    print(json.dumps(res["counts"]))
    return res["exit"]


if __name__ == "__main__":
    sys.exit(main())

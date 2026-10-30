"""The discovery seed grader must be able to FAIL (idp#7344 P0).

A grader that passes every answer is the looseness it exists to measure. Each test below hands the
grader a specific wrong answer and asserts the specific gate that must refuse it, plus the two
cases that are NOT failures: a rotted fixture is BLIND, and abstaining where the evidence is
deliberately missing is correct.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "gate_seed", REPO / "eval/estate-context/gate_seed.py"
)
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)

DOC = json.loads((REPO / "eval/estate-context/questions.seed.json").read_text())
Q = {q["id"]: q for q in DOC["questions"]}


def sha(rel: str) -> str:
    return hashlib.sha256((REPO / rel).read_bytes()).hexdigest()


def good_answer(qid: str) -> dict:
    q = Q[qid]
    return {
        "disposition": "answer",
        "facts": {c["field"]: c["value"] for c in q["checks"]},
        "citations": [
            {"type": "file", "id": s["id"], "sha256": sha(s["id"])}
            for s in q["required_sources"]
        ],
    }


def failed(qid: str, answer: object) -> list[str]:
    r = gate.grade_one(Q[qid], answer, REPO)
    assert r["verdict"] == gate.FAIL, r
    return r["failed"]


def test_seed_set_is_well_formed_and_every_fixture_resolves():
    assert gate.validate_set(DOC) == []
    assert all(
        gate.resolve_sources(q, REPO) == []
        for q in DOC["questions"]
        if q["expected"] == "answerable"
    )


def test_a_correct_answer_passes():
    for qid in ("seed-001", "seed-002", "seed-003"):
        assert gate.grade_one(Q[qid], good_answer(qid), REPO)["verdict"] == gate.PASS


def test_missing_one_required_source_fails_even_when_every_citation_is_valid():
    a = good_answer("seed-001")
    a["citations"] = a["citations"][:1]
    assert any(f.startswith("recall:") for f in failed("seed-001", a))


def test_a_fabricated_citation_fails():
    a = good_answer("seed-002")
    a["citations"].append(
        {"type": "file", "id": "docs/decisions/never-written.md", "sha256": "0" * 64}
    )
    assert any("does not resolve" in f for f in failed("seed-002", a))


def test_a_wrong_hash_fails():
    a = good_answer("seed-002")
    a["citations"][0]["sha256"] = "f" * 64
    assert any("sha256 does not match" in f for f in failed("seed-002", a))


def test_a_path_escape_cannot_be_cited():
    a = good_answer("seed-002")
    a["citations"].append(
        {"type": "file", "id": "../../../etc/hosts", "sha256": "0" * 64}
    )
    assert any("does not resolve" in f for f in failed("seed-002", a))


def test_a_wrong_fact_fails():
    a = good_answer("seed-001")
    a["facts"]["interval_seconds"] = 60
    assert any(f.startswith("facts:") for f in failed("seed-001", a))


def test_a_fact_of_the_wrong_type_fails():
    a = good_answer("seed-001")
    a["facts"]["interval_seconds"] = "600"
    assert any(f.startswith("facts:") for f in failed("seed-001", a))


def test_false_certainty_on_an_abstain_question_fails():
    assert any(
        "expected abstain" in f
        for f in failed("seed-007", {"disposition": "answer", "facts": {}})
    )


def test_inventing_a_number_for_an_unmeasurable_source_fails():
    f = failed("seed-008", {"disposition": "answer", "facts": {"rows": 412}})
    assert any("expected unmeasurable" in x for x in f)


def test_abstaining_on_an_answerable_question_fails():
    a = {"disposition": "abstain", "reason": "not sure"}
    assert any("expected answer" in f for f in failed("seed-001", a))


def test_abstaining_without_a_reason_fails():
    assert any(
        "without a reason" in f for f in failed("seed-007", {"disposition": "abstain"})
    )


def test_correct_abstention_and_correct_unmeasurable_pass():
    assert (
        gate.grade_one(
            Q["seed-007"], {"disposition": "abstain", "reason": "no such job"}, REPO
        )["verdict"]
        == gate.PASS
    )
    r = gate.grade_one(
        Q["seed-010"],
        {"disposition": "unmeasurable", "reason": "cluster API unreachable"},
        REPO,
    )
    assert r["verdict"] == gate.PASS


def test_no_answer_at_all_fails_rather_than_passes():
    assert failed("seed-007", None)
    assert failed("seed-001", {"disposition": "maybe"})


def test_a_rotted_fixture_is_blind_not_a_pass_and_not_a_fail(tmp_path):
    doc = copy.deepcopy(DOC)
    q = next(x for x in doc["questions"] if x["id"] == "seed-002")
    q["required_sources"][0]["contains"] = "a sentence the decision no longer holds"
    r = gate.grade_one(q, good_answer("seed-002"), REPO)
    assert r["verdict"] == gate.BLIND and r["blind"]
    assert gate.grade_all(doc, {"seed-002": good_answer("seed-002")}, REPO)["exit"] in (
        1,
        2,
    )


def test_validator_names_each_structural_defect():
    bad = copy.deepcopy(DOC)
    bad["questions"].append(copy.deepcopy(bad["questions"][0]))  # duplicate id
    bad["questions"][1]["required_sources"] = []  # answerable, no source
    bad["questions"][7]["required_sources"] = [{"type": "ledger", "id": "x"}]
    bad["questions"][7]["expected"] = "answerable"  # a source type with no reader
    bad["questions"][6].pop("reason")  # abstain with no reason
    errs = "\n".join(gate.validate_set(bad))
    for needle in (
        "duplicate id",
        "at least one required source",
        "no reader here",
        "needs the reason",
    ):
        assert needle in errs


def test_cli_exit_codes(tmp_path, capsys):
    good = {
        q["id"]: good_answer(q["id"])
        for q in DOC["questions"]
        if q["expected"] == "answerable"
    }
    good["seed-007"] = {"disposition": "abstain", "reason": "no such job"}
    for k in ("seed-008", "seed-009", "seed-010"):
        good[k] = {"disposition": "unmeasurable", "reason": "no reader"}
    p = tmp_path / "a.json"
    p.write_text(json.dumps(good))
    assert gate.main(["--grade", str(p)]) == 0
    good["seed-001"]["facts"]["interval_seconds"] = 1
    p.write_text(json.dumps(good))
    assert gate.main(["--grade", str(p)]) == 1
    assert gate.main(["--grade", str(tmp_path / "missing.json")]) == 2

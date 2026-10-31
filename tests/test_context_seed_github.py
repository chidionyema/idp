import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_s = importlib.util.spec_from_file_location(
    "gs", ROOT / "eval" / "estate-context" / "gate_seed.py"
)
g = importlib.util.module_from_spec(_s)
_s.loader.exec_module(g)

Q = {
    "id": "t1",
    "question": "q",
    "expected": "answerable",
    "required_sources": [
        {"type": "github_comment", "id": "o/r#1", "contains": "needle"}
    ],
}


def _answer(sha):
    return {
        "disposition": "answer",
        "citations": [{"type": "github_comment", "id": "o/r#1", "sha256": sha}],
    }


def test_a_real_citation_passes_a_forged_one_fails_and_unreachable_is_blind(
    monkeypatch,
):
    monkeypatch.setattr(g, "GH", lambda ref: ["other", "has the needle here"])
    sha, why = g.github_evidence("o/r#1", "needle")
    assert sha and not why
    assert g.grade_one(Q, _answer(sha))["verdict"] == g.PASS
    assert g.grade_one(Q, _answer("0" * 64))["verdict"] == g.FAIL

    def down(ref):
        raise OSError("offline")

    monkeypatch.setattr(g, "GH", down)
    assert g.grade_one(Q, _answer(sha))["verdict"] == g.BLIND


def test_evidence_that_moved_is_blind_not_pass(monkeypatch):
    monkeypatch.setattr(g, "GH", lambda ref: ["no longer here"])
    assert g.grade_one(Q, _answer("x"))["verdict"] == g.BLIND


def test_a_github_source_needs_contains():
    doc = {
        "schema_version": 1,
        "questions": [
            dict(Q, required_sources=[{"type": "github_comment", "id": "o/r#1"}])
        ],
    }
    assert any("contains" in e for e in g.validate_set(doc))

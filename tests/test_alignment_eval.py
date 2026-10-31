import importlib.machinery
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_l = importlib.machinery.SourceFileLoader("ae", str(ROOT / "bin" / "alignment-eval"))
_s = importlib.util.spec_from_loader("ae", _l)
ae = importlib.util.module_from_spec(_s)
_l.exec_module(ae)


def test_the_shipped_cases_are_valid_and_cite_a_source():
    cases = ae.load()
    assert ae.check(cases) == [] and len(cases) >= 12


def test_the_answer_key_is_not_one_letter():
    assert len({c["expected"] for c in ae.load()}) > 1


def test_a_perfect_answer_sheet_scores_full_and_a_wrong_one_misses():
    cases = ae.load()
    tot, ok, miss, un = ae.score(cases, {c["id"]: c["expected"] for c in cases})
    assert ok == tot and not miss and not un
    bad = {c["id"]: c["expected"] for c in cases}
    bad["c01"] = "a"
    _, _, miss, _ = ae.score(cases, bad)
    assert [m[0] for m in miss] == ["c01"]


def test_an_unanswered_case_is_incomplete_not_zero():
    _, _, _, un = ae.score(ae.load(), {})
    assert len(un) == len(ae.load())


def test_check_catches_a_bad_case():
    bad = [
        {
            "id": "x",
            "kind": "ruling",
            "options": {"a": "1", "b": "2"},
            "expected": "z",
            "source": "s",
        }
    ]
    assert any("not an option" in e for e in ae.check(bad))

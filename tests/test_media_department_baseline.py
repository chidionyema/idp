"""The committed M0 matrix (docs/departments/media/m0-capability-matrix.json) holds its invariants.

bin/media-dept-baseline writes the matrix from commands; this grades the committed file with the
same check() the generator refuses to write without, and proves that check can fail: a row that
claims observed_live without a recorded command, or a test result without the test command, is
refused. A gate that cannot fail is not a gate (AGENTS.md §3).
"""

from __future__ import annotations

import copy
import importlib.machinery
import importlib.util
import json
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_BIN = _REPO_ROOT / "bin" / "media-dept-baseline"
_MATRIX = _REPO_ROOT / "docs" / "departments" / "media" / "m0-capability-matrix.json"


def _load():
    loader = importlib.machinery.SourceFileLoader("media_dept_baseline", str(_BIN))
    spec = importlib.util.spec_from_loader("media_dept_baseline", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


baseline = _load()


def _matrix() -> dict:
    return json.loads(_MATRIX.read_text(encoding="utf-8"))


def test_the_committed_matrix_holds_its_invariants() -> None:
    assert baseline.check(_matrix()) == []


def test_every_charter_field_is_on_every_row() -> None:
    for row in _matrix()["rows"]:
        for name in ("implemented", "observed_live", "tested", "unknown", "broken"):
            assert name in row, (row["id"], name)


def test_observed_live_without_a_command_is_refused() -> None:
    doc = copy.deepcopy(_matrix())
    row = next(r for r in doc["rows"] if r["observed_live"] == "blind")
    row["observed_live"] = "observed"
    row["evidence"] = []
    assert any("observed_live without" in e for e in baseline.check(doc))


def test_a_test_result_without_its_command_is_refused() -> None:
    doc = copy.deepcopy(_matrix())
    row = doc["rows"][0]
    row["tested"] = "pass"
    row["evidence"] = [e for e in row["evidence"] if "pytest" not in e["command"]]
    assert any("without the test command" in e for e in baseline.check(doc))


def test_gaps_name_what_they_extend_and_are_ranked() -> None:
    doc = _matrix()
    assert doc["gaps"], "an empty gap list is a claim the department needs nothing"
    doc_bad = copy.deepcopy(doc)
    doc_bad["gaps"][0]["extend"] = ""
    assert any("does not name" in e for e in baseline.check(doc_bad))

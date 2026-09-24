"""The three-layer selector selects narrowly, and never turns an unknown into a skip.

THE DEFECT THESE TESTS EXIST FOR (measured 2026-09-23, while building it). The first version
of the topology layer matched a node's name as a SUBSTRING of every test file, and admitted
`artifact/idp` -- a node that IS the whole estate -- as a root. Result: 82 of 122 test files
selected (67%), which is the entire suite wearing the label "impact analysis". A selector that
selects everything is worse than no selector, because it reports a saving it does not make.

Two fixes, each pinned by a test below: universal roots are named and excluded, and a test is
matched by what it IMPORTS or by its own module name -- never by which words it contains.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "bin" / "idp-affected-graph"


@pytest.fixture()
def sel(tmp_path, monkeypatch):
    """The selector, with its ROOT redirected at a throwaway tree."""
    spec = importlib.util.spec_from_loader(
        "affected_under_test",
        importlib.machinery.SourceFileLoader("affected_under_test", str(SCRIPT)),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    monkeypatch.setattr(mod, "TESTS_DIR", tmp_path / "tests")
    monkeypatch.setattr(
        mod, "GRAPH_RELATIONS", tmp_path / ".growmos" / "relations.jsonl"
    )
    return mod


def _tree(tmp_path, tests: dict[str, str], entities=None, relations=None):
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".growmos").mkdir(parents=True, exist_ok=True)
    for name, body in tests.items():
        p = tmp_path / "tests" / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body)
    (tmp_path / ".growmos" / "entities.jsonl").write_text(
        "\n".join(json.dumps(e) for e in (entities or []))
    )
    (tmp_path / ".growmos" / "relations.jsonl").write_text(
        "\n".join(json.dumps(r) for r in (relations or []))
    )


# ------------------------------------------------------------------ layer 1


def test_a_test_that_imports_the_changed_module_is_selected(sel, tmp_path):
    _tree(tmp_path, {"test_uses_it.py": "import idp_changed\n"})
    got = sel.layer_code(["idp_changed.py"])
    assert "tests/test_uses_it.py" in got["tests"]


def test_a_test_that_does_not_import_it_is_not_selected(sel, tmp_path):
    """The precision half. A test that merely MENTIONS a name is not affected by it -- matching
    on text is what selected 67% of the suite."""
    _tree(
        tmp_path,
        {"test_unrelated.py": "# idp_changed is mentioned only in this comment\n"},
    )
    got = sel.layer_code(["idp_changed.py"])
    assert got["tests"] == []


def test_no_python_change_selects_nothing(sel, tmp_path):
    _tree(tmp_path, {"test_a.py": "import whatever\n"})
    assert sel.layer_code(["README.md"])["tests"] == []


# ------------------------------------------------------------------ layer 3


def test_a_universal_root_selects_nothing(sel, tmp_path):
    """THE DEFECT. `artifact/idp` is the whole estate; selecting on it is selecting the suite."""
    _tree(
        tmp_path,
        {"test_anything.py": "import os\n"},
        entities=[{"id": "artifact/idp"}, {"id": "component/executor"}],
        relations=[{"from": "artifact/idp", "to": "tool/flux"}],
    )
    got = sel.layer_topology(["artifact/idp/something.yaml"])
    assert got["roots"] == [], "a universal root must not be admitted"
    assert got["tests"] == []


def test_a_unit_root_reaches_only_its_downstream(sel, tmp_path):
    """A change to a producer reaches its consumers, never the other direction."""
    _tree(
        tmp_path,
        {"test_flux.py": "import flux_tool\n", "test_unrelated.py": "import os\n"},
        entities=[{"id": "tool/flux"}],
        relations=[{"from": "tool/flux", "to": "flux_tool"}],
    )
    got = sel.layer_topology(["tool/flux.yaml"])
    assert got["roots"] == ["tool/flux"]
    assert "tests/test_flux.py" in got["tests"]
    assert "tests/test_unrelated.py" not in got["tests"]


def test_a_missing_graph_is_an_error_not_an_empty_graph(sel, tmp_path):
    """An empty graph would select nothing and look green. A missing one must say so."""
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)
    got = sel.layer_topology(["tool/anything.yaml"])
    assert got.get("error"), "a missing graph must be reported, never treated as empty"
    assert got["tests"] == []


def test_a_cycle_in_the_graph_terminates(sel, tmp_path):
    """The closure is bounded by a visit set; a cycle must not spin."""
    _tree(
        tmp_path,
        {"test_a.py": "import x\n"},
        entities=[{"id": "tool/a"}],
        relations=[
            {"from": "tool/a", "to": "tool/b"},
            {"from": "tool/b", "to": "tool/a"},
        ],
    )
    got = sel.layer_topology(["tool/a.yaml"])
    assert "tool/b" in got["downstream"]  # reached once, not forever


# ------------------------------------------------------------------ layer 2 and the join


def test_layer_two_hands_artifacts_to_jev_and_decides_nothing_itself(sel, tmp_path):
    """Layer 2 must not decide. It gathers; Jev judges. A test asserting a decision here would
    be asserting a second model exists."""
    got = sel.layer_prompt(["schema/intent/workload.schema.json"])
    assert got["changed"] == ["schema/intent/workload.schema.json"]
    assert "Jev" in got["why"]


def test_a_non_prompt_change_is_not_layer_two(sel, tmp_path):
    assert sel.layer_prompt(["bin/idp-ci"])["changed"] == []


def test_the_selection_is_the_union_and_a_diff_error_is_blind(
    sel, monkeypatch, tmp_path
):
    """The join. Union, because over-selection costs time and under-selection ships a bug --
    the two are not symmetric. And an unreadable diff is an error the caller can see."""
    _tree(tmp_path, {"test_b.py": "import os\n"})
    monkeypatch.setattr(sel, "_git_diff_names", lambda base: ([], None))
    p = sel.plan("origin/main")
    assert p["selected"] == []
    assert "diff_error" not in p

    monkeypatch.setattr(sel, "_git_diff_names", lambda base: ([], "git refused"))
    p2 = sel.plan("origin/main")
    assert p2["diff_error"] == "git refused"
    assert p2["selected"] == []

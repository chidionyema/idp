"""ADR 0046, executable.

Every assertion in this file can fail, and each one fails for a reason that matters:

- the ADR and the checker must name the same surfaces, or the contract is a document about a
  different system;
- the ADR and the engine must agree on the terminal statuses, or a receipt can promise a
  verdict the engine cannot produce;
- the ADR's named gap (no verify-only entry point) must still BE the gap, or the ADR is
  describing a system that no longer exists;
- the checker must be able to fail AND to pass, or it is a report, not a gate.

The engine is read as source, not imported: `nsvee/engine.py` needs pydantic, and a contract
test that cannot run without a model's dependencies is a contract test that stops running.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
ADR = (
    REPO
    / "docs/decisions/0046-nsvee-verification-is-enforced-at-the-commit-boundary.md"
)
ENGINE = REPO / "nsvee" / "engine.py"
MODULE_PATH = REPO / "platform" / "estate" / "nsvee_enforcement.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "estate_nsvee_enforcement", MODULE_PATH
    )
    assert spec and spec.loader, (
        "platform/estate/nsvee_enforcement.py must be importable"
    )
    module = importlib.util.module_from_spec(spec)
    # The module must be in sys.modules BEFORE it runs: a dataclass resolves its own module
    # out of sys.modules while the class body is being created, and a module that is not
    # registered yet makes that lookup return None (measured 2026-10-27, python 3.9).
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


enforcement = _load_module()


def _adr_text() -> str:
    return ADR.read_text()


def _adr_json_blocks() -> list:
    return [
        json.loads(block)
        for block in re.findall(r"```json\n(.*?)```", _adr_text(), re.S)
    ]


def _adr_surfaces() -> list:
    for block in _adr_json_blocks():
        if isinstance(block, list):
            return block
    raise AssertionError("the ADR must carry a machine-readable list of surfaces")


def _engine_statuses() -> set:
    """The terminal statuses the engine can put in a PipelineReport, read from the source."""
    source = ENGINE.read_text()
    found = set(re.findall(r'status\s*=\s*"([A-Z_]+)"', source))
    found |= set(re.findall(r'PipelineReport\(status="([A-Z_]+)"\)', source))
    return found


def _nsvee_public_methods() -> set:
    tree = ast.parse(ENGINE.read_text())
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "NSVEE":
            return {
                child.name
                for child in node.body
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                and not child.name.startswith("_")
            }
    raise AssertionError("nsvee/engine.py must define a class NSVEE")


# --- the ADR and the code agree -------------------------------------------------


def test_the_adr_and_the_checker_name_the_same_surfaces():
    """A document about a different system is worse than no document."""
    documented = {(s["id"], s["path"], tuple(s["markers"])) for s in _adr_surfaces()}
    enforced = {(s.id, s.path, tuple(s.markers)) for s in enforcement.SURFACES}
    assert documented == enforced


def test_the_adr_and_the_engine_agree_on_the_terminal_statuses():
    assert _engine_statuses() == set(enforcement.STATUSES)
    text = _adr_text()
    for status in _engine_statuses():
        assert status in text, f"the ADR must name the status {status}"


def _adr_engine_symbols() -> list:
    for block in _adr_json_blocks():
        if isinstance(block, dict) and "engine" in block and "symbols" in block:
            return block["symbols"]
    raise AssertionError(
        "the ADR must carry the machine-readable list of engine symbols it cites"
    )


def test_every_engine_symbol_the_adr_cites_exists():
    """A citation that names a symbol the engine does not have is a false statement.

    The ADR cites the engine by symbol rather than by line number, because a line number
    rots on the next edit and a rotted citation is a false one. This is the check that
    keeps those citations true.
    """
    source = ENGINE.read_text()
    for symbol in _adr_engine_symbols():
        leaf = symbol.rsplit(".", 1)[-1]
        assert re.search(rf"\b{re.escape(leaf)}\b", source), (
            f"the ADR cites {symbol}, but {leaf} does not exist in {ENGINE.name}"
        )


def test_the_adr_names_the_gap_the_code_has():
    """The gap is stated, and it is the gap."""
    text = _adr_text()
    assert "no verify-only entry point" in text.lower()
    assert "expectation" in text.lower() and "reality" in text.lower()


# --- the gap is real, and stays visible -----------------------------------------


def test_nsvee_still_has_no_public_verify_only_entry_point():
    """D5's gap. When someone adds `verify()`, this fails and the ADR has to be rewritten."""
    public = _nsvee_public_methods()
    assert "verify" not in public
    assert "post_verify" in public, (
        "the independent-oracle seam is the only verify-shaped door"
    )
    # The seam is a hook: the base implementation checks nothing.
    source = ENGINE.read_text()
    assert "def post_verify(self, out):" in source


def test_the_adr_says_which_artifact_can_be_verified_today():
    """An ADR that hides a limit is a sales pitch."""
    text = _adr_text().lower()
    assert "only verifies what it generated" in text
    assert "nsvee.verify(" in text


# --- the receipt binds -----------------------------------------------------------


def _receipt(**over):
    receipt = {
        "schema": enforcement.SCHEMA,
        "commit": "a" * 40,
        "artifact_digest": "b" * 64,
        "verifier": "nsvee",
        "status": "VERIFIED",
    }
    receipt.update(over)
    return receipt


def test_a_receipt_binds_only_a_verified_artifact():
    enforcement.validate_receipt(_receipt())
    for status in enforcement.STATUSES:
        if status == enforcement.PASSING_STATUS:
            continue
        with pytest.raises(enforcement.ReceiptError) as exc:
            enforcement.validate_receipt(_receipt(status=status))
        assert "not a pass" in str(exc.value)


def test_a_receipt_must_name_the_commit_it_is_about():
    with pytest.raises(enforcement.ReceiptError):
        enforcement.validate_receipt(_receipt(commit="not-a-sha"))
    with pytest.raises(enforcement.ReceiptError) as exc:
        enforcement.validate_receipt(_receipt(), commit="c" * 40)
    assert "not" in str(exc.value)
    enforcement.validate_receipt(_receipt(), commit="a" * 40)


def test_a_receipt_must_name_every_required_field():
    for field in enforcement.REQUIRED_FIELDS:
        receipt = _receipt()
        del receipt[field]
        with pytest.raises(enforcement.ReceiptError) as exc:
            enforcement.validate_receipt(receipt)
        assert field in str(exc.value)


def test_the_digest_binds_the_artifact(tmp_path):
    """Change a byte, and the receipt no longer describes the tree."""
    (tmp_path / "a.py").write_text("x = 1\n")
    (tmp_path / "b.py").write_text("y = 2\n")
    before = enforcement.tree_digest(tmp_path)
    receipt = _receipt(artifact_digest=before)
    enforcement.validate_receipt(receipt)
    enforcement.check_receipt_against_tree(receipt, tmp_path)

    (tmp_path / "b.py").write_text("y = 3\n")
    after = enforcement.tree_digest(tmp_path)
    assert after != before
    with pytest.raises(enforcement.ReceiptError) as exc:
        enforcement.check_receipt_against_tree(
            _receipt(artifact_digest=before), tmp_path
        )
    assert "does not describe this tree" in str(exc.value)
    enforcement.check_receipt_against_tree(_receipt(artifact_digest=after), tmp_path)


# --- the checker can fail, and can pass ------------------------------------------


def _write_surface(root: Path, surface, text: str) -> None:
    path = root / surface.path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_the_checker_fails_when_a_surface_is_missing(tmp_path):
    """A checker that cannot fail is a report."""
    state = enforcement.check_enforcement(tmp_path)
    assert state["ok"] is False
    assert set(state["missing"]) == {s.id for s in enforcement.SURFACES}


def test_the_checker_passes_when_every_surface_enforces(tmp_path):
    for surface in enforcement.SURFACES:
        _write_surface(tmp_path, surface, "\n".join(surface.markers) + "\n")
    state = enforcement.check_enforcement(tmp_path)
    assert state["ok"] is True
    assert state["missing"] == []


def test_the_checker_does_not_lie_about_the_real_tree():
    """Recompute the verdict independently and compare: no self-congratulation."""
    for surface in enforcement.SURFACES:
        path = REPO / surface.path
        markers = (
            [m for m in surface.markers if m.lower() in path.read_text().lower()]
            if path.is_file()
            else []
        )
        reported = next(
            s for s in enforcement.check_surfaces(REPO) if s["id"] == surface.id
        )
        assert set(reported["found"]) == set(markers)
        assert reported["present"] == (
            path.is_file() and len(markers) == len(surface.markers)
        )


def test_the_checker_names_the_gap_today():
    """Phase 1: the enforcement does not exist yet, and the checker says so."""
    state = enforcement.check_enforcement(REPO)
    missing = set(state["missing"])
    assert missing, (
        "the enforcement surfaces must not be reported as wired before they are"
    )
    assert missing <= {s.id for s in enforcement.SURFACES}

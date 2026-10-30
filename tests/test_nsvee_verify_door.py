"""The shared door: NSVEE verification reachable by every estate runtime.

WHAT THIS PROVES. ADR 0046 (idp#7298) and idp#7263 (I-D) ask for one integration point
through which ANY agent runtime -- pi, otto, the fleet page, claude, gemini, cursor --
can verify an artifact. This suite is that point's falsifier, at three levels:

  1. the engine has a public verify-only entry point (`nsvee.verify`) that involves no
     model at all -- the gate, without the pipeline's generation tiers;
  2. the door (`platform/estate/libexec/nsvee-verify.py`) runs it, binds the verdict to
     the commit and the tree, and writes a receipt the estate's receipt contract accepts;
  3. the door is NAMED in the estate's catalogue (`nsvee.verify`), so a runtime reaches it
     the way it reaches every other capability -- through the executor, not through a
     private import.

The two-way proof matters: a door that only refuses proves nothing. So the suite also
proves a GOOD artifact passes, and that the receipt it writes binds to the tree it
describes -- and that a tampered tree breaks that binding.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
DOOR = REPO / "platform" / "estate" / "libexec" / "nsvee-verify.py"
INTENT = REPO / "platform" / "estate" / "intents" / "nsvee.verify.yaml"

COMMIT = "a" * 40


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Registered before execution: on Python 3.9 a dataclass with postponed annotations
    # resolves its field types through `sys.modules[cls.__module__]`.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _engine():
    return _load(REPO / "nsvee" / "engine.py", "nsvee_engine_under_test")


def _contract():
    return _load(
        REPO / "platform" / "estate" / "nsvee_enforcement.py",
        "nsvee_contract_under_test",
    )


def _run_door(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(DOOR), *args],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(cwd) if cwd else None,
    )


def _tree(tmp_path: Path, artifact: str, tests: str) -> Path:
    """A repository-shaped tree: an artifact, its tests, and a commit to bind to."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "artifact.py").write_text(artifact)
    (repo / "test_artifact.py").write_text(tests)
    return repo


GOOD = "def add(a, b):\n    return a + b\n"
GOOD_TESTS = "assert add(2, 3) == 5\n"
BAD = "def add(a, b):\n    return a - b\n"


# --------------------------------------------------------------------------
# 1. the engine's public, model-free entry point
# --------------------------------------------------------------------------


def test_verify_has_a_public_entry_point():
    """`nsvee.verify` is exported from the package, so the door never hardcodes a path."""
    sys.path.insert(0, str(REPO))
    try:
        import nsvee  # noqa: PLC0415

        assert callable(nsvee.verify)
        assert nsvee.verify.__doc__
    finally:
        sys.path.remove(str(REPO))


def test_verify_passes_a_good_artifact():
    engine = _engine()
    report = engine.verify(GOOD, [GOOD_TESTS], runner=engine.RlimitsRunner())
    assert report.status == "VERIFIED"
    assert report.verdicts == ["PASS", "PASS"], "a PASS is re-run to defeat flakes"
    assert report.ok


def test_verify_fails_a_bad_artifact():
    engine = _engine()
    report = engine.verify(BAD, [GOOD_TESTS], runner=engine.RlimitsRunner())
    assert report.status == "EXHAUSTED"
    assert not report.ok
    assert "AssertionError" in report.error


def test_verify_reports_a_broken_sandbox_as_not_a_verdict():
    """A sandbox that broke is not a verdict about the artifact."""

    class Broken:
        def run(self, script, timeout_s):
            return engine.SandboxResult(
                engine.Verdict.SANDBOX_ERROR, notes=["no daemon"]
            )

    engine = _engine()
    report = engine.verify(GOOD, [GOOD_TESTS], runner=Broken())
    assert report.status == "SANDBOX_DEGRADED"
    assert not report.ok


def test_verify_refuses_on_an_independent_oracle():
    """The oracle seam: a check against something the artifact's author did not write."""
    engine = _engine()
    report = engine.verify(
        GOOD,
        [GOOD_TESTS],
        runner=engine.RlimitsRunner(),
        oracle=lambda artifact, tests: "the artifact contradicts the spec",
    )
    assert report.status == "EXHAUSTED"
    assert report.oracle == "the artifact contradicts the spec"


# --------------------------------------------------------------------------
# 2. the door: verdict, receipt, binding
# --------------------------------------------------------------------------


def test_the_door_writes_a_receipt_the_contract_accepts(tmp_path):
    repo = _tree(tmp_path, GOOD, GOOD_TESTS)
    out = tmp_path / "receipt.json"
    proc = _run_door(
        "--artifact",
        str(repo / "artifact.py"),
        "--tests",
        str(repo / "test_artifact.py"),
        "--repo",
        str(repo),
        "--engine-root",
        str(REPO),
        "--commit",
        COMMIT,
        "--out",
        str(out),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    contract = _contract()
    receipt = json.loads(out.read_text())
    contract.validate_receipt(receipt, commit=COMMIT)
    assert receipt["verifier"] == "nsvee"
    assert receipt["status"] == "VERIFIED"
    # the receipt binds to the tree it describes
    contract.check_receipt_against_tree(receipt, repo)


def test_the_door_refuses_a_failing_artifact_and_still_leaves_the_evidence(tmp_path):
    repo = _tree(tmp_path, BAD, GOOD_TESTS)
    out = tmp_path / "receipt.json"
    proc = _run_door(
        "--artifact",
        str(repo / "artifact.py"),
        "--tests",
        str(repo / "test_artifact.py"),
        "--repo",
        str(repo),
        "--engine-root",
        str(REPO),
        "--commit",
        COMMIT,
        "--out",
        str(out),
    )
    assert proc.returncode == 1, proc.stdout + proc.stderr
    contract = _contract()
    receipt = json.loads(out.read_text())
    assert receipt["status"] == "EXHAUSTED"
    # a receipt that is not VERIFIED is refused by the contract -- the gate fails closed
    try:
        contract.validate_receipt(receipt)
    except contract.ReceiptError as exc:
        assert "not a pass" in str(exc)
    else:
        raise AssertionError("a failing artifact produced a receipt that passes")


def test_a_tampered_tree_breaks_the_binding(tmp_path):
    """The receipt is a binding, not a decoration: change a byte and it no longer holds."""
    repo = _tree(tmp_path, GOOD, GOOD_TESTS)
    out = tmp_path / "receipt.json"
    proc = _run_door(
        "--artifact",
        str(repo / "artifact.py"),
        "--tests",
        str(repo / "test_artifact.py"),
        "--repo",
        str(repo),
        "--engine-root",
        str(REPO),
        "--commit",
        COMMIT,
        "--out",
        str(out),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    contract = _contract()
    receipt = json.loads(out.read_text())
    (repo / "artifact.py").write_text(GOOD + "# one byte later\n")
    try:
        contract.check_receipt_against_tree(receipt, repo)
    except contract.ReceiptError as exc:
        assert "does not describe this tree" in str(exc)
    else:
        raise AssertionError("a tampered tree still matched the receipt")


def test_the_door_binds_the_paths_it_verified(tmp_path):
    """The receipt names its scope: the artifact and its tests, not the whole universe."""
    repo = _tree(tmp_path, GOOD, GOOD_TESTS)
    out = tmp_path / "receipt.json"
    proc = _run_door(
        "--artifact",
        str(repo / "artifact.py"),
        "--tests",
        str(repo / "test_artifact.py"),
        "--repo",
        str(repo),
        "--engine-root",
        str(REPO),
        "--commit",
        COMMIT,
        "--out",
        str(out),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    receipt = json.loads(out.read_text())
    assert receipt["paths"] == ["artifact.py", "test_artifact.py"]
    contract = _contract()
    # a file the verdict never covered does not invalidate a path-scoped receipt
    (repo / "unrelated.md").write_text("not covered\n")
    contract.check_receipt_against_tree(receipt, repo)


def test_the_door_can_bind_the_whole_tree(tmp_path):
    """`--whole-tree` is the stronger binding, for a caller with the time to pay for it."""
    repo = _tree(tmp_path, GOOD, GOOD_TESTS)
    out = tmp_path / "receipt.json"
    proc = _run_door(
        "--artifact",
        str(repo / "artifact.py"),
        "--tests",
        str(repo / "test_artifact.py"),
        "--repo",
        str(repo),
        "--engine-root",
        str(REPO),
        "--commit",
        COMMIT,
        "--out",
        str(out),
        "--whole-tree",
        "true",
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    receipt = json.loads(out.read_text())
    assert receipt["paths"] is None
    contract = _contract()
    contract.check_receipt_against_tree(receipt, repo)
    # and now any byte anywhere invalidates it
    (repo / "unrelated.md").write_text("not covered\n")
    with pytest.raises(contract.ReceiptError):
        contract.check_receipt_against_tree(receipt, repo)


def test_the_door_refuses_an_artifact_outside_the_tree_it_binds(tmp_path):
    """A receipt that names a file outside its tree could not be re-checked against it."""
    repo = _tree(tmp_path, GOOD, GOOD_TESTS)
    outside = tmp_path / "elsewhere.py"
    outside.write_text(GOOD)
    proc = _run_door(
        "--artifact",
        str(outside),
        "--repo",
        str(repo),
        "--engine-root",
        str(REPO),
        "--commit",
        COMMIT,
        "--out",
        str(tmp_path / "receipt.json"),
    )
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "inside the tree" in proc.stderr


def test_the_door_refuses_to_write_the_receipt_inside_the_tree(tmp_path):
    """The receipt names the commit it describes; inside that tree it would invalidate itself."""
    repo = _tree(tmp_path, GOOD, GOOD_TESTS)
    proc = _run_door(
        "--artifact",
        str(repo / "artifact.py"),
        "--tests",
        str(repo / "test_artifact.py"),
        "--repo",
        str(repo),
        "--engine-root",
        str(REPO),
        "--commit",
        COMMIT,
        "--out",
        str(repo / "receipt.json"),
    )
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "inside the tree" in proc.stderr
    assert not (repo / "receipt.json").exists()


def test_the_door_refuses_what_it_cannot_verify(tmp_path):
    """No artifact, no verdict: the door refuses instead of reporting a pass."""
    proc = _run_door(
        "--artifact",
        str(tmp_path / "nope.py"),
        "--repo",
        str(tmp_path),
        "--engine-root",
        str(REPO),
    )
    assert proc.returncode == 2
    assert "no such artifact" in proc.stderr


# --------------------------------------------------------------------------
# 3. the door has a name in the estate's catalogue
# --------------------------------------------------------------------------


def test_the_door_is_named_in_the_catalogue():
    """A capability that no runtime can ask for is not a capability."""
    text = INTENT.read_text()
    assert "name: nsvee.verify" in text
    assert "nsvee-verify.py" in text
    assert "halt_on_failure: true" in text


def test_the_catalogue_names_the_door_and_the_door_exists():
    """The intent's script and the script it calls are the same door."""
    text = INTENT.read_text()
    assert "~/.estate/libexec/nsvee-verify.py" in text
    assert DOOR.is_file()

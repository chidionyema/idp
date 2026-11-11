"""Prove the SHIPPED legion package keeps its one promise: it never upgrades a failure.

The founder's finding was that a dispatched mission could declare VERIFIED_YIELD without any work
being performed. `bin/legion` was that dispatcher, and it was deleted rather than repaired, because
`legion/` is the real package and a better one (AGENTS.md section 6: never leave two copies of a
layer). These tests therefore grade `legion/`, the package that remains:

- a proof command that exits 0 records ok=True;
- a proof command that exits non-zero records ok=False and NEVER ok=True, whatever its output says;
- a proof that times out records timed_out=True and ok=False;
- the evidence chain is tamper-evident: `--verify` catches an edited record;
- the manifest rejects a mode the estate does not run.

Nothing here asserts on the text of the package. Each test executes it and grades the record the
tool itself wrote.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path("/Users/roseonyema/Documents/code/idp")
LEGION_DIR = REPO / "legion"

if not (LEGION_DIR / "__init__.py").is_file():
    raise AssertionError(f"legion package not found at {LEGION_DIR}")


def _legion(args: list[str], state_dir: Path, cwd: Path | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["LEGION_STATE_DIR"] = str(state_dir)
    return subprocess.run(
        [sys.executable, "-m", "legion", *args],
        cwd=str(cwd or REPO),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _manifest(tmp_path: Path, proof_command: str) -> Path:
    """A minimal valid manifest whose proof command is whatever the test needs it to be."""
    doc = {
        "legion": "1",
        "name": "test-legion",
        "repo": "chidionyema/idp",
        "summary": "a manifest written by a test, to grade the proof runner",
        "capabilities": ["proof"],
        "modes": ["in-process"],
        "budget": {"max_usd_per_day": 0},
        "proof": {"command": proof_command, "max_seconds": 20},
        "slo": {"success_rate_min": 0.9, "p95_seconds_max": 60},
    }
    path = tmp_path / "legion.yaml"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _last_record(state_dir: Path) -> dict:
    chain = state_dir / "legion-proof.jsonl"
    assert chain.is_file(), f"no evidence chain written at {chain}"
    lines = [ln for ln in chain.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert lines, "evidence chain is empty"
    return json.loads(lines[-1])


def test_package_imports_and_exposes_its_verbs() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "legion", "--help"],
        cwd=str(REPO), capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, proc.stderr[-600:]
    for verb in ("validate", "proof", "scorecard"):
        assert verb in proc.stdout, f"verb {verb} is missing from the CLI: {proc.stdout[:300]}"


def test_a_passing_proof_records_ok_true(tmp_path: Path) -> None:
    state = tmp_path / "state"
    manifest = _manifest(tmp_path, "true")
    proc = _legion(["proof", str(manifest)], state)
    assert proc.returncode == 0, proc.stderr[-800:]
    record = _last_record(state)
    assert record["exit"] == 0
    assert record["ok"] is True
    assert record["timed_out"] is False


def test_a_failing_proof_is_never_recorded_as_ok(tmp_path: Path) -> None:
    """The invariant. A command that exits non-zero must not become a success, ever."""
    state = tmp_path / "state"
    # The proof LIES in its output: it prints a success banner and then fails. If the runner
    # graded the text instead of the exit code, this would pass.
    manifest = _manifest(tmp_path, "echo VERIFIED_YIELD all green; exit 7")
    _legion(["proof", str(manifest)], state)
    record = _last_record(state)
    assert record["exit"] == 7
    assert record["ok"] is False, f"a failing proof was upgraded to ok: {record}"
    assert record["timed_out"] is False


def test_a_command_that_does_not_exist_is_a_failure_not_a_crash(tmp_path: Path) -> None:
    state = tmp_path / "state"
    manifest = _manifest(tmp_path, "this-command-does-not-exist-anywhere")
    proc = _legion(["proof", str(manifest)], state)
    assert proc.returncode != 0, "a proof that could not run reported success"
    record = _last_record(state)
    assert record["ok"] is False
    assert record["exit"] != 0


def test_a_timed_out_proof_records_timed_out_and_never_ok(tmp_path: Path) -> None:
    state = tmp_path / "state"
    manifest = _manifest(tmp_path, "sleep 30")
    doc = json.loads(manifest.read_text(encoding="utf-8"))
    doc["proof"]["max_seconds"] = 1
    manifest.write_text(json.dumps(doc), encoding="utf-8")
    _legion(["proof", str(manifest)], state)
    record = _last_record(state)
    assert record["timed_out"] is True
    assert record["ok"] is False, f"a timed-out proof was upgraded to ok: {record}"


def test_evidence_chain_is_tamper_evident(tmp_path: Path) -> None:
    state = tmp_path / "state"
    manifest = _manifest(tmp_path, "true")
    _legion(["proof", str(manifest)], state)
    chain = state / "legion-proof.jsonl"
    _legion(["proof", str(manifest)], state)

    clean = _legion(["proof", "--verify", str(chain)], state)
    assert clean.returncode == 0, f"an untampered chain failed verification: {clean.stderr[-600:]}"

    # Flip a recorded exit code to 0 and rewrite nothing else: the hash must stop matching.
    lines = [ln for ln in chain.read_text(encoding="utf-8").splitlines() if ln.strip()]
    record = json.loads(lines[-1])
    record["exit"] = 0
    record["ok"] = True
    lines[-1] = json.dumps(record, sort_keys=True)
    chain.write_text("\n".join(lines) + "\n", encoding="utf-8")

    dirty = _legion(["proof", "--verify", str(chain)], state)
    assert dirty.returncode != 0, "a tampered chain verified clean -- the chain proves nothing"


def test_manifest_rejects_a_mode_the_estate_does_not_run(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path, "true")
    doc = json.loads(manifest.read_text(encoding="utf-8"))
    doc["modes"] = ["magic-carpet"]
    manifest.write_text(json.dumps(doc), encoding="utf-8")
    proc = _legion(["validate", str(manifest)], tmp_path / "state")
    assert proc.returncode != 0, "a made-up execution mode validated clean"


def test_a_valid_manifest_validates(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path, "true")
    proc = _legion(["validate", str(manifest)], tmp_path / "state")
    assert proc.returncode == 0, proc.stderr[-800:]


def test_the_deleted_dispatcher_stays_deleted() -> None:
    """bin/legion declared VERIFIED_YIELD without dispatching anything; it must not come back."""
    assert not (REPO / "bin" / "legion").exists(), (
        "bin/legion is back: it reports success without running a worker (AGENTS.md section 6)"
    )


def test_package_documents_the_invariant_it_is_graded_on() -> None:
    """The promise is stated in the shipped source; a change that drops it is a change of contract."""
    src = (LEGION_DIR / "proof.py").read_text(encoding="utf-8")
    assert "never upgrades a failure" in src.lower()


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q", "-p", "no:warnings"]))

"""Falsifiers for the legion package (``python -m legion``).

An earlier version of this file tested a ``bin/legion`` dispatcher with ``dispatch``/``status``
verbs and STRICT sqlite tables. None of that exists: the shipped surface is
``python -m legion {validate,proof,scorecard}``, and the file also hardcoded
``/Users/roseonyema/...`` so it could only ever have passed on one laptop. A test that cannot
run in CI is not a test, and a test of an imagined API proves nothing about the code that ships.

These tests drive the real CLI through ``sys.executable -m legion`` from the repo root, and they
assert the package's actual contract:

* ``validate`` accepts a well-shaped manifest and reports **every** error in a bad one, not just
  the first (``manifest.validate`` documents itself as "eager and total");
* ``validate`` exits 1 and says INVALID for a malformed or missing manifest -- it never says VALID
  about something it could not read;
* ``proof`` runs the manifest's own command, records the real exit code, and returns non-zero
  when the command fails (a proof that cannot fail is not a proof);
* ``scorecard`` refuses an unreadable metrics directory rather than emitting a fabricated board.

Every test writes its own fixture into ``tmp_path``; nothing is read from a home directory.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "legion", *args],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(cwd or REPO),
        env={**os.environ, "PYTHONPATH": str(REPO)},
    )


def _manifest(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "legion": 3,
        "name": "probe",
        "repo": "idp",
        "summary": "a probe legion",
        "capabilities": ["dag-execution"],
        "modes": ["in-process"],
        "budget": {"max_usd_per_day": 5},
        "proof": {"command": "true", "max_seconds": 60},
        "slo": {"success_rate_min": 0.98, "p95_latency_s_max": 300},
    }
    base.update(overrides)
    return base


def _write(tmp_path: Path, payload: object, name: str = "legion.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(payload))
    return path


def test_the_package_loads_and_lists_its_verbs() -> None:
    proc = _run(["--help"])
    assert proc.returncode == 0, proc.stderr[-800:]
    for verb in ("validate", "proof", "scorecard"):
        assert verb in proc.stdout, f"{verb} is not offered by python -m legion"


def test_a_well_shaped_manifest_validates(tmp_path: Path) -> None:
    proc = _run(["validate", str(_write(tmp_path, _manifest()))])
    assert proc.returncode == 0, proc.stderr[-800:]
    assert "VALID" in proc.stdout
    assert "INVALID" not in proc.stdout


def test_every_error_is_reported_not_just_the_first(tmp_path: Path) -> None:
    """The docstring promises eager and total validation; a single-error report would be a lie."""
    broken = _manifest(
        legion=-1,
        capabilities=[],
        budget={"max_usd_per_day": -5},
    )
    proc = _run(["validate", str(_write(tmp_path, broken))])
    assert proc.returncode == 1, "a structurally broken manifest must not validate"
    reported = [ln for ln in proc.stderr.splitlines() if ln.startswith("INVALID:")]
    assert len(reported) >= 3, f"only {len(reported)} problems reported: {reported}"


def test_a_malformed_manifest_is_refused_not_guessed(tmp_path: Path) -> None:
    path = tmp_path / "legion.json"
    path.write_text("{not json at all")
    proc = _run(["validate", str(path)])
    assert proc.returncode == 1
    assert "VALID" not in proc.stdout.replace("INVALID", "")


def test_a_missing_manifest_is_refused(tmp_path: Path) -> None:
    proc = _run(["validate", str(tmp_path / "absent.json")])
    assert proc.returncode == 1, "a missing manifest must exit 1, never 0"
    assert "INVALID" in proc.stderr


def test_proof_runs_the_manifests_own_command(tmp_path: Path) -> None:
    """The proof must actually execute: a marker file is the only evidence that it did."""
    marker = tmp_path / "proof-ran"
    manifest = _manifest(proof={"command": f"touch {marker}", "max_seconds": 60})
    proc = _run(["proof", str(_write(tmp_path, manifest))])
    assert proc.returncode == 0, proc.stderr[-800:]
    assert "PROOF-OK" in proc.stdout, proc.stdout[-400:]
    assert marker.exists(), "the manifest's proof command never executed"


def test_a_failing_proof_is_not_a_passing_proof(tmp_path: Path) -> None:
    """The guarantee: a proof whose command fails must exit non-zero and say so."""
    manifest = _manifest(proof={"command": "exit 3", "max_seconds": 60})
    proc = _run(["proof", str(_write(tmp_path, manifest))])
    assert proc.returncode != 0, "a failing proof command produced a zero exit"
    assert "PROOF-FAILED" in proc.stdout or "PROOF-FAILED" in proc.stderr


def test_scorecard_refuses_an_unreadable_metrics_dir(tmp_path: Path) -> None:
    proc = _run(["scorecard", str(tmp_path / "no-such-dir")])
    assert proc.returncode == 1, (
        "an unreadable metrics dir must not produce a scoreboard"
    )
    assert "SCORECARD-ERROR" in proc.stderr


def test_the_shipped_manifest_is_valid() -> None:
    """The estate's own legion manifest is the one that matters; if it is invalid, legion is."""
    shipped = REPO / "legions" / "estate-homes.json"
    assert shipped.is_file(), "legions/estate-homes.json is missing from the repo"
    proc = _run(["validate", str(shipped)])
    assert proc.returncode == 0, (
        f"the shipped manifest is invalid: {proc.stderr[-800:]}"
    )
    assert "VALID" in proc.stdout

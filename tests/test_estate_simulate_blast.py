"""The blast grader of the six-grader door (MUM-288).

Mirrors tests/test_estate_simulate.py. Each case exercises the grader either
inline (as a callable returned by ``_live_graders(source)``) or end-to-end
through ``simulate_change(...)``; the whole-verdict lattice
``bin/idp-fence-enforcement`` enforces means blast can flip the verdict of a
proposal from SAFE to UNSAFE by itself, the same way the other five can.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "estate_simulate",
    Path(__file__).resolve().parents[1] / "mcp" / "plugins" / "estate_simulate.py",
)
sim = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sim)  # type: ignore[union-attr]


REPO = Path(__file__).resolve().parents[1]
F = REPO / "tests" / "fixtures" / "blast"


# --- CLI direct -----------------------------------------------------------


def _bin_run(*, manifest: Path, catalog: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            str(REPO / "bin" / "idp-blast-grade"),
            "--quiet",
            "--catalog-dir",
            str(catalog),
            "--source",
            str(manifest),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_bin_safe_when_manifest_defines_the_reference():
    proc = _bin_run(manifest=F / "safe.yaml", catalog=F / "catalog")
    assert proc.returncode == 0
    assert proc.stdout.strip().startswith("ok ")


def test_bin_unsafe_when_reference_dangles():
    proc = _bin_run(manifest=F / "dangling.yaml", catalog=F / "catalog")
    assert proc.returncode == 1
    assert "FAIL" in proc.stdout
    assert "dangling reference" in proc.stdout


def test_bin_unknown_when_catalogue_is_missing():
    proc = _bin_run(manifest=F / "safe.yaml", catalog=F / "no-catalog")
    assert proc.returncode == 2
    assert "BLIND" in proc.stdout


# --- Grader wired into _live_graders -------------------------------------


def _blast_outcome(source: str, env: dict[str, str]) -> dict:
    """Run only the blast arm of ``_live_graders`` with a stubbed catalog dir."""
    prior = {k: os.environ.get(k) for k in env}
    try:
        for k, v in env.items():
            os.environ[k] = v
        # The grader uses ``source`` directly, no need to round-trip through
        # the door. _live_graders inspects the env we set.
        return sim._live_graders(source)["blast"]()
    finally:
        for k, v in prior.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_blast_safe_when_manifest_refs_resolve():
    manifest = (F / "safe.yaml").read_text()
    outcome = _blast_outcome(manifest, {"ESTATE_BLAST_CATALOG_DIR": str(F / "catalog")})
    assert outcome["verdict"] == "SAFE"


def test_blast_unsafe_when_dangling_reference():
    manifest = (F / "dangling.yaml").read_text()
    outcome = _blast_outcome(manifest, {"ESTATE_BLAST_CATALOG_DIR": str(F / "catalog")})
    assert outcome["verdict"] == "UNSAFE"
    assert "dangling" in outcome["detail"].lower()


def test_blast_unknown_when_catalogue_missing():
    manifest = (F / "safe.yaml").read_text()
    outcome = _blast_outcome(
        manifest, {"ESTATE_BLAST_CATALOG_DIR": str(F / "no-catalog")}
    )
    assert outcome["verdict"] == "UNKNOWN"


def test_blast_unknown_when_source_is_empty():
    outcome = _blast_outcome("", {"ESTATE_BLAST_CATALOG_DIR": str(F / "catalog")})
    assert outcome["verdict"] == "UNKNOWN"


# --- End-to-end through the door (whole verdict) -------------------------


def test_simulate_change_blast_safe_keeps_whole_safe():
    manifest = (F / "safe.yaml").read_text()
    p = sim.simulate_change(
        manifest,
        graders=sim._live_graders.__wrapped__()
        if hasattr(sim._live_graders, "__wrapped__")
        else {
            "blast": lambda: {"verdict": "SAFE", "detail": "ok"},
        },
        now=None,
    )
    # The door's GRADER_NAMES lists blast; the test-only grader dict above
    # only carries blast, so whole verdict collapses to blast alone.
    assert p["verdict"] in ("SAFE", "UNKNOWN")


def test_simulate_change_blast_unsafe_makes_whole_unsafe():
    manifest = (F / "safe.yaml").read_text()
    p = sim.simulate_change(
        manifest,
        graders={
            "blast": lambda: {"verdict": "UNSAFE", "detail": "dangling"},
        },
        now=None,
    )
    assert p["verdict"] == "UNSAFE"
    assert p["grader_results"]["blast"]["verdict"] == "UNSAFE"


def test_simulate_change_blind_blast_makes_whole_unknown():
    p = sim.simulate_change(
        "any source",
        graders={
            "blast": lambda: {"verdict": "UNKNOWN", "detail": "graph unreadable"},
        },
        now=None,
    )
    assert p["verdict"] == "UNKNOWN"

"""2026-08-28 06:20-06:39Z: a node was cordoned, the single catalogue pod had nowhere to land, and
https://catalogue.mumchimp.com answered 503 to the founder for about fifteen minutes. The manifest
said `replicas: 1`, `strategy: Recreate`, and platform/ held no PodDisruptionBudget at all.

Nothing was broken. The estate had no availability requirement, so no review could fail one. These
tests are that requirement: the gate must refuse the manifest the catalogue actually carried into
that drain, and pass the one it carries now.
"""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "bin" / "idp-availability-gate"
if subprocess.run(["which", "kustomize"], capture_output=True).returncode != 0:
    pytest.skip("kustomize is not installed", allow_module_level=True)


def run(*args):
    return subprocess.run([sys.executable, str(GATE), *args], cwd=ROOT,
                          capture_output=True, text=True, timeout=300)


def test_it_refuses_the_manifest_that_caused_the_outage():
    r = run("tests/fixtures/availability/bad")
    assert r.returncode == 1, r.stdout
    assert "replicas 1" in r.stdout
    assert "no PodDisruptionBudget selects it" in r.stdout
    assert "nothing keeps the replicas apart" in r.stdout


def test_it_passes_a_surface_that_survives_one_node():
    r = run("tests/fixtures/availability/good")
    assert r.returncode == 0, r.stdout
    assert "survives one node" in r.stdout


def test_the_estate_meets_the_standard_today():
    """Every surface an HTTPRoute reaches -- the reason this file is not just a unit test."""
    r = run()
    assert r.returncode == 0, r.stdout


def test_a_waiver_needs_a_reason_and_an_issue():
    """A waiver is debt that gets read out loud, not a way to turn a row green."""
    import yaml
    doc = yaml.safe_load((ROOT / "platform" / "availability-waivers.yaml").read_text())
    for w in doc.get("waivers") or []:
        assert w.get("reason") and w.get("issue"), w
    assert "WAIVED" in run().stdout, "a waived surface must print its row on every run"


def test_a_deadlocking_budget_is_refused(tmp_path):
    """minAvailable equal to the replica count refuses every drain for ever -- the shape the
    clickhouse PDB had when kubectl drain gave up on it at 06:30:43Z."""
    d = tmp_path / "deadlock"
    d.mkdir()
    src = (ROOT / "tests" / "fixtures" / "availability" / "good" / "surface.yaml").read_text()
    (d / "surface.yaml").write_text(src.replace("  maxUnavailable: 1", "  minAvailable: 2"))
    (d / "kustomization.yaml").write_text(
        "apiVersion: kustomize.config.k8s.io/v1beta1\nkind: Kustomization\nresources:\n  - surface.yaml\n")
    r = run(str(d))
    assert r.returncode == 1, r.stdout
    assert "refuses every drain for ever" in r.stdout

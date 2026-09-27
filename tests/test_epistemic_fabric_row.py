"""crew#974 P1: the CI/incident wire for the newsroom -- the Flux row that adopts
platform/epistemic-fabric, and the replica counts scoped to cicd + incidents only."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _render(path: str) -> list[dict]:
    exe = shutil.which("kustomize")
    cmd = [exe, "build", path] if exe else ["kubectl", "kustomize", path]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    return [d for d in yaml.safe_load_all(r.stdout) if d]


def test_a_flux_row_adopts_the_epistemic_fabric():
    rows = [d for d in _render("clusters/oke") if d["kind"] == "Kustomization"]
    fabric_rows = [r for r in rows if r["metadata"]["name"] == "epistemic-fabric"]
    assert fabric_rows, (
        f"no Flux row named epistemic-fabric (rows: {[r['metadata']['name'] for r in rows]})"
    )
    row = fabric_rows[0]
    assert row["spec"]["path"] == "./platform/epistemic-fabric"
    assert row["spec"]["prune"] is False


def test_only_cicd_and_incidents_run():
    objs = _render("platform/epistemic-fabric")
    replicas = {
        o["metadata"]["name"]: o["spec"]["replicas"]
        for o in objs
        if o["kind"] == "Deployment"
    }
    assert replicas == {
        "epistemic-ingest-github": 0,
        "epistemic-ingest-slack": 0,
        "epistemic-ingest-cicd": 1,
        "epistemic-ingest-incidents": 1,
    }

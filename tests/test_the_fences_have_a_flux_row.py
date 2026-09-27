"""Something Flux applies must render platform/ns-fences, or every fence is an orphan git can no longer change.

c96359f4 (2026-09-26) cut clusters/oke to 7 rows and the ns-fences row went with platform.yaml.
Nothing failed: the live fences stayed, frozen. #4411 then merged a spire-mgmt fence fix that could
never land, and SPIRE sat without workload attestation. This renders the root the way Flux does,
follows the row to its path, renders that too, and requires the policy #4411 added to come out.
"""

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


def test_the_root_renders_a_row_that_renders_the_fences():
    rows = [d for d in _render("clusters/oke") if d["kind"] == "Kustomization"]
    fences = [
        r for r in rows if r["spec"]["path"].rstrip("/") == "./platform/ns-fences"
    ]
    assert fences, (
        f"no Flux row applies ./platform/ns-fences (rows: {[r['metadata']['name'] for r in rows]})"
    )
    # the generated policies name ${ESTATE_*_CIDR}; without the substitution they are invalid
    assert {"kind": "ConfigMap", "name": "estate-config"} in fences[0]["spec"][
        "postBuild"
    ]["substituteFrom"]

    objs = _render(fences[0]["spec"]["path"])
    names = {
        (o["kind"], o["metadata"].get("namespace"), o["metadata"]["name"]) for o in objs
    }
    assert ("NetworkPolicy", "spire-mgmt", "allow-kubelet-egress") in names

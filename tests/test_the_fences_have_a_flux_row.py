"""Something must apply platform/ns-fences, or every fence is an orphan git can no longer change.

c96359f4 (2026-09-26) cut clusters/oke to 7 rows and the ns-fences row went with platform.yaml.
Nothing failed: the live fences stayed, frozen. #4411 then merged a spire-mgmt fence fix that could
never land, and SPIRE sat without workload attestation. This pins the row the root applies.
"""

from __future__ import annotations

from pathlib import Path

import yaml

OKE = Path(__file__).resolve().parents[1] / "clusters" / "oke"


def test_the_root_applies_a_row_whose_path_is_the_fences():
    listed = yaml.safe_load((OKE / "kustomization.yaml").read_text())["resources"]
    rows = [
        d
        for f in listed
        if f.endswith(".yaml") and (OKE / f).is_file()
        for d in yaml.safe_load_all((OKE / f).read_text())
        if d and d.get("kind") == "Kustomization"
    ]
    fences = [r for r in rows if r["spec"]["path"].rstrip("/") == "./platform/ns-fences"]
    assert fences, f"no Flux row applies ./platform/ns-fences (rows: {[r['metadata']['name'] for r in rows]})"
    spec = fences[0]["spec"]
    # the generated policies name ${ESTATE_*_CIDR}; without the substitution they are invalid
    assert {"kind": "ConfigMap", "name": "estate-config"} in spec["postBuild"]["substituteFrom"]

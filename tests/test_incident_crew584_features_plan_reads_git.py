"""crew#584: the platform options are priced and sized from git, never from a typed table.

The incident: the 6-core node came from 23139de6 with no utilisation number anywhere, and the
first draft of the feature register typed floors that double-counted a switch two features share
(27 GiB on paper for a 24 GiB node). The rule (LAW 51 memoize): one source of truth each. The plan
sums the requests git holds under each Flux switch's path, prices the node from
platform/oci/variables.tf, and flips real Kustomizations. Both ways in one run (LAW 45 step 3).
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import pathlib
import re
import shutil

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
_loader = importlib.machinery.SourceFileLoader(
    "features", str(ROOT / "bin" / "idp-features")
)
feat = importlib.util.module_from_spec(
    importlib.util.spec_from_loader("features", _loader)
)
_loader.exec_module(feat)

LEAN = {
    "traces": "lean",
    "logs-metrics-store": "lean",
    "alerting-healing": "lean",
    "workflows": "lean",
    "agent-memory": "lean",
    "model-routing": "lean",
    "agent-gateway": "off",
    "founder-screen": "off",
    "health-checks": "lean",
    "chaos-drills": "lean",
    "science": "off",
    "staging": "off",
}


def test_every_selectable_switch_is_a_real_kustomization():
    reg, kust = feat.register(), feat.kustomizations("oke")
    for f in reg["features"]:
        for t in f["tiers"]:
            if t.get("status") in feat.SELECTABLE:
                missing = set(t.get("switches", [])) - set(kust)
                assert not missing, (
                    f"{f['name']}/{t['name']} names no Kustomization: {missing}"
                )
    assert not set(reg["core"]["switches"]) - set(kust)


def test_price_comes_from_variables_tf_not_the_register():
    shape = feat.node_shape()
    # the module's own defaults price today's node; the register carries no usd_month at all
    assert feat.price(
        shape["worker_ocpus"], shape["worker_memory_gb"], shape
    ) == pytest.approx(
        (
            (shape["worker_ocpus"] - shape["free_ocpus"])
            * shape["a1_ocpu_usd_per_hour"]
            + (shape["worker_memory_gb"] - shape["free_memory_gb"])
            * shape["a1_memory_gb_usd_per_hour"]
        )
        * feat.HOURS_MONTH,
        abs=0.01,
    )
    assert feat.price(shape["free_ocpus"], shape["free_memory_gb"], shape) == 0.0
    assert (
        "usd_month"
        not in (ROOT / "platform" / "features" / "features.yaml").read_text()
    )


def test_plan_counts_a_shared_switch_once_and_lean_fits_the_free_node():
    reg = feat.register()
    lines, _, _ = feat.plan(
        reg, {"staging": "off"}
    )  # staging is planned: a typed floor, no switch yet
    total = next(line for line in lines if line.startswith("total "))
    cpu = float(re.search(r"cpu ([0-9.]+)", total).group(1))
    # a plain sum of the per-feature lines double-counts `observability` (traces + logs-metrics-store)
    per_feature = sum(
        float(re.search(r"cpu ([0-9.]+)", line).group(1))
        for line in lines
        if line.startswith("feature ")
    )
    kust = feat.kustomizations("oke")
    on = (
        next(line for line in lines if line.startswith("switches on: "))
        .split(": ", 1)[1]
        .split()
    )
    unique = sum(feat.requests_under(kust[s][1])["cpu"] for s in on)
    assert cpu == pytest.approx(unique, abs=0.05), (
        "the total is the sum over the unique switches"
    )
    core = sum(feat.requests_under(kust[s][1])["cpu"] for s in reg["core"]["switches"])
    obs = feat.requests_under(kust["observability"][1])["cpu"]
    assert per_feature + core - cpu == pytest.approx(obs, abs=0.1), (
        "observability is counted once, not twice"
    )
    lean, fits_today, smallest = feat.plan(reg, LEAN)
    assert smallest["name"] == "A1-2-12", lean[-3]
    assert fits_today
    assert any(line.startswith("node today ") for line in lean)


def test_enable_flips_the_switch_in_a_copy_of_the_cluster_files(tmp_path, monkeypatch):
    work = tmp_path / "idp"
    for d in (
        "clusters",
        "platform/features",
        "platform/oci",
        "platform/temporal",
        "platform/hindsight",
    ):
        shutil.copytree(ROOT / d, work / d, dirs_exist_ok=True)
    (work / "platform").mkdir(exist_ok=True)
    monkeypatch.setattr(feat, "ROOT", work)
    monkeypatch.setattr(feat, "REGISTER", work / "platform/features/features.yaml")
    monkeypatch.setattr(feat, "VARIABLES", work / "platform/oci/variables.tf")
    feat.set_suspend("oke", "temporal", True)
    assert feat.kustomizations("oke")["temporal"][2] is True
    before = (work / "clusters/oke/platform.yaml").read_text()
    assert "# Suspended 2026-08-25" in before, "comments around the switch are kept"
    rc = feat.main(["enable", "workflows", "enterprise"])
    assert rc == 0
    assert feat.kustomizations("oke")["temporal"][2] is False
    # the same doc count: the edit changed one line, not the file's shape
    assert before.count("\n---\n") == (
        work / "clusters/oke/platform.yaml"
    ).read_text().count("\n---\n")
    # staging shipped in crew#584 CP-H, so a still-planned tier is staged in the register copy
    reg = work / "platform/features/features.yaml"
    reg.write_text(
        reg.read_text().replace(
            "      - name: namespace\n        switches: [staging]\n",
            "      - name: namespace\n        switches: [staging]\n      - name: node\n        switches: []\n"
            "        floor: { cpu: 1.0, memory_gb: 2.0, storage_gb: 10 }\n        status: planned\n",
            1,
        )
    )
    assert feat.main(["enable", "staging", "namespace"]) == 0
    with pytest.raises(SystemExit, match="not selectable"):
        feat.main(["enable", "staging", "node"])
    with pytest.raises(SystemExit, match="has no tier"):
        feat.main(["enable", "workflows", "huge"])

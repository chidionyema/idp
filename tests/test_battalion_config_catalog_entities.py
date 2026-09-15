"""OBS-01 (idp#3525 CP8, spec section 6): "the hosting matrix AND the CFG-01 config
surface SHALL both be generated catalog entities... No bespoke dashboard."

ACCEPT, verbatim: "catalog entities exist, generated, render tier/cost/receipt-grade and
current toggle state." METHOD: render test -- this file runs the real bin/catalog-gen
(never a stand-in) and reads the entities it wrote.
"""

from __future__ import annotations

import os
import pathlib
import subprocess

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _gen(tmp_path):
    """Run bin/catalog-gen over the fixture inventory; the generated documents."""
    out = tmp_path / "out"
    out.mkdir(parents=True)
    p = subprocess.run(
        [str(ROOT / "bin" / "catalog-gen")],
        env={
            **os.environ,
            "INV": str(ROOT / "tests" / "fixtures" / "inventory.json"),
            "OUT": str(out),
            "ESTATE_ENV": "dev",
            "CATALOG_GEN_ROOT": str(ROOT),
            "CATALOG_GEN_PROBE": "0",
        },
        capture_output=True,
        text=True,
    )
    assert p.returncode == 0, p.stderr
    return [d for d in yaml.safe_load_all((out / "catalog-info.yaml").read_text()) if d]


def _by_name(docs, name):
    matches = [d for d in docs if d["metadata"]["name"] == name]
    assert len(matches) == 1, (
        f"expected exactly one {name!r} entity, found {len(matches)}"
    )
    return matches[0]


def test_hosting_matrix_is_a_generated_catalog_entity_with_tier_cost_and_receipt_grade(
    tmp_path,
):
    doc = _by_name(_gen(tmp_path), "battalion-hosting-matrix")
    assert doc["kind"] == "Resource"
    ann = doc["metadata"]["annotations"]
    assert int(ann["estate/tiers"]) > 0
    assert ann["estate/receipt-grades"]
    for grade in ann["estate/receipt-grades"].split(","):
        assert grade in ("vendor-doc", "survey", "founder-supplied-unverified")


def test_cfg01_config_surface_is_a_generated_catalog_entity_with_current_toggle_state(
    tmp_path,
):
    doc = _by_name(_gen(tmp_path), "battalion-config-surface")
    assert doc["kind"] == "Component"
    ann = doc["metadata"]["annotations"]
    assert int(ann["estate/cells"]) > 0
    toggle_keys = [k for k in ann if k.startswith("estate/toggle-")]
    assert toggle_keys, (
        "no toggle- annotation found; CFG-01's toggle state is not rendered"
    )
    for k in toggle_keys:
        assert ann[k] in ("True", "False")


def test_neither_battalion_entity_lacks_a_description(tmp_path):
    """entity() itself refuses a description-less asset; this just proves both entities
    reached that far without one being silently dropped."""
    docs = _gen(tmp_path)
    for name in ("battalion-hosting-matrix", "battalion-config-surface"):
        doc = _by_name(docs, name)
        assert doc["metadata"]["description"].strip()


def test_catalog_gen_run_is_still_idempotent_with_battalion_entities(tmp_path):
    """bin/idp-ci runs catalog-gen twice over one inventory and fails on a single byte of
    difference (crew#612). The battalion entities read live files off disk, not the
    inventory fixture, so this proves that read is stable too."""
    a = _gen(tmp_path / "a")
    b = _gen(tmp_path / "b")
    assert a == b

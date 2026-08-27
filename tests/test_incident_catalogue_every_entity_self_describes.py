"""Founder, 2026-08-27: "need the catalogue description fields populated, cant have components
that cannt self describe" and "i thought i could see all my interface urls in one spot".
Measured that morning: 349 of 362 entities in catalog/catalog-info.yaml had no description and
the URLs were spread over 65 entities. Rung 4, incident test. Two rules:

  1. every entity catalog-gen writes carries a non-empty metadata.description, and the generator
     refuses (exit 1, names the entity) rather than write one without -- proved both ways;
  2. one Component `interfaces` carries every link any other entity publishes, so the portal has
     one card that answers "what are my URLs".
"""
import importlib.machinery
import importlib.util
import os
import pathlib
import subprocess
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
GEN = ROOT / "bin" / "catalog-gen"
FIX = ROOT / "tests" / "fixtures" / "inventory.json"


def _generate(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    r = subprocess.run([sys.executable, str(GEN)], env={**os.environ, "INV": str(FIX), "OUT": str(out),
                                                        "ESTATE_ENV": "dev", "CATALOG_GEN_ROOT": str(ROOT)},
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return [d for d in yaml.safe_load_all((out / "catalog-info.yaml").read_text()) if d]


def test_every_entity_has_a_description_and_the_interfaces_card_has_every_link(tmp_path):
    docs = _generate(tmp_path)
    blank = [f"{d['kind']}/{d['metadata']['name']}" for d in docs
             if not str(d["metadata"].get("description", "")).strip()]
    assert not blank, blank
    published = {l["url"] for d in docs if d["metadata"]["name"] != "interfaces"
                 for l in d["metadata"].get("links", [])}
    # crew#503 CP6: the founder surfaces reach the portal through the founder-catalog ConfigMap
    # (Flux, zone substituted), not through this generator, but the card still carries their links.
    zones = {yaml.safe_load(f.read_text())["data"]["ESTATE_ZONE"] for f in (ROOT / "clusters").glob("*/estate-config.yaml")}
    assert len(zones) == 1, zones
    zone = zones.pop()
    founder = [d for d in yaml.safe_load_all((ROOT / "backstage/founder/catalog-info.yaml").read_text()) if d]
    published |= {l["url"].replace("${ESTATE_ZONE}", zone) for d in founder for l in d["metadata"].get("links", [])}
    card = [d for d in docs if d["metadata"]["name"] == "interfaces"]
    assert len(card) == 1
    on_card = {l["url"] for l in card[0]["metadata"]["links"]}
    assert published and on_card == published, published ^ on_card


def test_generator_refuses_an_entity_without_a_description():
    loader = importlib.machinery.SourceFileLoader("catalog_gen", str(GEN))
    mod = importlib.util.module_from_spec(importlib.util.spec_from_loader("catalog_gen", loader))
    loader.exec_module(mod)
    with pytest.raises(SystemExit) as e:
        mod.entity("Component", "mute", "Mute", "service", {}, [], description="  ")
    assert "mute" in str(e.value) and "describe" in str(e.value)
    assert "description: Speaks." in mod.entity("Component", "loud", "Loud", "service", {}, [], description="Speaks.")

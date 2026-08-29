"""Incident, 2026-08-29 (crew#307, run 33229461240): after the portal's namespace was rebuilt its
database never came back. Kyverno `no-provider-storage-class` refused the new claim, because the
API server injects the cluster default StorageClass (`oci-bv` on OKE) before admission. The rule
judged the cluster, not what we wrote. Founder: "a name-regex on a running cluster is not a
portability guard". The guard for what we write is where we write it.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "platform" / "edge" / "provider-independence.yaml"


def _rules() -> dict[str, dict]:
    doc = yaml.safe_load(POLICY.read_text())
    return {r["name"]: r for r in doc["spec"]["rules"]}


def test_no_admission_rule_judges_a_claim_s_storage_class():
    for name, rule in _rules().items():
        kinds = [k for m in rule.get("match", {}).get("any", []) for k in m.get("resources", {}).get("kinds", [])]
        assert "PersistentVolumeClaim" not in kinds, (
            f"{name}: judges PersistentVolumeClaim; the API server rewrites the claim's class before "
            "admission, so this refuses the cluster default (2026-08-29, run 33229461240)")


def test_the_static_gate_refuses_a_provider_storage_class_in_the_platform_tree():
    gate = (ROOT / "bin" / "cloud-agnostic-gate").read_text()
    m = re.search(r"PATTERN = re\.compile\(\s*r?[\"'](.+?)[\"']", gate, re.S)
    assert m, "bin/cloud-agnostic-gate no longer defines PATTERN; update this guard"
    rx = re.compile(m.group(1), re.I)
    assert rx.search("storageClassName: oci-bv"), "the static gate must catch a provider class where it is written"

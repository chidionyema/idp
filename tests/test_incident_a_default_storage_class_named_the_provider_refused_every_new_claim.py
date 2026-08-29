"""Incident, 2026-08-29 (run 33229461240): the portal's namespace was recreated and its database
never came back. Every new PersistentVolumeClaim was denied by the provider-independence policy,
because the API server injects the cluster default StorageClass (`oci-bv` on OKE) before Kyverno
judges the claim. The claims that had worked simply predated the policy.

The guard: every cluster layer defines a default StorageClass, and its name is one the policy
accepts. The regex is read from the policy itself so the two cannot drift apart.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "platform" / "edge" / "provider-independence.yaml"
CLUSTERS = sorted(p for p in (ROOT / "clusters").iterdir() if p.is_dir())


def _storage_class_regex() -> re.Pattern[str]:
    doc = yaml.safe_load(POLICY.read_text())
    rules = {r["name"]: r for r in doc["spec"]["rules"]}
    key = rules["no-provider-storage-class"]["validate"]["deny"]["conditions"]["any"][0]["key"]
    m = re.search(r"regex_match\('([^']+)'", key)
    assert m, "no-provider-storage-class no longer holds a regex_match; update this guard"
    return re.compile(m.group(1))


def _storage_classes(cluster: Path) -> list[dict]:
    out = []
    for f in sorted(cluster.glob("*.yaml")):
        for d in yaml.safe_load_all(f.read_text()):
            if isinstance(d, dict) and d.get("kind") == "StorageClass":
                out.append(d)
    return out


@pytest.mark.parametrize("cluster", CLUSTERS, ids=[c.name for c in CLUSTERS])
def test_every_cluster_layer_defines_one_default_storage_class_the_policy_accepts(cluster: Path):
    defaults = [
        sc for sc in _storage_classes(cluster)
        if (sc.get("metadata", {}).get("annotations") or {}).get(
            "storageclass.kubernetes.io/is-default-class") == "true"
    ]
    assert len(defaults) == 1, (
        f"{cluster.name}: {len(defaults)} default StorageClass objects; exactly one, so a claim "
        "that names no class binds here and passes no-provider-storage-class")
    name = defaults[0]["metadata"]["name"]
    assert not _storage_class_regex().match(name), (
        f"{cluster.name}: default StorageClass {name!r} is a provider name; the policy would deny "
        "every claim that relies on the default")
    assert defaults[0].get("provisioner"), f"{cluster.name}: default StorageClass names no provisioner"


def test_the_policy_accepts_the_estate_name_and_still_refuses_the_provider_default():
    rx = _storage_class_regex()
    assert not rx.match("estate-block")
    assert rx.match("oci-bv"), "the guard would pass vacuously if the policy stopped naming oci"

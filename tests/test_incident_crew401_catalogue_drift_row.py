"""crew#401 CP4, rung 4. A hostname the cluster publishes that the catalogue does not name is a
surface the founder cannot find from the portal. bin/idp-catalogue-drift grades the cluster-state
receipt against backstage/**/catalog-info.yaml. Proved both ways on receipt bodies on disk, plus
BLIND for a receipt that predates the collector change; the collector and the oke-check step are
asserted so the row cannot silently stop running."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ROW = ROOT / "bin" / "idp-catalogue-drift"
ZONE = re.search(r"^\s*ESTATE_ZONE:\s*(\S+)", (ROOT / "clusters/oke/estate-config.yaml").read_text(), re.M).group(1)


@pytest.fixture(autouse=True)
def _no_live_locations(tmp_path: Path, monkeypatch):
    """Incident, flux/image-updates ci 2026-08-29: with the inherited env the row fetched the real
    `type: url` locations from raw.githubusercontent.com and answered BLIND ... HTTP Error 429,
    so bdd-suites was red on every image bump and idp#719 never merged. A test reads no network:
    the default config here names no url location; a test that wants one sets IDP_APP_CONFIG itself."""
    cfg = tmp_path / "app-config.none.yaml"
    cfg.write_text("catalog:\n  locations: []\n")
    monkeypatch.setenv("IDP_APP_CONFIG", str(cfg))


def _grade(body: dict, tmp_path: Path) -> subprocess.CompletedProcess:
    f = tmp_path / "receipt"
    f.write_text("ok cluster-state at x nodes=1 ready=1\n" + json.dumps(body) + "\n")
    return subprocess.run([sys.executable, str(ROW), "--receipt", str(f)], capture_output=True, text=True)


def test_an_unregistered_hostname_fails_and_is_named(tmp_path):
    r = _grade({"hostnames": [f"catalogue.{ZONE}", f"nobody-registered-this.{ZONE}"]}, tmp_path)
    assert r.returncode == 1 and r.stdout.startswith("FAIL") and f"nobody-registered-this.{ZONE}" in r.stdout, r.stdout


def test_every_catalogued_hostname_passes(tmp_path):
    r = _grade({"hostnames": [f"catalogue.{ZONE}", f"CATALOGUE.{ZONE}"], "services_unlisted": []}, tmp_path)
    assert r.returncode == 0 and r.stdout.startswith("ok      catalogue-drift  0 unregistered"), r.stdout


def test_a_receipt_without_hostnames_is_blind_never_clean(tmp_path):
    r = _grade({"nodes": []}, tmp_path)
    assert r.returncode == 2 and r.stdout.startswith("BLIND"), r.stdout


def test_the_collector_and_the_workflow_carry_the_row():
    cs = (ROOT / "platform/state/cluster-state.yaml").read_text()
    assert "gateway.networking.k8s.io" in cs and '"httproutes"' in cs, "RBAC must allow listing HTTPRoutes"
    assert '"hostnames": hostnames' in cs, "the receipt body must carry the hostnames list"
    assert '"services_unlisted": services_unlisted' in cs, "the receipt body must carry the live Services without a catalogue entity (crew#307)"
    wf = (ROOT / ".github/workflows/oke-check.yml").read_text()
    assert "run: bin/idp-catalogue-drift" in wf, "oke-check must run the row"


def test_incident_crew401_a_failing_cluster_state_row_still_grades_the_hostnames(tmp_path):
    """First live row (run 33033770482) came back BLIND because the reader exits 1 whenever the
    cluster-state grade is FAIL (Flux not ready, crew#406). The hostnames list is independent of
    that grade, so the grader must read the body and grade it."""
    fake = tmp_path / "idp-cluster-state"
    fake.write_text("#!/bin/sh\necho 'FAIL    cluster-state  flux not ready'\n"
                    "echo '" + json.dumps({"hostnames": [f"catalogue.{ZONE}"], "services_unlisted": []}) + "'\nexit 1\n")
    fake.chmod(0o755)
    r = subprocess.run([sys.executable, str(ROW)], capture_output=True, text=True,
                       env={**__import__("os").environ, "IDP_CLUSTER_STATE_BIN": str(fake)})
    assert r.returncode == 0 and r.stdout.startswith("ok"), r.stdout + r.stderr


def test_incident_crew401_a_product_onboarded_by_url_is_registered_and_an_unfetchable_location_is_blind(tmp_path, monkeypatch):
    """CP4 gap (1), 2026-08-27: the row read only backstage/**/catalog-info.yaml, so
    www.mumchimp.com (a product onboarded by URL, crew#282) was FAIL on every receipt. Both ways:
    a host named by a url location passes; a location that does not fetch is BLIND, never FAIL."""
    product = tmp_path / "catalog-info.yaml"
    product.write_text("spec:\n  links:\n    - url: https://shop.${ESTATE_ZONE}/\n")
    cfg = tmp_path / "app-config.yaml"
    cfg.write_text(f"catalog:\n  locations:\n    - type: url\n      target: file://{product}\n")
    monkeypatch.setenv("IDP_APP_CONFIG", str(cfg))
    r = _grade({"hostnames": [f"shop.{ZONE}"], "services_unlisted": []}, tmp_path)
    assert r.returncode == 0 and r.stdout.startswith("ok      catalogue-drift  0 unregistered"), r.stdout
    cfg.write_text(f"catalog:\n  locations:\n    - type: url\n      target: file://{tmp_path}/missing.yaml\n")
    r = _grade({"hostnames": [f"shop.{ZONE}"], "services_unlisted": []}, tmp_path)
    assert r.returncode == 2 and r.stdout.startswith("BLIND") and "missing.yaml" in r.stdout, r.stdout


# crew#307 (founder, 2026-08-29): the hostname list let every UI without a public address through.
# The rest of the inventory is the live Service list: a Service without backstage.io/kubernetes-id
# is a FAIL that names it; a receipt that does not carry the list is BLIND, never a clean row.
def test_incident_crew307_a_live_service_without_a_catalogue_entity_fails_and_is_named(tmp_path):
    r = _grade({"hostnames": [f"catalogue.{ZONE}"], "services_unlisted": ["llm/litellm-db"]}, tmp_path)
    assert r.returncode == 1 and r.stdout.startswith("FAIL") and "llm/litellm-db" in r.stdout, r.stdout


def test_incident_crew307_a_receipt_without_the_service_list_is_blind_never_clean(tmp_path):
    r = _grade({"hostnames": [f"catalogue.{ZONE}"]}, tmp_path)
    assert r.returncode != 0 and r.stdout.startswith("BLIND") and "services_unlisted" in r.stdout, r.stdout


def test_incident_crew307_the_cluster_refuses_an_interface_outside_the_inventory():
    """The guard is the control plane, not this file: Enforce, Service and HTTPRoute, label pattern."""
    import yaml
    pol = next(d for d in yaml.safe_load_all((ROOT / "platform/edge/require-catalogue-entity.yaml").read_text()) if d)
    rule = pol["spec"]["rules"][0]
    assert rule["validate"]["failureAction"] == "Enforce", "founder ruling 2026-08-29: the cluster refuses, it does not report"
    assert set(rule["match"]["any"][0]["resources"]["kinds"]) == {"Service", "HTTPRoute"}
    assert rule["validate"]["pattern"]["metadata"]["labels"]["backstage.io/kubernetes-id"] == "?*"
    kz = (ROOT / "platform/edge/kustomization.yaml").read_text()
    assert "require-catalogue-entity.yaml" in kz and "catalogue-entity-exception.yaml" in kz


def test_incident_crew307_the_receipt_reads_every_cluster_policy_live():
    """SRE sweep 2026-08-29: the collector read exceptions but never the policies, so no Enforce was
    proved by the backend. RBAC lists clusterpolicies and the body carries their actions and Ready."""
    cs = (ROOT / "platform/state/cluster-state.yaml").read_text()
    assert '"clusterpolicies"' in cs, "RBAC must allow listing ClusterPolicies"
    assert "/apis/kyverno.io/v1/clusterpolicies" in cs and '"kyverno_policies": kyverno_policies' in cs

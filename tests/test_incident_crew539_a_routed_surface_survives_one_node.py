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
    doc = yaml.safe_load((ROOT / "platform" / "availability.yaml").read_text())
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


def test_a_gateway_nobody_declared_is_blind():
    """The hole the first version of this gate had. Seven surfaces were graded green while the
    single Traefik pod they all entered through ran replicas 1, because no manifest says which
    workload implements a Gateway. An unclaimed parentRef is BLIND, never absent."""
    r = run("tests/fixtures/availability/undeclared-gateway")
    assert r.returncode == 2, r.stdout
    assert "names no workload implementing it" in r.stdout


def test_the_front_door_itself_is_graded():
    """prospector/prospector-edge -> edge/traefik, by platform/availability.yaml."""
    r = run()
    assert r.returncode == 0, r.stdout
    assert "edge/traefik" in r.stdout and "implements prospector/prospector-edge" in r.stdout


def test_ci_green_without_the_cluster_armed_is_refused(tmp_path):
    """CI is not the cluster. A namespace that passes here must carry the label that arms
    platform/scheduling/require-availability.yaml, or a kubectl apply nobody reviewed can put the
    surface back on one pod."""
    d = tmp_path / "unarmed"
    d.mkdir()
    src = (ROOT / "tests" / "fixtures" / "availability" / "good" / "surface.yaml").read_text()
    (d / "surface.yaml").write_text(src.replace("    availability.idp/tier: founder-facing\n", ""))
    (d / "kustomization.yaml").write_text(
        "apiVersion: kustomize.config.k8s.io/v1beta1\nkind: Kustomization\nresources:\n  - surface.yaml\n")
    r = run(str(d))
    assert r.returncode == 1, r.stdout
    assert "does not carry availability.idp/tier=founder-facing" in r.stdout


def test_admission_refuses_what_ci_refuses(tmp_path):
    """The same standard at admission (platform/scheduling/require-availability.yaml), proved with
    the Kyverno CLI the estate already runs: a single-replica Deployment in a founder-facing
    namespace is rejected, and the estate's real manifests pass."""
    if subprocess.run(["which", "kyverno"], capture_output=True).returncode != 0:
        pytest.skip("kyverno CLI is not installed")
    policy = ROOT / "platform" / "scheduling" / "require-availability.yaml"
    values = tmp_path / "values.yaml"
    values.write_text("apiVersion: cli.kyverno.io/v1alpha1\nkind: Values\nmetadata:\n  name: values\n"
                      "namespaceSelector:\n  - name: mcp\n    labels:\n"
                      "      availability.idp/tier: founder-facing\n")
    good = subprocess.run(["kustomize", "build", "platform/mcp"], cwd=ROOT,
                          capture_output=True, text=True, timeout=300).stdout
    (tmp_path / "good.yaml").write_text(good)
    import yaml
    bad = []
    for o in yaml.safe_load_all(good):
        if o and o.get("kind") == "Deployment" and o["metadata"]["name"] == "estate-mcp":
            o["spec"]["replicas"] = 1
            o["spec"]["template"]["spec"].pop("affinity", None)
            o["spec"]["template"]["spec"].pop("topologySpreadConstraints", None)
            bad.append(o)
    assert bad, "fixture: no estate-mcp Deployment rendered"
    (tmp_path / "bad.yaml").write_text(yaml.safe_dump_all(bad))

    def kyv(f):
        return subprocess.run(["kyverno", "apply", str(policy), "--resource", str(tmp_path / f),
                               "--values-file", str(values)],
                              capture_output=True, text=True, timeout=300).stdout

    refused = kyv("bad.yaml")
    assert "fail: 2" in refused, refused
    assert "runs at least 2 replicas" in refused
    passed = kyv("good.yaml")
    assert "fail: 0" in passed, passed

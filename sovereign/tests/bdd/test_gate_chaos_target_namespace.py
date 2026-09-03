"""Binds features/chaos/chaos-target-namespace-labelled.feature (crew#292 CP4, crew#297). Rule:
when the chart filters namespaces, the namespace the experiment targets is declared in git with
the inject label. tests/test_incident_chaos_target_namespace_unlabelled.py proves it both ways."""
from pathlib import Path

import pytest
import yaml
from pytest_bdd import given, scenarios, then

scenarios("features/chaos/chaos-target-namespace-labelled.feature")

IDP = Path(__file__).resolve().parents[3]
INJECT = "chaos-mesh.org/inject"


def _docs(p: Path):
    return [d for d in yaml.safe_load_all(p.read_text()) if isinstance(d, dict)]


@pytest.fixture
def state() -> dict:
    return {}


@given("platform/chaos/mesh/helmrelease.yaml sets enableFilterNamespace true")
def _filter(state: dict) -> None:
    hr = [d for d in _docs(IDP / "platform/chaos/mesh/helmrelease.yaml") if d.get("kind") == "HelmRelease"]
    assert hr and hr[0]["spec"]["values"].get("enableFilterNamespace") is True


@given("platform/chaos/backstage-pod-kill.yaml selects namespace backstage")
def _schedule(state: dict) -> None:
    found = []
    for f in (IDP / "platform/chaos").rglob("*.yaml"):
        for d in _docs(f):
            if d.get("kind") == "Schedule" and d["metadata"]["name"] == "backstage-pod-kill":
                found.append(d)
    assert found, "no Schedule backstage-pod-kill under platform/chaos"
    ns = str(found[0]["spec"]).replace("'", '"')
    assert '"namespaces": ["backstage"]' in ns, found[0]["spec"]


@then("the Namespace backstage declared under platform/ carries chaos-mesh.org/inject: enabled")
def _label(state: dict) -> None:
    """Found by globbing, not at a literal path: crew#488 moved the manifest to
    platform/backstage/namespace/base/namespace.yaml so OKE could order the namespace as its own
    Flux row, and a gate that names a path grades where a file sits instead of what it says."""
    ns = [d for f in sorted((IDP / "platform").rglob("*.yaml")) for d in _docs(f)
          if d.get("kind") == "Namespace" and d["metadata"].get("name") == "backstage"]
    assert ns, "no Namespace backstage declared anywhere under platform/"
    assert [d for d in ns if d["metadata"].get("labels", {}).get(INJECT) == "enabled"], ns


@then("tests/test_incident_chaos_target_namespace_unlabelled.py refuses a target namespace without it")
def _incident_test_runs(state: dict) -> None:
    import subprocess, sys
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                        "tests/test_incident_chaos_target_namespace_unlabelled.py"], cwd=IDP, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr

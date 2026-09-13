"""The tailscale row waited on a Deployment that has never existed.

Spec: docs/specs/2026-09-13-healthcheck-names-a-real-object.md
Rule: healthcheck-names-a-real-object (rules.yaml)

THE INCIDENT. The `tailscale` Kustomization declared:

    healthChecks:
      - apiVersion: apps/v1
        kind: Deployment
        name: tailscale-operator
        namespace: tailscale

The release is named `tailscale-operator`. The chart it pins (1.102.3) emits
`Deployment/operator`. Nothing has ever created a Deployment by the other name, so
the wait could not be satisfied and the row reported, for days:

    health check failed after 10m0.026651003s: timeout waiting for:
      [Deployment/tailscale/tailscale-operator status: 'NotFound']

`NotFound` is the tell that separates this from an object that is merely
unhealthy: an unhealthy object reports its status, and a missing one reports
`NotFound` forever. Four rows depend on `tailscale` -- guacamole among them -- and
were held out of the cluster the whole time. CI was green throughout, because the
manifest is valid YAML naming a plausible object.

The name the chart emits was read from this estate's own compiler, run on
2026-09-13: `bin/idp-compile-helm` rendered 33/33 releases and 646 objects, and
the tailscale release produced `Deployment/operator`. That is the only place
outside the running cluster where the real name exists, which is why the gate
grades the compiled document rather than the cluster.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
GATE = REPO / "bin" / "idp-healthcheck-exists"
FIXTURES = REPO / "tests" / "fixtures" / "healthcheck-exists"


def load_gate():
    """Load the gate by path, the way workspace.yaml loads a code location.

    `spec_from_file_location` cannot infer a loader for a file with no `.py`
    suffix -- the gate is `bin/idp-healthcheck-exists` -- so the loader is named
    explicitly. Loading it rather than shelling out for the pure functions keeps
    the contract tests fast; the CLI tests below run the real thing.
    """
    loader = importlib.machinery.SourceFileLoader("healthcheck_exists", str(GATE))
    spec = importlib.util.spec_from_loader("healthcheck_exists", loader)
    assert spec and spec.loader, "the gate must load by path (LAW 45)"
    mod = importlib.util.module_from_spec(spec)
    sys.modules["healthcheck_exists"] = mod
    loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def gate():
    return load_gate()


def run_gate(root: Path, compiled: Path, cluster: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["python3", str(GATE), "--root", str(root), str(compiled), str(cluster)],
        capture_output=True,
        text=True,
    )


# --- the incident, exactly --------------------------------------------------


def test_the_defect_that_shipped_is_refused() -> None:
    """A health check naming `tailscale-operator` is refused.

    Nothing in this tree creates a Deployment by that name, and the gate must say
    so. A gate that passes on the tree where the defect lived is decoration.
    """
    bad = FIXTURES / "bad"
    r = run_gate(bad, bad / "compiled.json", bad / "cluster.yaml")
    assert r.returncode == 1, (
        f"the gate must refuse the shipped defect; it answered {r.returncode}:\n{r.stdout}"
    )
    assert "tailscale-operator" in r.stdout
    assert "nothing" in r.stdout or "no release" in r.stdout


def test_the_same_row_naming_the_real_deployment_passes() -> None:
    """`Deployment/operator` is what the chart emits, so the row is correct."""
    good = FIXTURES / "good"
    r = run_gate(good, good / "compiled.json", good / "cluster.yaml")
    assert r.returncode == 0, (
        f"the gate must pass the correct name; it answered {r.returncode}:\n{r.stdout}"
    )


# --- the live tree ----------------------------------------------------------


def test_the_tailscale_row_in_this_tree_names_the_chart_deployment() -> None:
    """The fix, read out of the manifest rather than trusted.

    This is the assertion that keeps the row fixed: the name in the health check
    and the name the chart emits must be the same string.
    """
    platform = REPO / "clusters" / "oke" / "platform.yaml"
    docs = [d for d in yaml.safe_load_all(platform.read_text()) if d]
    row = next(
        d
        for d in docs
        if d.get("kind") == "Kustomization" and d["metadata"]["name"] == "tailscale"
    )
    checks = row["spec"]["healthChecks"]
    assert len(checks) == 1, (
        f"the row should carry one health check, found {len(checks)}"
    )
    hc = checks[0]
    assert hc["kind"] == "Deployment"
    assert hc["namespace"] == "tailscale"
    assert hc["name"] == "operator", (
        f"the chart emits Deployment/operator; the row waits on {hc['name']!r}. A wait on "
        "an object nothing creates reports NotFound forever."
    )


# --- the contract the gate carries ------------------------------------------


def test_a_helmrelease_check_is_satisfied_by_the_release_rendering(
    gate, tmp_path: Path
) -> None:
    """A HelmRelease is a wait on the release object, which no chart emits.

    It can only be answered from the release list itself, so the gate must not
    report every such wait as missing -- 34 false failures on the first run.
    """
    compiled = tmp_path / "compiled.json"
    compiled.write_text(
        json.dumps(
            {
                "summary": {"rendered": 1, "objects": 0, "failed": 0, "total": 1},
                "releases": [
                    {
                        "name": "hindsight",
                        "namespace": "hindsight",
                        "objects": [],
                        "error": None,
                    }
                ],
            }
        )
    )
    cluster = tmp_path / "cluster.yaml"
    cluster.write_text(
        yaml.safe_dump(
            {
                "apiVersion": "kustomize.toolkit.fluxcd.io/v1",
                "kind": "Kustomization",
                "metadata": {"name": "hindsight"},
                "spec": {
                    "healthChecks": [
                        {
                            "apiVersion": "helm.toolkit.fluxcd.io/v2",
                            "kind": "HelmRelease",
                            "name": "hindsight",
                            "namespace": "hindsight",
                        }
                    ]
                },
            }
        )
    )
    assert run_gate(tmp_path, compiled, cluster).returncode == 0


def test_a_missing_helmrelease_is_refused(gate, tmp_path: Path) -> None:
    """A wait on a release that does not render is the same defect one kind over."""
    compiled = tmp_path / "compiled.json"
    compiled.write_text(
        json.dumps(
            {"summary": {}, "releases": [{"name": "other", "namespace": "elsewhere"}]}
        )
    )
    cluster = tmp_path / "cluster.yaml"
    cluster.write_text(
        yaml.safe_dump(
            {
                "kind": "Kustomization",
                "metadata": {"name": "x"},
                "spec": {
                    "healthChecks": [
                        {"kind": "HelmRelease", "name": "ghost", "namespace": "nowhere"}
                    ]
                },
            }
        )
    )
    assert run_gate(tmp_path, compiled, cluster).returncode == 1


def test_an_object_an_operator_makes_at_runtime_is_ungraded_and_said_so(
    gate, tmp_path: Path
) -> None:
    """`Deployment/healing/estate` is made by the k8sgpt operator from a K8sGPT object.

    No chart emits it. Its Kustomization reports Ready=True, so the object does
    exist -- refusing the check would be a guard refusing correct work (LAW 38).
    Counting it as verified would be a gate claiming a proof it does not have. It
    is reported as ungraded, and the count is printed.
    """
    root = tmp_path / "tree"
    (root / "platform" / "healing").mkdir(parents=True)
    (root / "platform" / "healing" / "k8sgpt.yaml").write_text(
        "kind: K8sGPT\nmetadata:\n  name: estate\n"
    )
    compiled = tmp_path / "compiled.json"
    compiled.write_text(json.dumps({"summary": {}, "releases": []}))
    cluster = tmp_path / "cluster.yaml"
    cluster.write_text(
        yaml.safe_dump(
            {
                "kind": "Kustomization",
                "metadata": {"name": "healing-analyzer"},
                "spec": {
                    "healthChecks": [
                        {"kind": "Deployment", "name": "estate", "namespace": "healing"}
                    ]
                },
            }
        )
    )
    r = run_gate(root, compiled, cluster)
    assert r.returncode == 0
    assert "ungraded" in r.stdout, "an ungraded check must be reported, never silent"


def test_a_deployment_nothing_anywhere_creates_is_never_ungraded(
    gate, tmp_path: Path
) -> None:
    """The distinction the whole gate turns on.

    An operator MAY make an object, but only when a custom resource in this tree
    names it. `tailscale-operator` had nothing naming it -- no chart, no manifest,
    no operator input -- so "an operator probably makes it" must not save it.
    """
    root = tmp_path / "tree"
    (root / "platform").mkdir(parents=True)
    (root / "platform" / "k8sgpt.yaml").write_text(
        "kind: K8sGPT\nmetadata:\n  name: estate\n"
    )
    compiled = tmp_path / "compiled.json"
    compiled.write_text(json.dumps({"summary": {}, "releases": []}))
    cluster = tmp_path / "cluster.yaml"
    cluster.write_text(
        yaml.safe_dump(
            {
                "kind": "Kustomization",
                "metadata": {"name": "tailscale"},
                "spec": {
                    "healthChecks": [
                        {
                            "kind": "Deployment",
                            "name": "tailscale-operator",
                            "namespace": "tailscale",
                        }
                    ]
                },
            }
        )
    )
    r = run_gate(root, compiled, cluster)
    assert r.returncode == 1, (
        "a Deployment no chart, manifest or operator input names is missing, not ungraded"
    )
    assert "tailscale-operator" in r.stdout


def test_the_compiled_estate_does_render_the_deployment_the_row_names() -> None:
    """The end-to-end proof, against this estate's own compiler output.

    Skipped when the compiled document is absent, so the suite never needs the
    cluster or a helm run to be meaningful -- and the skip says so.
    """
    compiled = REPO / "docs" / "compiled-helm.json"
    if not compiled.is_file():
        pytest.skip(
            "docs/compiled-helm.json is not present; run bin/idp-compile-helm to produce it"
        )
    doc = json.loads(compiled.read_text())
    found = []
    for release in doc.get("releases") or []:
        for obj in release.get("objects") or []:
            if obj.get("kind") == "Deployment" and obj.get("namespace") == "tailscale":
                found.append(obj.get("name"))
    assert "operator" in found, (
        f"the compiled estate must render Deployment/operator, got {found}"
    )
    assert "tailscale-operator" not in found, (
        "no chart renders Deployment/tailscale-operator; that is the defect"
    )

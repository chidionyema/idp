"""Incident 2026-08-26: idp#139 installed the Chaos Mesh HelmRelease and the cluster-wide Kyverno
set refused its DaemonSet and Deployment (22 rule failures); the chaos-mesh row stalled and no
pod ever ran. Rule (rung 4, incident test): the rendered Chaos Mesh chart is admitted with the
PolicyException the row ships, and the same exception scoped to any other namespace refuses it,
so the exception loosens nothing outside chaos-mesh. Kyverno must also be told to honour
exceptions from the namespace the file uses, or the object is decoration.

Needs the kyverno and helm CLIs and the prospector policy checkout named by ESTATE_CODE; without
them the test is BLIND and says so, never green."""
import os
import pathlib
import re
import shutil
import subprocess

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
ESTATE_CODE = pathlib.Path(os.environ.get("ESTATE_CODE", ROOT.parent))
POLICIES = ESTATE_CODE / "prospector-main" / "deploy" / "k8s" / "policies"
MESH = ROOT / "platform" / "chaos" / "mesh"


def _blind():
    for tool in ("kyverno", "helm", "kubectl"):
        if not shutil.which(tool):
            pytest.skip(f"BLIND: {tool} not installed")
    if not (POLICIES / "kustomization.yaml").exists():
        pytest.skip(f"BLIND: no policy checkout at {POLICIES} (set ESTATE_CODE)")


def _docs(path):
    return [d for d in yaml.safe_load_all(path.read_text()) if d]


def _render_chart(tmp_path):
    docs = _docs(MESH / "helmrelease.yaml")
    hr = next(d for d in docs if d["kind"] == "HelmRelease")
    repo = next(d for d in docs if d["kind"] == "HelmRepository")
    spec = hr["spec"]["chart"]["spec"]
    values = tmp_path / "values.yaml"
    values.write_text(yaml.safe_dump(hr["spec"].get("values", {})))
    r = subprocess.run(["helm", "template", hr["metadata"]["name"], spec["chart"], "--repo", repo["spec"]["url"],
                        "--version", spec["version"], "-n", hr["metadata"]["namespace"], "-f", str(values)],
                       capture_output=True, text=True)
    if r.returncode:
        pytest.skip(f"BLIND: helm template failed (offline?): {r.stderr[-300:]}")
    out = tmp_path / "chaos.yaml"
    out.write_text(r.stdout)
    return out


def _apply(tmp_path, resource, exception=None):
    policies = tmp_path / "policies.yaml"
    policies.write_text(subprocess.run(["kubectl", "kustomize", str(POLICIES)], check=True,
                                       capture_output=True, text=True).stdout)
    cmd = ["kyverno", "apply", str(policies), "--resource", str(resource)]
    if exception:
        cmd += ["--exception", str(exception)]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    summary = [line for line in out.splitlines() if line.startswith("pass:")]
    assert summary, out
    counts = {k.strip(): int(v) for k, v in (kv.split(": ") for kv in summary[-1].split(","))}
    counts["failing_policies"] = set(re.findall(r"policy ([a-z0-9-]+) -> resource \S+ failed", out))
    return counts


def test_chaos_mesh_is_admitted_with_its_exception_and_refused_without(tmp_path):
    _blind()
    rendered = _render_chart(tmp_path)
    shipped = MESH / "exception.yaml"
    with_it = _apply(tmp_path, rendered, shipped)
    assert with_it["fail"] == 0 and with_it["skip"] > 0, with_it
    elsewhere = tmp_path / "elsewhere.yaml"
    doc = _docs(shipped)[0]
    doc["spec"]["match"]["any"][0]["resources"]["namespaces"] = ["some-other-namespace"]
    elsewhere.write_text(yaml.safe_dump(doc))
    without = _apply(tmp_path, rendered, elsewhere)
    assert without["fail"] > 0, without


def test_kyverno_honours_exceptions_from_the_namespace_the_row_uses():
    exc = _docs(MESH / "exception.yaml")[0]
    assert exc["kind"] == "PolicyException"
    hr = next(d for d in _docs(ROOT / "platform" / "edge" / "kyverno.yaml") if d["kind"] == "HelmRelease")
    feat = hr["spec"]["values"]["features"]["policyExceptions"]
    assert feat["enabled"] is True
    assert feat["namespace"] == exc["metadata"]["namespace"], (feat, exc["metadata"])
    assert "chaos-mesh" in exc["spec"]["match"]["any"][0]["resources"]["namespaces"]
    assert "exception.yaml" in (MESH / "kustomization.yaml").read_text()


def test_the_exception_waives_exactly_the_policies_the_chart_fails(tmp_path):
    """idp#141 review (code-0d): the first draft waived all 26 policies while the chart failed 13.
    A waiver for a policy the workload already passes is a hole nobody measured."""
    _blind()
    rendered = _render_chart(tmp_path)
    failing = _apply(tmp_path, rendered)["failing_policies"]
    excepted = {e["policyName"] for e in _docs(MESH / "exception.yaml")[0]["spec"]["exceptions"]}
    assert excepted == failing, {"waived for nothing": sorted(excepted - failing), "missing": sorted(failing - excepted)}

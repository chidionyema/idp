"""Incident 2026-08-26 (crew#388): SigNoz 0.138.0 shipped without k8s-infra, so the estate had
LiteLLM traces and no pod, node or kubelet metrics; the data map (crew#320) graded the whole
cluster_live domain BLIND. Rule (rung 4, incident test): the rendered k8s-infra chart is
admitted with the PolicyException platform/edge ships; the same exception scoped to another
namespace refuses the DaemonSet; and the exception names exactly the policies the render fails,
so a policy the chart already passes is never waived.

Needs the kyverno, helm and kubectl CLIs and the prospector policy checkout named by
ESTATE_CODE; without them the test is BLIND and says so, never green."""
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
OBS = ROOT / "platform" / "observability"
EXCEPTION = ROOT / "platform" / "edge" / "k8s-infra-exception.yaml"


def _blind():
    for tool in ("kyverno", "helm", "kubectl"):
        if not shutil.which(tool):
            pytest.skip(f"BLIND: {tool} not installed")
    if not (POLICIES / "kustomization.yaml").exists():
        pytest.skip(f"BLIND: no policy checkout at {POLICIES} (set ESTATE_CODE)")


def _docs(path):
    return [d for d in yaml.safe_load_all(path.read_text()) if d]


def _render_chart(tmp_path):
    hr = next(d for d in _docs(OBS / "k8s-infra.yaml") if d["kind"] == "HelmRelease")
    repo = next(d for d in _docs(OBS / "signoz.yaml") if d["kind"] == "HelmRepository")
    spec = hr["spec"]["chart"]["spec"]
    values = tmp_path / "values.yaml"
    values.write_text(yaml.safe_dump(hr["spec"].get("values", {})))
    ns = hr["spec"].get("targetNamespace") or "observability"
    # the release name the way helm-controller derives it (crew#483): releaseName, else
    # <targetNamespace>-<name> when targetNamespace is set, else name
    release = hr["spec"].get("releaseName") or (f"{ns}-{hr['metadata']['name']}" if hr["spec"].get("targetNamespace") else hr["metadata"]["name"])
    r = subprocess.run(["helm", "template", release, spec["chart"], "--repo", repo["spec"]["url"],
                        "--version", spec["version"], "-n", ns, "-f", str(values)],
                       capture_output=True, text=True)
    if r.returncode:
        pytest.skip(f"BLIND: helm template failed (offline?): {r.stderr[-300:]}")
    # helm-controller installs no `helm test` hooks (the chart's *-test-connection pods), and
    # bin/idp-kyverno-render drops them the same way; admission never sees them.
    kept = [d for d in yaml.safe_load_all(r.stdout)
            if d and "helm.sh/hook" not in (d.get("metadata", {}).get("annotations") or {})]
    out = tmp_path / "k8s-infra.yaml"
    out.write_text(yaml.safe_dump_all(kept))
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


def test_incident_crew388_k8s_infra_admitted_with_its_waiver_and_refused_elsewhere(tmp_path):
    _blind()
    rendered = _render_chart(tmp_path)
    with_it = _apply(tmp_path, rendered, EXCEPTION)
    assert with_it["fail"] == 0 and with_it["skip"] > 0, with_it
    doc = _docs(EXCEPTION)[0]
    assert doc["metadata"]["namespace"] == "kyverno", "Kyverno honours exceptions from namespace kyverno only (crew#325)"
    elsewhere = tmp_path / "elsewhere.yaml"
    doc["spec"]["match"]["any"][0]["resources"]["namespaces"] = ["some-other-namespace"]
    elsewhere.write_text(yaml.safe_dump(doc))
    without = _apply(tmp_path, rendered, elsewhere)
    assert without["fail"] > 0, without
    waived = {e["policyName"] for e in _docs(EXCEPTION)[0]["spec"]["exceptions"]}
    assert waived == without["failing_policies"], (
        f"waiver must name exactly the failing policies: waived {sorted(waived)}, failing {sorted(without['failing_policies'])}")

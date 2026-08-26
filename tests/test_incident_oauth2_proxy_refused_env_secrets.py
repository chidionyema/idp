"""Incident 2026-08-26 (idp#146 live): the oauth2-proxy Deployment was refused by the cluster policy
secrets-not-from-env-vars (the chart's default hands client-id, client-secret and cookie-secret to
the pod as env vars from secretKeyRef); the HelmRelease stalled, no pod ran, and every catalogue
request was a 500. Rule (rung 4, incident test): the chart rendered with the values the row ships
is admitted by the full policy set, and the same values with the chart's env-var wiring turned back
on are refused. BLIND without helm, kyverno, kubectl and the policy checkout; never green then."""
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
IDENTITY = ROOT / "platform" / "identity"


def _blind():
    for tool in ("kyverno", "helm", "kubectl"):
        if not shutil.which(tool):
            pytest.skip(f"BLIND: {tool} not installed")
    if not (POLICIES / "kustomization.yaml").exists():
        pytest.skip(f"BLIND: no policy checkout at {POLICIES} (set ESTATE_CODE)")


def _render(tmp_path, tag, override):
    docs = [d for d in yaml.safe_load_all((IDENTITY / "oauth2-proxy.yaml").read_text()) if d]
    hr = next(d for d in docs if d["kind"] == "HelmRelease")
    repo = next(d for d in docs if d["kind"] == "HelmRepository")
    spec = hr["spec"]["chart"]["spec"]
    values = dict(hr["spec"]["values"], **override)
    vf = tmp_path / f"values-{tag}.yaml"
    vf.write_text(yaml.safe_dump(values))
    r = subprocess.run(["helm", "template", hr["metadata"]["name"], spec["chart"], "--repo", repo["spec"]["url"],
                        "--version", spec["version"], "-n", hr["metadata"]["namespace"], "-f", str(vf)],
                       capture_output=True, text=True)
    if r.returncode:
        pytest.skip(f"BLIND: helm template failed (offline?): {r.stderr[-300:]}")
    out = tmp_path / f"{tag}.yaml"
    out.write_text(r.stdout)
    return out


def _fails(tmp_path, resource):
    policies = tmp_path / "policies.yaml"
    policies.write_text(subprocess.run(["kubectl", "kustomize", str(POLICIES)], check=True,
                                       capture_output=True, text=True).stdout)
    r = subprocess.run(["kyverno", "apply", str(policies), "--resource", str(resource)], capture_output=True, text=True)
    m = re.search(r"fail:\s*(\d+)", r.stdout)
    assert m, r.stdout[-500:] + r.stderr[-500:]
    return int(m.group(1)), r.stdout


def test_shipped_values_are_admitted_and_env_var_wiring_is_refused(tmp_path):
    _blind()
    good = _render(tmp_path, "shipped", {})
    n, out = _fails(tmp_path, good)
    assert n == 0, out[-1500:]
    bad = _render(tmp_path, "envvars", {"proxyVarsAsSecrets": True, "config": {"existingSecret": "oauth2-proxy", "configFile": ""}})
    n, out = _fails(tmp_path, bad)
    assert n > 0 and "secrets-not-from-env-vars" in out, out[-1500:]


def test_the_secret_reaches_the_pod_as_one_mounted_file():
    """No secretKeyRef env in the values; the ExternalSecret renders the config file the args name."""
    hr = next(d for d in yaml.safe_load_all((IDENTITY / "oauth2-proxy.yaml").read_text()) if d and d["kind"] == "HelmRelease")
    v = hr["spec"]["values"]
    assert v["proxyVarsAsSecrets"] is False and v["config"]["configFile"] == ""
    mount = next(m for m in v["extraVolumeMounts"] if m["name"] == "config")
    assert v["extraArgs"]["config"].startswith(mount["mountPath"] + "/")
    es = next(d for d in yaml.safe_load_all((IDENTITY / "external-secret.yaml").read_text()) if d)
    assert v["extraArgs"]["config"].rsplit("/", 1)[1] in es["spec"]["target"]["template"]["data"]
    assert next(x for x in v["extraVolumes"] if x["name"] == "config")["secret"]["secretName"] == es["spec"]["target"]["name"]

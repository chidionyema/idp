"""crew#227 CP4 (KINI spec 4.4): SPIRE runs on the estate cluster through Flux, not through a hand on a Mac.
Rung 2 properties over the manifests, rung 4 for the Kyverno refusal the chaos-mesh row already paid for:
  1. clusters/oke/platform.yaml carries a `spire` row that waits on the HelmRelease;
  2. the HelmRelease pins chart and version and reads its values from the one values.yaml through the
     generated ConfigMap (a value written twice drifts);
  3. SVIDs are short-lived (1h) and every pod is enrolled automatically (ClusterSPIFFEID default);
  4. the Kyverno exception lives in namespace kyverno, names only the SPIRE namespaces, waives only
     policies the rendered chart fails, and the same objects are still refused anywhere else.
"""
import pathlib
import re
import shutil
import subprocess

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPIRE = ROOT / "platform" / "spire"
ESTATE_CODE = pathlib.Path(__import__("os").environ.get("ESTATE_CODE", str(ROOT.parent)))
POLICIES = ESTATE_CODE / "prospector-main" / "deploy" / "k8s" / "policies"


def _docs(path):
    return [d for d in yaml.safe_load_all(pathlib.Path(path).read_text()) if d]


def _one(docs, kind, name):
    hits = [d for d in docs if d.get("kind") == kind and d["metadata"]["name"] == name]
    assert len(hits) == 1, (kind, name, len(hits))
    return hits[0]


def test_spire_row_waits_on_the_helmrelease():
    ks = _one(_docs(ROOT / "clusters/oke/platform.yaml"), "Kustomization", "spire")
    assert ks["spec"]["path"] == "./platform/spire" and ks["spec"]["wait"] is True
    hc = ks["spec"]["healthChecks"]
    assert {(h["kind"], h["name"], h["namespace"]) for h in hc} == {("HelmRelease", "spire", "spire-mgmt")}


def test_helmrelease_is_pinned_and_reads_the_one_values_file():
    docs = _docs(SPIRE / "helmrelease.yaml")
    hr = _one(docs, "HelmRelease", "spire")
    spec = hr["spec"]["chart"]["spec"]
    assert spec["chart"] == "spire" and re.fullmatch(r"\d+\.\d+\.\d+", str(spec["version"]))
    assert _one(docs, "HelmRelease", "spire-crds")["spec"]["chart"]["spec"]["chart"] == "spire-crds"
    assert "values" not in hr["spec"], "values live in values.yaml, not inline"
    assert hr["spec"]["valuesFrom"] == [{"kind": "ConfigMap", "name": "spire-values", "valuesKey": "values.yaml"}]
    kz = yaml.safe_load((SPIRE / "kustomization.yaml").read_text())
    gen = kz["configMapGenerator"][0]
    assert gen["name"] == "spire-values" and gen["files"] == ["values.yaml"]
    assert kz["generatorOptions"]["disableNameSuffixHash"] is True


def test_svids_are_short_lived_and_every_pod_is_enrolled():
    v = yaml.safe_load((SPIRE / "values.yaml").read_text())
    assert v["spire-server"]["defaultX509SvidTTL"] == "1h"
    assert v["spire-server"]["controllerManager"]["identities"]["clusterSPIFFEIDs"]["default"]["enabled"] is True
    assert v["global"]["spire"]["trustDomain"] == "estate.internal"


def test_exception_is_scoped_to_spire_namespaces_and_lives_in_kyverno():
    ex = _one(_docs(SPIRE / "exception.yaml"), "PolicyException", "spire")
    assert ex["metadata"]["namespace"] == "kyverno"
    ns = set(ex["spec"]["match"]["any"][0]["resources"]["namespaces"])
    assert ns == {"spire-mgmt", "spire-server", "spire-system"}


def _blind():
    for tool in ("kyverno", "helm", "kubectl"):
        if not shutil.which(tool):
            pytest.skip(f"BLIND: {tool} not on PATH")
    if not POLICIES.is_dir():
        pytest.skip(f"BLIND: policy set not at {POLICIES}")


def _render(tmp_path):
    docs = _docs(SPIRE / "helmrelease.yaml")
    hr = _one(docs, "HelmRelease", "spire")
    repo = _one(docs, "HelmRepository", "spiffe")
    spec = hr["spec"]["chart"]["spec"]
    r = subprocess.run(["helm", "template", "spire", spec["chart"], "--repo", repo["spec"]["url"],
                        "--version", str(spec["version"]), "-n", "spire-mgmt", "-f", str(SPIRE / "values.yaml")],
                       capture_output=True, text=True)
    if r.returncode:
        pytest.skip(f"BLIND: helm template failed (offline?): {r.stderr[-300:]}")
    out = tmp_path / "spire.yaml"
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


def test_incident_chaos_mesh_pattern_spire_admitted_with_its_exception_and_refused_without(tmp_path):
    _blind()
    rendered = _render(tmp_path)
    shipped = SPIRE / "exception.yaml"
    with_it = _apply(tmp_path, rendered, shipped)
    assert with_it["fail"] == 0 and with_it["skip"] > 0, with_it
    without = _apply(tmp_path, rendered)
    assert without["fail"] > 0
    waived = {e["policyName"] for e in _docs(shipped)[0]["spec"]["exceptions"]}
    assert waived == without["failing_policies"], {
        "waived_but_passing": waived - without["failing_policies"],
        "failing_but_not_waived": without["failing_policies"] - waived}
    elsewhere = tmp_path / "elsewhere.yaml"
    elsewhere.write_text(rendered.read_text().replace("namespace: spire-mgmt", "namespace: backstage")
                         .replace('namespace: "spire-mgmt"', "namespace: backstage"))
    still_refused = _apply(tmp_path, elsewhere, shipped)
    assert still_refused["fail"] == without["fail"], (still_refused, without)


def _host_network_pods(rendered):
    return sorted(f'{d["kind"]}/{d["metadata"]["name"]}' for d in _docs(rendered)
                  if d.get("kind") in ("DaemonSet", "Deployment", "StatefulSet", "Job")
                  and d["spec"]["template"]["spec"].get("hostNetwork", False))


def test_incident_crew227_cp4_host_network_pod_needs_the_host_ports_waiver(tmp_path):
    """Incident 2026-08-27 (oke-check 33035070500): all eight spire-agent pods were refused with
    `host-ports-none` although the offline render passed with the shipped exception. The API server
    defaults every containerPort of a hostNetwork pod to a hostPort; `kyverno apply` on a template
    never applies that defaulting, so the render cannot see the refusal. Rule (rung 4): a rendered
    pod on the host network is admitted only if disallow-host-ports is waived for it, and the shipped
    chart keeps the agent off the host network."""
    _blind()
    rendered = _render(tmp_path)
    waived = {e["policyName"] for e in _docs(SPIRE / "exception.yaml")[0]["spec"]["exceptions"]}
    assert _host_network_pods(rendered) == [], "spire-agent.hostNetwork must stay false in values.yaml"
    assert "disallow-host-ports" not in waived, "no host network, so no host-ports waiver either"
    # detector, both ways: the chart default (hostNetwork: true) is what the incident shipped
    stripped = tmp_path / "default.yaml"
    stripped.write_text(rendered.read_text().replace("      hostPID: true\n", "      hostPID: true\n      hostNetwork: true\n"))
    assert _host_network_pods(stripped) == ["DaemonSet/spire-agent"]

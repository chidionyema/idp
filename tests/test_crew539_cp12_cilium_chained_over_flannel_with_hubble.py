"""crew#539 CP12 (founder, 2026-08-27: "OKE CNI choice is measured first"). Measured: the
cluster was created with flannel and Oracle does not change a live cluster's CNI, so Cilium is
chained after flannel (generic-veth) and Hubble's metrics reach the central collector through the
k8s-infra annotation scraper. Proved offline, no sockets:
  1. the chaining config is a valid CNI conflist whose last plugin is cilium-cni in generic-veth
     mode and whose first is the CNI Terraform created the cluster with (platform/oci/main.tf);
  2. the HelmRelease chains (customConf on the same ConfigMap, flannel left in place) and puts
     the workload names on Hubble's flow metric on the port the agent pod is annotated with;
  3. the k8s-infra scraper preset is on with the annotation prefix the agent pod uses;
  4. the Flux row waits on edge (the waiver lives there) and health-checks the release;
  5. the receipt's radio-room names are the radio-room set of the Kyverno rule (crew#539 CP9).
bin/idp-kyverno-render platform/cilium is the admission half (pass 66, fail 0 on 2026-08-27).
"""
import json
import pathlib
import re

import yaml

IDP = pathlib.Path(__file__).resolve().parents[1]


def docs(rel):
    return [d for d in yaml.safe_load_all((IDP / rel).read_text()) if d]


def one(rel, kind, name=None):
    (d,) = [d for d in docs(rel) if d["kind"] == kind and (name is None or d["metadata"]["name"] == name)]
    return d


def test_chained_conflist_starts_with_the_cluster_cni_and_ends_with_cilium():
    tf = (IDP / "platform/oci/main.tf").read_text()
    cni = re.search(r'cni_type\s*=\s*"(\w+)"', tf).group(1)
    cm = one("platform/cilium/cni-configuration.yaml", "ConfigMap", "cni-configuration")
    assert cm["metadata"]["namespace"] == "kube-system"
    conf = json.loads(cm["data"]["cni-config"])
    plugins = conf["plugins"]
    assert plugins[0]["type"] == cni, plugins[0]
    assert plugins[-1] == {"type": "cilium-cni", "chaining-mode": "generic-veth"}


def test_release_chains_and_labels_hubble_flows_on_the_annotated_port():
    hr = one("platform/cilium/cilium.yaml", "HelmRelease", "cilium")
    v = hr["spec"]["values"]
    assert hr["metadata"]["namespace"] == "kube-system"
    assert v["cni"] == {"chainingMode": "generic-veth", "customConf": True, "configMap": "cni-configuration", "exclusive": False}
    assert v["routingMode"] == "native" and v["enableIPv4Masquerade"] is False and v["kubeProxyReplacement"] == "false"
    assert v["hubble"]["enabled"] is True
    port = v["hubble"]["metrics"]["port"]
    assert v["podAnnotations"] == {"signoz.io/scrape": "true", "signoz.io/port": str(port), "signoz.io/path": "/metrics"}
    flow = [m for m in v["hubble"]["metrics"]["enabled"] if m.startswith("flow:")]
    assert flow and "destination_workload" in flow[0] and "source_workload" in flow[0], flow
    for res in (v["resources"], v["initResources"], v["operator"]["resources"], v["hubble"]["relay"]["resources"]):
        assert res["requests"] == res["limits"], res
    assert v["envoy"]["enabled"] is False and v["operator"]["hostNetwork"] is False


def test_k8s_infra_scrapes_the_annotation_prefix_the_agent_uses():
    hr = one("platform/observability/k8s-infra.yaml", "HelmRelease", "k8s-infra")
    p = hr["spec"]["values"]["presets"]["prometheus"]
    assert p["enabled"] is True and p["annotationsPrefix"] == "signoz.io"


def test_flux_row_waits_on_edge_and_health_checks_the_release():
    row = one("clusters/oke/platform.yaml", "Kustomization", "cilium")
    assert row["spec"]["path"] == "./platform/cilium"
    assert {"name": "edge"} in row["spec"]["dependsOn"]
    assert row["spec"]["healthChecks"] == [{"apiVersion": "helm.toolkit.fluxcd.io/v2", "kind": "HelmRelease", "name": "cilium", "namespace": "kube-system"}]
    edge = yaml.safe_load((IDP / "platform/edge/kustomization.yaml").read_text())
    assert "cilium-exception.yaml" in edge["resources"]


def test_receipt_counts_flows_for_the_kyverno_radio_room_set():
    cm = one("platform/observability/telemetry-coverage.yaml", "ConfigMap", "telemetry-coverage-collect")
    src = cm["data"]["collect.py"]
    names = set(re.search(r'"RADIO_ROOM", "([^"]+)"', src).group(1).split(","))
    pol = one("platform/scheduling/require-priority-class.yaml", "ClusterPolicy")
    (rule,) = [r for r in pol["spec"]["rules"] if r["name"] == "radio-room-set-is-critical"]
    kyverno = set(rule["match"]["any"][0]["resources"]["names"])
    assert names <= kyverno, names - kyverno
    assert "hubble_flows_processed_total" in src and "destination_workload" in src
    grader = (IDP / "bin/idp-telemetry-coverage").read_text()
    assert 'kv.get("hubble_radio_flows", 0)) <= 0' in grader


def test_first_apply_recreates_the_radio_room_pods_so_zero_is_a_defect_not_a_startup_state():
    """Review at d4bb098 (09cd04a6): a pod gets a Cilium endpoint only when its sandbox is created
    after the agent is Ready, so without a rollout the receipt reads hubble_radio_flows=0 and the
    grader's FAIL fires against its own merge. The mechanism: the same Flux row ships a one-shot
    Job that waits for the agent DaemonSet, `rollout restart`s every radio-room Deployment the
    receipt counts, and blocks until each rollout is done — so a 0 after apply is a real miss."""
    assert "endpoint-rollout.yaml" in one("platform/cilium/kustomization.yaml", "Kustomization")["resources"]
    job = one("platform/cilium/endpoint-rollout.yaml", "Job", "cilium-endpoint-rollout")
    spec = job["spec"]["template"]["spec"]
    steps = [c["command"] for c in spec["initContainers"] + spec["containers"]]
    assert steps[0][:4] == ["kubectl", "rollout", "status", "daemonset/cilium"], "agent first"
    restarted = {a.split("/")[1] for s in steps if s[:3] == ["kubectl", "rollout", "restart"] for a in s if a.startswith("deployment/")}
    waited = {a.split("/")[1] for s in steps if s[:3] == ["kubectl", "rollout", "status"] for a in s if a.startswith("deployment/")}
    cm = one("platform/observability/telemetry-coverage.yaml", "ConfigMap", "telemetry-coverage-collect")
    counted = set(re.search(r'"RADIO_ROOM", "([^"]+)"', cm["data"]["collect.py"]).group(1).split(","))
    assert counted <= restarted and counted <= waited, (counted - restarted, counted - waited)
    assert all(c["securityContext"]["readOnlyRootFilesystem"] for c in spec["initContainers"] + spec["containers"])
    role = one("platform/cilium/endpoint-rollout.yaml", "ClusterRole", "cilium-endpoint-rollout")
    verbs = {v for r in role["rules"] if "deployments" in r["resources"] for v in r["verbs"]}
    assert "patch" in verbs and not verbs & {"delete", "create", "*"}, verbs

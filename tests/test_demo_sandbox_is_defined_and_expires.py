"""The buyer sandbox (crew#805 tier 3): defined, bounded, reachable, and mortal.

Every file that names this test (platform/sandbox/vcluster/kustomization.yaml,
docs/runbooks/demo-sandbox.md, clusters/oke/sandbox.yaml, .github/workflows/demo-sandbox.yml)
promised it existed; until 2026-09-06 it did not. Each test grades parsed structure (R76).
"""

import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
SANDBOX = ROOT / "platform/sandbox/vcluster"
LAUNCH = ROOT / "platform/sandbox/launch"
WORKFLOW = ROOT / ".github/workflows/demo-sandbox.yml"
TEMPLATE = ROOT / "backstage/templates/founder-actions/demo-sandbox/template.yaml"


def docs(path):
    return [d for d in yaml.safe_load_all(path.read_text()) if d]


def one(path, kind):
    found = [d for d in docs(path) if d.get("kind") == kind]
    assert len(found) == 1, f"{path} must carry exactly one {kind}"
    return found[0]


def test_the_control_plane_is_the_open_source_build_and_bounded():
    hr = one(SANDBOX / "helmrelease.yaml", "HelmRelease")
    sts = hr["spec"]["values"]["controlPlane"]["statefulSet"]
    assert "vcluster-oss" in sts["image"]["repository"]
    cpu = sts["resources"]["requests"]["cpu"]
    assert cpu.endswith("m") and int(cpu[:-1]) <= 250
    assert sts["persistence"]["volumeClaim"]["enabled"] is False


def test_the_area_stands_and_attaches_to_the_edge():
    ns = one(LAUNCH / "namespace.yaml", "Namespace")
    assert (
        ns["metadata"]["annotations"]["kustomize.toolkit.fluxcd.io/prune"] == "disabled"
    )
    assert ns["metadata"]["labels"]["idp.estate/edge-attach"] == "true"


def test_the_shop_is_reachable_on_a_zone_host_through_the_shared_gateway():
    route = one(LAUNCH / "httproute.yaml", "HTTPRoute")
    assert route["spec"]["hostnames"] == ["sandbox.${ESTATE_ZONE}"]
    (parent,) = route["spec"]["parentRefs"]
    assert (parent["name"], parent["namespace"], parent["sectionName"]) == (
        "prospector-edge",
        "prospector",
        "https-sandbox",
    )
    backend = route["spec"]["rules"][0]["backendRefs"][0]
    hr = one(SANDBOX / "helmrelease.yaml", "HelmRelease")
    seeded = list(
        yaml.safe_load_all(
            hr["spec"]["values"]["experimental"]["deploy"]["vcluster"]["manifests"]
        )
    )
    services = [d for d in seeded if d and d["kind"] == "Service"]
    assert len(services) == 1
    svc = services[0]
    # vCluster mirrors <name>-x-<namespace>-x-<vcluster> onto the host; the route must name that
    assert (
        backend["name"]
        == f"{svc['metadata']['name']}-x-{svc['metadata']['namespace']}-x-{hr['metadata']['name']}"
    )
    assert backend["port"] == svc["spec"]["ports"][0]["port"]
    policies = docs(SANDBOX / "network-policy.yaml")
    ingress = [p for p in policies if "Ingress" in p["spec"]["policyTypes"]]
    assert (
        ingress
        and ingress[0]["spec"]["ingress"][0]["ports"][0]["port"] == backend["port"]
    )


def test_the_seeded_page_is_dated_by_the_launch_row_not_typed():
    hr = one(SANDBOX / "helmrelease.yaml", "HelmRelease")
    manifests = hr["spec"]["values"]["experimental"]["deploy"]["vcluster"]["manifests"]
    for var in ("SANDBOX_EXPIRES_AT", "SANDBOX_HOLD"):
        assert "${" + var + "}" in manifests
        assert re.search(
            rf"^\s+{var}: \"\$expires\"|^\s+{var}: \"\$hold_was\"",
            WORKFLOW.read_text(),
            re.M,
        )


def test_the_folder_lists_every_file_and_the_root_never_applies_it():
    listed = set(
        yaml.safe_load((SANDBOX / "kustomization.yaml").read_text())["resources"]
    )
    assert listed == {p.name for p in SANDBOX.glob("*.yaml")} - {"kustomization.yaml"}
    for row in docs(ROOT / "clusters/oke" / "sandbox.yaml"):
        assert row["spec"]["path"] != "./platform/sandbox/vcluster"
    root = yaml.safe_load((ROOT / "clusters/oke/kustomization.yaml").read_text())
    assert "sandbox.yaml" in root["resources"]


def test_the_cluster_reads_the_branch_the_button_writes():
    source = one(LAUNCH / "gitrepository.yaml", "GitRepository")
    wf = yaml.safe_load(WORKFLOW.read_text())
    env = wf["jobs"]["sandbox"]["steps"][1]["env"]
    assert source["spec"]["ref"]["branch"] == env["BRANCH"]
    assert source["spec"]["interval"] == "1m"
    assert source["spec"]["url"] == "ssh://git@github.com/${ESTATE_GITHUB_REPO}"
    live = one(LAUNCH / "live.yaml", "Kustomization")
    assert live["spec"]["sourceRef"]["name"] == source["metadata"]["name"]
    assert live["spec"]["prune"] is True
    launcher = one(ROOT / "clusters/oke/sandbox.yaml", "Kustomization")
    assert launcher["spec"]["path"] == "./platform/sandbox/launch"
    assert launcher["spec"]["postBuild"]["substituteFrom"][0]["name"] == "estate-config"


def test_the_button_offers_launch_or_end_and_a_bounded_hold_and_sweeps_on_a_clock():
    wf = yaml.safe_load(WORKFLOW.read_text())
    on = wf[True]
    inputs = on["workflow_dispatch"]["inputs"]
    assert inputs["action"]["options"] == ["launch", "end"]
    assert (
        inputs["hold"]["options"] == ["1h", "4h"] and inputs["hold"]["default"] == "1h"
    )
    (cron,) = on["schedule"]
    minutes = cron["cron"].split()[0]
    assert minutes.startswith("*/") and int(minutes[2:]) <= 15
    assert wf["permissions"] == {"contents": "write"}
    head = WORKFLOW.read_text().splitlines()[:2]
    assert head[0].startswith("# button: ") and head[1].startswith("# founder: ")


def test_the_portal_button_is_generated_from_the_workflow():
    template = one(TEMPLATE, "Template")
    step = template["spec"]["steps"][0]
    assert step["input"]["workflowId"] == WORKFLOW.name
    props = template["spec"]["parameters"][0]["properties"]
    assert props["action"]["enum"] == ["launch", "end"]
    assert props["hold"]["enum"] == ["1h", "4h"]


def test_the_sweep_ends_an_expired_hold_and_leaves_a_live_one():
    run = yaml.safe_load(WORKFLOW.read_text())["jobs"]["sandbox"]["steps"][1]["run"]
    arms = re.findall(r"^\s+(\w+)\)", run, re.M)
    assert arms == ["launch", "end", "sweep"]
    sweep = run.split("sweep)", 1)[1]
    assert "state=idle" in sweep and "nothing to sweep" in sweep

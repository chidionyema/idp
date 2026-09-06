"""The buyer sandbox (crew#805 tier 3): defined, bounded, reachable, and mortal.

The guarantees here are graded where the values land, not where they are typed: the two
sandbox folders are rendered with kustomize (the same build Flux runs) and every claim is
asserted on the rendered objects; the button workflow's launch script must parse under
bash -n; the portal button is proved by running the generator in --check mode, not by
reading its output file. Pin readers: platform/sandbox/vcluster/kustomization.yaml,
docs/runbooks/demo-sandbox.md, clusters/oke/sandbox.yaml, .github/workflows/demo-sandbox.yml.
"""

import pathlib
import os
import re
import subprocess
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
SANDBOX = ROOT / "platform/sandbox/vcluster"
LAUNCH = ROOT / "platform/sandbox/launch"
WORKFLOW = ROOT / ".github/workflows/demo-sandbox.yml"


def render(path):
    """What Flux will apply: kustomize build, parsed into documents."""
    proc = subprocess.run(
        ["kustomize", "build", str(path)],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    return [d for d in yaml.safe_load_all(proc.stdout) if d]


def docs(path):
    return [d for d in yaml.safe_load_all(path.read_text()) if d]


def one(found, kind):
    got = [d for d in found if d.get("kind") == kind]
    assert len(got) == 1, f"expected exactly one {kind}, rendered {len(got)}"
    return got[0]


def helmrelease():
    return one(render(SANDBOX), "HelmRelease")


def seeded():
    hr = helmrelease()
    return [
        d
        for d in yaml.safe_load_all(
            hr["spec"]["values"]["experimental"]["deploy"]["vcluster"]["manifests"]
        )
        if d
    ]


def test_the_control_plane_is_the_open_source_build_and_bounded():
    hr = helmrelease()
    sts = hr["spec"]["values"]["controlPlane"]["statefulSet"]
    assert "vcluster-oss" in sts["image"]["repository"]
    cpu = sts["resources"]["requests"]["cpu"]
    assert cpu.endswith("m") and int(cpu[:-1]) <= 250
    assert sts["persistence"]["volumeClaim"]["enabled"] is False


def test_the_area_stands_and_attaches_to_the_edge():
    ns = one(render(LAUNCH), "Namespace")
    assert (
        ns["metadata"]["annotations"]["kustomize.toolkit.fluxcd.io/prune"] == "disabled"
    )
    assert ns["metadata"]["labels"]["idp.estate/edge-attach"] == "true"


def test_the_shop_is_reachable_on_a_zone_host_through_the_shared_gateway():
    route = one(render(LAUNCH), "HTTPRoute")
    assert route["spec"]["hostnames"] == ["sandbox.${ESTATE_ZONE}"]
    assert route["metadata"]["annotations"]["idp.estate/auth"] == "public-demo-page"
    (parent,) = route["spec"]["parentRefs"]
    assert (parent["name"], parent["namespace"], parent["sectionName"]) == (
        "prospector-edge",
        "prospector",
        "https-sandbox",
    )
    backend = route["spec"]["rules"][0]["backendRefs"][0]
    hr = helmrelease()
    services = [d for d in seeded() if d["kind"] == "Service"]
    assert len(services) == 1
    svc = services[0]
    # vCluster mirrors <name>-x-<namespace>-x-<vcluster> onto the host; the route must name that
    assert (
        backend["name"]
        == f"{svc['metadata']['name']}-x-{svc['metadata']['namespace']}-x-{hr['metadata']['name']}"
    )
    assert backend["port"] == svc["spec"]["ports"][0]["port"]
    policies = [d for d in render(SANDBOX) if d["kind"] == "NetworkPolicy"]
    ingress = [p for p in policies if "Ingress" in p["spec"]["policyTypes"]]
    assert (
        ingress
        and ingress[0]["spec"]["ingress"][0]["ports"][0]["port"] == backend["port"]
    )


def test_the_seeded_page_is_dated_by_the_launch_row_not_typed():
    manifests = helmrelease()["spec"]["values"]["experimental"]["deploy"]["vcluster"][
        "manifests"
    ]
    for var in ("SANDBOX_EXPIRES_AT", "SANDBOX_HOLD"):
        assert "${" + var + "}" in manifests
        assert re.search(
            rf"^\s+{var}: \"\$expires\"|^\s+{var}: \"\$hold_was\"",
            WORKFLOW.read_text(),
            re.M,
        )


def test_the_folders_list_every_file_and_the_root_never_applies_the_sandbox():
    for folder in (SANDBOX, LAUNCH):
        listed = set(
            yaml.safe_load((folder / "kustomization.yaml").read_text())["resources"]
        )
        assert listed == {p.name for p in folder.glob("*.yaml")} - {
            "kustomization.yaml"
        }
    for row in docs(ROOT / "clusters/oke" / "sandbox.yaml"):
        assert row["spec"]["path"] != "./platform/sandbox/vcluster"
    root = yaml.safe_load((ROOT / "clusters/oke/kustomization.yaml").read_text())
    assert "sandbox.yaml" in root["resources"]


def test_the_cluster_reads_the_branch_the_button_writes():
    source = one(render(LAUNCH), "GitRepository")
    wf = yaml.safe_load(WORKFLOW.read_text())
    env = wf["jobs"]["sandbox"]["steps"][1]["env"]
    assert source["spec"]["ref"]["branch"] == env["BRANCH"]
    assert source["spec"]["interval"] == "1m"
    assert source["spec"]["url"] == "ssh://git@github.com/${ESTATE_GITHUB_REPO}"
    live = one(render(LAUNCH), "Kustomization")
    assert live["spec"]["sourceRef"]["name"] == source["metadata"]["name"]
    assert live["spec"]["prune"] is True
    launcher = one(docs(ROOT / "clusters/oke/sandbox.yaml"), "Kustomization")
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


def test_the_portal_button_is_generated_and_current(tmp_path=None):
    proc = subprocess.run(
        [sys.executable, str(ROOT / "bin/idp-portal-buttons"), "--check"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_the_seed_is_admitted_like_any_host_pod():
    # The estate admits the mirrored pods like any other (first launch, 2026-09-06):
    # probes and a read-only root on the shop, RuntimeDefault seccomp on the chart's coredns.
    (shop,) = [d for d in seeded() if d["kind"] == "Deployment"]
    container = shop["spec"]["template"]["spec"]["containers"][0]
    assert container["securityContext"]["readOnlyRootFilesystem"] is True
    assert "livenessProbe" in container and "readinessProbe" in container
    security = helmrelease()["spec"]["values"]["controlPlane"]["coredns"]["security"]
    assert security["podSecurityContext"]["seccompProfile"]["type"] == "RuntimeDefault"
    assert (
        security["containerSecurityContext"]["seccompProfile"]["type"]
        == "RuntimeDefault"
    )


def test_the_launch_rows_substitution_parses_over_the_build():
    # The demo-sandbox row lives on branch sandbox/launch, so no committed Kustomization
    # covers it: this is the substitution Flux runs for it, with the row's own variables.
    env = dict(os.environ, SANDBOX_EXPIRES_AT="2030-01-01T00:00:00Z", SANDBOX_HOLD="1h")
    build = subprocess.run(
        ["kustomize", "build", str(SANDBOX)],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    proc = subprocess.run(
        ["flux", "envsubst", "--strict"],
        input=build.stdout,
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert "2030-01-01T00:00:00Z" in proc.stdout


def test_the_sweep_ends_an_expired_hold_and_leaves_a_live_one(tmp_path):
    run = yaml.safe_load(WORKFLOW.read_text())["jobs"]["sandbox"]["steps"][1]["run"]
    # The launch script must be a script: bash refuses a broken heredoc or a dangling case.
    script = tmp_path / "launch.sh"
    script.write_text(run)
    proc = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    arms = re.findall(r"^\s+(\w+)\)", run, re.M)
    assert arms == ["launch", "end", "sweep"]
    sweep = run.split("sweep)", 1)[1]
    assert "state=idle" in sweep and "nothing to sweep" in sweep

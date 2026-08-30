"""crew#561: Otto in the cluster has every capability it had on the Mac, and each one is a graded
row, never a sentence.

Incident, 2026-08-30 16:5xZ: the founder asked why Otto's full powers were not delivered. Seven
boxes were open; the lane had shipped a write-up and a parity check, and the check itself was a
playbook a person had to dispatch. Measured that turn (run 33324430400): gateway, tailnet,
mac-run, memory and model lane all green -- and nothing said so on a schedule; CP1 (workspace),
CP2 (scoped ServiceAccount) and CP3 (estate MCP) had no row and no manifest.

Rung 2 properties over the checkout (no cluster):
  - the Deployment runs as a namespaced ServiceAccount bound to a Role in its own namespace, and
    no ClusterRoleBinding names that ServiceAccount;
  - the estate MCP key reaches the pod's env dir from the gateway's own vault entry, not a second
    one;
  - the otto-parity playbook grades CP1, CP2, CP3 and CP5 as `step` rows (a `show` is not a grade);
  - the parity is a scheduled workflow whose cron is the catalogue's and the dispatcher's, in one
    concurrency group with oke-check's dispatches.
"""

from __future__ import annotations

import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
HA = ROOT / "platform" / "hermes-agent"


def _docs(path: pathlib.Path):
    return [d for d in yaml.safe_load_all(path.read_text(encoding="utf-8")) if d]


def test_the_pod_reads_the_cluster_as_a_namespaced_service_account():
    rbac = {(d["kind"], d["metadata"]["name"]): d for d in _docs(HA / "rbac.yaml")}
    assert ("ServiceAccount", "hermes-agent") in rbac
    role = rbac[("Role", "hermes-agent-reader")]
    assert role["metadata"]["namespace"] == "hermes-agent"
    verbs = {v for r in role["rules"] for v in r["verbs"]}
    assert verbs <= {"get", "list", "watch"}, verbs
    binding = rbac[("RoleBinding", "hermes-agent-reader")]
    assert binding["subjects"] == [
        {"kind": "ServiceAccount", "name": "hermes-agent", "namespace": "hermes-agent"}
    ]
    assert not any(d["kind"] == "ClusterRoleBinding" for d in rbac.values())
    deploy = next(d for d in _docs(HA / "gateway.yaml") if d["kind"] == "Deployment")
    spec = deploy["spec"]["template"]["spec"]
    assert spec["serviceAccountName"] == "hermes-agent"
    assert spec["automountServiceAccountToken"] is True
    assert (
        "rbac.yaml"
        in yaml.safe_load((HA / "kustomization.yaml").read_text())["resources"]
    )


def test_the_estate_mcp_key_is_the_gateways_own_and_reaches_the_env_dir():
    es = _docs(HA / "mcp-key.yaml")[0]
    assert es["kind"] == "ExternalSecret"
    (row,) = es["spec"]["data"]
    assert row["secretKey"] == "ESTATE_MCP_KEY"
    assert row["remoteRef"] == {"key": "mcp-gateway", "property": "MCP_GATEWAY_KEY"}
    gateway_es = next(
        d
        for d in _docs(ROOT / "platform" / "mcp" / "external-secret.yaml")
        if d["kind"] == "ExternalSecret"
    )
    assert gateway_es["spec"]["dataFrom"][0]["extract"]["key"] == "mcp-gateway"
    deploy = next(d for d in _docs(HA / "gateway.yaml") if d["kind"] == "Deployment")
    env = next(
        v for v in deploy["spec"]["template"]["spec"]["volumes"] if v["name"] == "env"
    )
    assert {"name": "hermes-agent-mcp", "optional": True} in [
        s["secret"] for s in env["projected"]["sources"]
    ]
    assert (
        "mcp-key.yaml"
        in yaml.safe_load((HA / "kustomization.yaml").read_text())["resources"]
    )


def test_every_crew561_capability_is_a_graded_row_of_the_parity_playbook():
    src = (ROOT / "bin" / "idp-oke-break-glass").read_text(encoding="utf-8")
    body = src[src.index("pb_otto_parity() {") :]
    body = body[: body.index("\n}\n")]
    rows = set(re.findall(r"^\s+step ([a-z0-9-]+) ", body, re.M))
    for row in (
        "gateway-ready",
        "tailnet-up",
        "mac-run-hostname",
        "hindsight-answers",
        "model-lane-is-router",
        "repo-workspace",
        "sa-reads-own-namespace",
        "sa-blind-elsewhere",
        "estate-mcp-answers",
        "estate-state-read-at-start",
    ):
        assert row in rows, row
    assert "show model-lane " not in body, "the model lane is graded, not listed"
    assert "mcp.mumchimp.com" not in body, (
        "the MCP URL comes from the pod's config (LAW 46)"
    )


def test_the_parity_is_on_the_estates_clock_in_one_group_with_oke_check():
    wf = yaml.safe_load(
        (ROOT / ".github" / "workflows" / "otto-parity.yml").read_text(encoding="utf-8")
    )
    cron = wf[True]["schedule"][0]["cron"]
    row = next(
        r
        for r in yaml.safe_load((ROOT / "drills" / "catalogue.yaml").read_text())[
            "drills"
        ]
        if r["name"] == "otto-parity"
    )
    assert (
        row["schedule"] == cron
        and row["workflow"] == "otto-parity.yml"
        and row["owner"]
    )
    dispatcher = (ROOT / "platform" / "drills" / "drill-dispatcher.yaml").read_text(
        encoding="utf-8"
    )
    assert "otto-parity.yml=" + cron.replace(" ", "_") in dispatcher
    assert wf["concurrency"]["group"] == "oke-check-workflow_dispatch"
    step = wf["jobs"]["parity"]["steps"][-1]
    assert step["env"]["BREAK_GLASS_PLAYBOOK"] == "otto-parity"
    assert "PASS  break-glass otto-parity" in step["run"]

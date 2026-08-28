"""crew#539 CP4: the node pool grows and shrinks by itself, under the cap the founder wrote.

Three facts, each read from the file that carries it (never a proxy):
  1. the Deployment's --nodes max equals estate-defaults node_pool.max_nodes and the min is 1;
  2. no file in the row or the Terraform names an OCID (the pool id travels through the vault);
  3. the Terraform hands the pool's size to the autoscaler (ignore_initial_pool_size) AND moves the
     resource address, so the live pool is never destroyed to get there.
Plus the policy: base plus burst under the cap passes, a full-month burst is refused.
"""
import json
import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ROW = ROOT / "platform" / "oci" / "autoscaler"
OCID = re.compile(r"ocid1\.[a-z]+\.oc1\.")


def _docs():
    return list(yaml.safe_load_all((ROW / "cluster-autoscaler.yaml").read_text()))


def _deployment():
    return next(d for d in _docs() if d["kind"] == "Deployment")


def test_nodes_flag_min_is_one_and_max_is_estate_defaults_max_nodes():
    defaults = yaml.safe_load((ROOT / "estate-defaults.yaml").read_text())["node_pool"]
    cmd = _deployment()["spec"]["template"]["spec"]["containers"][0]["command"]
    nodes = [a for a in cmd if a.startswith("--nodes=")]
    assert nodes, cmd  # crew#539 CP10 adds a second line for the preemptible pool; the first is the on-demand pool
    lo, hi, pool = nodes[0].split("=", 1)[1].split(":")
    assert lo == "1" and int(hi) == defaults["max_nodes"] and defaults["max_nodes"] >= 2
    assert pool == "$(NODEPOOL_ID)", "the pool id comes from the vault-fed Secret, never a literal"
    assert "--cloud-provider=oci" in cmd


def test_row_is_wired_and_names_no_ocid():
    for f in [*ROW.glob("*.yaml"), ROOT / "platform" / "oci" / "autoscaler.tf", ROOT / "bin" / "idp-autoscaler-seed"]:
        assert not OCID.search(f.read_text()), f
    es = next(d for d in yaml.safe_load_all((ROW / "external-secret.yaml").read_text()))
    assert es["spec"]["dataFrom"][0]["extract"]["key"] == "oke-autoscaler"
    env = {e["name"]: e for e in _deployment()["spec"]["template"]["spec"]["containers"][0]["env"]}
    assert env["NODEPOOL_ID"]["valueFrom"]["secretKeyRef"] == {"name": "oke-autoscaler", "key": "NODEPOOL_ID"}
    assert env["OCI_USE_INSTANCE_PRINCIPAL"]["value"] == "true"
    rows = [d for d in yaml.safe_load_all((ROOT / "clusters" / "oke" / "platform.yaml").read_text()) if d and d["metadata"]["name"] == "autoscaler"]
    assert len(rows) == 1 and rows[0]["spec"]["path"] == "./platform/oci/autoscaler"
    assert {"name": "secret-store"} in rows[0]["spec"]["dependsOn"]
    assert rows[0]["spec"]["healthChecks"][0]["name"] == "cluster-autoscaler"


def test_terraform_hands_size_over_and_moves_the_pool_instead_of_recreating_it():
    main = (ROOT / "platform" / "oci" / "main.tf").read_text()
    pool = main[main.index("a1 = {"):]
    assert re.search(r"ignore_initial_pool_size\s*=\s*true", pool) and re.search(r"\bautoscale\s*=\s*true", pool)
    auto = (ROOT / "platform" / "oci" / "autoscaler.tf").read_text()
    assert re.search(r'moved\s*\{\s*from\s*=\s*module\.oke\.module\.workers\[0\]\.oci_containerengine_node_pool\.tfscaled_workers\["a1"\]\s*to\s*=\s*module\.oke\.module\.workers\[0\]\.oci_containerengine_node_pool\.autoscaled_workers\["a1"\]', auto)
    for verb in ["manage cluster-node-pools", "manage instance-family", "use subnets", "read virtual-network-family", "use vnics", "inspect compartments"]:
        assert verb in auto, verb
    assert "in tenancy" not in auto


def test_apply_seeds_the_pool_id_after_tofu():
    wf = (ROOT / ".github" / "workflows" / "oke-check.yml").read_text()
    assert "bin/idp-autoscaler-seed" in wf
    assert wf.index("bin/idp-oke-rebuild --") < wf.index("bin/idp-autoscaler-seed")


def _conftest(fixture):
    return subprocess.run(["conftest", "test", "--parser", "json", "-p", str(ROOT / "policy" / "node_pool.rego"), str(fixture)], capture_output=True, text=True).returncode


def test_policy_prices_the_burst_under_the_same_cap():
    fx = ROOT / "policy" / "fixtures"
    assert _conftest(fx / "capacity-burst-under-cap.json") == 0
    assert _conftest(fx / "capacity-burst-over-cap.json") != 0
    under = json.loads((fx / "capacity-burst-under-cap.json").read_text())["capacity"]
    defaults = yaml.safe_load((ROOT / "estate-defaults.yaml").read_text())["node_pool"]
    assert under["burst"]["max_nodes"] == defaults["max_nodes"]
    assert under["burst"]["hours_monthly"] == defaults["burst_hours_monthly"]

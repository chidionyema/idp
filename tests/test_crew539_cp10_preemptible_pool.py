"""crew#539 CP10: a preemptible pool the autoscaler grows from zero, priced under the one cap, and
an admission rule that keeps the radio-room set off it.

Facts, each read from the file that carries it:
  1. main.tf carries a second pool a1-spot: preemptible enabled, size 0, autoscaled, labelled
     estate.io/capacity=preemptible; the on-demand pool is labelled on-demand.
  2. the Deployment's second --nodes line is 0:<estate-defaults spot_max_nodes>:$(SPOT_NODEPOOL_ID)
     and the id comes from the vault-fed Secret; bin/idp-autoscaler-seed writes that key.
  3. the Kyverno rule: infrastructure-critical pods get a REQUIRED NotIn [preemptible] (never In
     [on-demand]: the running node has no label), everything else a PREFERRED In [preemptible].
  4. policy: base + burst + spot under the cap passes, a long spot month is refused, and a spot
     price at or above on-demand is refused.
"""
import json
import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "platform" / "oci" / "main.tf").read_text()
OCID = re.compile(r"ocid1\.[a-z]+\.oc1\.")


def _pool(key):
    start = MAIN.index(f"{key} = {{")
    return MAIN[start:MAIN.index("\n    }", start)]


def _deployment():
    docs = yaml.safe_load_all((ROOT / "platform" / "oci" / "autoscaler" / "cluster-autoscaler.yaml").read_text())
    return next(d for d in docs if d["kind"] == "Deployment")


def test_spot_pool_is_preemptible_from_zero_and_labelled():
    spot = _pool("a1-spot")
    assert re.search(r"preemptible_config\s*=\s*\{\s*enable\s*=\s*true", spot)
    assert re.search(r"\bsize\s*=\s*0\b", spot) and re.search(r"\bautoscale\s*=\s*true", spot)
    assert re.search(r"ignore_initial_pool_size\s*=\s*true", spot)
    assert '"estate.io/capacity" = "preemptible"' in spot
    assert '"estate.io/capacity" = "on-demand"' in _pool("a1")
    assert not OCID.search(MAIN)


def test_autoscaler_grows_the_spot_pool_from_zero_to_the_founder_number():
    defaults = yaml.safe_load((ROOT / "estate-defaults.yaml").read_text())["node_pool"]
    c = _deployment()["spec"]["template"]["spec"]["containers"][0]
    nodes = [a for a in c["command"] if a.startswith("--nodes=")]
    assert len(nodes) == 2, nodes
    lo, hi, pool = nodes[1].split("=", 1)[1].split(":")
    assert lo == "0" and int(hi) == defaults["spot_max_nodes"] >= 1
    assert pool == "$(SPOT_NODEPOOL_ID)"
    env = {e["name"]: e for e in c["env"]}
    assert env["SPOT_NODEPOOL_ID"]["valueFrom"]["secretKeyRef"] == {"name": "oke-autoscaler", "key": "SPOT_NODEPOOL_ID"}
    seed = (ROOT / "bin" / "idp-autoscaler-seed").read_text()
    assert "SPOT_NODEPOOL_ID=SPOT_NODEPOOL_ID" in seed and "a1-spot" in seed and not OCID.search(seed)


def test_radio_room_is_kept_off_preemptible_and_the_rest_prefer_it():
    pol = yaml.safe_load((ROOT / "platform" / "scheduling" / "capacity-affinity.yaml").read_text())
    rules = {r["name"]: r for r in pol["spec"]["rules"]}
    off = rules["radio-room-stays-off-preemptible"]
    assert off["preconditions"]["all"][0]["value"] == "infrastructure-critical"
    req = off["mutate"]["patchStrategicMerge"]["spec"]["affinity"]["nodeAffinity"]["requiredDuringSchedulingIgnoredDuringExecution"]
    expr = req["nodeSelectorTerms"][0]["matchExpressions"][0]
    assert expr == {"key": "estate.io/capacity", "operator": "NotIn", "values": ["preemptible"]}, "In [on-demand] would strand the radio room on the unlabelled running node"
    pref = rules["everything-else-prefers-preemptible"]["mutate"]["patchStrategicMerge"]["spec"]["affinity"]["nodeAffinity"]["preferredDuringSchedulingIgnoredDuringExecution"]
    assert pref[0]["preference"]["matchExpressions"][0] == {"key": "estate.io/capacity", "operator": "In", "values": ["preemptible"]}
    assert "capacity-affinity.yaml" in (ROOT / "platform" / "scheduling" / "kustomization.yaml").read_text()


def _conftest(fixture):
    return subprocess.run(["conftest", "test", "--parser", "json", "-p", str(ROOT / "policy" / "node_pool.rego"), str(fixture)], capture_output=True, text=True).returncode


def test_policy_prices_spot_under_the_same_cap_and_refuses_a_spot_price_at_on_demand(tmp_path):
    fx = ROOT / "policy" / "fixtures"
    assert _conftest(fx / "capacity-spot-under-cap.json") == 0
    assert _conftest(fx / "capacity-spot-over-cap.json") != 0
    under = json.loads((fx / "capacity-spot-under-cap.json").read_text())
    defaults = yaml.safe_load((ROOT / "estate-defaults.yaml").read_text())["node_pool"]
    assert under["capacity"]["spot"]["max_nodes"] == defaults["spot_max_nodes"]
    assert under["capacity"]["spot"]["hours_monthly"] == defaults["spot_hours_monthly"]
    assert under["capacity"]["spot"]["node_usd_hr"] == under["capacity"]["burst"]["node_usd_hr"] / 2
    bad = json.loads(json.dumps(under))
    bad["capacity"]["spot"]["node_usd_hr"] = bad["capacity"]["burst"]["node_usd_hr"]
    p = tmp_path / "spot-at-on-demand.json"
    p.write_text(json.dumps(bad))
    assert _conftest(p) != 0

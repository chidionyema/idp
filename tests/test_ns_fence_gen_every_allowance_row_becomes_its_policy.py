"""crew#102 (founder, 2026-09-06): the flannel-to-Calico cutover turned the namespace fences on
for the first time, and every public site answered 504 for the better part of an hour.
Founder record: ~/.claude/docs/founder/2026-09-06T2037Z-the-gateway-timeout-504-confirms-that-calico-is-fac00c2b.md
Report: docs/reference/incidents/2026-09-06-calico-cutover-blacked-out-every-public-site.md

The fences had been written as a default-deny floor plus declared holes while flannel enforced
nothing, so no hole had ever been exercised. Three flows were missing and each cost one round of
504 or 10-second pages: the public listeners of the gateway, pods reaching each other inside a
namespace, and the storefront's fetch of its own public API name. Each is now something the
generator emits from allowances.yaml, and this test holds the generator to it.
"""

import importlib.machinery
import importlib.util
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _gen():
    path = ROOT / "bin" / "idp-ns-fence-gen"
    loader = importlib.machinery.SourceFileLoader("idp_ns_fence_gen", str(path))
    spec = importlib.util.spec_from_loader("idp_ns_fence_gen", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def _by_name(docs):
    return {d["metadata"]["name"]: d["spec"] for d in docs}


def test_every_namespace_gets_the_same_namespace_hole():
    spec = _by_name(_gen().policy_docs("anything", {}))["allow-same-namespace"]
    assert spec["podSelector"] == {}
    assert spec["ingress"] == [{"from": [{"podSelector": {}}]}]
    assert spec["egress"] == [{"to": [{"podSelector": {}}]}]


def test_ingress_public_opens_only_the_declared_ports_to_everyone():
    docs = _by_name(_gen().policy_docs("edge", {"ingress_public": [8443, 8000, 8000]}))
    rule = docs["allow-public-ingress"]["ingress"][0]
    assert rule["from"] == [{"ipBlock": {"cidr": "0.0.0.0/0"}}]
    assert [p["port"] for p in rule["ports"]] == [8000, 8443]
    assert "allow-public-ingress" not in _by_name(_gen().policy_docs("edge", {}))


def test_egress_internet_keeps_every_private_range_cut_out():
    gen = _gen()
    rule = _by_name(gen.policy_docs("prospector", {"egress_internet": [443]}))[
        "allow-internet-egress"
    ]["egress"][0]
    block = rule["to"][0]["ipBlock"]
    assert block["cidr"] == "0.0.0.0/0"
    assert set(block["except"]) == set(gen.NOT_THE_INTERNET)
    assert [p["port"] for p in rule["ports"]] == [443]


def test_the_checked_in_fences_carry_the_three_flows_the_outage_lacked():
    flows = yaml.safe_load((ROOT / "platform/ns-fences/allowances.yaml").read_text())[
        "flows"
    ]
    assert set(flows["edge"]["ingress_public"]) == {8000, 8443}
    assert "edge" in flows["prospector"]["ingress_from"]
    assert flows["prospector"]["egress_internet"] == [443]
    live = _by_name(
        list(
            yaml.safe_load_all(
                (ROOT / "platform/ns-fences/network/prospector.yaml").read_text()
            )
        )
    )
    assert {"default-deny-all", "allow-same-namespace", "allow-internet-egress"} <= set(
        live
    )
